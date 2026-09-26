import { defineNuxtRouteMiddleware, navigateTo } from '#imports'
import { useAuth } from '~/stores/useAuth'

export default defineNuxtRouteMiddleware(async () => {
  const auth = useAuth()
  const userId = auth.user?.id
  if (!userId) {
    return navigateTo('/auth/sign-in')
  }

  if (await auth.isPatient(userId)) return

  if (auth.role === 'clinician') return navigateTo('/clincian')

  return navigateTo('/auth/pending-approval')
})