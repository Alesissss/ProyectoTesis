import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/auth.store'
import { isTokenExpired } from '../utils/jwt'

interface ProtectedRouteProps {
  requiredPermiso?: string
}

export default function ProtectedRoute({ requiredPermiso }: ProtectedRouteProps) {
  const { isAuthenticated, token, hasPermission, logout } = useAuthStore()

  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />
  }

  if (isTokenExpired(token)) {
    logout()
    return <Navigate to="/login" replace />
  }

  if (requiredPermiso && !hasPermission(requiredPermiso)) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
