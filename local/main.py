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

from modules.cameras import get_profile, listar_perfiles
from modules.m1_vision import ModuloVision, validar_liveness
from modules.m2_reglas import (
    FeaturesEMG,
    FeaturesHRV,
    Baseline,
    baseline_desde_dict,
    calcular_p_fatiga,
)
from modules.m3_fusion import fusionar

# Marcadores únicos que el backend usa para separar el JSON útil del ruido de
# MediaPipe / TensorFlow Lite / Torch en stdout.
#   • CALIBRACION_RESULT_MARKER → consumido por services/calibracion_service.py
#   • EVALUACION_RESULT_MARKER  → consumido por services/evaluacion_service.py
CALIBRACION_RESULT_MARKER = "===CALIBRACION_RESULT==="
EVALUACION_RESULT_MARKER  = "===EVALUACION_RESULT==="
CAMARAS_RESULT_MARKER     = "===CAMARAS_RESULT==="

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
             camara_id: int | None = None,
             puerto_arduino: str | None = None,
             camera_profile: str | None = None) -> None:

    # Cuando el backend invoca este script por subprocess, lee stdout para
    # extraer el JSON final tras EVALUACION_RESULT_MARKER. Cualquier otro
    # `print()` debe ir a stderr para no contaminar el JSON. Redirigimos
    # stdout → stderr durante toda la rutina y restauramos al final solo
    # para emitir el marcador + JSON en el stdout real.
    _stdout_real = sys.stdout
    sys.stdout = sys.stderr

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

    cam = get_profile(camera_profile)
    print(f"       Cámara: {cam.name} (idx={cam.index}, "
          f"{cam.width}x{cam.height}@{cam.fps_request}, real ~{cam.fps_real})")
    m1 = ModuloVision(ruta_modelo=MODELO_M1_PATH, duracion_s=duracion_s, camera=cam)
    resultado_m1 = m1.capturar_y_evaluar(camara_id=camara_id)

    if puerto_arduino:
        hilo_emg.join(timeout=duracion_s + 5)

    # ── Liveness check (anti-spoofing y guardia anti-cámara-vacía) ────────────
    liveness_ok, razones_liveness = validar_liveness(resultado_m1)
    if not liveness_ok:
        print("\n[LIVENESS FAIL] Captura no válida:", file=sys.stderr)
        for r in razones_liveness:
            print(f"  ✗ {r}", file=sys.stderr)
        # Emitir resultado por stdout para que el backend lo traduzca a HTTP 422.
        # NO POSTeamos a /evaluaciones — la captura inválida no contamina la BD.
        resultado_subprocess = {
            "liveness_ok": False,
            "razones_liveness": razones_liveness,
            "duracion_real_s": float(resultado_m1.duracion_s),
            "frames_procesados": int(resultado_m1.frames_procesados),
            "frames_totales":    int(resultado_m1.frames_totales),
            "tasa_deteccion_facial": resultado_m1.features.get("tasa_deteccion_facial", 0.0),
            "parpadeos_detectados": int(resultado_m1.parpadeos_detectados),
            "ear_std": resultado_m1.ear_std,
            "fps_observado": resultado_m1.features.get("fps_observado"),
        }
        sys.stdout = _stdout_real
        print(EVALUACION_RESULT_MARKER)
        print(json.dumps(resultado_subprocess, ensure_ascii=False))
        return

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
            "camara":             cam.name,
            "puerto_arduino":     puerto_arduino,
            "baseline_id":        baseline_dict.get("id_baseline") if baseline_dict else None,
            "hrv_fuente":         "rppg_camara" if resultado_m1.hrv else None,
        },
    }

    print("[4/4] Enviando resultado al backend...")
    respuesta = _post_evaluacion(token, payload)

    # `respuesta` es el ApiResponse envelope: {status, message, data: {...}}.
    # El id está en data.id_evaluacion.
    id_evaluacion: str | None = None
    if respuesta:
        data_eval = respuesta.get("data") if isinstance(respuesta, dict) else None
        if isinstance(data_eval, dict):
            id_evaluacion = data_eval.get("id_evaluacion")
        print(f"      Evaluación registrada: id={id_evaluacion or '?'}")
    else:
        print("      No se pudo registrar. Resultado guardado localmente.")
        with open("resultado_sin_enviar.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("      → resultado_sin_enviar.json")

    # ── Marcador para el backend (subprocess) ────────────────────────────────
    # El JSON debe ir al stdout REAL (no al stderr al que redirigimos arriba).
    resultado_subprocess = {
        "id_evaluacion":     id_evaluacion,
        "dictamen":          resultado_m3.dictamen,
        "p_somnolencia":     resultado_m3.p_somnolencia,
        "p_fatiga_fisiologica": resultado_m3.p_fatiga_fisiologica,
        "p_total":           resultado_m3.p_total,
        "duracion_real_s":   float(resultado_m1.duracion_s),
        "frames_procesados": int(resultado_m1.frames_procesados),
        "fps_observado":     resultado_m1.features.get("fps_observado"),
        "n_muestras_emg":    len(muestras),
        "hrv_disponible":    resultado_m1.hrv is not None,
        "justificacion":     list(resultado_m3.justificacion),
    }
    sys.stdout = _stdout_real
    print(EVALUACION_RESULT_MARKER)
    print(json.dumps(resultado_subprocess, ensure_ascii=False))


# ─── Modo calibración M1 ──────────────────────────────────────────────────────

def ejecutar_calibracion_m1(
    token: str,
    duracion_s: float = 30.0,
    camara_id: int | None = None,
    camera_profile: str | None = None,
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

    cam = get_profile(camera_profile)
    print(f"  Cámara: {cam.name}", file=sys.stderr)
    m1 = ModuloVision(ruta_modelo=MODELO_M1_PATH, duracion_s=duracion_s, camera=cam)
    resultado_m1 = m1.capturar_y_evaluar(camara_id=camara_id)

    # Liveness también aplica a calibración: si está mirando una foto, su
    # baseline sería basura y contaminaría TODAS las futuras evaluaciones.
    liveness_ok, razones_liveness = validar_liveness(resultado_m1)
    if not liveness_ok:
        print("\n[LIVENESS FAIL] Calibración rechazada:", file=sys.stderr)
        for r in razones_liveness:
            print(f"  ✗ {r}", file=sys.stderr)
        resultado = {
            "liveness_ok": False,
            "razones_liveness": razones_liveness,
            "frames_procesados": int(resultado_m1.frames_procesados),
            "frames_totales":    int(resultado_m1.frames_totales),
            "duracion_s":        float(resultado_m1.duracion_s),
            "tasa_deteccion_facial": resultado_m1.features.get("tasa_deteccion_facial", 0.0),
            "parpadeos_detectados": int(resultado_m1.parpadeos_detectados),
            "ear_std": resultado_m1.ear_std,
            "fps_observado": resultado_m1.features.get("fps_observado"),
        }
        print(CALIBRACION_RESULT_MARKER)
        print(json.dumps(resultado, ensure_ascii=False))
        return

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


# ─── Listado de cámaras disponibles ───────────────────────────────────────────

def listar_camaras_disponibles() -> list[dict]:
    """Escanea los índices 0..5 con DSHOW y, en los índices que matchean un
    perfil MSMF conocido, también prueba MSMF. Devuelve cada cámara que
    realmente entrega un frame, etiquetada con el perfil al que corresponde
    (o `null` si es desconocida). El backend invoca esta función vía
    subprocess con `--listar-camaras` y cachea el resultado.
    """
    import cv2  # local import: evita pagar el costo si no se invoca el listado
    from modules.cameras import PROFILES

    encontradas: list[dict] = []

    def _match(idx: int, backend_id: int) -> str | None:
        for nombre, p in PROFILES.items():
            if p.index == idx and p.backend == backend_id:
                return nombre
        return None

    def _probar(idx: int, backend_id: int, backend_label: str) -> None:
        cap = cv2.VideoCapture(idx, backend_id)
        try:
            if not cap.isOpened():
                return
            ret, _ = cap.read()
            if not ret:
                return
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            cap.release()

        profile = _match(idx, backend_id)
        nombre_humano = PROFILES[profile].name if profile else f"Cámara desconocida"
        label = (
            f"{nombre_humano} — idx {idx} ({backend_label}, {w}x{h})"
            if profile
            else f"Cámara {idx} — {backend_label} {w}x{h}"
        )
        encontradas.append({
            "index": idx,
            "backend": backend_label,
            "width": w,
            "height": h,
            "profile": profile,
            "label": label,
        })

    # 1) DSHOW: escaneo rápido de 0..5.
    for idx in range(6):
        _probar(idx, cv2.CAP_DSHOW, "DSHOW")

    # 2) MSMF: solo en índices que algún perfil MSMF declara como suyo.
    msmf_idx = {p.index for p in PROFILES.values() if p.backend == cv2.CAP_MSMF}
    for idx in sorted(msmf_idx):
        _probar(idx, cv2.CAP_MSMF, "MSMF")

    return encontradas


def _emitir_listado_camaras() -> None:
    """Imprime el listado en el formato esperado por el backend."""
    encontradas = listar_camaras_disponibles()
    print(CAMARAS_RESULT_MARKER)
    print(json.dumps(encontradas, ensure_ascii=False))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VigilanceAI — Detección local de somnolencia y fatiga"
    )
    # --listar-camaras es el único modo que NO requiere token (no toca la BD).
    if "--listar-camaras" in sys.argv:
        p.add_argument("--listar-camaras", action="store_true", required=True)
        return p.parse_args()

    p.add_argument("--listar-camaras", action="store_true",
                   help="Lista cámaras disponibles en JSON y sale.")
    p.add_argument("--token",     required=True, help="JWT de acceso del médico")
    p.add_argument("--duracion",  type=float, default=DURACION_S,
                   help="Segundos de captura (default: 30)")
    p.add_argument("--camara",    type=int, default=None,
                   help="Override del índice de cámara sobre el perfil "
                        "(default: el del perfil activo).")
    p.add_argument("--camera-profile", choices=listar_perfiles(), default=None,
                   help="Perfil de cámara: alpcam (producción), gopro (pruebas "
                        "GoPro Hero 11 vía utilidad), webcam (laptop). "
                        "Default: env VIGILANCE_CAMERA_PROFILE o 'alpcam'.")
    p.add_argument("--puerto",    default=None,
                   help="Puerto COM del Arduino (default: auto-detección)")
    p.add_argument("--calibracion-m1", action="store_true",
                   help="Modo calibración M1: captura sujeto alerta y registra "
                        "p_somnolencia_baseline en el backend (no ejecuta evaluación).")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if getattr(args, "listar_camaras", False):
        _emitir_listado_camaras()
        sys.exit(0)
    if args.calibracion_m1:
        ejecutar_calibracion_m1(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
            camera_profile=args.camera_profile,
        )
    else:
        ejecutar(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
            puerto_arduino=args.puerto,
            camera_profile=args.camera_profile,
        )
