import apiClient from './client'
import type { Rol } from '../types'

export const getRoles = () =>
  apiClient.get<Rol[]>('/roles').then((r) => r.data)
