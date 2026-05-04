import apiClient from './client'
import type {
  BaselineSomnolencia,
  CalibracionIniciarRequest,
  CalibracionResultado,
} from '../types'

// El backend envuelve respuestas en ApiResponse<T> = {status, message, data}.
// Aquí desempaquetamos a `.data.data` para que la UI reciba el T limpio.

interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

export const getBaselineSomnolenciaActivo = () =>
  apiClient
    .get<ApiEnvelope<BaselineSomnolencia>>('/baselines/somnolencia/activo')
    .then((r) => r.data.data)

export const getBaselineSomnolenciaHistorial = () =>
  apiClient
    .get<ApiEnvelope<BaselineSomnolencia[]>>('/baselines/somnolencia/historial')
    .then((r) => r.data.data)

export const iniciarCalibracionM1 = (
  body: CalibracionIniciarRequest = {},
  // El subprocess captura ~30 s de video → bumpeamos el timeout de axios.
  timeoutMs = 120_000,
) =>
  apiClient
    .post<ApiEnvelope<CalibracionResultado>>('/calibracion/somnolencia/iniciar', body, {
      timeout: timeoutMs,
    })
    .then((r) => r.data.data)
