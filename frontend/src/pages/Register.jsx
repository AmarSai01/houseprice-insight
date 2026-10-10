import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getApiErrorMessage } from '../services/apiErrors'
import LoadingSpinner from '../components/LoadingSpinner'
import './AuthPages.css'

const Register = () => {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register, login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (loading) return
    setError('')
    setLoading(true)

    try {
      // Register user
      await register(name, email, password)

      // Auto-login after registration
      await login(email, password)

      // Navigate to history archive after registration
      navigate('/history', { replace: true })
    } catch (err) {
      setError(
        getApiErrorMessage(err, 'Registration failed. Please try again.')
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
          <h1 className="hpi-auth-title">Create your account</h1>
          <p className="hpi-auth-lead">
            Already have an account?{' '}
            <Link to="/login">Sign in →</Link>
          </p>

          <form className="hpi-auth-form" onSubmit={handleSubmit} noValidate>
            <div className="hpi-auth-field">
              <label htmlFor="name" className="hpi-auth-label">
                Full name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                className="hpi-auth-input"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
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
                autoComplete="new-password"
                required
                minLength={8}
                className="hpi-auth-input"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

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
              {loading ? <LoadingSpinner size="sm" /> : 'Sign up'}
            </button>
          </form>

          <p className="hpi-auth-footer">
            Already have an account?{' '}
            <Link to="/login">Sign in →</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Register
