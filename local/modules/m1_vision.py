"""
Módulo 1 + rPPG — Visión conductual y fotopletismografía remota
Sistema de detección de somnolencia y fatiga mental — VigilanceAI
USAT 2025 · Caso NOR VISIÓN, Chiclayo

Pipeline M1 (somnolencia):
  Cámara ALPCAM AR0234 USB (1200P, 90 fps, obturador global) →
  MediaPipe FaceMesh (468 landmarks) →
  EAR + MAR por frame → sliding window (SEQ_LEN=20, STRIDE=5) →
  BiLSTM (LSTMDrowsy, 2 capas, hidden=128) → P_somnolencia ∈ [0, 1]

Pipeline rPPG (para M2 — HRV):
  Misma cámara → ROI facial (frente) →
  Canal verde por frame → filtrado → picos R → SDNN, RMSSD, pNN50

Modelo: lstm_A_subjindep_best.pt
  - Arquitectura: LSTMDrowsy (EXACTA del notebook Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb)
  - Estrategia A (subject-independent, 70/15/15 por sujeto): es la ÚNICA honesta para
    despliegue real, porque cada médico evaluado en NOR VISIÓN será un sujeto nuevo
    para el modelo. La Estrategia B (split aleatorio) infla métricas y NO se usa.
  - Métricas reales (test, sujetos no vistos):
      Accuracy=74.56%, F1=76.83%, Sensibilidad=87.59%, AUC=0.7942, latencia=0.11 ms/imagen
  - Checkpoint guardado con torch.save(model.state_dict(), path) — solo state_dict
  - Normalización: feat_mean / feat_std del train A — valores exactos del notebook:
      mean=[0.24429618, 0.03506882], std=[0.06629491, 0.0284285]

Dependencias:
  pip install mediapipe==0.10.14 opencv-python torch scipy
  (MediaPipe FIJADA en 0.10.14 — versiones posteriores dan AttributeError en FaceMesh)
"""

from __future__ import annotations
import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp
import scipy.signal as sig_proc
import numpy as np
import torch
import torch.nn as nn

# ─── Constantes del modelo (del notebook Modulo1...) ─────────────────────────

SEQ_LEN   = 20      # celda 29: SEQ_LEN = 20
STRIDE    = 5       # celda 29: STRIDE = 5
INPUT_DIM = 2       # [EAR, MAR]
HIDDEN    = 128
N_LAYERS  = 2
DROPOUT   = 0.3

# Estadísticos de normalización del train de Estrategia A — subject-independent.
# Valores EXACTOS impresos por el notebook (celda 32, fit del split A):
#   mean=[0.24429618, 0.03506882], std=[0.06629491, 0.0284285]
FEAT_MEAN_A = np.array([0.24429618, 0.03506882], dtype=np.float32)
FEAT_STD_A  = np.array([0.06629491, 0.0284285],  dtype=np.float32)

UMBRAL_DEFAULT = 0.50

# ─── Cámara — configuración por perfil ───────────────────────────────────────
# Los parámetros (índice, backend, resolución, fps, FOURCC) viven en
# `cameras.py` como perfiles ("alpcam", "gopro", "webcam"). Se eligen vía CLI
# (`--camera-profile`), variable de entorno (`VIGILANCE_CAMERA_PROFILE`), o
# por defecto el perfil de producción ("alpcam"). Para añadir una cámara nueva
# basta con sumar una entrada al diccionario PROFILES de cameras.py — el
# pipeline de captura no toca.
try:
    from .cameras import CameraConfig, get_profile  # como paquete (main.py)
except ImportError:                                  # como script directo
    from cameras import CameraConfig, get_profile  # type: ignore

# ─── Landmarks MediaPipe FaceMesh ────────────────────────────────────────────
EYE_RIGHT = [33, 160, 158, 133, 153, 144]
EYE_LEFT  = [362, 385, 387, 263, 373, 380]
MOUTH_TOP, MOUTH_BOT, MOUTH_LEFT, MOUTH_RIGHT = 13, 14, 78, 308

# ROI frente para rPPG — SOLO landmarks de la frente, NO el contorno facial.
# La lista anterior incluía landmarks del jaw (152, 148, 176, ...) y el convex
# hull cubría toda la cara (ojos, nariz, boca), introduciendo ruido masivo en
# la señal rPPG. Esta lista limita el ROI al parche cutáneo entre las cejas y
# la línea del cabello, donde la perfusión capilar superficial es más limpia.
# Landmarks de MediaPipe FaceMesh (índices verificados en v0.10.14):
#   10  : centro alto de la frente
#   109 : esquina superior izquierda
#   338 : esquina superior derecha
#   67  : medio izquierdo
#   297 : medio derecho
#   103 : esquina inferior izquierda (sobre ceja)
#   332 : esquina inferior derecha (sobre ceja)
#   151 : sobre el entrecejo (centro inferior del ROI)
FRENTE_LM = [10, 109, 67, 103, 151, 332, 297, 338]


# ─── Arquitectura del modelo — EXACTA del notebook ───────────────────────────

class LSTMDrowsy(nn.Module):
    """
    Arquitectura IDÉNTICA a la celda 31 del notebook
    Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb.

    in_feat=2, hidden=128, layers=2, dropout=0.3
    Pooling: mean_pool (out.mean(dim=1)) + last (out[:, -1, :]) → concat → head
    Head: Linear(512,128) → ReLU → Dropout → Linear(128,64) → ReLU → Dropout → Linear(64,2)
    """

    def __init__(self, in_feat: int = INPUT_DIM, hidden: int = HIDDEN,
                 layers: int = N_LAYERS, dropout: float = DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(
            in_feat, hidden, layers,
            batch_first=True,
            dropout=dropout if layers > 1 else 0.0,
            bidirectional=True,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden * 2 * 2, 128),   # 256 (mean) + 256 (last) = 512
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(64, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)                  # (B, T, hidden*2)
        mean_pool = out.mean(dim=1)            # (B, hidden*2)
        last      = out[:, -1, :]             # (B, hidden*2) — último step del output
        feat = torch.cat([mean_pool, last], dim=1)   # (B, hidden*4 = 512)
        return self.head(feat)                 # (B, 2)


# ─── Funciones de landmarks ───────────────────────────────────────────────────

def _dist(a: tuple, b: tuple) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def calcular_ear(lm: list, indices: list[int]) -> float:
    p = [(lm[i].x, lm[i].y) for i in indices]
    num = _dist(p[1], p[5]) + _dist(p[2], p[4])
    den = 2.0 * _dist(p[0], p[3])
    return num / (den + 1e-6)


def calcular_mar(lm: list) -> float:
    top   = (lm[MOUTH_TOP].x,   lm[MOUTH_TOP].y)
    bot   = (lm[MOUTH_BOT].x,   lm[MOUTH_BOT].y)
    left  = (lm[MOUTH_LEFT].x,  lm[MOUTH_LEFT].y)
    right = (lm[MOUTH_RIGHT].x, lm[MOUTH_RIGHT].y)
    return _dist(top, bot) / (_dist(left, right) + 1e-6)


# ─── Extracción rPPG — HRV para Módulo 2 ─────────────────────────────────────
#
# Pipeline rPPG (versión 2, con POS):
#   1. Por cada frame con cara → media (R, G, B) sobre la ROI de la frente.
#   2. Al cierre de la captura → método POS (Plane-Orthogonal-to-Skin) [Wang 2017]
#      que proyecta RGB sobre un plano ortogonal al tono de piel para cancelar
#      ruido de movimiento e iluminación. Sustituye al promedio del canal verde
#      [Verkruysse 2008] que es la línea base sensible al movimiento.
#   3. Detrend + Butterworth bandpass 0.7–3.5 Hz (42–210 bpm).
#   4. find_peaks → intervalos RR (ms) → HRV (SDNN, RMSSD, pNN50, HR) según
#      Task Force ESC/NASPE 1996 [11] y Shaffer 2017 [16].
#   5. Gate de calidad: si RMSSD/SDNN > 1.0 la señal está dominada por ruido
#      (físicamente RMSSD ≤ √2·SDNN) → marcar lectura como no confiable.

# Umbral del gate de calidad de señal HRV.
# Límite matemático: RMSSD ≤ √2 · SDNN ≈ 1.414 (Task Force ESC/NASPE 1996, [11]).
# Literatura aplicada (Shaffer & Ginsberg 2017, [16]): ratio típico 0.4–0.9 en
# reposo profundo, 1.0–1.3 admisible en estados de alerta tranquila o predominio
# parasimpático leve (capturas cortas con sujeto consciente del registro).
# Se elige 1.4 como "umbral físico" — solo se descarta lo matemáticamente imposible.
QC_RMSSD_SDNN_MAX = 1.4
RR_OUTLIER_PCT    = 0.20  # ±20% de la mediana — protocolo clínico Task Force [11]


def _filtrar_rr_clinicamente(rr_ms: np.ndarray) -> np.ndarray:
    """Filtrado de intervalos RR según protocolo clínico (Task Force ESC/NASPE 1996).

    Rechaza:
      1. RR fuera del rango fisiológico [300, 2000] ms (HR de 30 a 200 bpm).
      2. RR que difieran de la mediana en más de ±20% — marca de detección
         espuria, latido ectópico o artefacto, según la práctica clínica
         estándar de procesamiento HRV.

    El filtro se aplica iterativamente (máx 3 pasadas) porque rechazar un
    outlier mueve la mediana, lo que puede revelar nuevos outliers.
    """
    rr = rr_ms[(rr_ms >= 300) & (rr_ms <= 2000)]
    for _ in range(3):
        if len(rr) < 5:
            break
        med = np.median(rr)
        keep = np.abs(rr - med) <= RR_OUTLIER_PCT * med
        if keep.all():
            break
        rr = rr[keep]
    return rr


def _extraer_roi_frente(frame: np.ndarray, lm: list,
                        w: int, h: int) -> tuple[float, float, float] | None:
    """Extrae el valor medio (R, G, B) de la ROI de la frente.

    Devuelve None si la ROI cae fuera del frame o no contiene píxeles.
    El frame de OpenCV viene en BGR; se reordena a (R, G, B) para POS.
    """
    pts = np.array([(int(lm[i].x * w), int(lm[i].y * h)) for i in FRENTE_LM])
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(pts), 255)
    if not np.any(mask > 0):
        return None
    b_mean = float(frame[:, :, 0][mask > 0].mean())
    g_mean = float(frame[:, :, 1][mask > 0].mean())
    r_mean = float(frame[:, :, 2][mask > 0].mean())
    return (r_mean, g_mean, b_mean)


def _pulso_pos(senal_rgb: np.ndarray, fps: float,
               win_s: float = 1.6) -> np.ndarray:
    """Método POS — Plane-Orthogonal-to-Skin (Wang et al. 2017, ec. 5–8).

    Proyecta la serie temporal RGB sobre el plano ortogonal al vector de tono
    de piel para aislar el componente cardíaco del ruido de movimiento e
    iluminación. La intuición física: cuando hay movimiento o cambio de luz
    los tres canales suben/bajan proporcionalmente (variación en la dirección
    del tono de piel); cuando hay un latido, solo el verde cae por absorción
    de hemoglobina (variación ortogonal). Proyectar ortogonalmente cancela el
    primer componente y preserva el segundo.

    Algoritmo:
        Para cada ventana deslizante de longitud L = win_s · fps:
          Cn = C / mean(C)                    # normalización temporal
          P  = [[0, 1, -1], [-2, 1, 1]]
          S  = P · Cn                          # 2 × L
          α  = std(S₀) / std(S₁)
          h  = S₀ + α · S₁                    # señal de pulso de la ventana
          h  = h - mean(h)
        Overlap-add → señal de pulso completa.

    Args:
        senal_rgb: arreglo (N, 3) con la media de R, G, B por frame.
        fps:       frame rate real medido durante la captura.
        win_s:     longitud de la ventana POS (Wang 2017 sugiere 1.6 s).

    Returns:
        Pulso h de longitud N. Devuelve la señal proyectada incluso si
        N < L (caso fallback con una sola ventana sobre todo el segmento).
    """
    rgb = np.asarray(senal_rgb, dtype=np.float64)
    if rgb.ndim != 2 or rgb.shape[1] != 3:
        raise ValueError(f"senal_rgb debe ser (N,3), no {rgb.shape}")
    N = rgb.shape[0]
    L = max(int(win_s * fps), 32)

    P = np.array([[0.0, 1.0, -1.0],
                  [-2.0, 1.0, 1.0]])

    if N < L:
        # Señal corta: una sola "ventana" sobre todo el tramo.
        mean_C = rgb.mean(axis=0, keepdims=True) + 1e-9
        Cn = rgb / mean_C                    # (N, 3)
        S  = P @ Cn.T                         # (2, N)
        std0, std1 = np.std(S[0]), np.std(S[1])
        alpha = std0 / (std1 + 1e-9)
        h = S[0] + alpha * S[1]
        return h - h.mean()

    H = np.zeros(N, dtype=np.float64)
    for n in range(L, N + 1):
        Cn_window = rgb[n - L:n].T            # (3, L)
        mean_C = Cn_window.mean(axis=1, keepdims=True) + 1e-9
        Cn_norm = Cn_window / mean_C
        S = P @ Cn_norm                       # (2, L)
        std0, std1 = np.std(S[0]), np.std(S[1])
        alpha = std0 / (std1 + 1e-9)
        h = S[0] + alpha * S[1]
        h = h - h.mean()
        H[n - L:n] += h
    return H


def _calcular_hrv_desde_rppg(senal_rgb: list[tuple[float, float, float]],
                              fps: float = 30.0) -> dict | None:
    """Estima HRV (SDNN, RMSSD, pNN50, HR) desde la señal rPPG.

    Pipeline:
      1. POS sobre la serie RGB → señal de pulso h(t) robusta a movimiento.
      2. Butterworth bandpass 0.7–3.5 Hz (42–210 bpm) — banda fisiológica.
      3. find_peaks con distancia mínima 0.4 s (~150 bpm máx).
      4. Intervalos RR en ms, filtrados a [300, 2000] ms (rango plausible).
      5. SDNN, RMSSD, pNN50, HR según Task Force ESC/NASPE 1996.
      6. Gate de calidad: RMSSD/SDNN > QC_RMSSD_SDNN_MAX (= 1.4, límite físico
         √2 según Task Force [11]). Si excede ese ratio la señal es matemática-
         mente imposible como HRV genuino. Se devuelve el dict con flag
         `calidad ∈ {"alta", "baja"}` para que el motor de reglas (M2) lo
         considere. Valores entre 0.4 y 1.3 se aceptan como fisiológicamente
         válidos (Shaffer & Ginsberg 2017, [16]).

    Devuelve None si no hay suficiente señal o no se detectan picos.
    """
    if not senal_rgb or len(senal_rgb) < int(fps * 10):   # mínimo 10 s de señal
        return None

    rgb = np.array(senal_rgb, dtype=np.float64)
    if rgb.ndim != 2 or rgb.shape[1] != 3:
        return None

    # 1. POS — pulso robusto al movimiento
    pulso = _pulso_pos(rgb, fps=fps, win_s=1.6)

    # 2. Butterworth bandpass 0.7–3.5 Hz
    b, a = sig_proc.butter(
        N=3,
        Wn=[0.7 / (fps / 2), 3.5 / (fps / 2)],
        btype='bandpass',
    )
    s_filt = sig_proc.filtfilt(b, a, pulso)

    # 3. Detectar picos (umbral de prominencia adaptativo a la varianza)
    min_dist = int(fps * 0.4)
    prom = max(0.5 * np.std(s_filt), 1e-3)
    picos, _ = sig_proc.find_peaks(s_filt, distance=min_dist, prominence=prom)

    if len(picos) < 4:
        return None

    # 4. Intervalos RR — filtrado clínico (Task Force 1996, [11])
    rr_ms_raw = np.diff(picos) / fps * 1000.0
    n_rr_raw = len(rr_ms_raw)
    rr_ms = _filtrar_rr_clinicamente(rr_ms_raw)

    if len(rr_ms) < 3:
        return None

    # 5. HRV
    sdnn  = float(np.std(rr_ms, ddof=1))
    rmssd = float(np.sqrt(np.mean(np.diff(rr_ms) ** 2)))
    pnn50 = float(np.sum(np.abs(np.diff(rr_ms)) > 50) / max(len(rr_ms) - 1, 1) * 100)
    hr    = float(60000.0 / np.mean(rr_ms))

    # 6. Gate de calidad (RMSSD ≤ √2·SDNN en HRV físicamente válido)
    ratio = rmssd / sdnn if sdnn > 0 else float("inf")
    calidad = "alta" if ratio <= QC_RMSSD_SDNN_MAX else "baja"

    return {
        "sdnn":    round(sdnn, 2),
        "rmssd":   round(rmssd, 2),
        "pnn50":   round(pnn50, 2),
        "hr_bpm":  round(hr, 1),
        "n_picos": int(len(picos)),
        "rr_n_raw":  int(n_rr_raw),
        "rr_n":      int(len(rr_ms)),
        "rr_rechazados": int(n_rr_raw - len(rr_ms)),
        "ratio_rmssd_sdnn": round(ratio, 3),
        "calidad": calidad,
        "metodo":  "POS (Wang 2017) + filtro clínico RR ±20% mediana",
    }


# ─── Resultado del módulo ─────────────────────────────────────────────────────

@dataclass
class ResultadoM1:
    # M1 — somnolencia
    p_somnolencia:    float
    ear_promedio:     float
    mar_promedio:     float
    frames_procesados: int       # frames con cara detectada
    frames_totales:    int       # frames leídos (con o sin cara)
    ventanas_inferidas: int
    duracion_s:       float
    features:         dict = field(default_factory=dict)
    # rPPG — HRV (para M2; None si no pudo calcularse)
    hrv: dict | None = None
    # Anti-spoofing / liveness
    parpadeos_detectados: int = 0
    ear_std:              float = 0.0


# ─── Validación de liveness / anti-spoofing ──────────────────────────────────
#
# Defiende al sistema de tres modos de fallo evidentes:
#   1. La cámara no apunta a un sujeto (techo, escritorio, pared) → no hay cara.
#   2. La cámara apunta a una foto / pantalla con rostro estático → hay cara
#      detectable, pero no hay parpadeos ni perfusión sanguínea.
#   3. Fallo prolongado de detección facial por iluminación insuficiente.
#
# Criterios (todos deben pasar):
#   - tasa_deteccion_facial ≥ 0.70  → al menos 70% de los frames tuvo cara.
#   - ear_std ≥ 0.005               → variabilidad mínima del ojo (foto ≈ 0).
#   - parpadeos ≥ 1 cada 15 s       → al menos un parpadeo por bloque de 15 s.
#   - hrv.calidad == "alta" si HRV existió → señal cardíaca fisiológicamente
#     consistente (RMSSD/SDNN ≤ 1.4). Una foto da ratio aleatorio; alta calidad
#     es prácticamente imposible de forjar sin sujeto vivo.
#
# Estos umbrales son conservadores: priorizan SEGURIDAD (rechazar capturas
# dudosas) sobre conveniencia. En la tesis: defendible como "principio de
# precaución clínica" — mejor pedir repetir la captura que emitir un dictamen
# sobre datos no fisiológicos.

LIVENESS_TASA_DETECCION_MIN = 0.70
LIVENESS_EAR_STD_MIN        = 0.005
LIVENESS_PARPADEOS_POR_15S  = 1


def validar_liveness(resultado: "ResultadoM1") -> tuple[bool, list[str]]:
    """Devuelve (válido, razones_fallo). Si válido=True, razones está vacío."""
    razones: list[str] = []

    # 1. Tasa de detección facial
    tasa = resultado.features.get("tasa_deteccion_facial", 0.0)
    if tasa < LIVENESS_TASA_DETECCION_MIN:
        razones.append(
            f"Tasa de detección facial {tasa*100:.1f}% < "
            f"{LIVENESS_TASA_DETECCION_MIN*100:.0f}% requerido. "
            "Apunte la cámara al rostro y verifique iluminación."
        )

    # 2. Variabilidad del EAR (anti-foto)
    if resultado.ear_std < LIVENESS_EAR_STD_MIN:
        razones.append(
            f"Variabilidad ocular insuficiente (EAR std={resultado.ear_std:.4f} < "
            f"{LIVENESS_EAR_STD_MIN}). Compatible con imagen estática (foto/pantalla)."
        )

    # 3. Parpadeos esperados
    bloques_15s = max(1, int(resultado.duracion_s / 15))
    parpadeos_min = bloques_15s * LIVENESS_PARPADEOS_POR_15S
    if resultado.parpadeos_detectados < parpadeos_min:
        razones.append(
            f"Solo {resultado.parpadeos_detectados} parpadeos en "
            f"{resultado.duracion_s:.0f}s (mínimo {parpadeos_min}). "
            "Compatible con foto/pantalla o sujeto inconsciente."
        )

    # 4. Calidad de HRV — solo si la señal pudo calcularse
    if resultado.hrv is not None:
        calidad = resultado.hrv.get("calidad")
        if calidad == "baja":
            ratio = resultado.hrv.get("ratio_rmssd_sdnn", "?")
            razones.append(
                f"Señal rPPG sin perfusión consistente (ratio RMSSD/SDNN={ratio}). "
                "Compatible con superficie estática sin pulso cardíaco."
            )

    return (len(razones) == 0, razones)


# ─── Clase principal ──────────────────────────────────────────────────────────

class ModuloVision:
    """
    Captura video con la cámara ALPCAM AR0234 USB (1200P, 90 fps).
    Durante `duracion_s` segundos:
      - Extrae EAR+MAR por frame para el BiLSTM (M1)
      - Extrae señal rPPG del canal verde en ROI frente para HRV (M2)
    """

    def __init__(self, ruta_modelo: str | Path,
                 umbral: float = UMBRAL_DEFAULT,
                 duracion_s: float = 30.0,
                 device: str = "cpu",
                 camera: CameraConfig | None = None):
        self.umbral     = umbral
        self.duracion_s = duracion_s
        self.device     = torch.device(device)
        # Perfil de cámara — si no se pasa, lee env VIGILANCE_CAMERA_PROFILE
        # o cae al default ("alpcam"). Override por CLI desde main.py.
        self.cam        = camera if camera is not None else get_profile()

        # Cargar LSTMDrowsy — archivo guarda solo state_dict (torch.save(model.state_dict(), path))
        self.modelo = LSTMDrowsy()
        state = torch.load(str(ruta_modelo), map_location=self.device)
        # Si por algún motivo está envuelto en dict con 'model_state_dict'
        if isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        self.modelo.load_state_dict(state)
        self.modelo.to(self.device)
        self.modelo.eval()

        # MediaPipe FaceMesh — versión 0.10.14 fijada
        self._mp_face = mp.solutions.face_mesh
        self._face_mesh = self._mp_face.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def capturar_y_evaluar(self, camara_id: int | None = None) -> ResultadoM1:
        """
        Abre la cámara según el perfil activo, captura durante
        duracion_s segundos y devuelve ResultadoM1 con P_somnolencia + HRV.

        Si se pasa `camara_id`, sobrescribe el índice del perfil (útil cuando
        el backend invoca con `--camara N`). El backend OpenCV y demás
        parámetros (FOURCC, resolución, fps) provienen siempre del perfil.
        """
        cam = self.cam
        idx = camara_id if camara_id is not None else cam.index
        cap = cv2.VideoCapture(idx, cam.backend)
        # FOURCC se fija ANTES que ancho/alto/fps: cambiar el formato
        # redefine los modos disponibles. Algunos drivers (cámara virtual de
        # GoPro Webcam, p.ej.) no exponen un FOURCC UVC estándar — en ese
        # caso el perfil tiene fourcc=None y simplemente no se setea.
        if cam.fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cam.fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cam.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam.height)
        cap.set(cv2.CAP_PROP_FPS,          cam.fps_request)

        buffer: deque = deque(maxlen=SEQ_LEN)
        ears:   list[float] = []
        mars:   list[float] = []
        scores: list[float] = []
        senal_rgb: list[tuple[float, float, float]] = []
        frames_ok = 0
        frames_totales = 0
        t_inicio = time.time()

        try:
            while (time.time() - t_inicio) < self.duracion_s:
                ret, frame = cap.read()
                if not ret:
                    break
                frames_totales += 1

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = self._face_mesh.process(rgb)

                if result.multi_face_landmarks:
                    lm = result.multi_face_landmarks[0].landmark
                    h_px, w_px = frame.shape[:2]

                    # ── M1: EAR + MAR ──────────────────────────────────────
                    ear = (calcular_ear(lm, EYE_RIGHT) + calcular_ear(lm, EYE_LEFT)) / 2.0
                    mar = calcular_mar(lm)
                    ears.append(ear)
                    mars.append(mar)
                    frames_ok += 1

                    feat = np.array([ear, mar], dtype=np.float32)
                    feat = (feat - FEAT_MEAN_A) / (FEAT_STD_A + 1e-8)
                    buffer.append(feat)

                    if len(buffer) == SEQ_LEN:
                        seq = torch.tensor(
                            np.stack(buffer), dtype=torch.float32
                        ).unsqueeze(0).to(self.device)

                        with torch.no_grad():
                            logits = self.modelo(seq)
                            prob_drowsy = torch.softmax(logits, dim=1)[0, 1].item()
                        scores.append(prob_drowsy)

                        for _ in range(STRIDE):
                            if buffer:
                                buffer.popleft()

                    # ── rPPG: tripleta (R, G, B) media en ROI frente ──────
                    rgb_mean = _extraer_roi_frente(frame, lm, w_px, h_px)
                    if rgb_mean is not None:
                        senal_rgb.append(rgb_mean)

        finally:
            cap.release()
            self._face_mesh.close()

        duracion = time.time() - t_inicio

        p_somnolencia = float(np.mean(scores)) if scores else 0.0

        # Para HRV usamos el fps REAL medido — no el solicitado — porque
        # el filtro Butterworth y la conversión picos→ms dependen de fs real.
        fps_observado = (frames_ok / duracion) if duracion > 0 else cam.fps_real
        hrv = _calcular_hrv_desde_rppg(senal_rgb, fps=fps_observado)

        # ── Liveness: parpadeos detectados (cruces sub-umbral del EAR) ────────
        # Un parpadeo es la transición OPEN→CLOSED→OPEN. Lo detectamos como
        # el número de veces que EAR cae bajo el umbral. EAR_BLINK_THRESHOLD
        # = 0.21 es el clásico de Soukupová & Cech 2016 (Real-Time Eye Blink
        # Detection using Facial Landmarks).
        parpadeos = 0
        if len(ears) >= 3:
            EAR_BLINK_THRESHOLD = 0.21
            estado_anterior = ears[0] >= EAR_BLINK_THRESHOLD  # True = ojo abierto
            for ear in ears[1:]:
                estado = ear >= EAR_BLINK_THRESHOLD
                if estado_anterior and not estado:  # cierre
                    parpadeos += 1
                estado_anterior = estado

        ear_std_val = float(np.std(ears)) if ears else 0.0
        tasa_deteccion = (frames_ok / frames_totales) if frames_totales > 0 else 0.0

        return ResultadoM1(
            p_somnolencia=round(p_somnolencia, 4),
            ear_promedio=round(float(np.mean(ears)) if ears else 0.0, 4),
            mar_promedio=round(float(np.mean(mars)) if mars else 0.0, 4),
            frames_procesados=frames_ok,
            frames_totales=frames_totales,
            ventanas_inferidas=len(scores),
            duracion_s=round(duracion, 2),
            features={
                "ear_promedio":     round(float(np.mean(ears)) if ears else 0.0, 4),
                "mar_promedio":     round(float(np.mean(mars)) if mars else 0.0, 4),
                "ear_std":          round(ear_std_val, 4),
                "mar_std":          round(float(np.std(mars)) if mars else 0.0, 4),
                "video_duration_s": round(duracion, 2),
                "frames_con_cara":  frames_ok,
                "frames_totales":   frames_totales,
                "tasa_deteccion_facial": round(tasa_deteccion, 4),
                "parpadeos":        parpadeos,
                "ventanas_bilstm":  len(scores),
                "rppg_frames":      len(senal_rgb),
                "rppg_metodo":      "POS",
                "fps_observado":    round(fps_observado, 2),
            },
            hrv=hrv,
            parpadeos_detectados=parpadeos,
            ear_std=round(ear_std_val, 4),
        )

    def __del__(self):
        try:
            self._face_mesh.close()
        except Exception:
            pass


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    try:
        from .cameras import listar_perfiles
    except ImportError:
        from cameras import listar_perfiles  # type: ignore

    p = argparse.ArgumentParser(
        description="Demo Módulo 1 — BiLSTM somnolencia + rPPG/HRV"
    )
    p.add_argument("modelo", nargs="?",
                   default="modelos/lstm_A_subjindep_best.pt",
                   help="Ruta al checkpoint lstm_A_subjindep_best.pt")
    p.add_argument("--camera-profile", choices=listar_perfiles(), default=None,
                   help="Perfil de cámara (default: VIGILANCE_CAMERA_PROFILE o 'alpcam').")
    p.add_argument("--camara", type=int, default=None,
                   help="Override del índice de cámara (sobre el perfil).")
    p.add_argument("--duracion", type=float, default=15.0,
                   help="Segundos de captura.")
    args = p.parse_args()

    cam = get_profile(args.camera_profile)
    print(f"[cámara] {cam.name}  idx={cam.index} backend={cam.backend} "
          f"{cam.width}x{cam.height}@{cam.fps_request} (real ~{cam.fps_real})")
    m1 = ModuloVision(ruta_modelo=args.modelo, duracion_s=args.duracion, camera=cam)
    r = m1.capturar_y_evaluar(camara_id=args.camara)
    print(f"P_somnolencia      = {r.p_somnolencia:.4f}")
    print(f"EAR promedio       = {r.ear_promedio:.4f}")
    print(f"MAR promedio       = {r.mar_promedio:.4f}")
    print(f"Frames procesados  = {r.frames_procesados}")
    print(f"Ventanas inferidas = {r.ventanas_inferidas}")
    print(f"Duración real (s)  = {r.duracion_s}")
    print(f"HRV rPPG           = {r.hrv}")
