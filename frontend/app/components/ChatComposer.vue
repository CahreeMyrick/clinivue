<script setup lang="ts">
import { ref } from 'vue'
import type { ChatComposerPayload } from '~/types/chat'

const emit = defineEmits<{
  submit: [payload: ChatComposerPayload]
  imageError: [message: string]
}>()

const text = ref('')
const images = ref<File[]>([])

function submit() {
  const message = text.value.trim()
  if (!message && !images.value.length) return

  emit('submit', { text: message, images: images.value })
  text.value = ''
  images.value = []
}
</script>

<template>
  <form class="border-t border-teal-100 bg-[#f7fcfc] p-4 sm:p-5" @submit.prevent="submit">
    <label class="sr-only" for="chat-message">Message your care team</label>
    <textarea
      id="chat-message"
      v-model="text"
      class="cv-input min-h-24 resize-y"
      placeholder="Write a message to your care team..."
      rows="3"
    />
    <div class="mt-4">
      <ImageUploader v-model="images" @error="emit('imageError', $event)" />
    </div>
    <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
      <p class="text-xs text-slate-500">Shift+Enter adds a new line.</p>
      <button class="cv-btn" type="submit" :disabled="!text.trim() && !images.length">Send</button>
    </div>
  </form>
</template>