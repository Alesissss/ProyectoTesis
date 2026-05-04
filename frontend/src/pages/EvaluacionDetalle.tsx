import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getEvaluacion } from '../api/evaluaciones.api'
import Semaforo from '../components/Semaforo'
import type { Evaluacion } from '../types'

export default function EvaluacionDetalle() {
  const { id } = useParams<{ id: string }>()
  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getEvaluacion(id)
      .then(setEvaluacion)
      .catch(() => setError('No se encontró la evaluación'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-12">
        <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !evaluacion) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-500 mb-4">{error ?? 'Evaluación no encontrada'}</p>
        <Link to="/dashboard" className="text-blue-600 hover:underline text-sm">
          Volver al dashboard
        </Link>
      </div>
    )
  }

  const fc = evaluacion.features_conductuales as Record<string, number> | undefined
  const fEmg = evaluacion.features_emg as Record<string, unknown> | undefined
  const fHrv = evaluacion.features_hrv as Record<string, number> | undefined

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-5"
      >
        ← Volver al dashboard
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Resultado de evaluación</h1>
        <p className="text-slate-400 text-xs mt-1 font-mono">{evaluacion.id_evaluacion}</p>
        <p className="text-slate-500 text-sm mt-1">
          {new Date(evaluacion.fecha_registro).toLocaleString('es-PE', {
            dateStyle: 'full',
            timeStyle: 'short',
          })}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Semáforo */}
        <div>
          <Semaforo
            dictamen={evaluacion.dictamen}
            pSomnolencia={evaluacion.p_somnolencia}
            pFatigaFisiologica={evaluacion.p_fatiga_fisiologica}
            pTotal={evaluacion.p_total}
          />
        </div>

        {/* Info general */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900 mb-4 text-sm uppercase tracking-wide">
            Parámetros de decisión (M3)
          </h2>
          <dl className="space-y-2 text-sm">
            {[
              ['Umbral usado', (evaluacion.umbral_usado * 100).toFixed(0) + '%'],
              ['Duración captura', evaluacion.duracion_captura_s + ' s'],
              ['P(Somnolencia)', (evaluacion.p_somnolencia * 100).toFixed(2) + '%'],
              ['P(Fatiga fisiológica)', (evaluacion.p_fatiga_fisiologica * 100).toFixed(2) + '%'],
              ['P(Total fusión)', (evaluacion.p_total * 100).toFixed(2) + '%'],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between py-1 border-b border-slate-50 last:border-0">
                <dt className="text-slate-500">{label}</dt>
                <dd className="font-medium text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Features conductuales */}
        {fc && Object.keys(fc).length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-4 text-sm uppercase tracking-wide">
              Features conductuales (M1)
            </h2>
            <dl className="space-y-2 text-sm">
              {[
                ['EAR promedio', typeof fc.ear_promedio === 'number' ? fc.ear_promedio.toFixed(4) : '—'],
                ['MAR promedio', typeof fc.mar_promedio === 'number' ? fc.mar_promedio.toFixed(4) : '—'],
                ['PERCLOS', typeof fc.perclos === 'number' ? (fc.perclos * 100).toFixed(2) + '%' : '—'],
                ['Blink rate', typeof fc.blink_rate === 'number' ? fc.blink_rate.toFixed(1) + ' rpm' : '—'],
                ['Head pitch', typeof fc.head_pitch === 'number' ? fc.head_pitch.toFixed(1) + '°' : '—'],
                ['Head yaw', typeof fc.head_yaw === 'number' ? fc.head_yaw.toFixed(1) + '°' : '—'],
                ['Microsueños', typeof fc.microsleep_count === 'number' ? fc.microsleep_count.toString() : '—'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-1 border-b border-slate-50 last:border-0">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="font-medium text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* Features EMG / HRV raw */}
        {(fEmg || fHrv) && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-4 text-sm uppercase tracking-wide">
              Features fisiológicas (M2)
            </h2>
            <pre className="text-xs text-slate-600 font-mono overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify({ emg: fEmg, hrv: fHrv }, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Metadatos */}
      {evaluacion.metadatos && Object.keys(evaluacion.metadatos).length > 0 && (
        <div className="mt-4 bg-slate-50 rounded-xl border border-slate-200 p-4">
          <h2 className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Metadatos</h2>
          <pre className="text-xs text-slate-600 font-mono overflow-x-auto">
            {JSON.stringify(evaluacion.metadatos, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
