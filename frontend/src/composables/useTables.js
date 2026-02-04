import api from '@/api.js'

/**
 * fetchTables(params) => Promise<array>
 * 薄いラッパー：配列返却を保証
 */
export async function fetchTables(params = {}) {
  const { data } = await api.get('/billing/tables/', { params })
  return Array.isArray(data) ? data : (data.results || [])
}
