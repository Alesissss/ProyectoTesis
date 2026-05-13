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
import base64
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


# ─── Identidad del operador (extraída del JWT sin verificar firma) ───────────
# Solo para estampar `id_usuario` / `email` en el JSON guardado localmente
# (resultado_sin_enviar.json) cuando el POST al backend falla y necesitamos
# saber a quién corresponden los datos al recuperarlos. La verificación de
# firma la hace el backend en cada request — aquí solo leemos el payload.

def _decodificar_jwt(token: str) -> dict:
    try:
        _, payload_b64, _ = token.split(".")
        # base64 URL-safe sin padding → rellenar
        padding = "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


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
        leidas = 0
        while time.time() < t_fin:
            linea = ser.readline().decode("ascii", errors="ignore").strip()
            if "," in linea:
                partes = linea.split(",")
                if len(partes) >= 2:
                    try:
                        valor = float(partes[1])
                        cola.put(valor)
                        leidas += 1
                    except ValueError:
                        pass
        ser.close()
        if leidas == 0:
            # Puerto abierto pero Arduino no envió nada: shield apagado,
            # firmware no flasheado, o baud rate distinto.
            print(f"[EMG] Puerto {puerto} abierto pero 0 líneas leídas en "
                  f"{duracion_s:.0f}s a {BAUD_RATE} baudios.", file=sys.stderr)
    except serial.SerialException as exc:
        print(f"[EMG] No se pudo abrir {puerto}: {exc}", file=sys.stderr)
        cola.put(exc)
    except Exception as exc:
        print(f"[EMG] Error inesperado leyendo {puerto}: {exc}", file=sys.stderr)
        cola.put(exc)


def _procesar_senal_emg(
    muestras: list[float], fs: float = 500.0
) -> tuple[FeaturesEMG | None, dict]:
    """Filtra la señal EMG, calcula features espectrales y valida calidad.

    La señal del Arduino entra en cruda en 20–200 Hz; el filtro pasabanda del
    shield NO elimina el ruido de red (60 Hz cae DENTRO de la banda muscular).
    Aquí aplicamos:
      1) Notch IIR en 60 Hz y su segundo armónico (120 Hz).
      2) Cálculo de RMS y frecuencias en banda muscular útil 20–200 Hz
         (excluyendo bandas notch).
      3) Quality gate: si tras el filtrado la potencia residual en ±5 Hz de
         60 Hz sigue dominando el total → la señal NO es muscular válida
         (electrodos secos, cable largo sin shield, batería baja, etc.) y
         devolvemos (None, calidad) para que el motor M2 la omita y no
         contamine el dictamen con un falso "incremento RMS / caída espectral".

    Devuelve (features | None, calidad), donde calidad tiene:
      valido (bool), ratio_60hz, motivo (str).
    """
    import numpy as np
    from numpy.fft import rfft, rfftfreq
    from scipy.signal import iirnotch, filtfilt

    sig = np.array(muestras, dtype=np.float64)
    calidad: dict = {"valido": False, "ratio_60hz": None, "motivo": ""}

    if len(sig) < int(fs):  # menos de 1 segundo de señal
        calidad["motivo"] = "captura demasiado corta"
        return None, calidad

    # ── 1) Notch 60 Hz y 120 Hz ──────────────────────────────────────────────
    # Q=30 da un ancho ~2 Hz, suficiente para la red sin tocar 50/70/110/130.
    for f0 in (60.0, 120.0):
        if f0 < fs / 2:
            b, a = iirnotch(w0=f0 / (fs / 2), Q=30.0)
            sig = filtfilt(b, a, sig)

    # ── 2) Quality gate: medir potencia residual en 60 Hz ────────────────────
    fft_full = np.abs(rfft(sig)) ** 2
    freqs_full = rfftfreq(len(sig), d=1.0 / fs)
    total_pwr = float(fft_full[(freqs_full >= 20) & (freqs_full <= 250)].sum())
    ruido_60 = float(fft_full[(freqs_full >= 55) & (freqs_full <= 65)].sum()) + \
               float(fft_full[(freqs_full >= 115) & (freqs_full <= 125)].sum())
    ratio = ruido_60 / total_pwr if total_pwr > 0 else 1.0
    calidad["ratio_60hz"] = round(ratio, 4)

    # Umbral 30%: después del notch, si más de un tercio de la potencia útil
    # SIGUE en bandas de red, hay algo mal en el hardware (electrodos sueltos,
    # batería baja, cable sin shield). No es señal muscular fiable.
    if ratio > 0.30:
        calidad["motivo"] = (
            f"ruido de red dominante tras filtrar ({ratio * 100:.1f}% en 60/120 Hz). "
            "Revisar electrodos, gel y batería."
        )
        return None, calidad

    # ── 3) Features espectrales en banda muscular útil, excluyendo notch ─────
    rms = float(np.sqrt(np.mean(sig ** 2)))
    mask = ((freqs_full >= 20) & (freqs_full <= 200) &
            ~((freqs_full >= 55) & (freqs_full <= 65)) &
            ~((freqs_full >= 115) & (freqs_full <= 125)))
    pwr = fft_full[mask]
    f = freqs_full[mask]
    if pwr.sum() == 0:
        calidad["motivo"] = "sin potencia útil tras filtrado"
        return None, calidad

    pwr_acum = np.cumsum(pwr)
    idx_med = np.searchsorted(pwr_acum, pwr_acum[-1] / 2.0)
    freq_med = float(f[idx_med]) if idx_med < len(f) else 0.0
    freq_mean = float(np.average(f, weights=pwr))

    calidad["valido"] = True
    calidad["motivo"] = "OK"
    return FeaturesEMG(rms=rms, freq_mediana=freq_med, freq_media=freq_mean), calidad


# ─── Backend API helpers ──────────────────────────────────────────────────────

def _get_baseline(token: str) -> dict | None:
    try:
        r = requests.get(
            f"{BACKEND_URL}/baselines/activo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 200:
            payload = r.json()
            return payload.get("data") if "data" in payload else payload
        print(f"[BASELINE-EMG] backend devolvió {r.status_code}: {r.text[:200]}",
              file=sys.stderr)
    except Exception as exc:
        print(f"[BASELINE-EMG] error de red: {exc}", file=sys.stderr)
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
        # 404 esperado cuando el médico aún no calibró; otros códigos son síntoma.
        if r.status_code != 404:
            print(f"[BASELINE-M1] backend devolvió {r.status_code}: {r.text[:200]}",
                  file=sys.stderr)
        else:
            print("[BASELINE-M1] sin baseline activo en el backend "
                  "(404). ¿Calibraste primero?", file=sys.stderr)
    except Exception as exc:
        print(f"[BASELINE-M1] error de red: {exc}", file=sys.stderr)
    return None


def _post_evaluacion(token: str, payload: dict) -> tuple[dict | None, str | None]:
    """Devuelve (respuesta_json, error_msg). error_msg es None si todo OK."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/evaluaciones",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return r.json(), None
        err = f"backend devolvió {r.status_code}: {r.text[:400]}"
        print(f"[POST-EVALUACION] {err}", file=sys.stderr)
        return None, err
    except Exception as exc:
        err = f"no se pudo conectar al backend: {exc}"
        print(f"[POST-EVALUACION] {err}", file=sys.stderr)
        return None, err


# ─── Rutina principal ─────────────────────────────────────────────────────────

def ejecutar(token: str, duracion_s: float = DURACION_S,
             camara_id: int | None = None,
             puerto_arduino: str | None = None,
             camera_profile: str | None = None,
             post_al_backend: bool = True) -> None:

    # Cuando el backend invoca este script por subprocess, lee stdout para
    # extraer el JSON final tras EVALUACION_RESULT_MARKER. Cualquier otro
    # `print()` debe ir a stderr para no contaminar el JSON. Redirigimos
    # stdout → stderr durante toda la rutina y restauramos al final solo
    # para emitir el marcador + JSON en el stdout real.
    _stdout_real = sys.stdout
    sys.stdout = sys.stderr

    # Identidad del operador (para estampar en metadatos y respaldo local).
    jwt_payload = _decodificar_jwt(token)
    id_usuario  = jwt_payload.get("sub")
    email       = jwt_payload.get("email")
    if id_usuario:
        print(f"  Operador: {email or '?'} (id={id_usuario})")

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

    emg_calidad: dict = {"valido": False, "ratio_60hz": None, "motivo": "sin datos"}
    if muestras:
        emg_feat, emg_calidad = _procesar_senal_emg(muestras)
        if emg_feat is not None:
            resultado_m2 = calcular_p_fatiga(emg_feat, baseline, hrv=hrv_feat)
            print(f"       EMG: RMS={emg_feat.rms:.1f} µV, "
                  f"F_mediana={emg_feat.freq_mediana:.1f} Hz "
                  f"(ruido 60Hz={emg_calidad['ratio_60hz']*100:.1f}%)")
            for alerta in resultado_m2.alertas:
                print(f"       ⚠  {alerta}")
        else:
            # Señal EMG inválida (ruido de red dominante u otra anomalía).
            # No la usamos en M2 para no contaminar el dictamen con falsos
            # incrementos RMS y caídas espectrales que son artefactos.
            print(f"[AVISO] EMG omitido: {emg_calidad['motivo']}", file=sys.stderr)
            emg_feat = None
            if hrv_feat is not None:
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
    else:
        print("[AVISO] Sin datos EMG. M2 operará solo con rPPG si está disponible.")
        emg_feat = None
        if hrv_feat is not None:
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
            "calidad":      emg_calidad,   # {valido, ratio_60hz, motivo}
            "reglas_m2":    resultado_m2.reglas,
        },
        "features_hrv": resultado_m1.hrv,   # rPPG desde cámara ALPCAM AR0234
        "metadatos": {
            "fuente":             "local_script",
            "version_modelo_m1":  "lstm_A_subjindep_best",
            "camara":             cam.name,
            "puerto_arduino":     puerto_arduino,
            "baseline_id":        baseline_dict.get("id_baseline") if baseline_dict else None,
            "baseline_somnolencia_id": baseline_somn.get("id_baseline") if baseline_somn else None,
            "p_somnolencia_baseline": p_baseline_somn,
            "hrv_fuente":         "rppg_camara" if resultado_m1.hrv else None,
            "id_usuario":         id_usuario,
            "email_operador":     email,
        },
    }

    # Solo POSTeamos al backend desde CLI. Desde la web, el backend persiste
    # él mismo a partir del JSON que emitimos por stdout (evita duplicación).
    id_evaluacion: str | None = None
    post_error: str | None = None
    if post_al_backend:
        print("[4/4] Enviando resultado al backend...")
        respuesta, post_error = _post_evaluacion(token, payload)

        if respuesta:
            data_eval = respuesta.get("data") if isinstance(respuesta, dict) else None
            if isinstance(data_eval, dict):
                id_evaluacion = data_eval.get("id_evaluacion")
            print(f"      Evaluación registrada: id={id_evaluacion or '?'}")
        else:
            print(f"      No se pudo registrar. Resultado guardado localmente. "
                  f"Causa: {post_error}")
            respaldo = {
                "id_usuario":         id_usuario,
                "email_operador":     email,
                "post_error":         post_error,
                "timestamp_local":    time.strftime("%Y-%m-%dT%H:%M:%S"),
                "payload":            payload,
            }
            with open("resultado_sin_enviar.json", "w", encoding="utf-8") as f:
                json.dump(respaldo, f, ensure_ascii=False, indent=2)
            print("      → resultado_sin_enviar.json")
    else:
        print("[4/4] Datos emitidos por stdout — el backend los persistirá.")

    # ── Marcador para el backend (subprocess) ────────────────────────────────
    # El JSON debe ir al stdout REAL (no al stderr al que redirigimos arriba).
    resultado_subprocess = {
        "id_evaluacion":     id_evaluacion,
        "id_usuario":        id_usuario,
        "dictamen":          resultado_m3.dictamen,
        "p_somnolencia":     resultado_m3.p_somnolencia,
        "p_fatiga_fisiologica": resultado_m3.p_fatiga_fisiologica,
        "p_total":           resultado_m3.p_total,
        "duracion_real_s":   float(resultado_m1.duracion_s),
        "frames_procesados": int(resultado_m1.frames_procesados),
        "fps_observado":     resultado_m1.features.get("fps_observado"),
        "n_muestras_emg":    len(muestras),
        "hrv_disponible":    resultado_m1.hrv is not None,
        "post_error":        post_error,
        "justificacion":     list(resultado_m3.justificacion),
        # Payload completo para que el backend pueda persistir cuando
        # post_al_backend=False (modo web).
        "payload_evaluacion": payload,
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
    puerto_arduino: str | None = None,
    post_al_backend: bool = True,
) -> None:
    """Calibración unificada en estado alerta: captura M1 (visión), M2-EMG
    (Arduino sEMG) y M2-HRV (rPPG cara) en el MISMO intervalo de `duracion_s`.

    El sistema experto difuso M2 evalúa cada regla contra el baseline personal
    del sujeto (RNF-05). Si solo se calibra M1, las reglas EMG/HRV no tienen
    referencia y disparan falsos positivos. Esta función emite los DOS
    baselines (M1 y M2) tras la misma sesión de 30 s.

    Modos:
      • CLI (`post_al_backend=True`): el script POSTea ambos baselines.
      • Subprocess web (`post_al_backend=False`): el backend persiste a partir
        del JSON emitido por stdout. Evita race conditions.

    El JSON final, tras el marcador `CALIBRACION_RESULT_MARKER`, contiene:
      m1: {p_somnolencia, ear_promedio, mar_promedio, ...}
      m2: {emg: {...}, hrv: {...}, emg_calidad: {...}} — m2 puede ser parcial
          si Arduino no conectado o EMG ruidoso.
    """
    print("\n═══════════════════════════════════════", file=sys.stderr)
    print("  VigilanceAI — Calibración personal", file=sys.stderr)
    print(f"  Mantente alerta y quieto durante {duracion_s:.0f} s", file=sys.stderr)
    print("═══════════════════════════════════════\n", file=sys.stderr)

    # ── 1. Detectar Arduino para capturar EMG en paralelo ────────────────────
    if puerto_arduino is None:
        puerto_arduino = _detectar_puerto_arduino()
    if puerto_arduino:
        print(f"  Arduino detectado en {puerto_arduino} — se capturará EMG.",
              file=sys.stderr)
    else:
        print("  Arduino no detectado. El baseline M2 solo incluirá HRV.",
              file=sys.stderr)

    # ── 2. Captura paralela: cámara (M1+rPPG) + Arduino sEMG ─────────────────
    cola_emg: queue.Queue = queue.Queue()
    hilo_emg = None
    if puerto_arduino:
        hilo_emg = threading.Thread(
            target=_leer_emg_arduino,
            args=(puerto_arduino, duracion_s, cola_emg),
            daemon=True,
        )
        hilo_emg.start()

    cam = get_profile(camera_profile)
    print(f"  Cámara: {cam.name}", file=sys.stderr)
    m1 = ModuloVision(ruta_modelo=MODELO_M1_PATH, duracion_s=duracion_s, camera=cam)
    resultado_m1 = m1.capturar_y_evaluar(camara_id=camara_id)

    if hilo_emg is not None:
        hilo_emg.join(timeout=duracion_s + 5)

    # ── 3. Liveness check — si falla, baseline contaminaría todo el futuro ──
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

    # ── 4. Procesar EMG (con notch + quality gate) ───────────────────────────
    muestras: list[float] = []
    while not cola_emg.empty():
        item = cola_emg.get()
        if isinstance(item, float):
            muestras.append(item)

    baseline_emg: dict | None = None
    emg_calidad: dict = {"valido": False, "ratio_60hz": None,
                          "motivo": "sin Arduino" if not puerto_arduino else "sin datos"}
    if muestras:
        emg_feat, emg_calidad = _procesar_senal_emg(muestras)
        if emg_feat is not None:
            baseline_emg = {
                "rms_emg":      round(emg_feat.rms, 4),
                "freq_mediana": round(emg_feat.freq_mediana, 4),
                "freq_media":   round(emg_feat.freq_media, 4),
            }
            print(f"  Baseline EMG: RMS={emg_feat.rms:.1f} µV, "
                  f"F_med={emg_feat.freq_mediana:.1f} Hz "
                  f"(ruido 60Hz {emg_calidad['ratio_60hz']*100:.1f}%)",
                  file=sys.stderr)
        else:
            print(f"  [AVISO] EMG no válido: {emg_calidad['motivo']}", file=sys.stderr)

    # ── 5. HRV desde rPPG (cara) — siempre disponible si hubo señal facial ───
    baseline_hrv: dict | None = None
    if resultado_m1.hrv is not None:
        baseline_hrv = {
            "sdnn":  round(float(resultado_m1.hrv.get("sdnn", 0.0)), 4),
            "rmssd": round(float(resultado_m1.hrv.get("rmssd", 0.0)), 4),
            "pnn50": round(float(resultado_m1.hrv.get("pnn50", 0.0)), 4),
        }
        print(f"  Baseline HRV: SDNN={baseline_hrv['sdnn']:.1f} ms, "
              f"RMSSD={baseline_hrv['rmssd']:.1f} ms, "
              f"pNN50={baseline_hrv['pnn50']:.1f}%", file=sys.stderr)

    # ── 6. POST al backend (solo en modo CLI) ────────────────────────────────
    backend_response_m1: dict | None = None
    backend_response_m2: dict | None = None
    if post_al_backend:
        # M1
        payload_m1 = {
            "p_somnolencia":     resultado_m1.p_somnolencia,
            "ear_promedio":      resultado_m1.ear_promedio,
            "mar_promedio":      resultado_m1.mar_promedio,
            "duracion_s":        resultado_m1.duracion_s,
            "frames_procesados": resultado_m1.frames_procesados,
        }
        try:
            r = requests.post(
                f"{BACKEND_URL}/baselines/somnolencia",
                json=payload_m1,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if r.status_code in (200, 201):
                backend_response_m1 = r.json()
                print("[OK] Baseline M1 registrado.", file=sys.stderr)
            else:
                print(f"[BASELINE-M1-POST] {r.status_code}: {r.text[:200]}",
                      file=sys.stderr)
        except Exception as exc:
            print(f"[BASELINE-M1-POST] error: {exc}", file=sys.stderr)

        # M2 (requiere EMG válido por el schema actual de baselines_emg)
        if baseline_emg is not None:
            payload_m2 = {**baseline_emg}
            if baseline_hrv is not None:
                payload_m2.update(baseline_hrv)
            try:
                r = requests.post(
                    f"{BACKEND_URL}/baselines",
                    json=payload_m2,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                )
                if r.status_code in (200, 201):
                    backend_response_m2 = r.json()
                    print("[OK] Baseline M2 registrado.", file=sys.stderr)
                else:
                    print(f"[BASELINE-M2-POST] {r.status_code}: {r.text[:200]}",
                          file=sys.stderr)
            except Exception as exc:
                print(f"[BASELINE-M2-POST] error: {exc}", file=sys.stderr)
        else:
            print("[AVISO] Baseline M2 NO se registra (EMG no válido o sin Arduino).",
                  file=sys.stderr)

    # ── 7. Emitir JSON consumible por el backend (subprocess parser) ─────────
    resultado = {
        "m1": {
            "p_somnolencia":     resultado_m1.p_somnolencia,
            "ear_promedio":      resultado_m1.ear_promedio,
            "mar_promedio":      resultado_m1.mar_promedio,
            "duracion_s":        resultado_m1.duracion_s,
            "frames_procesados": resultado_m1.frames_procesados,
            "ventanas_inferidas": resultado_m1.ventanas_inferidas,
            "fps_observado":     resultado_m1.features.get("fps_observado"),
        },
        "m2": {
            "emg":         baseline_emg,
            "hrv":         baseline_hrv,
            "emg_calidad": emg_calidad,
            "n_muestras_emg": len(muestras),
            "arduino_detectado": bool(puerto_arduino),
        },
        "backend_response_m1": backend_response_m1,
        "backend_response_m2": backend_response_m2,
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
    p.add_argument("--no-post", action="store_true",
                   help="No POSTear al backend; solo emitir JSON por stdout. "
                        "Lo usa el backend cuando invoca este script como "
                        "subprocess para evitar registros duplicados.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if getattr(args, "listar_camaras", False):
        _emitir_listado_camaras()
        sys.exit(0)
    post_al_backend = not args.no_post
    if args.calibracion_m1:
        ejecutar_calibracion_m1(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
            camera_profile=args.camera_profile,
            puerto_arduino=args.puerto,
            post_al_backend=post_al_backend,
        )
    else:
        ejecutar(
            token=args.token,
            duracion_s=args.duracion,
            camara_id=args.camara,
            puerto_arduino=args.puerto,
            camera_profile=args.camera_profile,
            post_al_backend=post_al_backend,
        )
