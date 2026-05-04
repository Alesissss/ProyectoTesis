"""
VigilanceAI — Script local de detección
USAT 2025 · Caso NOR VISIÓN, Chiclayo

Orquestador principal. Ejecutar desde la laptop del consultorio:
    python main.py --token <JWT> [--duracion 30] [--camara 0] [--puerto COM3]

Cámara: ALPCAM AR0234 USB — 1200P, 90 fps, obturador global.
  Uso dual durante la captura:
    • M1: EAR+MAR por frame → BiLSTM (lstm_A_subjindep_best.pt, Estrategia A — la única honesta) → P_somnolencia
    • M2-rPPG: canal verde ROI frente → SDNN, RMSSD, pNN50 → reglas fisiológicas

Flujo:
  1. Autenticación (lee JWT o lo solicita)
  2. Descarga baseline personal desde el backend
  3. Captura simultánea: cámara ALPCAM (M1+rPPG) + Arduino sEMG (M2-EMG)
  4. Motor de reglas M2 (EMG + rPPG/HRV)
  5. Fusión tardía M3
  6. POST resultado al backend
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

import requests
import serial
import serial.tools.list_ports

from modules.m1_vision import ModuloVision
from modules.m2_reglas import (
    FeaturesEMG,
    FeaturesHRV,
    Baseline,
    baseline_desde_dict,
    calcular_p_fatiga,
)
from modules.m3_fusion import fusionar

# Marcador único que el backend (services/calibracion_service.py) usa para
# separar el JSON final del ruido de MediaPipe / TensorFlow Lite en stdout.
CALIBRACION_RESULT_MARKER = "===CALIBRACION_RESULT==="

# ─── Configuración ────────────────────────────────────────────────────────────

BACKEND_URL    = os.getenv("VIGILANCE_BACKEND", "http://localhost:8000/api")
MODELO_M1_PATH = Path(__file__).parent / "modelos" / "lstm_A_subjindep_best.pt"
BAUD_RATE      = 115200
DURACION_S     = 30.0


# ─── Adquisición EMG desde Arduino ───────────────────────────────────────────

def _detectar_puerto_arduino() -> str | None:
    """Detecta automáticamente el puerto serie del Arduino UNO."""
    for port in serial.tools.list_ports.comports():
        desc = (port.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "cp210" in desc or "ftdi" in desc:
            return port.device
    return None


def _leer_emg_arduino(puerto: str, duracion_s: float,
                       cola: queue.Queue) -> None:
    """
    Hilo lector: parsea líneas CSV del Arduino con formato:
        <timestamp_ms>,<valor_emg_uV>
    y deposita los valores en la cola compartida.
    """
    try:
        ser = serial.Serial(puerto, BAUD_RATE, timeout=1.0)
        time.sleep(2.0)  # esperar reset del Arduino tras apertura del puerto
        t_fin = time.time() + duracion_s
        while time.time() < t_fin:
            linea = ser.readline().decode("ascii", errors="ignore").strip()
            if "," in linea:
                partes = linea.split(",")
                if len(partes) >= 2:
                    try:
                        valor = float(partes[1])
                        cola.put(valor)
                    except ValueError:
                        pass
        ser.close()
    except Exception as exc:
        cola.put(exc)


def _procesar_senal_emg(muestras: list[float], fs: float = 500.0) -> FeaturesEMG:
    """
    Calcula RMS, frecuencia mediana y frecuencia media de la señal EMG filtrada.
    La señal ya llega filtrada por el Arduino (Butterworth ord. 4, 20–200 Hz).
    """
    import numpy as np
    from numpy.fft import rfft, rfftfreq

    sig = np.array(muestras, dtype=np.float64)
    if len(sig) == 0:
        return FeaturesEMG(rms=0.0, freq_mediana=0.0, freq_media=0.0)

    rms = float(np.sqrt(np.mean(sig ** 2)))

    # Espectro de potencia
    fft_vals = np.abs(rfft(sig)) ** 2
    freqs    = rfftfreq(len(sig), d=1.0 / fs)

    # Restringir a banda 20–200 Hz
    mask = (freqs >= 20) & (freqs <= 200)
    pwr  = fft_vals[mask]
    f    = freqs[mask]

    if pwr.sum() == 0:
        return FeaturesEMG(rms=rms, freq_mediana=0.0, freq_media=0.0)

    pwr_acum = np.cumsum(pwr)
    idx_med  = np.searchsorted(pwr_acum, pwr_acum[-1] / 2.0)
    freq_med = float(f[idx_med]) if idx_med < len(f) else 0.0
    freq_mean = float(np.average(f, weights=pwr))

    return FeaturesEMG(rms=rms, freq_mediana=freq_med, freq_media=freq_mean)


# ─── Backend API helpers ──────────────────────────────────────────────────────

def _get_baseline(token: str) -> dict | None:
    try:
        r = requests.get(
            f"{BACKEND_URL}/baselines/activo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _get_baseline_somnolencia(token: str) -> dict | None:
    """Descarga el baseline personal de M1. None si no hay calibración aún."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/baselines/somnolencia/activo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 200:
            payload = r.json()
            # ApiResponse envuelve en {data: {...}} — soportar ambos formatos.
            return payload.get("data") if "data" in payload else payload
    except Exception:
        pass
    return None


def _post_evaluacion(token: str, payload: dict) -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/evaluaciones",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return r.json()
        print(f"[ERROR] Backend devolvió {r.status_code}: {r.text}")
    except Exception as exc:
        print(f"[ERROR] No se pudo conectar al backend: {exc}")
    return None


# ─── Rutina principal ─────────────────────────────────────────────────────────

def ejecutar(token: str, duracion_s: float = DURACION_S,
             camara_id: int = 0, puerto_arduino: str | None = None) -> None:

    print("\n═══════════════════════════════════════")
    print("  VigilanceAI — Detección en curso")
    print(f"  Duración: {duracion_s:.0f} s")
    print("═══════════════════════════════════════\n")

    # ── 1. Baselines personales (EMG/HRV + somnolencia) ──────────────────────
    print("[1/4] Descargando baseline personal...")
    baseline_dict = _get_baseline(token)
    if baseline_dict is None:
        print("[AVISO] Sin baseline EMG. M2 usará valores por defecto.")
        baseline = Baseline(rms_emg=50.0, freq_mediana=80.0, freq_media=85.0)
    else:
        baseline = baseline_desde_dict(baseline_dict)
        print(f"       RMS baseline={baseline.rms_emg:.1f} µV, "
              f"F_mediana={baseline.freq_mediana:.1f} Hz")

    baseline_somn = _get_baseline_somnolencia(token)
    p_baseline_somn: float | None = None
    if baseline_somn:
        p_baseline_somn = float(baseline_somn.get("p_somnolencia", 0.0))
        print(f"       P_somnolencia baseline = {p_baseline_somn:.3f}")
    else:
        print("[AVISO] Sin baseline de somnolencia (M1). El dictamen NO aplicará "
              "corrección personalizada — recomendado calibrar primero.")

    # ── 2. Detectar Arduino ───────────────────────────────────────────────────
    if puerto_arduino is None:
        puerto_arduino = _detectar_puerto_arduino()
    if puerto_arduino:
        print(f"[2/4] Arduino detectado en {puerto_arduino}")
    else:
        print("[2/4] Arduino no encontrado. M2 operará sin EMG.")

    # ── 3. Captura paralela: cámara (M1) + Arduino EMG ───────────────────────
    print(f"[3/4] Capturando {duracion_s:.0f} s de video y señal EMG...")

    cola_emg: queue.Queue = queue.Queue()

    if puerto_arduino:
        hilo_emg = threading.Thread(
            target=_leer_emg_arduino,
            args=(puerto_arduino, duracion_s, cola_emg),
            daemon=True,
        )
        hilo_emg.start()

    m1 = ModuloVision(ruta_modelo=MODELO_M1_PATH, duracion_s=duracion_s)
    resultado_m1 = m1.capturar_y_evaluar(camara_id=camara_id)

    if puerto_arduino:
        hilo_emg.join(timeout=duracion_s + 5)

    # ── 4. Procesar EMG y calcular M2 ─────────────────────────────────────────
    muestras: list[float] = []
    while not cola_emg.empty():
        item = cola_emg.get()
        if isinstance(item, float):
            muestras.append(item)

    # Convertir rPPG de la cámara a FeaturesHRV para M2 (si está disponible)
    hrv_feat: FeaturesHRV | None = None
    if resultado_m1.hrv is not None:
        hrv_data = resultado_m1.hrv
        hrv_feat = FeaturesHRV(
            sdnn=hrv_data.get("sdnn", 0.0),
            rmssd=hrv_data.get("rmssd", 0.0),
            pnn50=hrv_data.get("pnn50", 0.0),
        )
        print(f"       rPPG/HRV: SDNN={hrv_feat.sdnn:.1f} ms, "
              f"RMSSD={hrv_feat.rmssd:.1f} ms, pNN50={hrv_feat.pnn50:.1f}%")
    else:
        print("[AVISO] rPPG/HRV no disponible (señal insuficiente).")

    if muestras:
        emg_feat = _procesar_senal_emg(muestras)
        resultado_m2 = calcular_p_fatiga(emg_feat, baseline, hrv=hrv_feat)
        print(f"       EMG: RMS={emg_feat.rms:.1f} µV, "
              f"F_mediana={emg_feat.freq_mediana:.1f} Hz")
        for alerta in resultado_m2.alertas:
            print(f"       ⚠  {alerta}")
    else:
        print("[AVISO] Sin datos EMG. M2 operará solo con rPPG si está disponible.")
        if hrv_feat is not None:
            # Sin EMG pero con rPPG: crear features EMG vacías (no activarán reglas EMG)
            emg_feat = None
            from modules.m2_reglas import FeaturesEMG as _FEMG
            emg_vacio = _FEMG(
                rms=baseline.rms_emg,
                freq_mediana=baseline.freq_mediana,
                freq_media=baseline.freq_media,
            )
            resultado_m2 = calcular_p_fatiga(emg_vacio, baseline, hrv=hrv_feat)
        else:
            from modules.m2_reglas import ResultadoM2
            resultado_m2 = ResultadoM2(
                p_fatiga=0.0, dictamen_parcial="BAJO", reglas={}, alertas=[]
            )
            emg_feat = None

    # ── 5. Fusión tardía M3 (con corrección por baseline si está disponible) ─
    resultado_m3 = fusionar(
        p_somnolencia=resultado_m1.p_somnolencia,
        p_fatiga_fisiologica=resultado_m2.p_fatiga,
        p_somnolencia_baseline=p_baseline_somn,
    )

    print("\n──────────── RESULTADO ─────────────────")
    print(f"  P_somnolencia        = {resultado_m3.p_somnolencia:.3f}")
    print(f"  P_fatiga_fisiológica = {resultado_m3.p_fatiga_fisiologica:.3f}")
    print(f"  P_total (fusión)     = {resultado_m3.p_total:.3f}")
    print(f"  DICTAMEN             = {resultado_m3.dictamen}")
    for j in resultado_m3.justificacion:
        print(f"  → {j}")
    print("────────────────────────────────────────\n")

    # ── 6. Enviar al backend ──────────────────────────────────────────────────
    payload = {
        "p_somnolencia":        resultado_m3.p_somnolencia,
        "p_fatiga_fisiologica": resultado_m3.p_fatiga_fisiologica,
        "p_total":              resultado_m3.p_total,
        "dictamen":             resultado_m3.dictamen,
        "umbral_usado":         resultado_m3.umbral_usado,
        "duracion_captura_s":   int(resultado_m1.duracion_s),
        "features_conductuales": resultado_m1.features,
        "features_emg": {
            "rms":          round(emg_feat.rms, 4) if emg_feat else None,
            "freq_mediana": round(emg_feat.freq_mediana, 4) if emg_feat else None,
            "freq_media":   round(emg_feat.freq_media, 4) if emg_feat else None,
            "n_muestras":   len(muestras),
            "reglas_m2":    resultado_m2.reglas,
        },
        "features_hrv": resultado_m1.hrv,   # rPPG desde cámara ALPCAM AR0234
        "metadatos": {
            "fuente":             "local_script",
            "version_modelo_m1":  "lstm_A_subjindep_best",
            "camara":             "ALPCAM_AR0234_USB_90fps",
            "puerto_arduino":     puerto_arduino,
            "baseline_id":        baseline_dict.get("id_baseline") if baseline_dict else None,
            "hrv_fuente":         "rppg_camara" if resultado_m1.hrv else None,
        },
    }

    print("[4/4] Enviando resultado al backend...")
    respuesta = _post_evaluacion(token, payload)
    if respuesta:
        print(f"      Evaluación registrada: id={respuesta.get('id_evaluacion', '?')}")
    else:
        print("      No se pudo registrar. Resultado guardado localmente.")
        with open("resultado_sin_enviar.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("      → resultado_sin_enviar.json")


# ─── Modo calibración M1 ──────────────────────────────────────────────────────

def ejecutar_calibracion_m1(
    token: str,
    duracion_s: float = 30.0,
    camara_id: int = 1,
) -> None:
    """Captura `duracion_s` segundos del médico en estado alerta declarado y
    POSTea el resultado a /baselines/somnolencia.

    Diseñado para ser llamado tanto desde CLI (`--calibracion-m1`) como desde
    el backend vía subprocess (servicio `CalibracionService`). En el segundo
    caso, el backend captura stdout: por eso el JSON final se imprime detrás
    del marcador `CALIBRACION_RESULT_MARKER` para que sea fácil de extraer
    aunque MediaPipe escupa warnings antes.
    """
    print("\n═══════════════════════════════════════", file=sys.stderr)
    print("  VigilanceAI — Calibración M1", file=sys.stderr)
    print(f"  Mantenete alerta y quieto durante {duracion_s:.0f} s", file=sys.stderr)
    print("═══════════════════════════════════════\n", file=sys.stderr)

    m1 = ModuloVision(ruta_modelo=MODELO_M1_PATH, duracion_s=duracion_s)
    resultado_m1 = m1.capturar_y_evaluar(camara_id=camara_id)

    # POST al backend para persistir el baseline.
    payload_post = {
        "p_somnolencia":     resultado_m1.p_somnolencia,
        "ear_promedio":      resultado_m1.ear_promedio,
        "mar_promedio":      resultado_m1.mar_promedio,
        "duracion_s":        resultado_m1.duracion_s,
        "frames_procesados": resultado_m1.frames_procesados,
    }
    backend_response: dict | None = None
    try:
        r = requests.post(
            f"{BACKEND_URL}/baselines/somnolencia",
            json=payload_post,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            backend_response = r.json()
            print(f"[OK] Baseline registrado en backend.", file=sys.stderr)
        else:
            print(f"[ERROR] Backend devolvió {r.status_code}: {r.text}", file=sys.stderr)
    except Exception as exc:
        print(f"[ERROR] No se pudo POSTear el baseline: {exc}", file=sys.stderr)

    # Imprimir resultado consumible por el backend (subprocess parser).
    resultado = {
        "p_somnolencia":     resultado_m1.p_somnolencia,
        "ear_promedio":      resultado_m1.ear_promedio,
        "mar_promedio":      resultado_m1.mar_promedio,
        "duracion_s":        resultado_m1.duracion_s,
        "frames_procesados": resultado_m1.frames_procesados,
        "ventanas_inferidas": resultado_m1.ventanas_inferidas,
        "fps_observado":     resultado_m1.features.get("fps_observado"),
        "backend_response":  backend_response,
    }
    print(CALIBRACION_RESULT_MARKER)
    print(json.dumps(resultado, ensure_ascii=False))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VigilanceAI — Detección local de somnolencia y fatiga"
    )
    p.add_argument("--token",     required=True, help="JWT de acceso del médico")
    p.add_argument("--duracion",  type=float, default=DURACION_S,
                   help="Segundos de captura (default: 30)")
    p.add_argument("--camara",    type=int, default=0,
                   help="Índice de cámara (default: 0)")
    p.add_argument("--puerto",    default=None,
                   help="Puerto COM del Arduino (default: auto-detección)")
    p.add_argument("--calibracion-m1", action="store_true",
                   help="Modo calibración M1: captura sujeto alerta y registra "
                        "p_somnolencia_baseline en el backend (no ejecuta evaluación).")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.calibracion_m1:
        ejecutar_calibracion_m1(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
        )
    else:
        ejecutar(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
            puerto_arduino=args.puerto,
        )
