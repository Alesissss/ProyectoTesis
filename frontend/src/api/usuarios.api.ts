import apiClient from './client'
import type { Usuario, UsuarioCreate, UsuarioUpdate } from '../types'

export const getMe = () =>
  apiClient.get<Usuario>('/usuarios/me').then((r) => r.data)

export const getUsuarios = () =>
  apiClient.get<Usuario[]>('/usuarios').then((r) => r.data)

export const createUsuario = (data: UsuarioCreate) =>
  apiClient.post<Usuario>('/usuarios', data).then((r) => r.data)

export const updateUsuario = (id: string, data: UsuarioUpdate) =>
  apiClient.put<Usuario>(`/usuarios/${id}`, data).then((r) => r.data)

export const deleteUsuario = (id: string) =>
  apiClient.delete(`/usuarios/${id}`).then((r) => r.data)
