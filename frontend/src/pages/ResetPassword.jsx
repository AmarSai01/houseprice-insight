import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { getApiErrorMessage } from '../services/apiErrors'
import LoadingSpinner from '../components/LoadingSpinner'
import './AuthPages.css'

const MIN_PASSWORD_LENGTH = 8

const ResetPassword = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const tokenFromQuery = useMemo(
    () => searchParams.get('token') || '',
    [searchParams]
  )

  const [token, setToken] = useState(tokenFromQuery)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (loading) return
    setError('')

    if (!token.trim()) {
      setError('Reset token is missing. Request a new password reset link.')
      return
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`)
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await api.post('/api/auth/reset-password', {
        token: token.trim(),
        new_password: password,
      })
      navigate('/login', {
        replace: true,
        state: {
          notice: 'Password reset successfully. You can now sign in.',
        },
      })
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to reset password.'))
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
          <h1 className="hpi-auth-title">Reset password</h1>
          <p className="hpi-auth-lead">
            Choose a new password for your account.
          </p>

          <form className="hpi-auth-form" onSubmit={handleSubmit} noValidate>
            {!tokenFromQuery && (
              <div className="hpi-auth-field">
                <label htmlFor="token" className="hpi-auth-label">
                  Reset token
                </label>
                <input
                  id="token"
                  name="token"
                  type="text"
                  required
                  className="hpi-auth-input"
                  placeholder="Reset token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
              </div>
            )}

            <div className="hpi-auth-field">
              <label htmlFor="password" className="hpi-auth-label">
                New password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={MIN_PASSWORD_LENGTH}
                className="hpi-auth-input"
                placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <div className="hpi-auth-field">
              <label htmlFor="confirm" className="hpi-auth-label">
                Confirm password
              </label>
              <input
                id="confirm"
                name="confirm"
                type="password"
                autoComplete="new-password"
                required
                minLength={MIN_PASSWORD_LENGTH}
                className="hpi-auth-input"
                placeholder="Confirm password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
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
              {loading ? <LoadingSpinner size="sm" /> : 'Reset password'}
            </button>

            <p className="hpi-auth-footer">
              <Link to="/login">Back to sign in →</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ResetPassword
