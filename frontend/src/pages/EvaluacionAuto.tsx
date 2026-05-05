import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { iniciarEvaluacion } from '../api/evaluaciones.api'
import CameraSelector from '../components/CameraSelector'
import Semaforo from '../components/Semaforo'
import type { Dictamen, EvaluacionIniciarResultado } from '../types'

type Step = 'idle' | 'loading' | 'success' | 'error' | 'invalid'

const DURACION_DEFAULT = 30

export default function EvaluacionAuto() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('idle')
  const [error, setError] = useState<string | null>(null)
  const [resultado, setResultado] = useState<EvaluacionIniciarResultado | null>(null)

  const [duracion, setDuracion] = useState(DURACION_DEFAULT)
  const [cameraProfile, setCameraProfile] = useState<string | null>(null)
  const [puerto, setPuerto] = useState('')

  const handleIniciar = async () => {
    setStep('loading')
    setError(null)
    try {
      const r = await iniciarEvaluacion({
        duracion_s: duracion,
        camera_profile: cameraProfile,
        puerto_arduino: puerto.trim() || null,
      })
      setResultado(r)
      setStep('success')
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { message?: string } } }
      const msg =
        ax?.response?.data?.message ??
        (err as Error)?.message ??
        'Error desconocido al ejecutar la evaluación'
      setError(msg)
      // 422 = liveness fail (cámara apuntando a la nada, foto, etc.).
      // Mostramos UI específica en lugar del banner rojo de error genérico.
      setStep(ax?.response?.status === 422 ? 'invalid' : 'error')
    }
  }

  const dictamen = resultado?.evaluacion.dictamen as Dictamen | undefined

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Evaluación de aptitud</h1>
        <p className="text-slate-500 text-sm mt-1">
          Captura un video de {duracion} s y, si está conectado, lee la señal sEMG
          del Arduino. El sistema fusiona M1 (visión) + M2 (fisiológico) y emite el
          dictamen final del Módulo 3.
        </p>
      </div>

      {/* Parámetros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-3">Antes de empezar</h2>
        <ol className="text-sm text-slate-600 space-y-1.5 mb-4 list-decimal list-inside">
          <li>Asegúrate de tener calibrada tu línea base personal (Calibración M1).</li>
          <li>Conecta la cámara y, si vas a usar EMG, el Arduino con el sensor Olimex.</li>
          <li>Siéntate frente a la cámara, a 40–60 cm, con luz constante.</li>
          <li>Pulsa "INICIAR EVALUACIÓN" y comportate con normalidad durante la captura.</li>
        </ol>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Duración (s)
            </label>
            <input
              type="number"
              min={10}
              max={180}
              value={duracion}
              onChange={(e) => setDuracion(parseInt(e.target.value, 10) || DURACION_DEFAULT)}
              disabled={step === 'loading'}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            />
          </div>
          <CameraSelector
            value={cameraProfile}
            onChange={(profile) => setCameraProfile(profile)}
            disabled={step === 'loading'}
          />
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Puerto Arduino
            </label>
            <input
              type="text"
              value={puerto}
              onChange={(e) => setPuerto(e.target.value)}
              disabled={step === 'loading'}
              placeholder="auto"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            />
            <p className="text-xs text-slate-400 mt-1">vacío = auto-detección</p>
          </div>
        </div>

        <button
          onClick={handleIniciar}
          disabled={step === 'loading'}
          className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors text-base"
        >
          {step === 'loading' ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Capturando {duracion}s y procesando…
            </span>
          ) : (
            'INICIAR EVALUACIÓN'
          )}
        </button>
        {step === 'loading' && (
          <p className="text-xs text-slate-500 text-center mt-2">
            Mantente quieto. La cámara puede tardar 5–15 s en abrir la primera vez.
          </p>
        )}
      </div>

      {/* Resultado */}
      {step === 'success' && resultado && dictamen && (
        <div className="space-y-4">
          <Semaforo
            dictamen={dictamen}
            pSomnolencia={resultado.evaluacion.p_somnolencia}
            pFatigaFisiologica={resultado.evaluacion.p_fatiga_fisiologica}
            pTotal={resultado.evaluacion.p_total}
          />

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-900 mb-3">Métricas de captura</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <Stat label="Duración real" value={`${resultado.duracion_real_s.toFixed(1)} s`} />
              <Stat label="Frames procesados" value={String(resultado.frames_procesados)} />
              <Stat
                label="FPS observado"
                value={resultado.fps_observado != null ? resultado.fps_observado.toFixed(1) : '—'}
              />
              <Stat label="Muestras EMG" value={String(resultado.n_muestras_emg)} />
              <Stat label="rPPG / HRV" value={resultado.hrv_disponible ? 'Disponible' : 'No disponible'} />
              <Stat label="Umbral usado" value={resultado.evaluacion.umbral_usado.toFixed(2)} />
            </div>
          </div>

          {resultado.justificacion.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="font-semibold text-slate-900 mb-3">Justificación del dictamen (M3)</h3>
              <ul className="text-sm text-slate-700 space-y-1.5 list-disc list-inside">
                {resultado.justificacion.map((j, i) => (
                  <li key={i}>{j}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => {
                setStep('idle')
                setResultado(null)
              }}
              className="px-5 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Nueva evaluación
            </button>
            <button
              onClick={() => navigate(`/evaluaciones/${resultado.evaluacion.id_evaluacion}`)}
              className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Ver detalle completo
            </button>
          </div>
        </div>
      )}

      {step === 'error' && error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <p className="font-semibold mb-1">No se pudo completar la evaluación</p>
          <p>{error}</p>
          <button
            onClick={() => setStep('idle')}
            className="mt-2 text-red-600 hover:text-red-800 underline"
          >
            Reintentar
          </button>
        </div>
      )}

      {step === 'invalid' && error && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 text-sm text-amber-900">
          <div className="flex items-start gap-3 mb-3">
            <span className="text-2xl leading-none">⚠</span>
            <div>
              <p className="font-semibold text-base text-amber-900 mb-1">
                Captura no válida — no se registró evaluación
              </p>
              <p className="text-amber-800/90 text-xs">
                El sistema detectó que la captura no corresponde a un sujeto
                vivo y consciente frente a la cámara. La evaluación NO fue
                guardada en el sistema. Verifica los siguientes puntos y
                reintenta:
              </p>
            </div>
          </div>
          <ul className="space-y-1 ml-9 list-disc list-inside">
            {error
              .replace(/^Captura inválida:\s*/, '')
              .split('|')
              .map((razon, i) => (
                <li key={i}>{razon.trim()}</li>
              ))}
          </ul>
          <div className="mt-4 ml-9 p-3 bg-white/60 rounded-lg text-xs text-amber-800/90">
            <p className="font-semibold mb-1">Posibles causas:</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>La cámara no está apuntando al rostro del médico.</li>
              <li>Hay una imagen estática, foto o pantalla frente a la cámara.</li>
              <li>Iluminación insuficiente para detección facial.</li>
              <li>El sujeto no parpadeó durante la captura.</li>
            </ul>
          </div>
          <button
            onClick={() => setStep('idle')}
            className="mt-3 ml-9 px-4 py-2 text-sm font-medium bg-amber-100 hover:bg-amber-200 text-amber-900 rounded-lg border border-amber-300"
          >
            Reintentar captura
          </button>
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
