import { useEffect, useRef, useState } from 'react'

interface Props {
  /**
   * Cuando es true, el preview se detiene y libera la cámara. Importante en
   * Windows: si el navegador tiene un handle MSMF abierto, OpenCV puede no
   * poder abrir la misma cámara en el subprocess de captura. La página padre
   * debe poner `paused={true}` mientras step === 'loading'.
   */
  paused?: boolean
}

interface VideoDevice {
  deviceId: string
  label: string
}

/**
 * Previsualización en vivo de la cámara seleccionada en el navegador.
 *
 * NO usa el perfil de OpenCV del backend: muestra lo que el navegador ve.
 * Sirve como ayuda visual al médico para confirmar encuadre, iluminación y
 * posición ANTES de iniciar la captura. La captura real la dispara el
 * subprocess cv2 con su propio perfil.
 */
export default function CameraPreview({ paused = false }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [devices, setDevices] = useState<VideoDevice[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [ready, setReady] = useState(false)

  // Detener cualquier stream activo (utilidad).
  const detenerStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) videoRef.current.srcObject = null
    setReady(false)
  }

  // Pedir permisos y enumerar dispositivos.
  useEffect(() => {
    let alive = true
    const init = async () => {
      try {
        // En Chrome/Edge enumerateDevices() solo devuelve `label` después de
        // que el usuario otorgó permiso a CUALQUIER cámara. Pedimos un stream
        // mínimo solo para forzar el prompt, lo soltamos, y luego enumeramos.
        const temp = await navigator.mediaDevices.getUserMedia({ video: true })
        temp.getTracks().forEach((t) => t.stop())

        const all = await navigator.mediaDevices.enumerateDevices()
        const videoIns = all
          .filter((d) => d.kind === 'videoinput')
          .map((d, i) => ({
            deviceId: d.deviceId,
            label: d.label || `Cámara ${i + 1}`,
          }))

        if (!alive) return
        setDevices(videoIns)
        if (videoIns.length > 0) setSelectedId(videoIns[0].deviceId)
      } catch (err: unknown) {
        if (!alive) return
        const e = err as { name?: string; message?: string }
        if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
          setError(
            'Permiso de cámara denegado. Habilita el acceso desde el ícono ' +
            'de candado en la barra del navegador y recarga la página.',
          )
        } else if (e.name === 'NotFoundError' || e.name === 'DevicesNotFoundError') {
          setError('No se detectó ninguna cámara conectada.')
        } else {
          setError('No se pudo iniciar la previsualización de la cámara.')
        }
      }
    }
    init()
    return () => {
      alive = false
      detenerStream()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Cuando cambia el device o el flag paused, reabrir o detener stream.
  useEffect(() => {
    if (!selectedId) return
    if (paused) {
      detenerStream()
      return
    }

    let alive = true
    detenerStream()
    navigator.mediaDevices
      .getUserMedia({
        video: { deviceId: { exact: selectedId }, width: 640, height: 480 },
        audio: false,
      })
      .then((stream) => {
        if (!alive) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play().catch(() => {
            /* autoplay bloqueado: el atributo `playsInline + muted` debería
               permitirlo en todos los browsers modernos. */
          })
        }
        setReady(true)
      })
      .catch((err: { name?: string }) => {
        if (!alive) return
        if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          setError(
            'La cámara ya está en uso por otra aplicación. Cierra cualquier ' +
            'app que la esté utilizando y reintenta.',
          )
        } else {
          setError('No se pudo abrir la cámara seleccionada.')
        }
      })

    return () => {
      alive = false
    }
  }, [selectedId, paused])

  return (
    <div className="bg-slate-900 rounded-xl overflow-hidden border border-slate-200">
      {/* Header con selector */}
      <div className="bg-slate-800 px-4 py-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
            paused
              ? 'bg-slate-500'
              : ready
                ? 'bg-green-400 animate-pulse'
                : 'bg-amber-400'
          }`} />
          <span className="text-xs text-slate-300 font-medium truncate">
            {paused ? 'Previsualización pausada' : ready ? 'En vivo' : 'Conectando…'}
          </span>
        </div>
        {devices.length > 1 && !paused && (
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="text-xs bg-slate-700 text-slate-100 border border-slate-600 rounded px-2 py-1 max-w-[60%] truncate"
          >
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Video / mensaje */}
      <div className="relative aspect-video bg-black flex items-center justify-center">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`w-full h-full object-contain ${error || paused ? 'hidden' : ''}`}
        />
        {paused && (
          <div className="text-center text-slate-400 text-sm px-4">
            <p className="text-3xl mb-2">⏸</p>
            <p>Cámara liberada para la captura.</p>
          </div>
        )}
        {!paused && error && (
          <div className="text-center text-amber-300 text-sm px-4 py-6">
            <p className="text-2xl mb-2">⚠</p>
            <p>{error}</p>
          </div>
        )}
        {!paused && !error && !ready && (
          <div className="text-slate-500 text-sm">Cargando…</div>
        )}
      </div>

      {/* Footer informativo */}
      {!error && !paused && (
        <div className="bg-slate-50 border-t border-slate-200 px-4 py-2">
          <p className="text-xs text-slate-500">
            Esta vista previa es solo para verificar encuadre e iluminación.
            La captura real usa la cámara configurada arriba.
          </p>
        </div>
      )}
    </div>
  )
}
