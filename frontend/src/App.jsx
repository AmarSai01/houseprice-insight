import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import LandingPage from './pages/LandingPage'
import EstimatePage from './pages/EstimatePage'
import ComparePage from './pages/ComparePage'
import AffordabilityPage from './pages/AffordabilityPage'
import MarketPage from './pages/MarketPage'
import HowItWorksPage from './pages/HowItWorksPage'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import HistoryPage from './pages/HistoryPage'

function App() {
  return (
    <AuthProvider>
      <Router future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/estimate" element={<EstimatePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/affordability" element={<AffordabilityPage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/dashboard" element={<Navigate to="/history" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App
