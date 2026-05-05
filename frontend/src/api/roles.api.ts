import apiClient from './client'
import type { Rol } from '../types'

interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

export const getRoles = () =>
  apiClient
    .get<ApiEnvelope<Rol[]>>('/roles')
    .then((r) => r.data.data)
