import apiClient from './client'
import type { CamaraDisponible } from '../types'

interface ApiEnvelope<T> {
  status: boolean
  message: string
  data: T
}

/**
 * Lista las cámaras disponibles en la unidad de procesamiento local.
 * El backend cachea por TTL (5 min por defecto). Pasar `refresh=true`
 * fuerza un re-escaneo (DSHOW + MSMF), que tarda ~5-10 s.
 */
export const getCamarasDisponibles = (refresh = false, timeoutMs = 90_000) =>
  apiClient
    .get<ApiEnvelope<CamaraDisponible[]>>('/dispositivos/camaras', {
      params: { refresh },
      timeout: timeoutMs,
    })
    .then((r) => r.data.data)
