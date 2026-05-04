import apiClient from './client'
import type { Baseline, BaselineCreate } from '../types'

export const createBaseline = (data: BaselineCreate) =>
  apiClient.post<Baseline>('/baselines', data).then((r) => r.data)

export const getBaselineActivo = () =>
  apiClient.get<Baseline>('/baselines/activo').then((r) => r.data)

export const getBaselineHistorial = () =>
  apiClient.get<Baseline[]>('/baselines/historial').then((r) => r.data)
