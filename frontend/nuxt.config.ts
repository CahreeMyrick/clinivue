// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: ['@nuxtjs/supabase', '@nuxtjs/tailwindcss', '@pinia/nuxt'],
  css: ['~/assets/css/tailwind.css'],
  supabase: {
    url: process.env.NUXT_PUBLIC_SUPABASE_URL,
    key: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY,
    types: '~~/types/supabase.ts',
    redirectOptions: {
      login: '/auth/sign-in',
      callback: '/',
      exclude: [
        '/auth/sign-in',
        '/auth/sign-up',
        '/auth/forgot-password',
        '/auth/reset-password',
        '/auth/pending-approval',
        '/auth/deactivated',
        '/auth/invite',
        '/public/surveys',
        '/public/surveys/*'
      ]
    }
  },
  runtimeConfig: {
    public: {
      appBaseUrl: process.env.NUXT_PUBLIC_APP_BASE_URL || 'http://localhost:3000'
    }
  },
  typescript: {
    strict: true
  }
})
