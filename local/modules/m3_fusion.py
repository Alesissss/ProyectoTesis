"""
Módulo 3 — Fusión tardía y dictamen final
Sistema de detección de somnolencia y fatiga mental — VigilanceAI
USAT 2025 · Caso NOR VISIÓN, Chiclayo

Fusión ponderada: 40% visión (M1) + 60% fisiológico (M2)
Regla OR de alta confianza: si cualquier módulo > 0.85 → escalar dictamen.

RF-11: Fusión tardía ponderada (40% visión, 60% fisiológico) + regla OR (>0.85)
RF-12: Clasificar en APTO / ATENCIÓN / NO APTO
RF-13: Mostrar dictamen + probabilidades individuales + justificación
"""

from __future__ import annotations
from dataclasses import dataclass, field

PESO_VISION      = 0.40
PESO_FISIOLOGICO = 0.60
UMBRAL_OR        = 0.85   # si cualquier módulo supera esto → escalar dictamen

# Umbrales de dictamen sobre P_total
UMBRAL_APTO     = 0.35   # < 0.35 → APTO
UMBRAL_ATENCION = 0.60   # 0.35–0.60 → ATENCIÓN, > 0.60 → NO APTO


@dataclass
class ResultadoFusion:
    p_somnolencia:        float
    p_fatiga_fisiologica: float
    p_total:              float
    dictamen:             str          # 'APTO' | 'ATENCION' | 'NO_APTO'
    umbral_usado:         float
    justificacion:        list[str] = field(default_factory=list)
    # Trazabilidad de la corrección por baseline personal (M1).
    p_somnolencia_obs:      float | None = None
    p_somnolencia_baseline: float | None = None


def fusionar(
    p_somnolencia: float,
    p_fatiga_fisiologica: float,
    umbral: float = UMBRAL_APTO,
    p_somnolencia_baseline: float | None = None,
) -> ResultadoFusion:
    """
    Aplica la fusión tardía ponderada y determina el dictamen.

    p_somnolencia            ∈ [0, 1] — salida del Módulo 1 (BiLSTM).
    p_fatiga_fisiologica     ∈ [0, 1] — salida del Módulo 2 (motor de reglas).
    umbral                   umbral de decisión APTO/ATENCIÓN.
    p_somnolencia_baseline   P_somnolencia del sujeto en estado alerta declarado,
                             obtenido durante la calibración M1. Si se provee,
                             se aplica corrección personalizada:
                                 P_efectiva = max(0, P_obs - P_baseline)
                             según el RNF-05 y la tarea 7.5 del Pre Informe
                             (subject-dependence verificada empíricamente).
                             Si es None, se usa P_obs directamente.
    """
    p_obs = p_somnolencia
    if p_somnolencia_baseline is not None:
        p_somnolencia = max(0.0, p_obs - p_somnolencia_baseline)

    p_total = (PESO_VISION * p_somnolencia) + (PESO_FISIOLOGICO * p_fatiga_fisiologica)
    p_total = max(0.0, min(1.0, p_total))

    justificacion: list[str] = []

    # Regla OR de alta confianza (RF-11)
    or_activada = False
    if p_somnolencia > UMBRAL_OR:
        justificacion.append(
            f"P_somnolencia={p_somnolencia:.3f} supera umbral OR ({UMBRAL_OR}): "
            "indicios visuales severos de somnolencia."
        )
        or_activada = True
    if p_fatiga_fisiologica > UMBRAL_OR:
        justificacion.append(
            f"P_fatiga_fisiológica={p_fatiga_fisiologica:.3f} supera umbral OR ({UMBRAL_OR}): "
            "señales fisiológicas severas de fatiga."
        )
        or_activada = True

    if or_activada:
        dictamen = "NO_APTO"
        justificacion.append("Regla OR activada → dictamen escalado a NO APTO.")
    elif p_total < UMBRAL_APTO:
        dictamen = "APTO"
        justificacion.append(
            f"P_total={p_total:.3f} < {UMBRAL_APTO}: "
            "sin señales significativas de somnolencia o fatiga."
        )
    elif p_total < UMBRAL_ATENCION:
        dictamen = "ATENCION"
        justificacion.append(
            f"P_total={p_total:.3f} en rango [{UMBRAL_APTO}, {UMBRAL_ATENCION}): "
            "señales leves. Se recomienda descanso breve."
        )
    else:
        dictamen = "NO_APTO"
        justificacion.append(
            f"P_total={p_total:.3f} ≥ {UMBRAL_ATENCION}: "
            "nivel elevado de fatiga. No continuar con actividades críticas."
        )

    if p_somnolencia_baseline is not None:
        justificacion.append(
            f"Corrección por baseline personal (RNF-05): "
            f"P_obs={p_obs:.3f} - P_baseline={p_somnolencia_baseline:.3f} "
            f"→ P_efectiva={p_somnolencia:.3f}."
        )

    return ResultadoFusion(
        p_somnolencia=round(p_somnolencia, 4),
        p_fatiga_fisiologica=round(p_fatiga_fisiologica, 4),
        p_total=round(p_total, 4),
        dictamen=dictamen,
        umbral_usado=round(umbral, 4),
        justificacion=justificacion,
        p_somnolencia_obs=round(p_obs, 4),
        p_somnolencia_baseline=(
            round(p_somnolencia_baseline, 4) if p_somnolencia_baseline is not None else None
        ),
    )


if __name__ == "__main__":
    casos = [
        (0.10, 0.15, "descansado"),
        (0.45, 0.50, "fatiga moderada"),
        (0.80, 0.75, "fatiga alta"),
        (0.90, 0.40, "somnolencia severa (OR)"),
        (0.30, 0.88, "fatiga fisiológica severa (OR)"),
    ]
    for ps, pf, desc in casos:
        r = fusionar(ps, pf)
        print(f"[{desc:35s}] P_total={r.p_total:.3f} → {r.dictamen}")
        for j in r.justificacion:
            print(f"  → {j}")
