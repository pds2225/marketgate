import axios from 'axios'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_VALUEUP_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : '/api')

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let _refreshing = false

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry && !_refreshing) {
      original._retry = true
      _refreshing = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) throw new Error('no_refresh')
        const { data } = await axios.post(`${API_BASE}/v1/auth/refresh`, {
          refresh_token: refresh,
        })
        localStorage.setItem('access_token', data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        _refreshing = false
        return api(original)
      } catch {
        _refreshing = false
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.dispatchEvent(new Event('auth:logout'))
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export default api
