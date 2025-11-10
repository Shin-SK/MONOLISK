// src/utils/roles.js
import { computed } from 'vue'
import { useUser } from '@/stores/useUser'

export function useRoleGate() {
  const u = useUser()
  const role = computed(() => u.me?.current_role || null)
  const isSuper = computed(() => !!u.me?.is_superuser)
  function hasRole(allowed = []) {
    if (isSuper.value) return true
    return allowed.includes(role.value)
  }
  return { role, isSuper, hasRole }
}
