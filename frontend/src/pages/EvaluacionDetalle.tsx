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

  // Tabla de reglas del sistema de inferencia difusa (M2).
  // Pesos definidos en local/modules/m2_reglas.py — espejo aquí solo para
  // mostrar el aporte ponderado (μᵢ × wᵢ) de cada regla al P_fatiga.
  const PESOS_M2: Record<string, { peso: number; descripcion: string; fuente: string }> = {
    rms_incremento: { peso: 0.15, descripcion: 'Incremento RMS-EMG (>20% baseline)',  fuente: 'Wijsman [8], Merletti [12]' },
    rms_decremento: { peso: 0.10, descripcion: 'Decremento RMS-EMG (>25% baseline)',  fuente: 'De Luca [13]' },
    freq_mediana:   { peso: 0.30, descripcion: 'Caída frec. mediana EMG (>15%) ★',   fuente: 'Cifrek [10], De Luca [13]' },
    freq_media:     { peso: 0.10, descripcion: 'Caída frec. media EMG (>15%)',       fuente: 'Cifrek [10]' },
    sdnn:           { peso: 0.15, descripcion: 'Caída SDNN (>20% baseline)',          fuente: 'Task Force ESC/NASPE [11]' },
    rmssd:          { peso: 0.12, descripcion: 'Caída RMSSD (>20% baseline)',         fuente: 'Task Force [11]' },
    pnn50:          { peso: 0.08, descripcion: 'Caída pNN50 (>25% baseline)',         fuente: 'Task Force [11]' },
  }
  const reglasM2 = (fEmg?.reglas_m2 ?? null) as Record<string, number> | null

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
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

      {/* Sistema de inferencia difusa M2 — trazabilidad por regla */}
      {reglasM2 && Object.keys(reglasM2).length > 0 && (
        <div className="mt-6 bg-white rounded-2xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900 mb-1 text-sm uppercase tracking-wide">
            Inferencia difusa M2 — aporte por regla
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Sistema tipo Sugeno orden 0: cada regla emite un grado de pertenencia
            μᵢ ∈ [0,1] mediante función sigmoidal centrada en el umbral clínico.
            P_fatiga = Σ wᵢ·μᵢ.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="text-left py-2 pr-3 font-medium">Regla</th>
                  <th className="text-right py-2 px-3 font-medium">Activación μᵢ</th>
                  <th className="text-right py-2 px-3 font-medium">Peso wᵢ</th>
                  <th className="text-right py-2 px-3 font-medium">Aporte μᵢ·wᵢ</th>
                  <th className="text-left py-2 pl-3 font-medium">Base bibliográfica</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {Object.entries(reglasM2).map(([clave, mu]) => {
                  const meta = PESOS_M2[clave]
                  const peso = meta?.peso ?? 0
                  const aporte = mu * peso
                  const activa = mu > 0.5
                  return (
                    <tr key={clave} className={activa ? 'bg-amber-50/60' : ''}>
                      <td className="py-2 pr-3">
                        <p className="font-medium text-slate-800">
                          {meta?.descripcion ?? clave}
                        </p>
                        <p className="text-xs text-slate-400 font-mono">{clave}</p>
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className={`font-mono ${activa ? 'text-amber-700 font-semibold' : 'text-slate-600'}`}>
                          {mu.toFixed(3)}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right text-slate-500 font-mono">
                        {peso.toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className={`font-mono ${aporte > 0.05 ? 'text-amber-700 font-semibold' : 'text-slate-500'}`}>
                          {aporte.toFixed(3)}
                        </span>
                      </td>
                      <td className="py-2 pl-3 text-xs text-slate-500">
                        {meta?.fuente ?? '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot className="border-t-2 border-slate-200 font-semibold">
                <tr>
                  <td className="py-2 pr-3 text-slate-700">P_fatiga (Σ μᵢ·wᵢ)</td>
                  <td colSpan={2}></td>
                  <td className="py-2 px-3 text-right font-mono text-slate-900">
                    {evaluacion.p_fatiga_fisiologica.toFixed(3)}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="text-xs text-slate-400 mt-3">
            Las reglas resaltadas en ámbar tienen activación μᵢ &gt; 0.5
            (indicador clínico disparado). ★ = indicador espectral más robusto
            de fatiga muscular según literatura.
          </p>
        </div>
      )}

      {/* Métricas de liveness — anti-spoofing del M1 */}
      {fc && (fc.tasa_deteccion_facial !== undefined || fc.parpadeos !== undefined) && (
        <div className="mt-6 bg-white rounded-2xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900 mb-1 text-sm uppercase tracking-wide">
            Validación de liveness (anti-spoofing)
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Métricas que demuestran que la captura corresponde a un sujeto vivo
            y consciente, no a una imagen estática o cámara desenfocada.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {fc.tasa_deteccion_facial !== undefined && (
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Detección facial</p>
                <p className="font-mono text-slate-900">{(fc.tasa_deteccion_facial * 100).toFixed(1)}%</p>
                <p className="text-xs text-slate-400">≥ 70% requerido</p>
              </div>
            )}
            {fc.parpadeos !== undefined && (
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Parpadeos</p>
                <p className="font-mono text-slate-900">{fc.parpadeos}</p>
                <p className="text-xs text-slate-400">indica sujeto vivo</p>
              </div>
            )}
            {fc.ear_std !== undefined && (
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">EAR std</p>
                <p className="font-mono text-slate-900">{fc.ear_std.toFixed(4)}</p>
                <p className="text-xs text-slate-400">≥ 0.005 (foto ≈ 0)</p>
              </div>
            )}
            {fHrv?.calidad && (
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">rPPG calidad</p>
                <p className={`font-mono ${fHrv.calidad === 'alta' ? 'text-green-700' : 'text-amber-700'}`}>
                  {String(fHrv.calidad)}
                </p>
                <p className="text-xs text-slate-400">ratio RMSSD/SDNN</p>
              </div>
            )}
          </div>
        </div>
      )}

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
