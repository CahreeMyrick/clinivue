<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { ChatMessage } from '~/types/chat'
import { createChatActions } from './_sendMessage'

const imageError = ref('')
const messages = ref<ChatMessage[]>([])
const conversationId = crypto.randomUUID()
const chatEndpoint = '' //TODO: Replace with actual chat endpoint URL in Backend

const { sendMessage, loadHistory, cleanup } = createChatActions({
  messages,
  imageError,
  conversationId,
  chatEndpoint
})

function onImageError(message: string) {
  imageError.value = message
}

onMounted(() => {
  void loadHistory()
})

onBeforeUnmount(() => {
  cleanup()
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
        <p class="cv-kicker">Medical Conversations Made Easy</p>
        <h1 class="cv-title mt-2 text-3xl">What can we help with?</h1>
      </div>

      <section aria-label="Chat" class="cv-card overflow-hidden p-0">
        <ChatHistory :messages="messages" />
        <ChatComposer @submit="sendMessage" @image-error="onImageError" />
        <p v-if="imageError" class="cv-error bg-[#f7fcfc] px-5 pb-4 text-center" role="alert">{{ imageError }}</p>
      </section>
    </section>
  </main>
</template>
