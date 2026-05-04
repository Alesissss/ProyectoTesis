"""
Módulo 2 — Motor de reglas fisiológicas
Sistema de detección de somnolencia y fatiga mental — VigilanceAI
USAT 2025 · Caso NOR VISIÓN, Chiclayo

Entradas:
  - features_emg: RMS, freq_mediana, freq_media  (del sensor Olimex/Arduino)
  - features_hrv: SDNN, RMSSD, pNN50             (del rPPG sobre el video)
  - baseline:     valores de referencia personales capturados en calibración

Salida:
  - p_fatiga: float ∈ [0, 1]     (probabilidad de fatiga fisiológica)
  - detalle:  dict                (contribución individual de cada regla)

RNF-03: detectar RMS >20 % vs baseline O caída freq_mediana >15 % vs baseline.
"""

from __future__ import annotations
from dataclasses import dataclass
import math


# ─── Estructuras de datos ────────────────────────────────────────────────────

@dataclass
class FeaturesEMG:
    rms: float          # µV RMS del trapecio superior (señal filtrada)
    freq_mediana: float # Hz — frecuencia mediana de la señal EMG
    freq_media: float   # Hz — frecuencia media de la señal EMG


@dataclass
class FeaturesHRV:
    sdnn: float         # ms — desviación estándar de intervalos NN
    rmssd: float        # ms — raíz cuadrada de la media de diferencias
    pnn50: float        # %  — porcentaje de diferencias NN > 50 ms


@dataclass
class Baseline:
    # EMG
    rms_emg: float
    freq_mediana: float
    freq_media: float
    # HRV (opcionales; si son None se omite la regla)
    sdnn: float | None = None
    rmssd: float | None = None
    pnn50: float | None = None


@dataclass
class ResultadoM2:
    p_fatiga: float              # probabilidad de fatiga ∈ [0, 1]
    dictamen_parcial: str        # 'BAJO' | 'MODERADO' | 'ALTO'
    reglas: dict[str, float]     # contribución individual de cada regla
    alertas: list[str]           # reglas que superaron sus umbrales


# ─── Umbrales (según literatura + RNF-03 de la tesis) ────────────────────────

# EMG — umbrales expresados como cambio relativo al baseline
UMBRAL_RMS_INCREMENTO  = 0.20   # +20 % → carga muscular elevada (fatiga temprana)
UMBRAL_RMS_DECREMENTO  = 0.25   # -25 % → fatiga avanzada (agotamiento)
UMBRAL_FREQ_MED_CAIDA  = 0.15   # -15 % → desplazamiento espectral por fatiga (RNF-03)
UMBRAL_FREQ_MEDIA_CAIDA = 0.15  # -15 % → idem para frecuencia media

# HRV — umbrales de reducción relativa respecto al baseline
UMBRAL_SDNN_CAIDA  = 0.20       # -20 % → reducción de variabilidad autonómica
UMBRAL_RMSSD_CAIDA = 0.20       # -20 % → retiro parasimpático
UMBRAL_PNN50_CAIDA = 0.25       # -25 % → predominio simpático (estrés/fatiga)

# Pesos de cada regla en la puntuación final (deben sumar 1.0)
PESOS = {
    "rms_incremento":   0.15,   # carga EMG aumentada
    "rms_decremento":   0.10,   # fatiga EMG avanzada
    "freq_mediana":     0.30,   # desplazamiento espectral (indicador más robusto)
    "freq_media":       0.10,   # confirmación del desplazamiento
    "sdnn":             0.15,   # variabilidad cardíaca global
    "rmssd":            0.12,   # control parasimpático
    "pnn50":            0.08,   # predominio simpático
}

assert abs(sum(PESOS.values()) - 1.0) < 1e-9, "Los pesos deben sumar 1.0"

# Umbrales de dictamen parcial sobre p_fatiga
UMBRAL_BAJO     = 0.30
UMBRAL_MODERADO = 0.55


# ─── Función de activación suave (sigmoide desplazada) ───────────────────────

def _activacion(desviacion: float, umbral: float, k: float = 12.0) -> float:
    """
    Retorna 0 si no hay desviación significativa, y se acerca a 1 cuando la
    desviación excede el umbral. Usa una sigmoide centrada en el umbral.

    desviacion: valor positivo (ya sea incremento o caída absoluta relativa)
    umbral:     punto de inflexión (valor de RNF-03)
    k:          pendiente de la sigmoide (más alto = transición más abrupta)
    """
    if desviacion <= 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-k * (desviacion - umbral)))


# ─── Motor de reglas ──────────────────────────────────────────────────────────

def calcular_p_fatiga(
    emg: FeaturesEMG,
    baseline: Baseline,
    hrv: FeaturesHRV | None = None,
) -> ResultadoM2:
    """
    Aplica el motor de reglas fisiológicas y devuelve P(fatiga) ∈ [0, 1].

    Si hrv es None (el módulo rPPG no está disponible), los pesos HRV se
    redistribuyen automáticamente entre las reglas EMG.
    """
    scores: dict[str, float] = {}
    alertas: list[str] = []

    # ── Reglas EMG ────────────────────────────────────────────────────────────

    # 1. Incremento de RMS: fatiga muscular temprana / mayor reclutamiento
    delta_rms = (emg.rms - baseline.rms_emg) / (baseline.rms_emg + 1e-9)
    scores["rms_incremento"] = _activacion(delta_rms, UMBRAL_RMS_INCREMENTO)
    if delta_rms >= UMBRAL_RMS_INCREMENTO:
        alertas.append(f"RMS EMG aumentó {delta_rms*100:.1f}% (umbral: +{UMBRAL_RMS_INCREMENTO*100:.0f}%)")

    # 2. Decremento de RMS: fatiga avanzada / agotamiento muscular
    caida_rms = (baseline.rms_emg - emg.rms) / (baseline.rms_emg + 1e-9)
    scores["rms_decremento"] = _activacion(caida_rms, UMBRAL_RMS_DECREMENTO)
    if caida_rms >= UMBRAL_RMS_DECREMENTO:
        alertas.append(f"RMS EMG disminuyó {caida_rms*100:.1f}% (umbral: -{UMBRAL_RMS_DECREMENTO*100:.0f}%)")

    # 3. Caída de frecuencia mediana (RNF-03 — indicador principal)
    caida_fmed = (baseline.freq_mediana - emg.freq_mediana) / (baseline.freq_mediana + 1e-9)
    scores["freq_mediana"] = _activacion(caida_fmed, UMBRAL_FREQ_MED_CAIDA)
    if caida_fmed >= UMBRAL_FREQ_MED_CAIDA:
        alertas.append(f"Frec. mediana EMG cayó {caida_fmed*100:.1f}% (umbral: -{UMBRAL_FREQ_MED_CAIDA*100:.0f}%)")

    # 4. Caída de frecuencia media
    caida_fmedia = (baseline.freq_media - emg.freq_media) / (baseline.freq_media + 1e-9)
    scores["freq_media"] = _activacion(caida_fmedia, UMBRAL_FREQ_MEDIA_CAIDA)
    if caida_fmedia >= UMBRAL_FREQ_MEDIA_CAIDA:
        alertas.append(f"Frec. media EMG cayó {caida_fmedia*100:.1f}% (umbral: -{UMBRAL_FREQ_MEDIA_CAIDA*100:.0f}%)")

    # ── Reglas HRV ────────────────────────────────────────────────────────────

    hrv_disponible = (
        hrv is not None
        and baseline.sdnn is not None
        and baseline.rmssd is not None
        and baseline.pnn50 is not None
    )

    if hrv_disponible and hrv is not None:
        assert baseline.sdnn is not None
        assert baseline.rmssd is not None
        assert baseline.pnn50 is not None

        # 5. SDNN: variabilidad cardíaca global
        caida_sdnn = (baseline.sdnn - hrv.sdnn) / (baseline.sdnn + 1e-9)
        scores["sdnn"] = _activacion(caida_sdnn, UMBRAL_SDNN_CAIDA)
        if caida_sdnn >= UMBRAL_SDNN_CAIDA:
            alertas.append(f"SDNN redujo {caida_sdnn*100:.1f}% (umbral: -{UMBRAL_SDNN_CAIDA*100:.0f}%)")

        # 6. RMSSD: control parasimpático
        caida_rmssd = (baseline.rmssd - hrv.rmssd) / (baseline.rmssd + 1e-9)
        scores["rmssd"] = _activacion(caida_rmssd, UMBRAL_RMSSD_CAIDA)
        if caida_rmssd >= UMBRAL_RMSSD_CAIDA:
            alertas.append(f"RMSSD redujo {caida_rmssd*100:.1f}% (umbral: -{UMBRAL_RMSSD_CAIDA*100:.0f}%)")

        # 7. pNN50: predominio simpático
        caida_pnn50 = (baseline.pnn50 - hrv.pnn50) / (max(baseline.pnn50, 1e-9))
        scores["pnn50"] = _activacion(caida_pnn50, UMBRAL_PNN50_CAIDA)
        if caida_pnn50 >= UMBRAL_PNN50_CAIDA:
            alertas.append(f"pNN50 redujo {caida_pnn50*100:.1f}% (umbral: -{UMBRAL_PNN50_CAIDA*100:.0f}%)")

        pesos_activos = PESOS
    else:
        # Sin HRV: redistribuir sus pesos entre reglas EMG proporcionalmente
        scores["sdnn"] = 0.0
        scores["rmssd"] = 0.0
        scores["pnn50"] = 0.0
        peso_hrv_total = PESOS["sdnn"] + PESOS["rmssd"] + PESOS["pnn50"]
        peso_emg_total = 1.0 - peso_hrv_total
        factor = 1.0 / peso_emg_total  # escala los pesos EMG para sumar 1
        pesos_activos = {
            k: (v * factor if k not in ("sdnn", "rmssd", "pnn50") else 0.0)
            for k, v in PESOS.items()
        }

    # ── Puntuación ponderada ──────────────────────────────────────────────────

    p_fatiga = sum(scores[r] * pesos_activos[r] for r in scores)
    p_fatiga = max(0.0, min(1.0, p_fatiga))

    if p_fatiga < UMBRAL_BAJO:
        dictamen_parcial = "BAJO"
    elif p_fatiga < UMBRAL_MODERADO:
        dictamen_parcial = "MODERADO"
    else:
        dictamen_parcial = "ALTO"

    return ResultadoM2(
        p_fatiga=round(p_fatiga, 4),
        dictamen_parcial=dictamen_parcial,
        reglas={r: round(scores[r], 4) for r in scores},
        alertas=alertas,
    )


# ─── Utilidad: crear baseline desde dict del backend ─────────────────────────

def baseline_desde_dict(d: dict) -> Baseline:
    """Convierte la respuesta JSON del backend (/baselines/activo) en Baseline."""
    return Baseline(
        rms_emg=float(d["rms_emg"]),
        freq_mediana=float(d["freq_mediana"]),
        freq_media=float(d["freq_media"]),
        sdnn=float(d["sdnn"]) if d.get("sdnn") is not None else None,
        rmssd=float(d["rmssd"]) if d.get("rmssd") is not None else None,
        pnn50=float(d["pnn50"]) if d.get("pnn50") is not None else None,
    )


# ─── Demo / prueba rápida ─────────────────────────────────────────────────────

if __name__ == "__main__":
    baseline = Baseline(
        rms_emg=45.0,
        freq_mediana=80.0,
        freq_media=85.0,
        sdnn=55.0,
        rmssd=35.0,
        pnn50=18.0,
    )

    # Escenario 1: médico descansado
    emg_ok = FeaturesEMG(rms=46.0, freq_mediana=79.0, freq_media=84.0)
    hrv_ok = FeaturesHRV(sdnn=54.0, rmssd=34.5, pnn50=17.5)
    r1 = calcular_p_fatiga(emg_ok, baseline, hrv_ok)
    print(f"[OK]     P_fatiga={r1.p_fatiga:.3f}  {r1.dictamen_parcial}")

    # Escenario 2: fatiga moderada (RNF-03 activado)
    emg_mod = FeaturesEMG(rms=55.0, freq_mediana=67.0, freq_media=70.0)
    hrv_mod = FeaturesHRV(sdnn=42.0, rmssd=26.0, pnn50=11.0)
    r2 = calcular_p_fatiga(emg_mod, baseline, hrv_mod)
    print(f"[FATIGA] P_fatiga={r2.p_fatiga:.3f}  {r2.dictamen_parcial}")
    for alerta in r2.alertas:
        print(f"  ⚠  {alerta}")

    # Escenario 3: sin HRV disponible
    r3 = calcular_p_fatiga(emg_mod, baseline, hrv=None)
    print(f"[NO-HRV] P_fatiga={r3.p_fatiga:.3f}  {r3.dictamen_parcial}")
