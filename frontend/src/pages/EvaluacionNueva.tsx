import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { createEvaluacion } from '../api/evaluaciones.api'
import type { Dictamen, EvaluacionCreate } from '../types'

type Step = 'form' | 'loading' | 'error'

const dictamenOpciones: { value: Dictamen; label: string }[] = [
  { value: 'APTO', label: 'APTO' },
  { value: 'ATENCION', label: 'ATENCIÓN' },
  { value: 'NO_APTO', label: 'NO APTO' },
]

export default function EvaluacionNueva() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('form')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Resultado de fusión (M3)
  const [dictamen, setDictamen] = useState<Dictamen>('APTO')
  const [pSomnolencia, setPSomnolencia] = useState('0.15')
  const [pFatigaFisiologica, setPFatigaFisiologica] = useState('0.10')
  const [pTotal, setPTotal] = useState('0.75')
  const [umbralUsado, setUmbralUsado] = useState('0.50')
  const [duracionCaptura, setDuracionCaptura] = useState('60')

  // Features conductuales (schema libre → JSONB)
  const [earPromedio, setEarPromedio] = useState('0.28')
  const [marPromedio, setMarPromedio] = useState('0.02')
  const [perclos, setPerclos] = useState('0.05')
  const [blinkRate, setBlinkRate] = useState('18.0')
  const [headPitch, setHeadPitch] = useState('2.1')
  const [headYaw, setHeadYaw] = useState('1.5')
  const [microsleepCount, setMicrosleepCount] = useState('0')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setStep('loading')

    const payload: EvaluacionCreate = {
      dictamen,
      p_somnolencia: parseFloat(pSomnolencia),
      p_fatiga_fisiologica: parseFloat(pFatigaFisiologica),
      p_total: parseFloat(pTotal),
      umbral_usado: parseFloat(umbralUsado),
      duracion_captura_s: parseInt(duracionCaptura, 10),
      features_conductuales: {
        ear_promedio: parseFloat(earPromedio),
        mar_promedio: parseFloat(marPromedio),
        perclos: parseFloat(perclos),
        blink_rate: parseFloat(blinkRate),
        head_pitch: parseFloat(headPitch),
        head_yaw: parseFloat(headYaw),
        microsleep_count: parseInt(microsleepCount, 10),
        video_duration_s: parseInt(duracionCaptura, 10),
      },
      metadatos: {
        fuente: 'manual_frontend',
        version_modelo: '1.0',
      },
    }

    try {
      const evaluacion = await createEvaluacion(payload)
      navigate(`/evaluaciones/${evaluacion.id_evaluacion}`)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al registrar la evaluación'
      setErrorMsg(msg)
      setStep('error')
    }
  }

  if (step === 'loading') {
    return (
      <div className="flex items-center justify-center h-full p-12">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600 font-medium">Procesando evaluación...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Nueva Evaluación</h1>
        <p className="text-slate-500 text-sm mt-1">
          Ingresa los datos calculados por el script local de detección
        </p>
      </div>

      {step === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 mb-4">
          {errorMsg}
          <button
            onClick={() => setStep('form')}
            className="ml-3 underline text-red-600 hover:text-red-800"
          >
            Reintentar
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Resultado fusión M3 */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900 mb-4">Resultado de fusión tardía (M3)</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Dictamen</label>
              <div className="flex gap-3">
                {dictamenOpciones.map((op) => (
                  <label
                    key={op.value}
                    className={`flex-1 flex items-center justify-center px-4 py-2.5 rounded-lg border-2 cursor-pointer text-sm font-semibold transition-all ${
                      dictamen === op.value
                        ? op.value === 'APTO'
                          ? 'border-green-500 bg-green-50 text-green-700'
                          : op.value === 'ATENCION'
                          ? 'border-yellow-500 bg-yellow-50 text-yellow-700'
                          : 'border-red-500 bg-red-50 text-red-700'
                        : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="dictamen"
                      value={op.value}
                      checked={dictamen === op.value}
                      onChange={() => setDictamen(op.value)}
                      className="sr-only"
                    />
                    {op.label}
                  </label>
                ))}
              </div>
            </div>

            {[
              { label: 'P(Somnolencia) — M1', value: pSomnolencia, setter: setPSomnolencia },
              { label: 'P(Fatiga fisiológica) — M2', value: pFatigaFisiologica, setter: setPFatigaFisiologica },
              { label: 'P(Total fusión) — M3', value: pTotal, setter: setPTotal },
              { label: 'Umbral de decisión', value: umbralUsado, setter: setUmbralUsado },
            ].map(({ label, value, setter }) => (
              <div key={label}>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.001"
                  value={value}
                  onChange={(e) => setter(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Duración captura (s)
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={duracionCaptura}
                onChange={(e) => setDuracionCaptura(e.target.value)}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Features conductuales (schema libre) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900 mb-1">Features conductuales (M1 — Visión)</h2>
          <p className="text-xs text-slate-400 mb-4">Almacenadas como JSON libre en la BD</p>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'EAR promedio', value: earPromedio, setter: setEarPromedio },
              { label: 'MAR promedio', value: marPromedio, setter: setMarPromedio },
              { label: 'PERCLOS', value: perclos, setter: setPerclos },
              { label: 'Blink rate (rpm)', value: blinkRate, setter: setBlinkRate },
              { label: 'Head pitch (°)', value: headPitch, setter: setHeadPitch },
              { label: 'Head yaw (°)', value: headYaw, setter: setHeadYaw },
              { label: 'Microsueños (#)', value: microsleepCount, setter: setMicrosleepCount },
            ].map(({ label, value, setter }) => (
              <div key={label}>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
                <input
                  type="number"
                  step="any"
                  value={value}
                  onChange={(e) => setter(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-5 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Registrar evaluación
          </button>
        </div>
      </form>
    </div>
  )
}
