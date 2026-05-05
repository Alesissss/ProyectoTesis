import apiClient from './client'
import type { Baseline, BaselineCreate } from '../types'

interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

export const createBaseline = (data: BaselineCreate) =>
  apiClient
    .post<ApiEnvelope<Baseline>>('/baselines', data)
    .then((r) => r.data.data)

export const getBaselineActivo = () =>
  apiClient
    .get<ApiEnvelope<Baseline>>('/baselines/activo')
    .then((r) => r.data.data)

export const getBaselineHistorial = () =>
  apiClient
    .get<ApiEnvelope<Baseline[]>>('/baselines/historial')
    .then((r) => r.data.data)
