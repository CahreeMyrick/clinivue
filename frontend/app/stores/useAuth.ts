// app/stores/useAuth.ts
import { defineStore, skipHydrate } from 'pinia'
import { computed, ref, watch } from 'vue'
import type { PostgrestSingleResponse } from '@supabase/supabase-js'
import { useSupabaseClient, useSupabaseUser } from '#imports'
import type { Database } from '~~/types/supabase'

type UserProfileRow = Database['public']['Tables']['user_profile']['Row']
type UserRole = Database['public']['Enums']['user_role'] | null

export const useAuth = defineStore('auth', () => {
  // ✅ Pass Database to the client so .from() is typed properly
  // ✅ Wrap with skipHydrate to prevent serialization errors during SSR
  const sb = skipHydrate(useSupabaseClient<Database>())
  const user = useSupabaseUser()

  const fullName = ref<string>('')
  const avatarPath = ref<string | null>(null)
  const avatarSignedUrl = ref<string>('https://placehold.co/40x40?text=U')
  const loading = ref<boolean>(false)
  const role = ref<UserRole>(null)
  const loadingRole = ref(false)

  watch(() => user.value?.id, () => {
    role.value = null
  })

  function profile() {
    // infer Update/Insert/Row from Database
    return sb.from('user_profile')
  }

  async function loadRole(userId?: string): Promise<UserRole> {
    const targetUserId = userId ?? user.value?.id
    if (!targetUserId) {
      role.value = null
      return null
    }

    loadingRole.value = true
    const { data, error } = await profile()
      .select('role')
      .eq('id', targetUserId)
      .single()
    loadingRole.value = false

    if (error) {
      role.value = null
      return null
    }

    role.value = data.role
    return role.value
  }

  async function isClinician(userId?: string): Promise<boolean> {
    return (await loadRole(userId)) === 'clinician'
  }

  async function isPatient(userId?: string): Promise<boolean> {
    return (await loadRole(userId)) === 'patient'
  }

  async function loadProfile() {
    if (!user.value) return
    loading.value = true

    const { data, error }: PostgrestSingleResponse<UserProfileRow> = await profile()
      .select('full_name, avatar_url')
      .eq('id', user.value.id)
      .single()

    if (!error && data) {
      fullName.value = data.full_name || ''
      avatarPath.value = data.avatar_url || null
      await refreshAvatarSignedUrl()
    }

    loading.value = false
  }

  async function refreshAvatarSignedUrl() {
    if (!avatarPath.value) return
    const { data } = await sb
      .storage
      .from('profile-avatars')
      .createSignedUrl(avatarPath.value, 60 * 60 * 24 * 365)
    if (data?.signedUrl) avatarSignedUrl.value = data.signedUrl
  }

  async function updateFullName(name: string) {
    if (!user.value) return
    // ✅ Update payload now matches Database.public.Tables.user_profile.Update
    await profile()
      .update({ full_name: name || null })
      .eq('id', user.value.id)
    fullName.value = name
  }

  async function uploadAvatar(file: File) {
    if (!user.value) return
    const ext = (file.name.split('.').pop() || 'jpg').toLowerCase()
    const path = `${user.value.id}/avatar.${ext}`

    await sb.storage
      .from('profile-avatars')
      .upload(path, file, { upsert: true, cacheControl: '3600', contentType: file.type })

    await profile()
      .update({ avatar_url: path })
      .eq('id', user.value.id)

    avatarPath.value = path
    await refreshAvatarSignedUrl()
  }

  async function signOut() {
    await sb.auth.signOut()
    fullName.value = ''
    avatarPath.value = null
    avatarSignedUrl.value = 'https://placehold.co/40x40?text=U'
    role.value = null
  }

  return {
    sb, user, loading,
    fullName, avatarPath, avatarSignedUrl, role, loadingRole, isPatient, isClinician,
    loadProfile, loadRole, refreshAvatarSignedUrl,
    updateFullName, uploadAvatar, signOut
  }
})
