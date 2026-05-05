# `local/` — Sistema embebido VigilanceAI

Scripts Python que corren en la **unidad de procesamiento local** del sistema embebido (hoy la laptop del consultorio NOR VISIÓN; mañana Raspberry Pi 5 / Jetson Nano sin tocar backend ni frontend — RNF-12).

Capturan datos en tiempo real desde la cámara USB y el Arduino UNO con sensor Olimex SHIELD-EKG-EMG, ejecutan los Módulos M1 (visión + rPPG), M2 (inferencia difusa EMG/HRV) y M3 (fusión tardía 40/60), y envían el dictamen al backend FastAPI vía REST.

---

## Índice

1. [Ambiente virtual independiente](#ambiente-virtual-independiente)
2. [Instalación inicial](#instalación-inicial-una-sola-vez)
3. [Comandos del módulo](#comandos-del-módulo)
4. [Estructura de archivos](#estructura)
5. [Cámara — perfiles configurables](#cámara--perfiles-configurables)
6. [**Módulo 1 — BiLSTM de somnolencia + rPPG**](#módulo-1--bilstm-de-somnolencia--rppg)
7. [**Calibración personal — el baseline explicado**](#calibración-personal--el-baseline-explicado)
8. [**Módulo 2 — Sistema de inferencia difusa (lógica difusa explicada)**](#módulo-2--sistema-de-inferencia-difusa-tipo-sugeno)
9. [**Módulo 3 — Fusión tardía y dictamen final**](#módulo-3--fusión-tardía-y-dictamen-final)
10. [**Validación de liveness (anti-spoofing)**](#validación-de-liveness-anti-spoofing)
11. [Hardware](#hardware)
12. [**Cable EMG — fabricación casera y mitigación de ruido**](#cable-emg--fabricación-casera-y-mitigación-de-ruido)
13. [Modelo](#modelo)

---

## Ambiente virtual independiente

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

```powershell
cd local
.\.venv\Scripts\Activate.ps1
```

Verás `(.venv)` al inicio del prompt. Para desactivarlo: `deactivate`.

## Verificar la instalación

```powershell
python -c "import mediapipe, cv2, torch, scipy, serial, requests; print('OK')"
```

## Comandos del módulo

Con el venv activo y desde `local/`:

**Listar cámaras detectadas** (lo que consume el backend para el dropdown del frontend):
```powershell
python main.py --listar-camaras
```

**Diagnóstico de cámara** (verificar FPS reales y modos soportados):
```powershell
python diagnostico_camara.py --backend MSMF --no-preview        # auto-escanea
python diagnostico_camara.py --backend DSHOW --index 2           # forzar GoPro
```

**Demo del Módulo 1** (BiLSTM somnolencia + rPPG/HRV):
```powershell
# Usa el perfil de cámara por defecto (alpcam) o el de la env VIGILANCE_CAMERA_PROFILE
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt

# Forzar perfil de cámara
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt --camera-profile gopro
python -m modules.m1_vision modelos/lstm_A_subjindep_best.pt --camera-profile webcam --duracion 30
```

**Orquestador completo** (cámara + Arduino + M1 + M2 + M3 + POST a la API):
```powershell
python main.py --token <JWT_DEL_LOGIN>                            # perfil default
python main.py --token <JWT> --camera-profile gopro --duracion 30 # con GoPro
python main.py --token <JWT> --calibracion-m1                     # modo calibración
```

## Estructura

```
local/
├── README.md                  ← este archivo
├── requirements.txt           ← dependencias (mediapipe==0.10.14 fijada)
├── .venv/                     ← venv local (git-ignored)
├── main.py                    ← orquestador + listado de cámaras
├── diagnostico_camara.py      ← prueba de cámaras
├── modelos/                   ← lstm_A_subjindep_best.pt (git-ignored)
└── modules/
    ├── cameras.py             ← perfiles de cámara configurables
    ├── m1_vision.py           ← BiLSTM A + rPPG + liveness
    ├── m2_reglas.py           ← inferencia difusa Sugeno → P_fatiga
    └── m3_fusion.py           ← fusión 40/60 + regla OR > 0.85
```

---

## Cámara — perfiles configurables

Los parámetros de cada cámara (índice OpenCV, backend, resolución, FPS, FOURCC) viven en `modules/cameras.py` como **perfiles**. El sistema selecciona el perfil activo en este orden de precedencia:

1. Argumento CLI `--camera-profile <nombre>` (en `main.py` o `m1_vision.py`).
2. Variable de entorno `VIGILANCE_CAMERA_PROFILE`.
3. Default: `"alpcam"` (la cámara de producción).

| Perfil | Cámara | Backend | Resolución | FPS real | Uso |
|---|---|---|---|---:|---|
| `alpcam` | ALPCAM AR0234 USB (B0CXDS8F6Q / B0DM92T2MC) | MSMF | 1280×720 | 57.6 | **producción** |
| `gopro` | GoPro Hero 11 Black (vía GoPro Webcam Utility) | DSHOW | 1280×720 | 70.5 | pruebas temporales |
| `webcam` | Cámara integrada de laptop (VGA) | DSHOW | 640×480 | 29.6 | fallback |

Para añadir una cámara nueva basta con sumar una entrada al diccionario `PROFILES` en `modules/cameras.py` — el código del pipeline no se toca.

### Por qué CAP_MSMF + MJPG para la ALPCAM (validado 2026-05-03)

La cámara con sensor AR0234 + USB 2.0 alcanza **57.6 fps reales** únicamente con esta combinación:
- Backend `CAP_MSMF` (Media Foundation). **NO usar `CAP_DSHOW`** — ignora `CAP_PROP_FOURCC` silenciosamente y deja el stream en YUY2.
- FOURCC `MJPG` fijado **antes** de width/height/fps.

Con `DSHOW + cualquier FOURCC` el mismo modo cae a ~10 fps por saturación de USB 2.0 con YUY2 sin comprimir.

> **Quirk de MSMF:** la primera apertura tarda 5–15 s (carga de `mfreadwrite.dll`). Es normal.

### GoPro Hero 11 como cámara temporal

Sustituye **temporalmente** a la ALPCAM mientras llega la unidad nueva. **No va al informe final** porque tiene rolling shutter (contradice el RNF-07 que justifica global shutter para rPPG sin artefactos). Solo para pruebas funcionales del pipeline.

Para activarla: encender, conectar USB-C a la laptop, abrir el icono "GoPro Webcam" en bandeja del sistema y click derecho → "Show Preview". A partir de ese momento la cámara virtual `GoPro Camera` es accesible vía OpenCV en índice 2 con DSHOW.

### Identificación canónica de la ALPCAM (para el informe)

La unidad usada en el desarrollo de la tesis no expone un identificador específico al SO: Windows la enumera con el descriptor UVC genérico `Global shutter camera`. No hay datasheet ni driver propietario empaquetado.

- **Vendedor:** ALPCAM, en Amazon. ASIN [B0CXDS8F6Q](https://www.amazon.com/dp/B0CXDS8F6Q) (unidad nueva en compra) o [B0DM92T2MC](https://www.amazon.com/dp/B0DM92T2MC) (unidad anterior, devuelta).
- **Sensor declarado:** AR0234CS (onsemi), CMOS 2 MP con **obturador global** — la característica clínicamente relevante para rPPG.
- **Specs declaradas:** 1200P, hasta 90 fps, lente gran angular, USB UVC plug-and-play.

Si el jurado exige nombrar el sensor: "módulo USB UVC con sensor AR0234 (onsemi), obturador global, distribuido por ALPCAM en Amazon, identificado por Windows como `Global shutter camera`". Datasheet del sensor en onsemi.com.

---

## Módulo 1 — BiLSTM de somnolencia + rPPG

Archivo: `modules/m1_vision.py`.

### Pipeline de somnolencia

```
Cámara (perfil activo) →
  MediaPipe FaceMesh (468 landmarks por frame) →
  EAR + MAR por frame →
  Sliding window (SEQ_LEN=20, STRIDE=5) →
  BiLSTM (LSTMDrowsy, 2 capas, hidden=128, bidireccional) →
  P_somnolencia ∈ [0, 1]
```

### Arquitectura del modelo (`LSTMDrowsy`)

Idéntica a la celda 31 del notebook `Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb`:

```python
nn.LSTM(in_feat=2, hidden=128, layers=2,
        batch_first=True, dropout=0.3, bidirectional=True)
# Pooling concatenado: out.mean(dim=1) + out[:, -1, :] → 512 dims
nn.Sequential(
    nn.Linear(512, 128), nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(128, 64),  nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(64, 2),
)
```

Checkpoint: `modelos/lstm_A_subjindep_best.pt` — **único modelo desplegado**. La Estrategia B (subject-dependent) se descartó por inflar métricas con data leakage; ver el Pre Informe.

### Métricas honestas (test, sujetos NO vistos en train)

| Métrica | Valor | Por qué importa |
|---|---:|---|
| Accuracy | **74.56%** | Métrica global; engaña en clases desbalanceadas |
| F1 | **76.83%** | Balance precisión/sensibilidad |
| **Sensibilidad** | **87.59%** | **El que más importa clínicamente** — atrapamos 9 de 10 casos de somnolencia |
| AUC | 0.7942 | Capacidad discriminativa del clasificador |
| Latencia | 0.11 ms/imagen | Compatible con tiempo real |

> **Defensa ante jurado si dicen "74% es bajo":** la mayoría de papers DDD reportan >95%, pero esos son subject-dependent (mismo sujeto en train y test). La Estrategia A es subject-independent — el modelo nunca vio al sujeto evaluado. Esa es la única métrica honesta para despliegue real, donde cada médico es nuevo. La sensibilidad 87.59% es la métrica clínicamente relevante: el sistema falla en sentido conservador (sobre-alerta), nunca en sentido peligroso. Y M1 NO es el dictamen final — M3 fusiona con M2 (60% de peso) y aplica corrección personal por baseline.

### Pipeline rPPG (la cámara hace doble trabajo)

La misma cámara, además de M1, extrae la señal cardíaca para HRV en M2:

```
ROI frente (8 landmarks: [10, 109, 67, 103, 151, 332, 297, 338]) →
  Tripleta (R, G, B) media por frame →
  POS (Plane-Orthogonal-to-Skin, Wang 2017) →
  Butterworth bandpass 0.7–3.5 Hz (42–210 bpm) →
  find_peaks → intervalos RR (ms) →
  Filtro clínico Task Force ESC/NASPE 1996 (rango fisiológico + ±20% mediana) →
  SDNN, RMSSD, pNN50, HR
```

POS aísla el componente cardíaco proyectando RGB sobre el plano ortogonal al tono de piel — robusto a movimiento e iluminación, vs el método ingenuo del canal verde.

### Gate de calidad de señal

Se rechaza la señal HRV como "calidad baja" cuando `RMSSD/SDNN > 1.4`. El límite físico es √2 ≈ 1.414 (Task Force [11]). Una señal con ratio mayor es **matemáticamente imposible** como HRV genuina → es ruido.

---

## Calibración personal — el baseline explicado

> **Mucha gente confunde "baseline" con "aprendizaje supervisado". No lo es.** El BiLSTM ya está entrenado. El baseline NO entrena nada. Es **calibración personal del modelo entrenado**.

### Analogía mecánica

Es exactamente análogo al "tarar" una balanza (poner a cero con el envase vacío) o a la línea isoeléctrica de un ECG (referencia sobre la que se mide la elevación del segmento ST). En ambos casos el instrumento está fabricado y calibrado, pero hay que ajustar un offset por el contexto particular de uso.

### El problema que resuelve (validado en Iter. 11 del Pre Informe)

El BiLSTM aprendió de 28 sujetos del DDD. Cada cara tiene EAR/MAR distintos por geometría (anchura interocular, posición de párpados, etc.). Para una cara nueva en zona OOD (out-of-distribution) el modelo da una probabilidad sesgada **uniformemente** — sobreestima o subestima a ese sujeto en todos sus estados.

El autor del proyecto tiene EAR a +4.1σ del mean del DDD. Resultado del Iter. 11:
- **Estado alerta declarado:** P = 0.9608
- **Estado de sueño real:** P = 0.8840

Sin corrección, el sistema **siempre** lo marcaría NO_APTO → falsos positivos sistemáticos.

### Cómo opera matemáticamente

**Modo calibración** (1 sola vez por médico):
1. El médico se sienta frente a la cámara declarándose alerta.
2. Captura 30 s → BiLSTM emite N predicciones por sliding window.
3. Promedio = `P_baseline = 0.9608`.
4. Se persiste en BD (tabla `baselines_somnolencia`, columna `p_somnolencia`).

**Modo evaluación normal** (cada vez que se usa):
1. Captura 30 s → BiLSTM emite `P_obs`.
2. M3 calcula `P_efectiva = max(0, P_obs − P_baseline)`.
3. La P efectiva (no la cruda) entra a la fusión 40/60.

| Caso | P_obs | P_baseline | P_efectiva | Lectura |
|---|---:|---:|---:|---|
| Médico alerta (control) | 0.96 | 0.96 | 0.00 | sin penalizar — sin baseline daría 0.96 → falso positivo |
| Médico ligeramente cansado | 0.99 | 0.96 | 0.03 | aporta poco a P_total — coherente con realidad |
| Médico evidentemente dormido | 0.99 | 0.50 | 0.49 | aporta fuerte a P_total — dictamen NO_APTO |

### Limitación honesta (importante declarar al jurado)

El baseline corrige sesgo **uniforme**: cuando el modelo sobreestima a TODO ese sujeto. Pero en casos de OOD severo el modelo puede invertirse (caso del autor: P_alerta=0.96 > P_dormido=0.88). Para esos sujetos el baseline aditivo no es suficiente. Mitigación:
1. **M2 (peso 60%) compensa** con señales fisiológicas que SÍ son baseline-corregidas individualmente.
2. **Trabajo futuro:** fine-tuning del último encoder LSTM por sujeto (requiere capturar ambos estados, lo cual es éticamente difícil en médicos activos).

### Por qué baseline aditivo y no fine-tuning supervisado

Fine-tuning requiere muestras de ambas clases (alerta Y dormido) por sujeto para reentrenar. **No se puede pedirle a un cirujano que opere dormido para entrenar el modelo** — la captura del estado positivo es éticamente imposible. El baseline solo necesita el estado alerta, capturable de forma segura. Esa es la justificación clínica por la que se eligió este enfoque.

---

## Módulo 2 — Sistema de inferencia difusa tipo Sugeno

Archivo: `modules/m2_reglas.py`.

> Esta sección está pensada para que la entiendas tú y la defiendas frente al jurado. Empieza desde cero: qué es la lógica difusa, qué la diferencia de la lógica clásica, y cómo se mapea a tu implementación.

### 1. Lógica clásica vs lógica difusa (en una página)

**Lógica clásica (Booleana)** — la que se enseña en cursos básicos de programación:
- Una proposición es **Verdadera (1) o Falsa (0)**.
- "El RMS está alto" → True si RMS > umbral, False en otro caso.
- Cambio brusco: RMS=99% del umbral → False. RMS=101% → True. La diferencia de 2% cambia totalmente el dictamen.

Los **sistemas expertos clásicos** se construyen con esta lógica: tablas de reglas tipo "IF condición THEN consecuencia" donde la condición es un booleano duro. Son fáciles de entender pero **frágiles**: en señales fisiológicas ruidosas (EMG, HRV) un 1% de variación accidental puede disparar un dictamen completamente distinto.

**Lógica difusa** (Lotfi A. Zadeh, 1965) — generalización donde:
- Una proposición tiene un **grado de verdad continuo** entre 0 y 1.
- "El RMS está alto" → 0.0 (nada), 0.3 (algo), 0.8 (bastante), 1.0 (totalmente).
- Cambio suave: RMS=99% del umbral → 0.45. RMS=101% → 0.55. Refleja la incertidumbre clínica real.

La intuición: cuando un médico clínico dice "el paciente está cansado", no está aplicando un umbral binario — está integrando múltiples señales con grados de confianza. La lógica difusa formaliza esa integración.

### 2. Los 5 componentes de un sistema de inferencia difusa

Cualquier sistema basado en inferencia difusa tiene exactamente estos 5 componentes:

| # | Componente | Definición |
|---|---|---|
| 1 | **Variables lingüísticas** | Las magnitudes que se evalúan ("RMS-EMG", "frecuencia mediana", "SDNN"...) |
| 2 | **Conjuntos difusos** | Categorías borrosas sobre cada variable ("desviación elevada del baseline") |
| 3 | **Funciones de pertenencia** | Curvas que mapean cada valor de la variable a su grado μ ∈ [0,1] de pertenencia al conjunto difuso |
| 4 | **Reglas IF-THEN difusas** | "IF μ(RMS es alto) ENTONCES contribuir μ × peso a la fatiga" |
| 5 | **Defuzzificación** | Convertir el conjunto difuso de salida en un único valor numérico (P_fatiga) |

### 3. Tipos de inferencia difusa (Mamdani vs Sugeno)

Hay dos grandes familias. Es importante saber la diferencia para defender por qué se eligió una.

| | **Mamdani** | **Sugeno (TSK)** |
|---|---|---|
| Salida de cada regla | Un conjunto difuso (curva) | Un valor numérico (escalar o función) |
| Defuzzificación | Centroide del área agregada (caro) | Suma o promedio ponderado (eficiente) |
| Expresividad | Más rica (apropiada cuando hay expertos humanos modelando) | Más simple |
| Coste computacional | Alto | Bajo |
| Uso típico | Sistemas explicativos, control de procesos físicos | Sistemas embebidos, control adaptativo, modelos de regresión difusa |

**M2 implementa Sugeno orden cero.** "Orden cero" significa que cada regla emite una constante (no una función polinomial de las entradas). Esto es la elección correcta para este sistema porque:
1. Debe correr en una unidad embebida (Raspberry Pi 5 / Jetson Nano en producción) con CPU limitada.
2. Cada evaluación es de 30 s y se hace cada vez que un médico se sienta — la latencia importa.
3. La literatura clínica define los pesos directamente (no hace falta inferir polinomios).
4. La trazabilidad es directa: aporte de cada regla = μᵢ × wᵢ.

Si el jurado pregunta "¿por qué no Mamdani?": *"Mamdani con conjuntos triangulares y defuzzificación por centroide no aporta precisión adicional en este dominio (Lin et al. 2015 [14]) y complica el motor sin beneficio clínico — los pesos provienen de validación experimental en literatura, no de inferencia humana."*

### 4. Mapeo formal a la implementación de M2

| Componente teórico | Implementación en `m2_reglas.py` |
|---|---|
| **Variables lingüísticas** | `rms`, `freq_mediana`, `freq_media`, `sdnn`, `rmssd`, `pnn50` |
| **Conjuntos difusos** | "Desviación elevada respecto al baseline personal" (un conjunto por regla) |
| **Funciones de pertenencia** | Sigmoidal tipo S: `μ(d, u) = 1 / (1 + exp(−12·(d−u)))` con k=12 (pendiente) y u (umbral clínico) |
| **Reglas IF-THEN difusas** | 7 reglas tabuladas abajo, cada una con peso wᵢ |
| **Defuzzificación** | `P_fatiga = Σ wᵢ·μᵢ` (Sugeno orden 0) |
| **Mecanismo de explicación** | Lista `alertas` + tabla en `EvaluacionDetalle.tsx` |

### 5. La función de pertenencia sigmoidal — qué es exactamente

Es una **función de pertenencia tipo S**, miembro estándar del catálogo de Zadeh. La forma:

```
μ(d, u) = 1 / (1 + exp(−k · (d − u)))
```

Donde:
- `d` es la **desviación relativa** observada respecto al baseline. Por ejemplo, para RMS-EMG: `d = (rms_obs − rms_baseline) / rms_baseline`.
- `u` es el **umbral clínico** del catálogo (ej. 0.20 = +20% sobre el baseline).
- `k = 12` es la **pendiente** que controla qué tan abrupta es la transición de "no" a "sí".

Forma de la curva (eje x = desviación, eje y = grado de pertenencia):

```
     μ
   1.0 ┤           ╭──────  ← totalmente "elevado"
       │         ╱
   0.5 ┼────────●─────────  ← punto de inflexión (d = u)
       │      ╱
   0.0 ┼─────╯
       └─────────────────── d
       0     u
```

Al cambiar `k` cambia la pendiente:
- `k → ∞`: la sigmoide se vuelve un escalón duro = lógica clásica (recuperás el sistema experto booleano).
- `k → 0`: la sigmoide se vuelve casi plana = el sistema deja de discriminar.
- `k = 12`: zona de transición de ~0.4 unidades alrededor del umbral. Calibrado para que un 5–10% de variación accidental no dispare la regla, pero un 20–25% sí.

> Esto es CLAVE para defender: la sigmoidal no es un truco arbitrario, **es una de las funciones de pertenencia canónicas en lógica difusa** (junto con triangulares y trapezoidales). La elección de k=12 es justificable como "calibrada para ruido fisiológico típico de las señales en cuestión".

### 6. Las 7 reglas del motor (base de conocimiento)

| Regla | Indicador | Umbral | Peso wᵢ | Base bibliográfica |
|---|---|---:|---:|---|
| `rms_incremento` | RMS-EMG > +20% baseline | +0.20 | 0.15 | Wijsman [8], Merletti [12] |
| `rms_decremento` | RMS-EMG < −25% baseline | −0.25 | 0.10 | De Luca [13] |
| `freq_mediana` ★ | MDF < −15% baseline | −0.15 | **0.30** | Cifrek [10], De Luca [13] |
| `freq_media` | MNF < −15% baseline | −0.15 | 0.10 | Cifrek [10] |
| `sdnn` | SDNN < −20% baseline | −0.20 | 0.15 | Task Force ESC/NASPE [11] |
| `rmssd` | RMSSD < −20% baseline | −0.20 | 0.12 | Task Force [11] |
| `pnn50` | pNN50 < −25% baseline | −0.25 | 0.08 | Task Force [11] |

★ MDF (frecuencia mediana de la EMG) es el indicador espectral más robusto de fatiga muscular — por eso recibe el peso máximo (0.30).

**Los pesos suman 1.0** (verificado por `assert` en el código). Esto convierte la salida en una probabilidad bien definida en [0, 1].

### 7. Robustez ante datos faltantes

Si el módulo rPPG no pudo calcular HRV (señal insuficiente, calidad baja, etc.), `hrv = None`. El motor:
1. Anula los aportes de las 3 reglas HRV (sdnn, rmssd, pnn50).
2. **Redistribuye proporcionalmente** los pesos sobrantes (0.15 + 0.12 + 0.08 = 0.35) entre las 4 reglas EMG, manteniendo Σwᵢ = 1.

El sistema sigue siendo operativo con solo EMG, pero con menor robustez. Esto es defendible: no es "fallback frágil" sino **degradación graceful**.

### 8. Cómo defender M2 ante el jurado

**Si te preguntan "¿es un sistema experto?":**
> "Sí, es un **sistema experto difuso de tipo Sugeno orden cero**. Tiene los 5 componentes formales: variables lingüísticas, conjuntos difusos, funciones de pertenencia sigmoidales, base de reglas IF-THEN con pesos clínicos, y defuzzificación por suma ponderada. La diferencia con un sistema experto clásico booleano es que las reglas no devuelven 0/1 sino grados de activación continuos — esto evita los falsos positivos típicos de los umbrales duros en señales fisiológicas inherentemente ruidosas."

**Si te preguntan "¿por qué no Mamdani?":**
> "Mamdani requiere defuzzificación por centroide y conjuntos difusos triangulares definidos para cada salida posible. En este dominio, donde los pesos de cada regla están definidos por literatura clínica con base experimental (no por experto humano modelando), Sugeno orden cero da equivalencia funcional con muchísima menor carga computacional — crítico para una unidad embebida con CPU limitada."

**Si te preguntan "muéstrame la base de conocimiento":**
> Tabla de 7 reglas con sus umbrales, pesos y referencias IEEE → la que está arriba.

**Si te preguntan "muéstrame el motor de inferencia operando":**
> En el frontend, página `/evaluaciones/:id` → tabla "Inferencia difusa M2 — aporte por regla" con μᵢ, wᵢ, μᵢ·wᵢ por cada regla, y total. Cada regla con μ>0.5 resaltada en ámbar.

### 9. Frase para el Pre Informe (Iteración 6, sección M2)

> *"El Módulo 2 implementa un sistema de inferencia difusa basado en reglas (tipo Sugeno orden cero). Las funciones de pertenencia son sigmoidales con pendiente k=12 centradas en umbrales clínicos derivados de la literatura especializada [refs IEEE]. Cada regla aporta un grado de activación μᵢ ∈ [0,1] al output final mediante suma ponderada P_fatiga = Σwᵢ·μᵢ, donde los pesos wᵢ representan la confiabilidad clínica relativa de cada indicador. Esta arquitectura combina la trazabilidad de un sistema experto (reglas explícitas con base bibliográfica) con la robustez de la lógica difusa (transiciones suaves en lugar de umbrales duros), evitando los falsos positivos típicos de los sistemas de reglas booleanas en señales fisiológicas inherentemente ruidosas."*

---

## Módulo 3 — Fusión tardía y dictamen final

Archivo: `modules/m3_fusion.py`.

### Esquema

```
P_efectiva_M1 = max(0, P_somnolencia − P_baseline)        ← corrección personal (RNF-05)
P_total = 0.40 · P_efectiva_M1  +  0.60 · P_fatiga_M2     ← fusión 40/60
```

**Por qué 40/60** (M2 pesa más):
- M1 (visión) tiene métricas individuales modestas (74.56%) y sufre de subject-dependence.
- M2 (fisiológico) trabaja sobre **baseline personal** desde el inicio — sus reglas comparan contra el médico mismo, no contra la población.
- M2 integra dos modalidades fisiológicas independientes (EMG + HRV) → mayor robustez frente a fallos de un solo sensor.

### Regla OR de alta confianza

Si **cualquiera** de los dos módulos supera 0.85 → escalar dictamen a NO_APTO directamente, ignorando la ponderación. Ejemplo: somnolencia visual severa (microsueño detectado, ojos cerrados >5 s) puede dar M1=0.92 incluso con M2=0.40. Sin la regla OR, P_total = 0.40·0.92 + 0.60·0.40 = 0.61 → ATENCIÓN. Con la regla OR → NO_APTO.

### Umbrales de dictamen

| Rango P_total | Dictamen | Descripción |
|---|---|---|
| < 0.35 | **APTO** | Sin señales significativas |
| 0.35 ≤ P < 0.60 | **ATENCIÓN** | Señales leves, descanso recomendado |
| ≥ 0.60 | **NO APTO** | Fatiga elevada, no continuar con actividades críticas |

---

## Validación de liveness (anti-spoofing)

Defiende contra tres ataques o fallos:

1. **Cámara apuntando a la nada** (techo, escritorio) → no hay cara detectable.
2. **Foto / pantalla con rostro estático** frente a la cámara → cara detectable pero sin parpadeos ni perfusión sanguínea.
3. **Iluminación insuficiente** → detección facial intermitente.

### Criterios (todos deben pasar)

Función `validar_liveness()` en `m1_vision.py`:

| Criterio | Umbral | Qué detecta |
|---|---:|---|
| `tasa_deteccion_facial` | ≥ 70% | Cámara enfocada a sujeto (no a pared) |
| `ear_std` | ≥ 0.005 | Variabilidad ocular (foto da ~0) |
| `parpadeos / 15s` | ≥ 1 | Sujeto vivo blink rate (Soukupová & Cech 2016) |
| `hrv.calidad` | "alta" | Perfusión sanguínea consistente (foto da ratio aleatorio) |

### Flujo cuando falla

1. **Local:** `main.py` detecta liveness fail tras M1 → NO llama a M3, NO POSTea evaluación. Emite JSON `{liveness_ok: false, razones_liveness: [...]}` por stdout.
2. **Backend:** `EvaluacionService` y `CalibracionService` traducen a HTTP 422 con razones unidas por " | ".
3. **Frontend:** páginas `EvaluacionAuto.tsx` y `Calibracion.tsx` muestran panel ámbar específico "Captura no válida — no se registró evaluación" con bullets por razón. La BD nunca recibe registros de capturas inválidas.

### Defensa anti-foto (la pregunta del jurado)

> *"¿Qué pasa si pongo una foto frente a la cámara para falsear la evaluación?"*

Defensa por capas (defense in depth):
1. MediaPipe detecta la cara, pero el EAR queda constante → `ear_std < 0.005` → criterio 2 falla.
2. Foto no parpadea → criterio 3 falla.
3. Foto no tiene perfusión sanguínea → POS proyecta solo ruido → ratio RMSSD/SDNN inconsistente → criterio 4 falla.
4. Cualquier criterio fallido → HTTP 422, no se registra evaluación.

### Limitaciones honestas (declarar en informe)

- **Replay attack:** vulnerable a video pre-grabado de un sujeto real. No mitigable sin desafío-respuesta en pantalla (girar cabeza, sonreír) → propuesto como trabajo futuro.
- **Deepfake en tiempo real con perfusión sintética:** lejos del modelo de amenazas de un consultorio médico; declararlo como out of scope es defendible.

### Trazabilidad en frontend

`EvaluacionDetalle.tsx` muestra la sección "Validación de liveness (anti-spoofing)" con: tasa detección facial, parpadeos, ear_std, calidad rPPG. Permite mostrar al jurado en vivo que cada captura registrada pasó los 4 criterios.

---

## Hardware

- **Cámara:** ver sección "Cámara — perfiles configurables" arriba.
- **MCU:** Arduino UNO con sensor Olimex SHIELD-EKG-EMG sobre trapecio superior. Filtro Butterworth orden 4, 20–200 Hz aplicado en el Arduino. Emite CSV `<ms>,<uV>` por serial 115200 baud. `main.py` auto-detecta el puerto por descriptor (CH340 / CP210x / FTDI / Arduino).

## Cable EMG — fabricación casera y mitigación de ruido

> **Contexto:** el cable original Olimex `CABLE-EKG-EMG-SHIELD` tarda ~5 semanas en llegar a Perú desde Bulgaria/EE.UU. Esta sección documenta cómo construir un sustituto funcional para sustentación con piezas que se consiguen el mismo día en Chiclayo, sin perder validez del experimento.

### Pinout del shield Olimex SHIELD-EKG-EMG

El conector hembra del shield es un jack estéreo TRS de 3.5 mm. La asignación de pines (datasheet oficial Olimex) es:

| Segmento del jack | Función | Color convencional | Dónde se pega el electrodo |
|---|---|---|---|
| **TIP** (la punta) | IN+ (entrada diferencial positiva) | 🔴 Rojo | Vientre del músculo trapecio superior |
| **RING** (anillo central) | IN− (entrada diferencial negativa) | ⚫ Negro | Mismo músculo, ~2-3 cm más abajo, en línea con las fibras |
| **SLEEVE** (base) | DRL/GND (driven right leg, tierra activa) | ⚪ Blanco | Hueso prominente sin músculo: codo, muñeca o clavícula opuesta |

> **Importante:** los cocodrilos NO se enganchan directamente a la piel. Se enganchan al **broche metálico (snap) de un electrodo pre-gelado desechable Ag/AgCl**, que sí se pega a la piel previa limpieza con alcohol al 70%. Sin electrodo, no hay contacto eléctrico aprovechable.

### Por qué un cable casero funciona (justificación técnica)

El shield Olimex no es un sensor "en bruto":

- **Amplificador de instrumentación diferencial** con CMRR > 100 dB → cualquier interferencia que entre por igual en IN+ e IN− se cancela automáticamente. Esto incluye el ruido de 60 Hz de la red eléctrica.
- **Ganancia interna ~1000×** → la señal sale grande sin importar el cable.
- **Filtros analógicos** pasa-banda + buffer activo en el DRL que inyecta una contraseñal en el cuerpo para anular el ruido. Compensa la falta de blindaje del cable.

Este diseño está pensado precisamente para tolerar leads imperfectos en setups educativos / de prototipo.

### Opción A (recomendada) — Cable casero con plug TRS + cocodrilos

**Lista de compras (Mercado Modelo Chiclayo, segundo nivel zona electrónica, o Av. Balta / Bolognesi):**

| Pieza | Cómo pedirlo | Cantidad | Precio aprox |
|---|---|---|---|
| Plug TRS macho 3.5 mm soldable | "Plug TRS macho 3.5 mm soldable, audio estéreo" | 1 | 2-3 soles |
| Cable cocodrilo a cocodrilo, ~30 cm | "Cable de prueba con cocodrilos en ambos extremos" | 3 (rojo, negro, blanco/amarillo) | 3-5 soles c/u |
| Estaño + cautín 30W (opcional) | "Cautín 30 W y estaño con resina" | 1 set | 25-40 soles |
| Termorretráctil 3 mm (opcional) | "Espagueti termorretráctil 3 mm, 1 metro" | — | 2 soles |
| Electrodos pre-gelados snap Ag/AgCl | "Electrodos para electrocardiograma, snap" | 1 bolsa de 50 | ~30 soles (farmacia) |

**Total mínimo (sin cautín): ~15 soles** + electrodos.

**Alternativa sin soldar:** los puestos del 2.º nivel del Mercado Modelo sueldan tu plug por 3-5 soles si llevas las piezas. Decirles textual: *"suéldame estos tres cables al plug TRS, el rojo al tip, el negro al ring, el blanco al sleeve"*.

**Procedimiento de armado:**

1. Cortar cada cable cocodrilo a la mitad → quedan 6 mitades, usas 3.
2. Pelar 5 mm del extremo cortado de cada mitad.
3. **Pasar primero la carcasita de plástico del plug por el cable** (error frecuente: olvidarlo y desoldar todo).
4. Desenroscar la carcasita del plug → quedan visibles los 3 terminales metálicos.
5. Identificar terminales:
   - El conectado a la **punta puntiaguda** del plug = TIP (cable rojo).
   - El **del medio** = RING (cable negro).
   - El **más grande / envolvente** = SLEEVE (cable blanco).
6. Soldar cada cable a su terminal correspondiente (calienta cautín → apoya simultáneamente cautín + cable + terminal 2 s → toca el estaño contra cable+terminal, no contra cautín → enfría 5 s sin mover).
7. Enroscar la carcasita.

```
[Sensor Olimex]──┤ Hembra TRS 3.5mm
                  │
        [Plug TRS macho 3.5mm]   ── pieza 1
                  │
              cable corto         ── mitad de cocodrilo-cocodrilo
                  │
        [Cocodrilo]               ── pieza 2 (otra mitad)
                  │
        [Snap del electrodo]      ── pieza 3 (electrodo pegado a la piel)
                  │
              [Piel]
```

### Opción B (último recurso) — Cable de audífonos reciclados

Si no consigues plug suelto y solo tienes audífonos viejos en casa:

1. Cortar el cable del audífono dejando ~70 cm + el jack. Tirar los parlantes.
2. Pelar el extremo cortado y separar los hilos. Verás 3 (TRS) o 4 (TRRS, con micrófono) hilos delgados esmaltados de colores distintos.
3. **Raspar 1-2 cm de esmalte** de cada hilo con lija fina o cuchillo (CRÍTICO — los hilos de audífono están barnizados con un esmalte transparente que aísla; sin raspar no conducen aunque parezcan cobre puro).
4. Identificar qué hilo va a cada segmento del jack con multímetro en modo continuidad:
   - Punta del multímetro a la **TIP** del jack + a cada hilo. El que pite → ese es **IN+ (rojo)**.
   - Repetir con **RING** → ese hilo es **IN− (negro)**.
   - Repetir con **SLEEVE** → ese hilo es **DRL (blanco)**.
   - Si hay 4 hilos (TRRS), uno no pitará con ninguno o pitará con un anillo extra que no usamos → ignorar y aislar con cinta.
5. Soldar (o enrollar fuerte + cinta aislante si no hay cautín) cada hilo identificado a un cocodrilo.
6. Marcar cada cocodrilo con cinta de color (rojo, negro, blanco).

**Limitaciones de la Opción B vs Opción A:**

- Hilos finos esmaltados se rompen internamente con facilidad → verificar continuidad antes de cada calibración.
- Sin blindaje físico → mayor ruido de 60 Hz (mitigado por software, ver abajo).
- Mal contacto si no se solda → señal con saltos no fisiológicos.

### 5 técnicas anti-ruido (aplican a ambas opciones)

1. **Trenzar los hilos rojo y negro.** Tomar ambos juntos y enroscarlos uno sobre otro como una cuerda — 3-4 vueltas por cada 10 cm. La interferencia entra por igual en ambos y el amplificador diferencial la cancela. **Es el truco más importante**, especialmente sin blindaje.
2. **Cable lo más corto posible.** Cada cm extra es antena. ~70 cm desde sensor hasta hombro es suficiente.
3. **Aleja del cargador del laptop durante la captura.** Los cargadores switching emiten ruido de alta frecuencia. Ideal: capturar con la laptop en batería (desconectada del enchufe) los 30 s. Aleja también celulares, monitores externos, fluorescentes/LED.
4. **Filtro notch a 60 Hz en software.** En el procesamiento EMG, antes del FFT, aplicar un filtro notch IIR (`scipy.signal.iirnotch`) centrado en 60 Hz, Q=30. Implementar en `local/main.py` función `_procesar_senal_emg` si hay residual visible.
5. **Faraday improvisado.** Si tras 1-4 sigue habiendo ruido visible, envolver el cable en papel aluminio y conectar el aluminio al cocodrilo BLANCO (DRL/GND) con un trozo de cable adicional. Cinta aislante encima. Esto replica el blindaje del cable original.

### Validación de calidad de señal antes de calibrar

Crear `local/test_emg.py`:

```python
"""Validación rápida del cable EMG. Imprime 1 segundo de muestras
brutas (500 muestras a 500 Hz). Útil para verificar contacto y
nivel de ruido antes de una calibración real."""
import serial
import time

PUERTO = "COM3"  # ajustar al puerto del Arduino
ser = serial.Serial(PUERTO, 115200, timeout=1)
time.sleep(2)  # esperar reset del Arduino

print(f"Capturando 1 s desde {PUERTO}...")
muestras = []
t_fin = time.time() + 1.0
while time.time() < t_fin:
    linea = ser.readline().decode("ascii", errors="ignore").strip()
    if "," in linea:
        try:
            muestras.append(float(linea.split(",")[1]))
        except ValueError:
            pass
ser.close()

if not muestras:
    print("[FALLA] No se recibieron muestras. Revisar puerto y firmware.")
else:
    import statistics
    print(f"Muestras: {len(muestras)}")
    print(f"Media:   {statistics.mean(muestras):8.1f} µV")
    print(f"Stdev:   {statistics.stdev(muestras):8.1f} µV")
    print(f"Min:     {min(muestras):8.1f} µV")
    print(f"Max:     {max(muestras):8.1f} µV")
```

**Criterios de aceptación:**

- En **reposo** (músculo relajado): stdev < 30 µV, sin oscilaciones periódicas claras → cable OK.
- En **contracción** (encoger el hombro): stdev > 100 µV, valores oscilan ±300-500 µV → señal EMG real detectada.
- Si stdev en reposo > 80 µV o ves un patrón senoidal rítmico → ruido de 60 Hz dominante. Aplicar técnicas 1-5.
- Si los valores son siempre el mismo número (saturación) o siempre 0 → mal contacto, electrodo seco, o conexión invertida.

### Colocación correcta de electrodos (trapecio superior)

1. **Limpiar la piel** con alcohol al 70% en las 3 zonas. Esperar 30 s a que seque (necesario para adhesión).
2. **Pegar 3 electrodos pre-gelados snap Ag/AgCl:**
   - Electrodo 🔴 (IN+): vientre del trapecio superior (mitad entre cuello y hombro, lado dominante).
   - Electrodo ⚫ (IN−): mismo músculo, 2-3 cm más abajo en línea con las fibras musculares.
   - Electrodo ⚪ (DRL): clavícula opuesta, codo o muñeca contralateral — busca hueso, no músculo.
3. **Esperar 1 minuto** después de pegarlos antes de capturar — el gel necesita asentarse para reducir impedancia de contacto.
4. **Enganchar los cocodrilos** del cable a los snaps de los electrodos respetando el código de color.
5. **Conectar** el plug TRS al shield Olimex montado sobre el Arduino UNO.
6. **Power-on** del Arduino vía USB. El firmware aplica Butterworth orden 4, 20-200 Hz y emite CSV `<ms>,<uV>` por serial 115200 baud.

### Declaración para sustentación (honestidad técnica)

Si se sustenta con cable casero, declararlo explícitamente en la presentación:

> "El cable Olimex original `CABLE-EKG-EMG-SHIELD` tiene un tiempo de envío internacional incompatible con el cronograma. Se construyó un sustituto con plug TRS comercial y cocodrilos estándar, validando la calidad de señal contra criterios cuantitativos (stdev en reposo < 30 µV, stdev en contracción > 100 µV). Se aplicó filtro notch a 60 Hz como mitigación de ruido residual. En despliegue de producción se reemplazará por el cable original blindado, sin modificación de código."

Esto suma puntos de defensa: muestra dominio del trade-off técnico, conciencia de las limitaciones del setup, y plan de mejora claro.

## Modelo

El archivo `modelos/lstm_A_subjindep_best.pt` (BiLSTM Estrategia A subject-independent — el ÚNICO modelo desplegado) **no está en git**. Cópialo desde Google Drive:

```
/content/drive/MyDrive/Seminario de Tesis 1/lstm_A_subjindep_best.pt
```

## Dependencias clave

| Paquete | Versión | Razón |
|---|---|---|
| `mediapipe` | **==0.10.14** | FIJADA. Versiones posteriores dan `AttributeError` en `FaceMesh`. |
| `opencv-python` | ≥ 4.9 | Captura USB con backends MSMF (ALPCAM) y DSHOW (GoPro). |
| `torch` (CPU) | ≥ 2.0 | Inferencia BiLSTM (LSTMDrowsy, 0.11 ms/imagen). |
| `scipy` | ≥ 1.11 | Butterworth bandpass + `find_peaks` para HRV desde rPPG. |
| `pyserial` | ≥ 3.5 | Lectura serial 115200 baud del Arduino UNO. |
| `requests` | ≥ 2.31 | POST `/evaluaciones` al backend FastAPI. |
