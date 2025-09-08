// src/composables/useProfile.js
import { computed } from 'vue'
import { useUser } from '@/stores/useUser'

export function useProfile() {
  const user = useUser()
  const displayName = computed(() =>
    user.me?.display_name ??
    user.me?.stage_name ??
    user.me?.username ??
    user.name ?? 'Guest'
  )
  const avatarURL = computed(() =>
    user.me?.avatar_url            // meに追加したURL（最優先）
    ?? user.me?.profile_image      // 互換
    ?? user.avatar_url             // 旧store互換（URL）
    ?? user.avatar                 // 旧store互換（public_id）
    ?? ''
  )
  return { displayName, avatarURL }
}
