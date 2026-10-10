import axios from 'axios'
import { clearAuthStorage, notifyInvalidSession } from './authSession'
import { resolveApiBaseUrl } from './apiBaseUrl'

// Runtime resolution: use VITE_API_URL when present; otherwise the local backend.
// Production deploy builds validate VITE_API_URL in vite.config.js (fail closed).
const API_BASE_URL = resolveApiBaseUrl({
  viteApiUrl: import.meta.env.VITE_API_URL,
  isProduction: false,
})

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 10000 // 10 second timeout
})

// Request interceptor: Add token to every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Set initial token if it exists
const initialToken = localStorage.getItem('token')
if (initialToken) {
  api.defaults.headers.common['Authorization'] = `Bearer ${initialToken}`
}

function hadAuthToken(error) {
  const header =
    error?.config?.headers?.Authorization ||
    api.defaults.headers.common?.Authorization
  return Boolean(localStorage.getItem('token') || header)
}

// Response interceptor: Handle authentication failures
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && hadAuthToken(error)) {
      // Synchronize storage + AuthContext. Do not treat public/guest APIs
      // as requiring a hard navigation when no session existed.
      clearAuthStorage()
      delete api.defaults.headers.common['Authorization']
      notifyInvalidSession()

      const path = window.location.pathname
      // Only hard-redirect leftover protected shell URLs; page-level UI handles the rest.
      // /dashboard itself redirects to /history; keep this for any in-flight path match.
      if (path === '/dashboard') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
