<script setup lang="ts">
import { ref } from 'vue'
import { useRuntimeConfig, useSupabaseClient } from '#imports'

const supabase = useSupabaseClient()
const config = useRuntimeConfig()

const email = ref('')
const loading = ref(false)
const errorMessage = ref('')
const sent = ref(false)

function getBaseUrl(): string {
  if (typeof window !== 'undefined' && window.location?.origin) return window.location.origin

  const fromConfig = config.public.appBaseUrl
  return fromConfig || 'http://localhost:3000'
}

async function onSubmit() {
  loading.value = true
  errorMessage.value = ''

  try {
    const redirectTo = `${getBaseUrl()}/auth/reset-password`
    const { error } = await supabase.auth.resetPasswordForEmail(email.value, { redirectTo })

    if (error) {
      errorMessage.value = error.message
      return
    }

    sent.value = true
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="mx-auto max-w-lg cv-card cv-animate-fade-up">
    <template v-if="sent">
      <p class="cv-kicker">Recovery Email Sent</p>
      <h1 class="cv-title">Check Your Inbox</h1>
      <p class="cv-subtitle">If an account exists for this email, a reset link is on its way.</p>
      <NuxtLink class="cv-link mt-4 inline-block" to="/auth/sign-in">Back to sign in</NuxtLink>
    </template>

    <template v-else>
      <p class="cv-kicker">Account Recovery</p>
      <h1 class="cv-title">Forgot Your Password?</h1>
      <p class="cv-subtitle">Enter your email and we will send a secure reset link.</p>

      <form class="mt-6 grid gap-4" @submit.prevent="onSubmit">
        <div>
          <label class="cv-label" for="email">Email</label>
          <input id="email" v-model="email" class="cv-input" type="email" required autocomplete="email">
        </div>

        <button class="cv-btn mt-1" type="submit" :disabled="loading || !email">
          {{ loading ? 'Sending...' : 'Send reset link' }}
        </button>

        <p v-if="errorMessage" class="cv-error">{{ errorMessage }}</p>
      </form>

      <p class="mt-5">
        <NuxtLink class="cv-link" to="/auth/sign-in">Back to sign in</NuxtLink>
      </p>
    </template>
  </section>
</template>
