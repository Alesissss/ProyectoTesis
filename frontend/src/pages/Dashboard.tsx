import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMisEvaluaciones, getAllEvaluaciones } from '../api/evaluaciones.api'
import { useAuthStore } from '../store/auth.store'
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

export default function Dashboard() {
  const { user, hasPermission } = useAuthStore()
  const [evaluaciones, setEvaluaciones] = useState<EvaluacionResumen[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = hasPermission('evaluacion:ver_todas')
      ? getAllEvaluaciones
      : getMisEvaluaciones

    fetch()
      .then(setEvaluaciones)
      .catch(() => setError('No se pudieron cargar las evaluaciones'))
      .finally(() => setLoading(false))
  }, [hasPermission])

  const totals = evaluaciones.reduce(
    (acc, ev) => {
      acc[ev.dictamen] = (acc[ev.dictamen] ?? 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  const recent = [...evaluaciones]
    .sort((a, b) => new Date(b.fecha_registro).getTime() - new Date(a.fecha_registro).getTime())
    .slice(0, 8)

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Bienvenido, {user?.nombre}</h1>
        <p className="text-slate-500 text-sm mt-1">
          {hasPermission('evaluacion:ver_todas')
            ? 'Vista global — todas las evaluaciones del sistema'
            : 'Tus evaluaciones recientes'}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total',     value: evaluaciones.length,    color: 'text-slate-900', bg: 'bg-slate-100' },
          { label: 'Aptos',     value: totals['APTO'] ?? 0,    color: 'text-green-700', bg: 'bg-green-50' },
          { label: 'Atención',  value: totals['ATENCION'] ?? 0, color: 'text-yellow-700', bg: 'bg-yellow-50' },
          { label: 'No Aptos',  value: totals['NO_APTO'] ?? 0, color: 'text-red-700',   bg: 'bg-red-50' },
        ].map((stat) => (
          <div key={stat.label} className={`rounded-xl p-4 ${stat.bg}`}>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{stat.label}</p>
            <p className={`text-3xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {hasPermission('evaluacion:registrar') && (
        <Link
          to="/evaluaciones/nueva"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-lg text-sm mb-6 transition-colors"
        >
          + Registrar nueva evaluación
        </Link>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-900">Evaluaciones recientes</h2>
        </div>

        {loading && <div className="text-center py-10 text-slate-400 text-sm">Cargando...</div>}
        {error && <div className="text-center py-10 text-red-400 text-sm">{error}</div>}

        {!loading && !error && recent.length === 0 && (
          <div className="text-center py-10 text-slate-400 text-sm">
            Sin evaluaciones registradas aún.
          </div>
        )}

        {!loading && !error && recent.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Fecha</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Dictamen</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">P(Total)</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Detalle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recent.map((ev) => (
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
        )}
      </div>
    </div>
  )
}
