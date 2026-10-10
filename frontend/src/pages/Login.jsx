import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getApiErrorMessage } from '../services/apiErrors'
import LoadingSpinner from '../components/LoadingSpinner'
import './AuthPages.css'

const Login = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const notice = location.state?.notice

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (loading) return
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      await new Promise((resolve) => setTimeout(resolve, 100))
      navigate('/history', { replace: true })
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          'Login failed. Please check your credentials.'
        )
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="hpi-auth hpi-ds">
      <div className="hpi-auth-shell">
        <Link to="/" className="hpi-auth-brand">
          <span>HousePrice</span>
          <span className="hpi-auth-brand-sub">Insight</span>
        </Link>

        <div className="hpi-auth-panel">
          <h1 className="hpi-auth-title">Sign in to your account</h1>
          <p className="hpi-auth-lead">
            Don&apos;t have an account?{' '}
            <Link to="/register">Create one →</Link>
          </p>

          {notice && (
            <p className="hpi-auth-notice" role="status">
              {notice}
            </p>
          )}

          <form className="hpi-auth-form" onSubmit={handleSubmit} noValidate>
            <div className="hpi-auth-field">
              <label htmlFor="email" className="hpi-auth-label">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="hpi-auth-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="hpi-auth-field">
              <label htmlFor="password" className="hpi-auth-label">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="hpi-auth-input"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <p className="hpi-auth-aside">
              <Link to="/forgot-password" className="hpi-auth-text-link">
                Forgot password?
              </Link>
            </p>

            {error && (
              <div className="hpi-auth-error" role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              aria-busy={loading}
              className="hpi-auth-submit"
            >
              {loading ? <LoadingSpinner size="sm" /> : 'Sign in'}
            </button>
          </form>

          <p className="hpi-auth-footer">
            Don&apos;t have an account?{' '}
            <Link to="/register">Create one →</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
