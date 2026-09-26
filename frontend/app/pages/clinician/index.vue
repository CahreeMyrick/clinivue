<script setup lang="ts">
definePageMeta({
  middleware: ['clincian-only']
})

const {user} = useAuth()
</script>

<template>
  <main class="mx-auto max-w-2xl cv-card cv-animate-fade-up">
    <p class="cv-kicker">Clinician Workspace</p>
    <h1 class="cv-title">Clinician Area</h1>
    <p class="cv-subtitle">Only approved clinician or platform-admin users should land on this route.</p>

    <div class="mt-6 cv-card-soft">
      <p class="text-sm text-slate-600">Current user</p>
      <p class="mt-1 break-all text-sm font-semibold text-slate-800">{{ user?.email || 'unknown' }}</p>
    </div>

    <NuxtLink class="cv-link mt-5 inline-block" to="/">Back home</NuxtLink>
  </main>
</template>
