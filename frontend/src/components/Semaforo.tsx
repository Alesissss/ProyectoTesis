import type { Dictamen } from '../types'

const config: Record<Dictamen, { color: string; bg: string; label: string; desc: string }> = {
  APTO: {
    color: 'text-green-700',
    bg: 'bg-green-100 border-green-300',
    label: 'APTO',
    desc: 'El personal evaluado se encuentra en condiciones óptimas para operar.',
  },
  ATENCION: {
    color: 'text-yellow-700',
    bg: 'bg-yellow-100 border-yellow-300',
    label: 'ATENCIÓN',
    desc: 'Se detectan señales leves de fatiga. Se recomienda descanso breve.',
  },
  NO_APTO: {
    color: 'text-red-700',
    bg: 'bg-red-100 border-red-300',
    label: 'NO APTO',
    desc: 'Nivel de fatiga elevado. No se recomienda continuar con actividades críticas.',
  },
}

interface SemaforoProps {
  dictamen: Dictamen
  pSomnolencia?: number
  pFatigaFisiologica?: number
  pTotal?: number
}

export default function Semaforo({ dictamen, pSomnolencia, pFatigaFisiologica, pTotal }: SemaforoProps) {
  const c = config[dictamen]

  return (
    <div className={`rounded-2xl border-2 p-8 text-center ${c.bg}`}>
      {/* Luces del semáforo */}
      <div className="flex flex-col items-center gap-3 mb-6">
        <div className={`w-20 h-20 rounded-full border-4 border-white shadow-lg ${dictamen === 'NO_APTO' ? 'bg-red-500 shadow-red-300' : 'bg-red-200'}`} />
        <div className={`w-20 h-20 rounded-full border-4 border-white shadow-lg ${dictamen === 'ATENCION' ? 'bg-yellow-400 shadow-yellow-300' : 'bg-yellow-100'}`} />
        <div className={`w-20 h-20 rounded-full border-4 border-white shadow-lg ${dictamen === 'APTO' ? 'bg-green-500 shadow-green-300' : 'bg-green-200'}`} />
      </div>

      <h2 className={`text-3xl font-bold mb-2 ${c.color}`}>{c.label}</h2>
      <p className="text-slate-600 text-sm max-w-xs mx-auto">{c.desc}</p>

      {(pSomnolencia !== undefined || pFatigaFisiologica !== undefined || pTotal !== undefined) && (
        <div className="mt-6 grid grid-cols-3 gap-3 text-sm">
          {pSomnolencia !== undefined && (
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-slate-500 text-xs uppercase tracking-wide">Somnolencia</p>
              <p className={`text-xl font-bold ${c.color}`}>{(pSomnolencia * 100).toFixed(1)}%</p>
            </div>
          )}
          {pFatigaFisiologica !== undefined && (
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-slate-500 text-xs uppercase tracking-wide">Fatiga fisiol.</p>
              <p className={`text-xl font-bold ${c.color}`}>{(pFatigaFisiologica * 100).toFixed(1)}%</p>
            </div>
          )}
          {pTotal !== undefined && (
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-slate-500 text-xs uppercase tracking-wide">Fusión (M3)</p>
              <p className={`text-xl font-bold ${c.color}`}>{(pTotal * 100).toFixed(1)}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
