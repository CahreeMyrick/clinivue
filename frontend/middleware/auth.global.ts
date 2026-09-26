import { defineNuxtRouteMiddleware, navigateTo, useSupabaseClient, useSupabaseUser } from '#imports'
import { useAuth } from '~~/stores'
const PUBLIC_PATH_PREFIXES = [
  '/auth/sign-in',
  '/auth/sign-up',
  '/auth/pending-approval',
  '/auth/deactivated',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/invite',
  '/public/surveys'
]

export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/') return

  if (PUBLIC_PATH_PREFIXES.some((prefix) => to.path.startsWith(prefix))) {
    return
  }

  const {supabase, user} = useAuth()

  if (user?.id) return

  const { data } = await supabase.auth.getSession()
  if (!data.session) return navigateTo('/auth/sign-in')
})
