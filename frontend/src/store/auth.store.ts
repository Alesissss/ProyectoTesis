import { create } from 'zustand'
import { jwtDecode } from '../utils/jwt'
import type { TokenData } from '../types'

interface AuthState {
  token: string | null
  user: TokenData | null
  isAuthenticated: boolean
  setToken: (token: string) => void
  logout: () => void
  hasPermission: (permiso: string) => boolean
}

const storedToken = localStorage.getItem('access_token')
const storedUser = storedToken ? jwtDecode(storedToken) : null

export const useAuthStore = create<AuthState>((set, get) => ({
  token: storedToken,
  user: storedUser,
  isAuthenticated: !!storedToken,

  setToken: (token: string) => {
    localStorage.setItem('access_token', token)
    const user = jwtDecode(token)
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ token: null, user: null, isAuthenticated: false })
  },

  hasPermission: (permiso: string) => {
    const { user } = get()
    return user?.permisos.includes(permiso) ?? false
  },
}))
