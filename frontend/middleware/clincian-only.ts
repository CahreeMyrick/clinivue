import { defineNuxtRouteMiddleware, navigateTo, useSupabaseClient } from '#imports'
import { useAuth } from '~/stores/useAuth'

export default defineNuxtRouteMiddleware(async () => {
  const auth = useAuth()

  const userId = auth.user?.id
  if (!userId) {
    return navigateTo('/auth/sign-in')
  }

  if (await auth.isClinician(userId)) return

  if (auth.role === 'patient') return navigateTo('/patient')

  return navigateTo('/auth/pending-approval')
})