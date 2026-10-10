import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { getApiErrorMessage } from '../services/apiErrors'
import LoadingSpinner from '../components/LoadingSpinner'
import './AuthPages.css'

const ForgotPassword = () => {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (loading) return
    setError('')
    setResult(null)
    setLoading(true)

    try {
      const response = await api.post('/api/auth/forgot-password', { email })
      setResult(response.data)
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          'Unable to request a password reset right now.'
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
          <h1 className="hpi-auth-title">Forgot password</h1>
          <p className="hpi-auth-lead">
            Enter your account email to request a reset link.
          </p>

          {result ? (
            <div className="hpi-auth-success">
              <p role="status">{result.message}</p>
              {result.delivery === 'dev' && result.dev_reset_url && (
                <p>
                  Local development mode (email provider not configured).{' '}
                  <Link
                    to={`/reset-password?token=${encodeURIComponent(
                      result.dev_reset_token || ''
                    )}`}
                    className="hpi-auth-text-link"
                  >
                    Continue to reset password →
                  </Link>
                </p>
              )}
              <p className="hpi-auth-footer">
                <Link to="/login">Back to sign in →</Link>
              </p>
            </div>
          ) : (
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
                {loading ? <LoadingSpinner size="sm" /> : 'Send reset link'}
              </button>

              <p className="hpi-auth-footer">
                <Link to="/login">Back to sign in →</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

export default ForgotPassword
