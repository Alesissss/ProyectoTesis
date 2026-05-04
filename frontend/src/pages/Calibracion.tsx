import { useEffect, useState } from 'react'
import {
  getBaselineSomnolenciaActivo,
  iniciarCalibracionM1,
} from '../api/baselineSomnolencia.api'
import type { BaselineSomnolencia, CalibracionResultado } from '../types'

type Step = 'idle' | 'loading' | 'success' | 'error'

const DURACION_DEFAULT = 30
const CAMARA_DEFAULT = 1

export default function Calibracion() {
  const [step, setStep] = useState<Step>('idle')
  const [error, setError] = useState<string | null>(null)
  const [resultado, setResultado] = useState<CalibracionResultado | null>(null)
  const [activo, setActivo] = useState<BaselineSomnolencia | null>(null)

  // Parámetros de captura (el RNF-05 fija 30 s, pero permitimos ajustarlo).
  const [duracion, setDuracion] = useState(DURACION_DEFAULT)
  const [camaraId, setCamaraId] = useState(CAMARA_DEFAULT)

  // Cargar el baseline vigente del usuario al entrar a la pantalla.
  useEffect(() => {
    getBaselineSomnolenciaActivo()
      .then(setActivo)
      .catch(() => setActivo(null)) // 404 = aún no calibrado, es OK
  }, [])

  const handleIniciar = async () => {
    setStep('loading')
    setError(null)
    try {
      const r = await iniciarCalibracionM1({
        duracion_s: duracion,
        camara_id: camaraId,
      })
      setResultado(r)
      setActivo(r.baseline)
      setStep('success')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (err as Error)?.message ??
        'Error desconocido al ejecutar la calibración'
      setError(msg)
      setStep('error')
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Calibración personal — M1</h1>
        <p className="text-slate-500 text-sm mt-1">
          Registra tu probabilidad de somnolencia base en estado alerta. El sistema
          la usará como referencia personal (RNF-05) para corregir el dictamen del
          Módulo 1, evitando falsos positivos por subject-dependence.
        </p>
      </div>

      {/* Baseline vigente */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-3">Baseline vigente</h2>
        {activo ? (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <Stat label="P_somnolencia base" value={activo.p_somnolencia.toFixed(4)} />
            <Stat
              label="EAR promedio"
              value={activo.ear_promedio?.toFixed(4) ?? '—'}
            />
            <Stat
              label="MAR promedio"
              value={activo.mar_promedio?.toFixed(4) ?? '—'}
            />
            <Stat
              label="Frames procesados"
              value={String(activo.frames_procesados ?? '—')}
            />
            <Stat
              label="Registrado"
              value={new Date(activo.fecha_registro).toLocaleString('es-PE')}
            />
            <Stat
              label="Estado"
              value={activo.activo ? 'Activo' : 'Histórico'}
            />
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Aún no has registrado un baseline de somnolencia. Inicia tu primera
            calibración para activar la corrección personalizada del Módulo 1.
          </p>
        )}
      </div>

      {/* Instrucciones + parámetros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-3">Nueva calibración</h2>
        <ol className="text-sm text-slate-600 space-y-1.5 mb-4 list-decimal list-inside">
          <li>Asegúrate de estar en un ambiente con luz blanca constante.</li>
          <li>Siéntate a 40–60 cm de la cámara, mirándola de frente.</li>
          <li>Mantente alerta, ojos abiertos, sin bostezos durante toda la captura.</li>
          <li>Evita movimientos bruscos. La cámara se activará al pulsar el botón.</li>
        </ol>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Duración (s)
            </label>
            <input
              type="number"
              min={10}
              max={120}
              value={duracion}
              onChange={(e) => setDuracion(parseInt(e.target.value, 10) || DURACION_DEFAULT)}
              disabled={step === 'loading'}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Índice de cámara
            </label>
            <input
              type="number"
              min={0}
              max={10}
              value={camaraId}
              onChange={(e) => setCamaraId(parseInt(e.target.value, 10) || 0)}
              disabled={step === 'loading'}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            />
            <p className="text-xs text-slate-400 mt-1">
              0 = webcam integrada · 1 = ALPCAM USB (default)
            </p>
          </div>
        </div>

        <button
          onClick={handleIniciar}
          disabled={step === 'loading'}
          className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
        >
          {step === 'loading' ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Capturando {duracion}s en estado alerta…
            </span>
          ) : (
            'Iniciar calibración'
          )}
        </button>
        {step === 'loading' && (
          <p className="text-xs text-slate-500 text-center mt-2">
            La primera vez la cámara puede tardar 5–15 s en abrir (carga MSMF).
          </p>
        )}
      </div>

      {/* Resultado */}
      {step === 'success' && resultado && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 mb-6">
          <h3 className="font-semibold text-green-900 mb-2">Calibración registrada</h3>
          <div className="grid grid-cols-2 gap-3 text-sm text-green-900/90">
            <Stat
              label="P_somnolencia base"
              value={resultado.baseline.p_somnolencia.toFixed(4)}
            />
            <Stat
              label="Duración real"
              value={`${resultado.duracion_real_s.toFixed(2)} s`}
            />
            <Stat
              label="Frames procesados"
              value={String(resultado.frames_procesados)}
            />
            <Stat
              label="Ventanas BiLSTM"
              value={String(resultado.ventanas_inferidas)}
            />
            {resultado.fps_observado != null && (
              <Stat
                label="FPS real"
                value={resultado.fps_observado.toFixed(1)}
              />
            )}
          </div>
          <p className="text-xs text-green-800/80 mt-3">
            A partir de ahora las evaluaciones se corrigen contra esta línea base
            personal: <code>P_efectiva = max(0, P_obs − {resultado.baseline.p_somnolencia.toFixed(2)})</code>.
          </p>
        </div>
      )}

      {step === 'error' && error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <p className="font-semibold mb-1">No se pudo completar la calibración</p>
          <p>{error}</p>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="font-mono text-slate-900">{value}</p>
    </div>
  )
}
