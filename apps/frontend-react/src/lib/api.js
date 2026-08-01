import axios from 'axios'
import { createAuthRefreshQueue } from './authRefreshQueue.js'

const API_BASE =
  import.meta.env?.VITE_API_URL ||
  import.meta.env?.VITE_API_BASE_URL ||
  import.meta.env?.VITE_VALUEUP_API_BASE_URL ||
  (import.meta.env?.DEV ? 'http://localhost:8000' : '/api')

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const refreshQueue = createAuthRefreshQueue({
  refreshAccessToken: async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) throw new Error('no_refresh')
    try {
      const { data } = await axios.post(`${API_BASE}/v1/auth/refresh`, {
        refresh_token: refresh,
      })
      localStorage.setItem('access_token', data.access_token)
      // Server rotates refresh (L024). Without this, the next 401 burns a
      // blacklisted refresh_token and forces logout.
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      return data.access_token
    } catch (error) {
      // Another tab may have already rotated; reuse its tokens if present.
      const latestRefresh = localStorage.getItem('refresh_token')
      const latestAccess = localStorage.getItem('access_token')
      if (latestRefresh && latestRefresh !== refresh && latestAccess) {
        return latestAccess
      }
      throw error
    }
  },
  onRefreshFailed: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.dispatchEvent(new Event('auth:logout'))
  },
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true
      try {
        const accessToken = await refreshQueue.runSingleFlight()
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${accessToken}`
        return api(original)
      } catch {
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export default api
