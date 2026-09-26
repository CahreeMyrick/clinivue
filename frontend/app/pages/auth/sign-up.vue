<script setup lang="ts">
import { ref } from 'vue'
import { navigateTo, useSupabaseClient } from '#imports'
import { useAuth } from '~/stores/useAuth'
type UserRole = 'clinician' | 'patient'

const auth = useAuth()
const supabase = useSupabaseClient()
const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const selectedRole = ref<UserRole | ''>('')
const loading = ref(false)
const errorMessage = ref('')
const notice = ref('')

async function onSubmit() {
  errorMessage.value = ''
  notice.value = ''

  if (!selectedRole.value) {
    errorMessage.value = 'Choose whether you are signing up as a clinician or patient.'
    return
  }

  loading.value = true

  try {
    const { data, error } = await supabase.auth.signUp({
      email: email.value.trim(),
      password: password.value,
      options: {
        data: {
          first_name: firstName.value.trim().toLowerCase(),
          last_name: lastName.value.trim().toLowerCase(),
          role: selectedRole.value
        }
      }
    })
    if (error) {
      errorMessage.value = error
      return
    }

    if (!data.session || !data.user) {
      notice.value = 'Your account request was received, but no active session was returned. Check your email confirmation settings or sign in if the account already exists.'
      return
    }

    const savedRole = await auth.loadRole(data.user.id)
    if (savedRole !== selectedRole.value) {
      errorMessage.value = 'Your account was created, but its role could not be verified. Please contact support before continuing.'
      return
    }

    await navigateTo(savedRole === 'clinician' ? '/clincian' : '/patient')
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Account creation failed.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="mx-auto max-w-xl cv-card cv-animate-fade-up">
    <p class="cv-kicker">Join Clinivue</p>
    <h1 class="cv-title">Create Your Account</h1>
    <p class="cv-subtitle">Choose your care role and enter your details to get started.</p>

    <form class="mt-6 grid gap-4" @submit.prevent="onSubmit">
      <fieldset>
        <legend class="cv-label">I am signing up as a</legend>
        <div class="mt-2 grid grid-cols-2 gap-3">
          <label
            class="cursor-pointer rounded-xl border p-3 transition-colors"
            :class="selectedRole === 'clinician' ? 'border-teal-700 bg-teal-50' : 'border-teal-100 bg-white hover:bg-teal-50/50'"
          >
            <input v-model="selectedRole" class="sr-only" type="radio" name="role" value="clinician" required>
            <span class="block text-sm font-bold text-slate-900">Clinician</span>
            <span class="mt-1 block text-xs text-slate-600">I provide care</span>
          </label>
          <label
            class="cursor-pointer rounded-xl border p-3 transition-colors"
            :class="selectedRole === 'patient' ? 'border-teal-700 bg-teal-50' : 'border-teal-100 bg-white hover:bg-teal-50/50'"
          >
            <input v-model="selectedRole" class="sr-only" type="radio" name="role" value="patient" required>
            <span class="block text-sm font-bold text-slate-900">Patient</span>
            <span class="mt-1 block text-xs text-slate-600">I receive care</span>
          </label>
        </div>
      </fieldset>

      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="cv-label" for="first-name">First name</label>
          <input id="first-name" v-model="firstName" class="cv-input" type="text" autocomplete="given-name" required>
        </div>
        <div>
          <label class="cv-label" for="last-name">Last name</label>
          <input id="last-name" v-model="lastName" class="cv-input" type="text" autocomplete="family-name" required>
        </div>
      </div>

      <div>
        <label class="cv-label" for="email">Email</label>
        <input id="email" v-model="email" class="cv-input" type="email" autocomplete="email" required>
      </div>

      <div>
        <label class="cv-label" for="password">Password</label>
        <input id="password" v-model="password" class="cv-input" type="password" autocomplete="new-password" required>
      </div>

      <button class="cv-btn mt-1" type="submit" :disabled="loading || !selectedRole || !firstName.trim() || !lastName.trim() || !email || !password">
        {{ loading ? 'Creating account...' : 'Create account' }}
      </button>

      <p v-if="errorMessage" class="cv-error" role="alert">{{ errorMessage }}</p>
      <p v-if="notice" class="cv-subtitle" role="status">{{ notice }}</p>

      <p class="text-sm text-slate-600">
        Already have an account?
        <NuxtLink class="cv-link" to="/auth/sign-in">Sign in</NuxtLink>
      </p>
    </form>
  </section>
</template>
