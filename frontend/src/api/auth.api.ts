import apiClient from './client'
import type { LoginRequest, LoginResponse } from '../types'

export const login = (data: LoginRequest) =>
  apiClient
    .post<{ status: boolean; message: string; data: LoginResponse }>('/auth/login', data)
    .then((r) => r.data.data)
