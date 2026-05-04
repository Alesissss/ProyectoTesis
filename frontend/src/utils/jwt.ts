import type { TokenData } from '../types'

export function jwtDecode(token: string): TokenData | null {
  try {
    const payload = token.split('.')[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as TokenData
  } catch {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const decoded = jwtDecode(token)
  if (!decoded) return true
  return decoded.exp * 1000 < Date.now()
}
