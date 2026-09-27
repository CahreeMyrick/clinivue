<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: File[]
  maxTotalSizeMb?: number
}>(), {
  modelValue: () => [],
  maxTotalSizeMb: 500
})

const emit = defineEmits<{
  'update:modelValue': [files: File[]]
  error: [message: string]
}>()

const input = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const previews = ref<Array<{ file: File; url: string }>>([])

const maxTotalBytes = computed(() => props.maxTotalSizeMb * 1024 * 1024)
const totalBytes = computed(() => props.modelValue.reduce((total, file) => total + file.size, 0))
const remainingBytes = computed(() => Math.max(maxTotalBytes.value - totalBytes.value, 0))
const canAddImages = computed(() => remainingBytes.value > 0)

function syncPreviews(files: File[]) {
  const activeFiles = new Set(files)

  for (const preview of previews.value) {
    if (!activeFiles.has(preview.file)) URL.revokeObjectURL(preview.url)
  }

  previews.value = previews.value.filter((preview) => activeFiles.has(preview.file))

  for (const file of files) {
    if (!previews.value.some((preview) => preview.file === file)) {
      previews.value.push({ file, url: URL.createObjectURL(file) })
    }
  }
}

watch(() => props.modelValue, (files) => syncPreviews(files), { immediate: true })

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function addFiles(fileList: FileList | File[]) {
  if (!canAddImages.value) {
    emit('error', `You have reached the ${props.maxTotalSizeMb} MB image limit.`)
    return
  }

  const acceptedFiles: File[] = []

  for (const file of Array.from(fileList)) {
    if (!file.type.startsWith('image/')) {
      emit('error', `${file.name} is not an image file.`)
      continue
    }

    const alreadySelected = props.modelValue.some((selected) => selected.name === file.name && selected.size === file.size)
    const alreadyAccepted = acceptedFiles.some((accepted) => accepted.name === file.name && accepted.size === file.size)
    if (!alreadySelected && !alreadyAccepted) acceptedFiles.push(file)
  }

  const availableFiles: File[] = []
  let bytesLeft = remainingBytes.value

  for (const file of acceptedFiles) {
    if (file.size > bytesLeft) continue
    availableFiles.push(file)
    bytesLeft -= file.size
  }

  if (availableFiles.length < acceptedFiles.length) {
    emit('error', `Some images were skipped because the total limit is ${props.maxTotalSizeMb} MB.`)
  }

  const nextFiles = [...props.modelValue, ...availableFiles]
  emit('update:modelValue', nextFiles)
  syncPreviews(nextFiles)
}

function onInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) addFiles(target.files)
  target.value = ''
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files) addFiles(event.dataTransfer.files)
}

function removeFile(index: number) {
  const nextFiles = props.modelValue.filter((_, fileIndex) => fileIndex !== index)
  emit('update:modelValue', nextFiles)
  syncPreviews(nextFiles)
}

onBeforeUnmount(() => {
  for (const preview of previews.value) URL.revokeObjectURL(preview.url)
})
</script>

<template>
  <div class="grid gap-3">
    <div
      class="flex items-center gap-3 rounded-lg border border-dashed px-3 py-2.5 transition-colors"
      :class="isDragging ? 'border-teal-600 bg-teal-50' : 'border-teal-200 bg-white hover:border-teal-400'"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input
        ref="input"
        class="sr-only"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        @change="onInputChange"
      >
      <div class="min-w-0 flex-1">
        <p class="truncate text-xs font-semibold text-slate-800">Drag and drop or select from computer</p>
        <p class="truncate text-[11px] text-slate-500">{{ modelValue.length }} images · {{ formatFileSize(totalBytes) }} / {{ maxTotalSizeMb }} MB used</p>
      </div>
      <button
        class="cv-upload-button shrink-0"
        type="button"
        :disabled="!canAddImages"
        @click="input?.click()"
      >
        <span aria-hidden="true" class="mr-1 text-base leading-none">+</span>
        {{ canAddImages ? 'Add image' : 'Full' }}
      </button>
    </div>

    <div v-if="previews.length" class="grid grid-cols-3 gap-2 sm:grid-cols-5">
      <div v-for="(preview, index) in previews" :key="`${preview.file.name}-${preview.file.size}-${index}`" class="overflow-hidden rounded-lg border border-teal-100 bg-white shadow-sm">
        <div class="relative flex aspect-square items-center justify-center overflow-hidden bg-slate-100 p-0.5">
          <img class="h-full w-full rounded-md object-cover" :src="preview.url" :alt="preview.file.name">
          <span class="absolute bottom-1 left-1 flex h-5 w-5 items-center justify-center rounded-full bg-slate-900/75 text-[10px] font-bold text-white">{{ index + 1 }}</span>
          <button
            class="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/90 text-base leading-none text-slate-700 shadow-sm transition hover:bg-rose-50 hover:text-rose-700"
            type="button"
            :aria-label="`Remove ${preview.file.name}`"
            @click="removeFile(index)"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="min-w-0 border-t border-teal-50 px-2 py-1.5">
          <p class="truncate text-[11px] font-semibold text-slate-800" :title="preview.file.name">{{ preview.file.name }}</p>
          <p class="text-[10px] text-slate-500">{{ formatFileSize(preview.file.size) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
