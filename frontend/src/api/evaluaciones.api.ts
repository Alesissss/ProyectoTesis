import apiClient from './client'
import type {
  Evaluacion,
  EvaluacionCreate,
  EvaluacionIniciarRequest,
  EvaluacionIniciarResultado,
  EvaluacionResumen,
} from '../types'

// El backend envuelve TODA respuesta en ApiResponse<T> = {status, message, data}.
// Hay que desempaquetar a `.data.data` para obtener el T limpio que la UI espera.
interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

export const createEvaluacion = (data: EvaluacionCreate) =>
  apiClient
    .post<ApiEnvelope<Evaluacion>>('/evaluaciones', data)
    .then((r) => r.data.data)

export const getMisEvaluaciones = () =>
  apiClient
    .get<ApiEnvelope<EvaluacionResumen[]>>('/evaluaciones/mis-evaluaciones')
    .then((r) => r.data.data)

export const getAllEvaluaciones = () =>
  apiClient
    .get<ApiEnvelope<EvaluacionResumen[]>>('/evaluaciones')
    .then((r) => r.data.data)

export const getEvaluacion = (id: string) =>
  apiClient
    .get<ApiEnvelope<Evaluacion>>(`/evaluaciones/${id}`)
    .then((r) => r.data.data)

// ── Evaluación automatizada (subprocess) ─────────────────────────────────────

export const iniciarEvaluacion = (
  body: EvaluacionIniciarRequest = {},
  // Captura ~30 s + procesamiento + POST → bumpeamos el timeout de axios.
  timeoutMs = 240_000,
) =>
  apiClient
    .post<ApiEnvelope<EvaluacionIniciarResultado>>('/evaluaciones/iniciar', body, {
      timeout: timeoutMs,
    })
    .then((r) => r.data.data)
