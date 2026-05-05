import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMisEvaluaciones } from '../api/evaluaciones.api'
import type { EvaluacionResumen } from '../types'

const dictamenStyle: Record<string, string> = {
  APTO: 'bg-green-100 text-green-700',
  ATENCION: 'bg-yellow-100 text-yellow-700',
  NO_APTO: 'bg-red-100 text-red-700',
}

const dictamenLabel: Record<string, string> = {
  APTO: 'Apto',
  ATENCION: 'Atención',
  NO_APTO: 'No Apto',
}

export default function MisEvaluaciones() {
  const [evaluaciones, setEvaluaciones] = useState<EvaluacionResumen[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMisEvaluaciones()
      .then((data) =>
        setEvaluaciones(
          [...data].sort(
            (a, b) => new Date(b.fecha_registro).getTime() - new Date(a.fecha_registro).getTime()
          )
        )
      )
      .catch(() => setError('No se pudieron cargar las evaluaciones'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Mis Evaluaciones</h1>
          <p className="text-slate-500 text-sm mt-1">Historial completo de tus evaluaciones</p>
        </div>
        <Link
          to="/evaluaciones/iniciar"
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors text-center sm:text-left whitespace-nowrap"
        >
          ▶ Iniciar evaluación
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading && <div className="text-center py-10 text-slate-400 text-sm">Cargando...</div>}
        {error && <div className="text-center py-10 text-red-400 text-sm">{error}</div>}

        {!loading && !error && evaluaciones.length === 0 && (
          <div className="text-center py-10 text-slate-400 text-sm">
            No tienes evaluaciones registradas.
            <Link to="/evaluaciones/iniciar" className="block mt-2 text-blue-600 hover:underline">
              Iniciar primera evaluación →
            </Link>
          </div>
        )}

        {!loading && !error && evaluaciones.length > 0 && (
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[480px]">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Fecha</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Dictamen</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">P(Total)</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Detalle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {evaluaciones.map((ev) => (
                <tr key={ev.id_evaluacion} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3 text-slate-600">
                    {new Date(ev.fecha_registro).toLocaleString('es-PE', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${dictamenStyle[ev.dictamen]}`}>
                      {dictamenLabel[ev.dictamen]}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    {(ev.p_total * 100).toFixed(1)}%
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Link
                      to={`/evaluaciones/${ev.id_evaluacion}`}
                      className="text-blue-600 hover:underline text-xs font-medium"
                    >
                      Ver →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  )
}
