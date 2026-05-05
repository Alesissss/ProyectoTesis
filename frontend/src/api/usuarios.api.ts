import apiClient from './client'
import type { Usuario, UsuarioCreate, UsuarioUpdate } from '../types'

interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

export const getMe = () =>
  apiClient
    .get<ApiEnvelope<Usuario>>('/usuarios/me')
    .then((r) => r.data.data)

export const getUsuarios = () =>
  apiClient
    .get<ApiEnvelope<Usuario[]>>('/usuarios')
    .then((r) => r.data.data)

export const createUsuario = (data: UsuarioCreate) =>
  apiClient
    .post<ApiEnvelope<Usuario>>('/usuarios', data)
    .then((r) => r.data.data)

export const updateUsuario = (id: string, data: UsuarioUpdate) =>
  apiClient
    .put<ApiEnvelope<Usuario>>(`/usuarios/${id}`, data)
    .then((r) => r.data.data)

export const deleteUsuario = (id: string) =>
  apiClient
    .delete<ApiEnvelope<unknown>>(`/usuarios/${id}`)
    .then((r) => r.data.data)
