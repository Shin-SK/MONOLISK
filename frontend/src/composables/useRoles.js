// useRoles.js
import { computed } from 'vue'
import { useUser } from '@/stores/useUser'

export function useRoles() {
  const u = useUser()
  const role    = computed(() => u.me?.current_role || null)
  const isSuper = computed(() => !!u.me?.is_superuser)
  const claims  = computed(() => u.me?.claims || [])

  // ★ UI用：superでも “現在ロール” を基準に判定
  const hasRole = (allowed = []) => {
    if (!Array.isArray(allowed) || allowed.length === 0) return true
    return allowed.includes(role.value)
  }

  // ★ ルーター用：superは常に通す（今までの挙動）
  const hasRoleOrSuper = (allowed = []) => {
    if (isSuper.value) return true
    return hasRole(allowed)
  }

  const can = (need = []) => need.every(c => claims.value.includes(c))

  const homePath = () => {
    switch (role.value) {
      case 'cast':    return '/cast/mypage'
      case 'owner':   return '/owner/dashboard'
      case 'staff':
      case 'manager': return '/dashboard'
      default:        return '/dashboard'
    }
  }

  return { role, isSuper, claims, hasRole, hasRoleOrSuper, can, homePath }
}
