<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: File[]
  maxImages?: number
  maxFileSizeMb?: number
}>(), {
  modelValue: () => [],
  maxImages: 10,
  maxFileSizeMb: 5
})

const emit = defineEmits<{
  'update:modelValue': [files: File[]]
  error: [message: string]
}>()

const input = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const previews = ref<Array<{ file: File; url: string }>>([])

const remainingSlots = computed(() => Math.max(props.maxImages - props.modelValue.length, 0))
const canAddImages = computed(() => remainingSlots.value > 0)

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

watch(() => props.modelValue, (files) => {
  syncPreviews(files)
}, { immediate: true })

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function addFiles(fileList: FileList | File[]) {
  if (!canAddImages.value) {
    emit('error', `You can add up to ${props.maxImages} images.`)
    return
  }

  const incomingFiles = Array.from(fileList)
  const acceptedFiles: File[] = []
  const maxBytes = props.maxFileSizeMb * 1024 * 1024

  for (const file of incomingFiles) {
    if (!file.type.startsWith('image/')) {
      emit('error', `${file.name} is not an image file.`)
      continue
    }

    if (file.size > maxBytes) {
      emit('error', `${file.name} is larger than ${props.maxFileSizeMb} MB.`)
      continue
    }

    const alreadySelected = props.modelValue.some((selected) => selected.name === file.name && selected.size === file.size)
    const alreadyAccepted = acceptedFiles.some((accepted) => accepted.name === file.name && accepted.size === file.size)
    if (!alreadySelected && !alreadyAccepted) {
      acceptedFiles.push(file)
    }
  }

  const availableFiles = acceptedFiles.slice(0, remainingSlots.value)
  if (acceptedFiles.length > availableFiles.length) {
    emit('error', `You can add up to ${props.maxImages} images.`)
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
      class="rounded-xl border-2 border-dashed p-4 text-center transition-colors"
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
      <p class="text-sm font-semibold text-slate-800">Drop images here</p>
      <p class="mt-1 text-xs text-slate-500">JPEG, PNG, or WebP up to {{ maxFileSizeMb }} MB each</p>
      <button
        class="cv-btn cv-btn-secondary mt-3 text-sm"
        type="button"
        :disabled="!canAddImages"
        @click="input?.click()"
      >
        {{ canAddImages ? 'Choose images' : 'Image limit reached' }}
      </button>
      <p class="mt-2 text-xs text-slate-500">{{ modelValue.length }} of {{ maxImages }} images selected</p>
    </div>

    <div v-if="previews.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <div v-for="(preview, index) in previews" :key="`${preview.file.name}-${preview.file.size}-${index}`" class="group overflow-hidden rounded-xl border border-teal-100 bg-white shadow-sm">
        <div class="relative flex aspect-[4/3] items-center justify-center overflow-hidden bg-slate-100 p-1">
          <img class="h-full w-full rounded-lg object-contain" :src="preview.url" :alt="preview.file.name">
          <span class="absolute left-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-slate-900/75 text-xs font-bold text-white">{{ index + 1 }}</span>
          <button
            class="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-lg leading-none text-slate-700 shadow-sm transition hover:bg-rose-50 hover:text-rose-700"
            type="button"
            :aria-label="`Remove ${preview.file.name}`"
            @click="removeFile(index)"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="min-w-0 border-t border-teal-50 px-3 py-2">
          <p class="truncate text-xs font-semibold text-slate-800" :title="preview.file.name">{{ preview.file.name }}</p>
          <p class="mt-0.5 text-[11px] text-slate-500">{{ formatFileSize(preview.file.size) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>