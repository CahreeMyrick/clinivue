<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { ChatComposerPayload, ChatMessage } from '~/types/chat'

const imageError = ref('')
const messages = ref<ChatMessage[]>([])
const conversationId = crypto.randomUUID()
const chatEndpoint = ''

function onImageError(message: string) {
  imageError.value = message
}

function createId() {
  return crypto.randomUUID()
}

function addImageUrls(files: File[]) {
  return files.map((file) => URL.createObjectURL(file))
}

async function sendMessage(payload: ChatComposerPayload) {
  imageError.value = ''
  const imageUrls = addImageUrls(payload.images)
  const userMessage: ChatMessage = {
    id: createId(),
    sender: 'user',
    text: payload.text,
    imageUrls,
    createdAt: new Date().toISOString()
  }
  const loadingId = createId()
  messages.value.push(userMessage, {
    id: loadingId,
    sender: 'assistant',
    text: '',
    createdAt: new Date().toISOString(),
    loading: true
  })

  if (!chatEndpoint) {
    messages.value = messages.value.map((message) => message.id === loadingId
      ? { ...message, loading: false, error: true, text: '' }
      : message)
    return
  }

  try {
    const formData = new FormData()
    formData.append('conversationId', conversationId)
    formData.append('text', payload.text)
    payload.images.forEach((file) => formData.append('images', file))

    const response = await $fetch<{ message?: { text?: string } | string; text?: string }>(chatEndpoint, {
      method: 'POST',
      body: formData
    })
    const responseText = typeof response.message === 'string'
      ? response.message
      : response.message?.text ?? response.text ?? ''

    messages.value = messages.value.map((message) => message.id === loadingId
      ? { ...message, loading: false, text: responseText }
      : message)
  } catch {
    messages.value = messages.value.map((message) => message.id === loadingId
      ? { ...message, loading: false, error: true }
      : message)
  }
}

onMounted(() => {
  if (!chatEndpoint) return
  void $fetch<ChatMessage[]>(`${chatEndpoint}/history`, { query: { conversationId } })
    .then((history) => { messages.value = history })
})

onBeforeUnmount(() => {
  messages.value.flatMap((message) => message.imageUrls ?? []).forEach((url) => URL.revokeObjectURL(url))
})
</script>

<template>
  <main class="mx-auto max-w-4xl cv-animate-fade-up">
    <header class="mb-10 flex flex-wrap items-center justify-between gap-4">
      <NuxtLink to="/" class="font-['Space_Grotesk'] text-xl font-bold text-slate-900">Clinivue</NuxtLink>
      <nav aria-label="Sign in" class="flex flex-wrap gap-2">
        <NuxtLink class="cv-btn cv-btn-secondary text-sm" :to="{ path: '/auth/sign-in'}">Sign in</NuxtLink>
        <NuxtLink class="cv-btn cv-btn-secondary text-sm" :to="{ path: '/auth/sign-up' }">Sign up</NuxtLink>
      </nav>
    </header>

    <section class="mx-auto max-w-3xl">
      <div class="mb-7 text-center">
        <p class="cv-kicker">A calmer way to connect</p>
        <h1 class="cv-title mt-2 text-3xl">What can we help with?</h1>
        <p class="cv-subtitle">Start a conversation with your care team.</p>
      </div>

      <section aria-label="Chat" class="cv-card overflow-hidden p-0">
        <ChatHistory :messages="messages" />
        <ChatComposer @submit="sendMessage" @image-error="onImageError" />
        <p v-if="imageError" class="cv-error bg-[#f7fcfc] px-5 pb-4 text-center" role="alert">{{ imageError }}</p>
      </section>
    </section>
  </main>
</template>
