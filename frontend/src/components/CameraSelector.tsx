import { useEffect, useState } from 'react'
import { getCamarasDisponibles } from '../api/dispositivos.api'
import type { CamaraDisponible } from '../types'

interface Props {
  value: string | null            // camera_profile seleccionado
  onChange: (profile: string | null, camara: CamaraDisponible | null) => void
  disabled?: boolean
}

/**
 * Dropdown de cámaras detectadas en la unidad de procesamiento local.
 * Carga el listado al montar (cacheado por el backend). Botón "Refrescar"
 * fuerza re-escaneo si el usuario conectó/desconectó hardware.
 */
export default function CameraSelector({ value, onChange, disabled }: Props) {
  const [camaras, setCamaras] = useState<CamaraDisponible[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cargar = async (refresh: boolean) => {
    setLoading(true)
    setError(null)
    try {
      const lista = await getCamarasDisponibles(refresh)
      setCamaras(lista)
      // Auto-seleccionar la primera que tenga perfil conocido si no hay
      // selección previa o la previa ya no está disponible.
      if (lista.length > 0) {
        const yaValido = value && lista.some((c) => c.profile === value)
        if (!yaValido) {
          const conPerfil = lista.find((c) => c.profile)
          const elegida = conPerfil ?? lista[0]
          onChange(elegida.profile, elegida)
        }
      } else {
        onChange(null, null)
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (err as Error)?.message ??
        'No se pudo listar cámaras'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-w-0">
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        Cámara
      </label>
      <div className="flex gap-2 min-w-0">
        <select
          value={value ?? ''}
          onChange={(e) => {
            const profile = e.target.value || null
            const cam = camaras.find((c) => c.profile === profile) ?? null
            onChange(profile, cam)
          }}
          disabled={disabled || loading || camaras.length === 0}
          className="flex-1 min-w-0 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 truncate"
        >
          {camaras.length === 0 && !loading && (
            <option value="">— sin cámaras detectadas —</option>
          )}
          {loading && <option value="">Escaneando…</option>}
          {camaras.map((c) => (
            <option key={`${c.backend}-${c.index}`} value={c.profile ?? ''}>
              {c.label}
              {!c.profile ? ' [perfil desconocido]' : ''}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => cargar(true)}
          disabled={disabled || loading}
          className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Re-escanear cámaras (tarda ~5-10s)"
        >
          {loading ? '…' : '⟳'}
        </button>
      </div>
      {error && (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      )}
      {!error && camaras.length === 0 && !loading && (
        <p className="text-xs text-amber-600 mt-1">
          No se detectó ninguna cámara. Conecta el dispositivo y refresca.
        </p>
      )}
    </div>
  )
}
