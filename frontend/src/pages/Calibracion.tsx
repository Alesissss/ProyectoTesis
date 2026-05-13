import { useEffect, useState } from 'react'
import {
  getBaselineSomnolenciaActivo,
  iniciarCalibracionM1,
} from '../api/baselineSomnolencia.api'
import { getBaselineActivo } from '../api/baselines.api'
import CameraSelector from '../components/CameraSelector'
import CameraPreview from '../components/CameraPreview'
import type {
  Baseline,
  BaselineSomnolencia,
  CalibracionResultado,
} from '../types'

type Step = 'idle' | 'loading' | 'success' | 'error' | 'invalid'

const DURACION_DEFAULT = 30

export default function Calibracion() {
  const [step, setStep] = useState<Step>('idle')
  const [error, setError] = useState<string | null>(null)
  const [resultado, setResultado] = useState<CalibracionResultado | null>(null)

  // Baselines vigentes (uno por módulo).
  const [activoM1, setActivoM1] = useState<BaselineSomnolencia | null>(null)
  const [activoM2, setActivoM2] = useState<Baseline | null>(null)

  // Parámetros de captura (el RNF-05 fija 30 s, pero permitimos ajustarlo).
  const [duracion, setDuracion] = useState(DURACION_DEFAULT)
  const [cameraProfile, setCameraProfile] = useState<string | null>(null)
  const [puerto, setPuerto] = useState('')

  // Cargar baselines vigentes (M1 y M2) al entrar a la pantalla.
  useEffect(() => {
    getBaselineSomnolenciaActivo()
      .then(setActivoM1)
      .catch(() => setActivoM1(null)) // 404 = aún no calibrado
    getBaselineActivo()
      .then(setActivoM2)
      .catch(() => setActivoM2(null))
  }, [])

  const handleIniciar = async () => {
    setStep('loading')
    setError(null)
    try {
      const r = await iniciarCalibracionM1({
        duracion_s: duracion,
        camera_profile: cameraProfile,
        puerto_arduino: puerto.trim() || null,
      })
      setResultado(r)
      setActivoM1(r.baseline)
      // El backend solo registra M2 si hubo EMG válido; mantén el M2 previo
      // si esta vez no se actualizó.
      if (r.baseline_m2?.id_baseline) {
        setActivoM2({
          id_baseline: r.baseline_m2.id_baseline,
          id_usuario: r.baseline.id_usuario,
          rms_emg: r.baseline_m2.rms_emg ?? 0,
          freq_mediana: r.baseline_m2.freq_mediana ?? 0,
          freq_media: r.baseline_m2.freq_media ?? 0,
          sdnn: r.baseline_m2.sdnn,
          rmssd: r.baseline_m2.rmssd,
          pnn50: r.baseline_m2.pnn50,
          activo: true,
          fecha_registro: new Date().toISOString(),
        })
      }
      setStep('success')
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { message?: string } } }
      const msg =
        ax?.response?.data?.message ??
        (err as Error)?.message ??
        'No se pudo ejecutar la calibración.'
      setError(msg)
      setStep(ax?.response?.status === 422 ? 'invalid' : 'error')
    }
  }

  const m2Nuevo = resultado?.baseline_m2

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Calibración personal</h1>
        <p className="text-slate-500 text-sm mt-1">
          Registra tus valores en estado alerta para que el sistema corrija sus
          dictámenes en función de tu línea base personal (RNF-05). Una sola
          captura de {duracion} s calibra los dos módulos: visión (M1) y
          fisiológico (M2: EMG + HRV).
        </p>
      </div>

      {/* Baselines vigentes — dos paneles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-900">Visión (M1)</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              activoM1 ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
            }`}>
              {activoM1 ? 'Vigente' : 'Sin registrar'}
            </span>
          </div>
          {activoM1 ? (
            <dl className="space-y-1.5 text-sm">
              <DlRow label="P_somnolencia base" value={activoM1.p_somnolencia.toFixed(4)} />
              <DlRow label="EAR promedio" value={activoM1.ear_promedio?.toFixed(4) ?? '—'} />
              <DlRow label="MAR promedio" value={activoM1.mar_promedio?.toFixed(4) ?? '—'} />
              <DlRow
                label="Registrado"
                value={new Date(activoM1.fecha_registro).toLocaleString('es-PE', {
                  dateStyle: 'short', timeStyle: 'short',
                })}
              />
            </dl>
          ) : (
            <p className="text-sm text-slate-500">
              Aún no calibras la visión. La evaluación usará el modelo sin corrección
              personal.
            </p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-900">Fisiológico (M2)</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              activoM2 ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
            }`}>
              {activoM2 ? 'Vigente' : 'Sin registrar'}
            </span>
          </div>
          {activoM2 ? (
            <dl className="space-y-1.5 text-sm">
              <DlRow label="RMS EMG base" value={`${activoM2.rms_emg.toFixed(1)} µV`} />
              <DlRow label="F. mediana EMG" value={`${activoM2.freq_mediana.toFixed(1)} Hz`} />
              <DlRow label="F. media EMG" value={`${activoM2.freq_media.toFixed(1)} Hz`} />
              <DlRow label="SDNN" value={activoM2.sdnn != null ? `${activoM2.sdnn.toFixed(1)} ms` : '—'} />
              <DlRow label="RMSSD" value={activoM2.rmssd != null ? `${activoM2.rmssd.toFixed(1)} ms` : '—'} />
              <DlRow label="pNN50" value={activoM2.pnn50 != null ? `${activoM2.pnn50.toFixed(1)}%` : '—'} />
              <DlRow
                label="Registrado"
                value={new Date(activoM2.fecha_registro).toLocaleString('es-PE', {
                  dateStyle: 'short', timeStyle: 'short',
                })}
              />
            </dl>
          ) : (
            <p className="text-sm text-slate-500">
              Aún no calibras el módulo fisiológico. Las reglas de fatiga (EMG/HRV)
              se aplican con baseline por defecto y pueden dar falsos positivos.
              Conecta el Arduino para registrarlo.
            </p>
          )}
        </div>
      </div>

      {/* Previsualización de cámara */}
      <div className="mb-6">
        <CameraPreview paused={step === 'loading'} />
      </div>

      {/* Instrucciones + parámetros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-3">Nueva calibración</h2>
        <ol className="text-sm text-slate-600 space-y-1.5 mb-4 list-decimal list-inside">
          <li>Estate en un ambiente con luz blanca constante y sin reflejos.</li>
          <li>Siéntate a 40–60 cm de la cámara, mirándola de frente.</li>
          <li>Mantente alerta, ojos abiertos, sin bostezos durante toda la captura.</li>
          <li>Si vas a calibrar EMG: conecta los electrodos con gel conductor y
            <strong> desenchufa el cargador de la laptop</strong> (las fuentes
            conmutadas inducen ruido de 60 Hz).</li>
        </ol>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
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
        <div className="space-y-4 mb-6">
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <h3 className="font-semibold text-green-900 mb-2">
              Calibración registrada — Visión (M1)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-green-900/90">
              <Stat label="P_somnolencia base" value={resultado.baseline.p_somnolencia.toFixed(4)} />
              <Stat label="Duración real" value={`${resultado.duracion_real_s.toFixed(2)} s`} />
              <Stat label="Frames procesados" value={String(resultado.frames_procesados)} />
              <Stat label="Ventanas BiLSTM" value={String(resultado.ventanas_inferidas)} />
              {resultado.fps_observado != null && (
                <Stat label="FPS real" value={resultado.fps_observado.toFixed(1)} />
              )}
            </div>
            <p className="text-xs text-green-800/80 mt-3">
              A partir de ahora las evaluaciones de visión corrigen contra esta línea base:
              <code className="ml-1">P_efectiva = max(0, P_obs − {resultado.baseline.p_somnolencia.toFixed(2)})</code>.
            </p>
          </div>

          {/* Resultado M2 */}
          {m2Nuevo?.emg_valido && m2Nuevo.id_baseline && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-5">
              <h3 className="font-semibold text-green-900 mb-2">
                Calibración registrada — Fisiológico (M2)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-green-900/90">
                <Stat label="RMS EMG base" value={`${m2Nuevo.rms_emg?.toFixed(1) ?? '—'} µV`} />
                <Stat label="F. mediana EMG" value={`${m2Nuevo.freq_mediana?.toFixed(1) ?? '—'} Hz`} />
                <Stat label="F. media EMG" value={`${m2Nuevo.freq_media?.toFixed(1) ?? '—'} Hz`} />
                <Stat label="SDNN" value={m2Nuevo.sdnn != null ? `${m2Nuevo.sdnn.toFixed(1)} ms` : '—'} />
                <Stat label="RMSSD" value={m2Nuevo.rmssd != null ? `${m2Nuevo.rmssd.toFixed(1)} ms` : '—'} />
                <Stat label="pNN50" value={m2Nuevo.pnn50 != null ? `${m2Nuevo.pnn50.toFixed(1)}%` : '—'} />
                {m2Nuevo.emg_ratio_60hz != null && (
                  <Stat
                    label="Ruido 60 Hz residual"
                    value={`${(m2Nuevo.emg_ratio_60hz * 100).toFixed(1)}%`}
                  />
                )}
                <Stat label="Muestras EMG" value={String(m2Nuevo.n_muestras_emg)} />
              </div>
              <p className="text-xs text-green-800/80 mt-3">
                Las 7 reglas del sistema experto difuso M2 evaluarán cada captura
                contra estos valores personales.
              </p>
            </div>
          )}

          {m2Nuevo && !m2Nuevo.emg_valido && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-900">
              <p className="font-semibold mb-2">
                Baseline fisiológico (M2) <strong>no</strong> se registró
              </p>
              {!m2Nuevo.arduino_detectado ? (
                <p>
                  No se detectó Arduino conectado. Para calibrar el módulo
                  fisiológico, conecta el shield EKG-EMG por USB y reintenta la
                  calibración.
                </p>
              ) : (
                <>
                  <p>
                    Motivo: {m2Nuevo.emg_motivo ?? 'señal EMG no válida'}
                    {m2Nuevo.emg_ratio_60hz != null &&
                      ` — ${(m2Nuevo.emg_ratio_60hz * 100).toFixed(1)}% de ruido en 60 Hz`}
                    .
                  </p>
                  <p className="mt-2 text-amber-800/80">
                    Pasos sugeridos: desenchufa el cargador de la laptop, aplica
                    gel conductor a los electrodos, verifica que el electrodo de
                    referencia esté sobre hueso (codo o muñeca), y reduce la
                    longitud del cable.
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {step === 'error' && error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <p className="font-semibold mb-1">No se pudo completar la calibración</p>
          <p>{error}</p>
        </div>
      )}

      {step === 'invalid' && error && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 text-sm text-amber-900">
          <div className="flex items-start gap-3 mb-3">
            <span className="text-2xl leading-none">⚠</span>
            <div>
              <p className="font-semibold text-base mb-1">
                Calibración rechazada — baseline NO registrado
              </p>
              <p className="text-amber-800/90 text-xs">
                El sistema no validó la captura como un sujeto vivo y atento
                frente a la cámara. Tu baseline anterior (si lo tienes) sigue
                vigente. Razones detectadas:
              </p>
            </div>
          </div>
          <ul className="space-y-1 ml-9 list-disc list-inside">
            {error
              .replace(/^Calibración rechazada:\s*/, '')
              .split('|')
              .map((razon, i) => (
                <li key={i}>{razon.trim()}</li>
              ))}
          </ul>
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

function DlRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-mono text-slate-800 text-right">{value}</dd>
    </div>
  )
}
