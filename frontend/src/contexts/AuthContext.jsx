import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from '../services/api'
import { registerInvalidSessionHandler } from '../services/authSession'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(() => localStorage.getItem('token'))

  const clearSession = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    delete api.defaults.headers.common['Authorization']
  }, [])

  // Fetch user data on mount if token exists
  useEffect(() => {
    const fetchUser = async () => {
      const storedToken = localStorage.getItem('token')
      if (!storedToken) {
        setLoading(false)
        return
      }

      try {
        api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`

        const response = await api.get('/api/auth/me')
        setUser(response.data)
        setToken(storedToken)
      } catch {
        clearSession()
      } finally {
        setLoading(false)
      }
    }

    fetchUser()
  }, [clearSession])

  // Allow api.js 401 handling to clear AuthContext without circular imports.
  useEffect(() => registerInvalidSessionHandler(clearSession), [clearSession])

  const login = async (email, password) => {
    try {
      // OAuth2PasswordRequestForm on the backend expects
      // application/x-www-form-urlencoded (field names: username, password)
      const params = new URLSearchParams()
      params.append('username', email)
      params.append('password', password)

      const response = await api.post('/api/auth/login', params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })

      const access_token = response.data.access_token || response.data.token
      const userData = response.data.user || response.data

      if (!access_token) {
        throw new Error('No access token received from server')
      }

      if (!userData) {
        throw new Error('No user data received from server')
      }

      localStorage.setItem('token', access_token)

      const savedToken = localStorage.getItem('token')
      if (savedToken !== access_token) {
        throw new Error('Failed to save token to localStorage')
      }

      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      setToken(access_token)
      setUser(userData)

      await new Promise((resolve) => setTimeout(resolve, 50))

      return userData
    } catch (error) {
      clearSession()
      throw error
    }
  }

  const register = async (name, email, password) => {
    const response = await api.post('/api/auth/register', {
      name,
      email,
      password
    })
    return response.data
  }

  const logout = () => {
    clearSession()
  }

  const value = {
    user,
    login,
    register,
    logout,
    clearSession,
    loading,
    token,
    isAuthenticated: !!user && !!token
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
