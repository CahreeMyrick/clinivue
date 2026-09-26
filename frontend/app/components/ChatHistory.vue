<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage } from '~/types/chat'

const props = defineProps<{
  messages: ChatMessage[]
}>()

const history = ref<HTMLElement | null>(null)
const isNearBottom = ref(true)

function updateScrollState() {
  const element = history.value
  if (!element) return
  isNearBottom.value = element.scrollHeight - element.scrollTop - element.clientHeight < 96
}

async function scrollToBottom(force = false) {
  await nextTick()
  const element = history.value
  if (!element || (!force && !isNearBottom.value)) return
  element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
}

watch(() => props.messages.length, () => scrollToBottom())
</script>

<template>
  <div
    ref="history"
    class="min-h-72 max-h-[32rem] space-y-4 overflow-y-auto px-5 py-6 sm:px-8"
    aria-live="polite"
    @scroll="updateScrollState"
  >
    <div v-if="!messages.length" class="flex min-h-60 items-center justify-center text-center">
      <div class="max-w-sm">
        <div class="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-teal-200 bg-teal-50 text-sm font-bold text-teal-800" aria-hidden="true">CV</div>
        <h2 class="font-['Space_Grotesk'] text-lg font-semibold text-slate-900">Your conversation starts here</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">Send a message to begin a conversation.</p>
      </div>
    </div>

    <article
      v-for="message in messages"
      :key="message.id"
      class="flex gap-3"
      :class="message.sender === 'user' ? 'justify-end' : 'justify-start'"
    >
      <div
        class="max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm"
        :class="message.sender === 'user' ? 'rounded-br-sm bg-teal-700 text-white' : 'rounded-bl-sm border border-teal-100 bg-[#f7fcfc] text-slate-800'"
      >
        <div v-if="message.loading" class="flex items-center gap-2 text-slate-500">
          <span class="h-2 w-2 animate-pulse rounded-full bg-teal-600" />
          <span>Thinking...</span>
        </div>
        <p v-else class="whitespace-pre-wrap">{{ message.text }}</p>

        <div v-if="message.imageUrls?.length" class="mt-3 grid grid-cols-2 gap-2">
          <img
            v-for="(imageUrl, index) in message.imageUrls"
            :key="`${message.id}-image-${index}`"
            class="aspect-square w-full rounded-lg object-cover"
            :src="imageUrl"
            :alt="`Attached image ${index + 1}`"
          >
        </div>

        <p v-if="message.error" class="mt-2 text-xs text-rose-700">Unable to get a response. Please try again.</p>
      </div>
    </article>

    <button
      v-if="messages.length && !isNearBottom"
      class="sticky bottom-2 left-1/2 mx-auto block rounded-full border border-teal-200 bg-white px-3 py-1 text-xs font-semibold text-teal-800 shadow-sm"
      type="button"
      @click="scrollToBottom(true)"
    >
      Newest message
    </button>
  </div>
</template>