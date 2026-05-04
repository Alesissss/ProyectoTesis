# `local/` — Sistema embebido VigilanceAI

Scripts Python que corren en la **unidad de procesamiento local** del sistema embebido (hoy la laptop del consultorio NOR VISIÓN; mañana Raspberry Pi 5 / Jetson Nano sin tocar backend ni frontend — RNF-12).

Capturan datos en tiempo real desde la cámara ALPCAM AR0234 USB y el Arduino UNO con sensor Olimex SHIELD-EKG-EMG, ejecutan los Módulos M1 (visión + rPPG), M2 (motor de reglas EMG/HRV) y M3 (fusión tardía 40/60), y envían el dictamen al backend FastAPI vía REST.

## ⚠️ Ambiente virtual independiente

Esta carpeta usa un **venv propio**, separado del que utiliza el backend FastAPI. La razón es arquitectónica: la unidad de procesamiento es un nodo embebido distinto del servidor — sus dependencias (MediaPipe, OpenCV, PyTorch, pyserial) no deben mezclarse con las del backend (SQLAlchemy, Alembic, FastAPI, asyncpg). Esto garantiza que el portado a Raspberry/Jetson sea limpio y que un upgrade en cualquiera de los dos lados no rompa al otro.

**Nunca** instales estas dependencias en el venv del backend ni viceversa.

## Instalación inicial (una sola vez)

Desde la raíz del repositorio, abre PowerShell y ejecuta:

```powershell
cd local
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Notas:
- Se usa **Python 3.11** explícitamente (`py -3.11`) porque MediaPipe 0.10.14 está empaquetada para CPython 3.9–3.11; Python 3.12+ falla al importar `mediapipe.solutions.face_mesh`.
- Si PowerShell bloquea `Activate.ps1` por política de ejecución, abre PowerShell **como administrador** una sola vez y corre:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- El venv queda en `local/.venv/` y está ignorado por git.

## Activar el venv en sesiones posteriores

Cada vez que abras una terminal nueva para trabajar en `local/`:

```powershell
cd local
.\.venv\Scripts\Activate.ps1
```

Verás `(.venv)` al inicio del prompt. Para desactivarlo: `deactivate`.

En CMD (no PowerShell): `.\.venv\Scripts\activate.bat`.

## Verificar la instalación

```powershell
python -c "import mediapipe, cv2, torch, scipy, serial, requests; print('OK')"
```

Debe imprimir `OK` sin errores. Si MediaPipe falla, confirma con `python --version` que estás en 3.11.x.

## Comandos del módulo

Con el venv activo y desde `local/`:

**Diagnóstico de cámara** (verificar que la AR0234 entrega frames y FPS reales):
```powershell
# Comando recomendado (combinación validada empíricamente para AR0234 en USB 2.0):
python diagnostico_camara.py --index 1 --backend MSMF --fourcc MJPG --width 1280 --height 720 --fps 60

# Otros usos:
python diagnostico_camara.py                      # auto-escanear
python diagnostico_camara.py --index 1            # forzar índice
python diagnostico_camara.py --no-preview         # sin ventana
```

### Configuración de cámara validada (2026-05-03)

La AR0234 + USB 2.0 alcanza **57.6 fps reales** con esta combinación:
- Backend `CAP_MSMF` (Media Foundation). **NO usar `CAP_DSHOW`** — ignora `CAP_PROP_FOURCC` silenciosamente y deja el stream en YUY2.
- FOURCC `MJPG` fijado **antes** de width/height/fps.
- Resolución 1280×720 @ 60 fps solicitados.

Con esta config las HRV vía rPPG son fiables (resolución temporal de RR ~17 ms). Para llegar a 90 fps haría falta puerto USB 3.0 (azul). Estos parámetros ya están hardcodeados en `modules/m1_vision.py` (`CAM_BACKEND`, `CAM_FOURCC`, `CAM_WIDTH`, `CAM_HEIGHT`, `CAM_FPS`, `CAM_FPS_REAL`).

> **Quirk de MSMF:** la primera apertura tarda 5–15 s (carga de `mfreadwrite.dll`). Es normal. El string `formato activo` puede salir vacío en MSMF — no significa que no esté en MJPG; valida con el FPS real medido.

**Demo del Módulo 1** (BiLSTM somnolencia + rPPG/HRV, requiere `modelos/lstm_A_subjindep_best.pt`):
```powershell
# Por defecto usa cámara índice 1 (la ALPCAM USB; si tu laptop no tiene webcam
# integrada o la global shutter es el índice 0, pasar --camara 0).
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt --camara 0
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt --duracion 30
```

**Orquestador completo** (cámara + Arduino + M1 + M2 + M3 + POST a la API):
```powershell
python main.py --token <JWT_DEL_LOGIN>
```

## Estructura

```
local/
├── README.md                  ← este archivo
├── requirements.txt           ← dependencias (mediapipe==0.10.14 fijada)
├── .venv/                     ← venv local (git-ignored)
├── main.py                    ← orquestador
├── diagnostico_camara.py      ← prueba de la cámara AR0234
├── modelos/                   ← lstm_A_subjindep_best.pt (git-ignored)
└── modules/
    ├── m1_vision.py           ← BiLSTM A + rPPG → P_somnolencia, HRV
    ├── m2_reglas.py           ← motor de 7 reglas EMG+HRV → P_fatiga
    └── m3_fusion.py           ← fusión 40/60 + regla OR > 0.85
```

## Dependencias clave y por qué

| Paquete | Versión | Razón |
|---|---|---|
| `mediapipe` | **==0.10.14** | FIJADA. Versiones posteriores dan `AttributeError` en `FaceMesh`. |
| `opencv-python` | ≥ 4.9 | Captura USB con backend `CAP_DSHOW` (Windows). |
| `torch` (CPU) | ≥ 2.0 | Inferencia BiLSTM (LSTMDrowsy, 0.11 ms/imagen). |
| `scipy` | ≥ 1.11 | Butterworth bandpass + `find_peaks` para HRV desde rPPG. |
| `pyserial` | ≥ 3.5 | Lectura serial 115200 baud del Arduino UNO. |
| `requests` | ≥ 2.31 | POST `/evaluaciones` al backend FastAPI. |

## Modelo

El archivo `modelos/lstm_A_subjindep_best.pt` (BiLSTM Estrategia A, subject-independent — el ÚNICO modelo desplegado) **no está en git**. Cópialo manualmente desde Google Drive:

```
/content/drive/MyDrive/Seminario de Tesis 1/lstm_A_subjindep_best.pt
```

Métricas honestas: Accuracy 74.56%, F1 76.83%, Sensibilidad 87.59%, AUC 0.7942, Latencia 0.11 ms/imagen.

## Hardware esperado

- **Cámara:** ver "Identificación y validación de la cámara" abajo.
- **MCU:** Arduino UNO con sensor Olimex SHIELD-EKG-EMG sobre trapecio superior. Filtro Butterworth orden 4, 20–200 Hz aplicado en el Arduino. Emite CSV `<ms>,<uV>` por serial 115200 baud.

`main.py` auto-detecta el puerto del Arduino por descriptor (CH340 / CP210x / FTDI / Arduino).

## Identificación y validación de la cámara

La unidad usada en el desarrollo de la tesis (cámara del autor) **no expone un identificador específico al sistema operativo**: Windows la enumera con el descriptor UVC genérico `Global shutter camera`. No hay datasheet ni driver propietario empaquetado. Esto refleja una práctica común en módulos OEM revendidos por integradores varios.

### Lo que se sabe del producto (del listado de compra)

- **Vendedor:** ALPCAM, en Amazon.
- **ASIN:** [B0DM92T2MC](https://www.amazon.com/dp/B0DM92T2MC).
- **Sensor declarado:** AR0234 (onsemi), CMOS 2 MP con **obturador global** (la característica clínicamente relevante para rPPG: elimina el rolling shutter que distorsiona la señal de fotopletismografía remota).
- **Specs declaradas por el vendedor:** 1200P, hasta 90 fps, lente gran angular sin distorsión, salida USB UVC plug-and-play.

### Lo que se confirmó empíricamente (2026-05-03)

Mediante `diagnostico_camara.py` se midió la cámara en la laptop del autor (USB 2.0, MediaPipe FaceMesh activo). Los modos que el driver UVC reportó como soportados:

| Resolución solicitada | FPS reportado por driver | Comentario |
|---|---:|---|
| 1920×1200 | 90 / 60 / 30 | Modo nativo declarado |
| 1280×720  | 90 / 60 / 30 | Modo elegido para el sistema |
| 640×480   | 60 / 30      | Para hardware más limitado |

**FPS real medido a 1280×720 @ 60 solicitados con backend MSMF + FOURCC MJPG: 57.6 fps.**
Este es el valor canónico usado en el código (`CAM_FPS_REAL` en `modules/m1_vision.py`). Bajo `CAP_DSHOW` con cualquier FOURCC el mismo modo cae a ~10 fps por saturación de USB 2.0 con YUY2 sin comprimir — por eso el código fija `cv2.CAP_MSMF` explícitamente.

### Estatus en la tesis

Se documenta como **hallazgo de hardware**, no como requisito formal nuevo, dado que los RNF-01..RNF-12 ya están congelados en el Pre Informe oficial. El hallazgo se incorpora a:

- **RNF-07 (Portabilidad):** se complementa con la nota de que el equipo embebido debe disponer de **una cámara USB UVC con sensor de obturador global y soporte UVC para formato MJPG**, alcanzando ≥ 30 fps reales medidos. Cualquier módulo que cumpla esto es intercambiable con el actual sin tocar código.
- **RNF-12 (Escalabilidad):** la portabilidad a Raspberry Pi 5 / Jetson Nano se beneficia de mantener la cámara como un periférico UVC genérico, no atado a un driver propietario.

> Si el jurado exige nombrar el sensor, se referencia como "módulo USB con sensor AR0234 (onsemi), obturador global, distribuido por ALPCAM bajo el ASIN B0DM92T2MC en Amazon, identificado por Windows como `Global shutter camera`". Las especificaciones técnicas del **sensor** (no del módulo) están públicas en el datasheet AR0234CS de onsemi.com.
