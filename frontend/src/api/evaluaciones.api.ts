import apiClient from './client'
import type { Evaluacion, EvaluacionCreate, EvaluacionResumen } from '../types'

export const createEvaluacion = (data: EvaluacionCreate) =>
  apiClient.post<Evaluacion>('/evaluaciones', data).then((r) => r.data)

// El backend devuelve EvaluacionResumenResponse (id, dictamen, p_total, fecha_registro)
export const getMisEvaluaciones = () =>
  apiClient.get<EvaluacionResumen[]>('/evaluaciones/mis-evaluaciones').then((r) => r.data)

export const getAllEvaluaciones = () =>
  apiClient.get<EvaluacionResumen[]>('/evaluaciones').then((r) => r.data)

export const getEvaluacion = (id: string) =>
  apiClient.get<Evaluacion>(`/evaluaciones/${id}`).then((r) => r.data)
