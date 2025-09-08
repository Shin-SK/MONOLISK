// src/composables/useRoles.js
import { computed } from 'vue'
import { useUser } from '@/stores/useUser'

export function useRoles() {
  const u = useUser()
  const role    = computed(() => u.me?.current_role || null)   // 'cast'|'staff'|'manager'|'owner'|null
  const isSuper = computed(() => !!u.me?.is_superuser)

  // 画面/ルート制御用：superuserは常に通す
  const hasRole = (allowed = []) => {
    if (isSuper.value) return true
    if (!Array.isArray(allowed) || allowed.length === 0) return true
    return allowed.includes(role.value)
  }

  // ホーム遷移：superuserでも current_role を優先
	const homePath = () => {
	switch (role.value) {
		case 'cast':
		return '/cast/mypage'
		case 'owner':
		return '/owner/dashboard'
		case 'staff':
		case 'manager':
		default:
		return '/dashboard'
	}
	}

  return { role, isSuper, hasRole, homePath }
}
