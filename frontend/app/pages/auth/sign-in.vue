<script setup lang="ts">
import { computed, ref } from 'vue'
import { navigateTo, useSupabaseClient, useSupabaseUser } from '#imports'
import { useAuth } from '~/stores/useAuth'

const supabase = useSupabaseClient()
const user = useSupabaseUser()
const auth = useAuth()
const route = useRoute()
const requestedRole = computed(() => {
  if (route.query.role === 'clinician') return 'Clinician'
  if (route.query.role === 'patient') return 'Patient'
  return null
})

if (user.value) {
  await navigateTo('/')
}

const email = ref('')
const password = ref('')
const loading = ref(false)
const message = ref('')

async function onSubmit() {
  loading.value = true
  message.value = ''

  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.value,
      password: password.value
    })

    if (error) {
      message.value = error.message
      return
    }

    const userId = data.user?.id
    if (!userId) {
      await navigateTo('/auth/pending-approval')
      return
    }

    if (await auth.isClinician(userId)) {
      await navigateTo('/clincian')
      return
    }

    await navigateTo(await auth.isPatient(userId) ? '/patient' : '/auth/pending-approval')
  } catch (error: any) {
    message.value = error?.message ?? 'Sign-in failed.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="mx-auto max-w-md cv-card cv-animate-fade-up">
    <p class="cv-kicker">{{ requestedRole ? `${requestedRole} Access` : 'Clinivue Access' }}</p>
    <h1 class="cv-title">{{ requestedRole ? `${requestedRole} Sign In` : 'Welcome Back' }}</h1>
    <p class="cv-subtitle">Sign in to continue to your care workflow.</p>

    <form class="mt-6 grid gap-4" @submit.prevent="onSubmit">
      <div>
        <label class="cv-label" for="email">Email</label>
        <input id="email" v-model="email" class="cv-input" type="email" required autocomplete="email">
      </div>

      <div>
        <label class="cv-label" for="password">Password</label>
        <input id="password" v-model="password" class="cv-input" type="password" required autocomplete="current-password">
      </div>

      <button class="cv-btn mt-1" type="submit" :disabled="loading || !email || !password">
        {{ loading ? 'Signing in...' : 'Sign in' }}
      </button>

      <p v-if="message" class="cv-error">{{ message }}</p>

      <div class="mt-1 flex items-center justify-between text-sm">
        <NuxtLink class="cv-link" to="/auth/sign-up">Need access?</NuxtLink>
      </div>
    </form>
  </section>
</template>
