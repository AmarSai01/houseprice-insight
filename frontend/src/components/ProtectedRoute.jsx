import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const ProtectedRoute = ({ children }) => {
  const { user, loading, isAuthenticated } = useAuth()
  
  // Check localStorage as fallback (for immediate token check)
  const hasToken = !!localStorage.getItem('token')

  // Show loading while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // If not authenticated (check both state and localStorage), redirect to login
  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/login" replace />
  }

  // If we have a token but user data isn't loaded yet, wait a bit
  if (hasToken && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return children
}

export default ProtectedRoute

