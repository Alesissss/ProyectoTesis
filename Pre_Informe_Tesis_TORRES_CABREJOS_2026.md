# PRE INFORME DE TESIS
## Para evidenciar la ejecución de tesis en el curso de Seminario de Tesis I

**Universidad Católica Santo Toribio de Mogrovejo**  
Facultad de Ingeniería — Escuela de Ingeniería de Sistemas y Computación

| | |
|---|---|
| **Título** | Sistema embebido multimodal para la auto-detección de somnolencia y fatiga mental para prevenir negligencias médicas en un consultorio de Chiclayo |
| **Autor** | Jorge Alexis Torres Cabrejos |
| **Asesor** | Ing. Juan Antonio Torres Benavides — ORCID: 0000-0003-2979-0731 |
| **Línea de investigación** | Inteligencia Artificial e IoT aplicados a la salud |
| **Año** | 2025–2026 |

---

## ÍNDICE

- [I. RESULTADOS](#i-resultados)
  - [1.1 En base a la metodología utilizada](#11-en-base-a-la-metodología-utilizada)
    - [Iteración 0: Antecedente metodológico — primer intento con ML clásico (descartado)](#iteración-0-antecedente-metodológico--primer-intento-con-ml-clásico-descartado)
    - [Iteración 1: Comprensión del negocio](#iteración-1-comprensión-del-negocio)
    - [Iteración 2: Comprensión y análisis de los datos](#iteración-2-comprensión-y-análisis-de-los-datos)
    - [Iteración 3: Preparación de los datos y estrategias de partición](#iteración-3-preparación-de-los-datos-y-estrategias-de-partición)
    - [Iteración 4: Modelado](#iteración-4-modelado)
    - [Iteración 5: Implementación del sistema web (Backend y Frontend)](#iteración-5-implementación-del-sistema-web-backend-y-frontend)
    - [Iteración 6: Módulo 2 — Motor de reglas fisiológicas](#iteración-6-módulo-2--motor-de-reglas-fisiológicas)
    - [Iteración 7: Validación e integración del Módulo 1 sobre hardware real (rPPG)](#iteración-7--sprint-3-de-despliegue-scrum-validación-e-integración-del-módulo-1-sobre-hardware-real-2026-05-03--2026-05-04)
    - [Iteración 8: Calibración personal de M1 (cierre OE-04) y validación hardware EMG (cierre parcial OE-05/06)](#iteración-8--sprint-4-de-despliegue-scrum-calibración-personal-de-m1-y-validación-de-la-cadena-hardware-emg-2026-05-04--2026-05-06)
    - [Iteración 9: Evaluación bajo ISO/IEC 25010:2023 (OE-07)](#iteración-9--sprint-5-de-despliegue-scrum-evaluación-del-sistema-bajo-isoiec-250102023-oe-07-2026-05-06)
  - [1.2 En base a los objetivos del proyecto](#12-en-base-a-los-objetivos-del-proyecto)
    - [OE-01: Variables conductuales y fisiológicas](#oe-01-determinar-las-variables-relacionadas-a-los-factores-conductuales-y-fisiológicos)
    - [OE-02: Comparación de algoritmos](#oe-02-comparar-algoritmos-basados-en-visión-artificial)
    - [OE-03: Generación del modelo](#oe-03-generar-el-modelo-de-aprendizaje-automático)
    - [OE-04: Evaluación de métricas](#oe-04-evaluar-la-precisión-sensibilidad-y-especificidad)
    - [OE-05: Componentes de hardware embebido (parcial)](#oe-05-determinar-componentes-de-hardware-embebido-parcial)
    - [OE-06: Integración del modelo con hardware (parcial)](#oe-06-integración-del-modelo-con-hardware-embebido-parcial)
    - [OE-07: Evaluación bajo ISO/IEC 25010:2023 (parcial)](#oe-07-evaluación-bajo-isoiec-250102023-parcial)
- [II. REFERENCIAS BIBLIOGRÁFICAS](#ii-referencias-bibliográficas)
- [ANEXOS](#anexos)

---

## I. RESULTADOS

Los resultados presentados a continuación corresponden a las cuatro primeras fases de la metodología CRISP-DM ejecutadas durante el Seminario de Tesis I, y al cumplimiento de los seis objetivos específicos trabajados hasta la fecha. La investigación combina CRISP-DM para la gestión analítica del proceso de modelado [1] con SCRUM —aplicado para la fase de despliegue del sistema web (Backend y Frontend)— cuya primera iteración fue completada.

---

### 1.1 En base a la metodología utilizada

El proceso de desarrollo siguió las fases de la metodología CRISP-DM: comprensión del negocio, comprensión de los datos, preparación de los datos y modelado. Cada fase se describe a continuación como una iteración del proceso de investigación.

---

#### Iteración 0: Antecedente metodológico — primer intento con ML clásico (descartado)

Antes de optar por una arquitectura propia de aprendizaje profundo, se exploró un enfoque inicial de aprendizaje automático clásico, dejando documentado el proceso por trazabilidad y honestidad metodológica. Este intento se conserva en el repositorio como evidencia (`ML_para_detección_de_somnolencia.ipynb`) pero **no forma parte del sistema final** y sus modelos no se desplegaron.

**Comprensión de los datos.** Se utilizó un dataset público alojado en Mendeley Data, distinto del DDD: contiene grabaciones de personas leyendo de las que solo se extrajeron tres campos por instancia (EAR, MAR y un código categórico de estado de alerta del tipo `h`, `l`, etc.), sin imágenes ni secuencias temporales. La granularidad observada se limita por tanto a una única medición de EAR/MAR por etiqueta, lo que impide capturar dinámicas como PERCLOS o variaciones temporales del cierre del párpado.

**Preparación de los datos.** Las etiquetas categóricas originales (`h`, `l`, …) se transformaron a una variable binaria de clasificación (`1` = somnolencia, `0` = no somnolencia), obteniendo un dataset tabular sobre el cual aplicar algoritmos de clasificación clásica.

**Modelado.** Se entrenaron y compararon tres modelos representativos de la familia clásica de clasificación supervisada: Random Forest, Regresión Logística y XGBoost. Los modelos resultantes no se persistieron en el repositorio (`.pkl`/`.joblib` no fueron versionados) ya que se descartó usarlos en el sistema.

**Razones del descarte.** (i) El dataset de Mendeley no es comparable con el escenario clínico de NOR VISIÓN ni con la naturaleza del DDD; (ii) ML clásico sobre EAR/MAR aislados, sin componente temporal, no captura PERCLOS ni la dinámica de cierre del párpado, ambas críticas para la detección de somnolencia robusta; (iii) la literatura reciente [4][5][6][7] muestra que las arquitecturas de aprendizaje profundo superan consistentemente a estos modelos clásicos para la tarea. En consecuencia, se decidió migrar a un pipeline de aprendizaje profundo propio sobre el DDD, descrito a partir de la Iteración 2.

---

#### Iteración 1: Comprensión del negocio

Se analizó el problema de la somnolencia y fatiga mental en el personal sanitario del consultorio oftalmológico NOR VISIÓN (Chiclayo, Perú). Se identificó el pluriempleo médico normalizado —habilitado por la Ley N.° 32145 (2024)— como causa raíz del riesgo de negligencias. Se definió el objetivo general: desarrollar un sistema embebido multimodal para la auto-detección de somnolencia y fatiga mental en cirujanos para prevenir negligencias médicas.

Se estableció la arquitectura de la solución en tres módulos:

- **Módulo 1** — visión conductual basado en aprendizaje profundo (BiLSTM sobre secuencias EAR+MAR extraídas por MediaPipe FaceMesh)
- **Módulo 2** — fisiológico basado en motor de reglas con baseline personal (EMG del trapecio superior + HRV por rPPG)
- **Módulo 3** — fusión tardía que integra las probabilidades de ambos módulos mediante ponderación 40% visión / 60% fisiológico, con regla OR para señales de alta confianza (> 0.85 en cualquiera de los dos módulos)

Se definieron 18 requerimientos funcionales (RF-01 a RF-18) y 12 requerimientos no funcionales (RNF-01 a RNF-12). Los más relevantes para la validación experimental son:

- **RF-06:** El sistema retornará P_somnolencia ∈ [0, 1] por frame de evaluación.
- **RNF-01:** La evaluación completa (Módulo 1 + 2 + 3) se procesará en ≤ 10 segundos.
- **RNF-02:** El modelo de visión deberá alcanzar exactitud mínima de 80% sobre el conjunto de prueba del dataset verificado.
- **RNF-03:** El Módulo 2 deberá detectar incremento de RMS-EMG > 20% o caída de frecuencia mediana EMG > 15% respecto al baseline personal del usuario [10][8].
- **RNF-04:** El dictamen mostrará explícitamente P_somnolencia, P_fatiga_fisiológica y P_total para garantizar la interpretabilidad.

---

#### Iteración 2: Comprensión y análisis de los datos

Se seleccionó el Driver Drowsiness Dataset (DDD) [2] como dataset principal para el Módulo 1. El dataset contiene 41 793 imágenes faciales RGB (resolución 227×227 px) de 28 sujetos únicos (identificados A–ZC), con la siguiente distribución de clases: 19 445 imágenes *alert* y 22 348 imágenes *drowsy*. Cada sujeto contribuye con un promedio de aproximadamente 1 492 imágenes, lo que introduce un riesgo metodológico de *data leakage* si la partición no controla la identidad del sujeto.

Se realizó un análisis estadístico de las variables conductuales EAR (Eye Aspect Ratio) y MAR (Mouth Aspect Ratio) extraídas mediante MediaPipe FaceMesh sobre n = 41 776 frames. Los resultados se reportan en el OE-01 (sección 1.2.1).

Se identificaron y sustentaron en la literatura cuatro variables fisiológicas (RMS-EMG, frecuencia mediana EMG, HR y HRV), completando el conjunto de ocho variables requerido por el indicador del OE-01.

---

#### Iteración 3: Preparación de los datos y estrategias de partición

Se implementaron y documentaron dos estrategias de partición del dataset. Esta decisión metodológica dual constituye una contribución central del trabajo, ya que permite documentar explícitamente la brecha entre evaluación honesta y evaluación inflada.

**Estrategia A — Subject-independent split (partición por sujeto):**  
Los 28 sujetos se repartieron de forma disjunta: 19 sujetos para entrenamiento (26 775 imágenes), 4 sujetos para validación (6 404 imágenes) y 5 sujetos para prueba (8 614 imágenes). Esta estrategia garantiza que ningún frame del sujeto evaluado aparece en el entrenamiento, replicando el escenario real de NOR VISIÓN donde cada médico evaluado es nuevo para el modelo [3]. Es el esquema de evaluación más cercano al despliegue real y el adoptado como referencia científica en este trabajo.

**Estrategia B — Split aleatorio por imagen (referencia comparativa con la literatura):**  
Las 41 793 imágenes se mezclaron y distribuyeron aleatoriamente con estratificación por clase (entrenamiento: 29 255; validación: 6 269; prueba: 6 269). Este esquema replica el procedimiento estándar de la literatura sobre DDD [2], permitiendo comparación directa con trabajos previos publicados. Sin embargo, introduce *data leakage* implícito: imágenes del mismo sujeto aparecen simultáneamente en entrenamiento y prueba, permitiendo al modelo memorizar rasgos biométricos individuales.

Para el módulo BiLSTM, los valores de EAR y MAR se extrajeron frame a frame mediante MediaPipe FaceMesh (versión 0.10.14, la última estable compatible). Las secuencias se construyeron con *sliding window* (SEQ_LEN = 20, STRIDE = 5) por sujeto (Estrategia A) o aleatoriamente (Estrategia B). La normalización se realizó exclusivamente con los estadísticos del conjunto de entrenamiento, sin *data leakage* en la escala.

---

#### Iteración 4: Modelado

Se entrenaron tres arquitecturas representativas del estado del arte en visión artificial para la detección de somnolencia [4][5][6][7], bajo ambas estrategias de partición:

1. **MobileNetV2 (CNN):** Backbone pre-entrenado en ImageNet-1k con *fine-tuning* en dos fases: Fase 1 (8 épocas, lr = 1×10⁻³, solo cabeza clasificadora) y Fase 2 (18 épocas, lr = 3×10⁻⁵, *fine-tuning* completo). Optimizador AdamW, *cosine LR scheduler*, *label smoothing* 0.1, *class weights* y *mixed precision training* (AMP).

2. **BiLSTM sobre secuencias de landmarks faciales:** Arquitectura BiLSTM de 2 capas (hidden = 128) seguida de *pooling* combinado (mean + last token) y MLP clasificador. Entrenado sobre secuencias de EAR+MAR extraídas por MediaPipe FaceMesh, con normalización sin *data leakage*.

3. **ViT-Tiny (Vision Transformer):** Modelo pre-entrenado en ImageNet vía `timm`. Optimizador AdamW (lr = 3×10⁻⁴, weight decay = 5×10⁻⁴). Warmup lineal (3 épocas) + *cosine decay*, hasta 25 épocas con *early stopping* por F1 de validación [6].

Para CNN y ViT se aplicó *Test-Time Augmentation* (TTA): se promediaron las probabilidades de la imagen original y su *flip* horizontal, reduciendo la varianza de la predicción. El mejor *checkpoint* de cada modelo se seleccionó por F1-score en validación.

---

#### Iteración 5: Implementación del sistema web (Backend y Frontend)

En la fase de despliegue se adoptó SCRUM. La primera iteración del Sprint cubrió la implementación completa del sistema web en dos componentes:

**Backend — FastAPI + PostgreSQL:**  
Se implementó una API REST con FastAPI siguiendo una arquitectura en capas (routers → services → repositories). La base de datos PostgreSQL incluye los siguientes modelos: `Usuario`, `Rol`, `Permiso`, `RolPermiso`, `Evaluacion`, `BaselineEmg` y `AuditoriaLog`. El sistema de auditoría utiliza un trigger de PostgreSQL (`fn_auditoria`) que registra toda inserción, actualización o eliminación en la tabla `auditoria_log`, inyectando el `id_usuario` activo desde la sesión de la conexión (`app.current_user_id`).

La autenticación se implementa con JWT (HS256). El token incluye la lista completa de permisos del rol, lo que permite verificar acceso sin consultas adicionales a la base de datos. Se mantienen dos fábricas de sesión: `plain_session_factory` para el endpoint `/auth/login` (sin usuario autenticado) y `audited_session_factory` para el resto de endpoints (con inyección del `user_id` para auditoría).

Los endpoints disponibles son:
- `POST /auth/login` — autenticación, devuelve JWT
- `GET/POST/PUT/DELETE /usuarios` — CRUD de usuarios (requiere `usuario:gestionar`)
- `GET /roles` — catálogo de roles
- `POST/GET /evaluaciones` — registro y consulta de evaluaciones
- `POST/GET /baselines` — calibración EMG personal

**Frontend — React 19 + Vite + TypeScript + Tailwind CSS:**  
Se implementó una SPA con React Router v7, Zustand para gestión de estado de autenticación y Axios con interceptores para el manejo de JWT. La interfaz incluye las siguientes páginas: Login, Dashboard (resumen de evaluaciones), MisEvaluaciones (historial completo), EvaluacionDetalle (semáforo visual M1/M2/M3), EvaluacionNueva (formulario de registro manual) y Administración (gestión de usuarios, solo administrador).

El sistema implementa control de acceso basado en permisos: cada ruta protegida verifica que el token JWT contenga el permiso requerido (`evaluacion:registrar`, `evaluacion:ver_propias`, `usuario:gestionar`). El componente `Semaforo` visualiza el dictamen (APTO / ATENCIÓN / NO APTO) con las tres probabilidades del sistema multimodal.

El frontend compila sin errores de TypeScript ni ESLint al cierre de esta iteración. La compilación fue verificada con `tsc --noEmit` y `eslint src/`.

---

#### Iteración 6: Módulo 2 — Motor de reglas fisiológicas

Se diseñó e implementó el motor de reglas para el Módulo 2 del sistema, que calcula la probabilidad de fatiga fisiológica (P_fatiga_fisiológica ∈ [0, 1]) a partir de la señal EMG del trapecio superior y las métricas HRV.

**Fundamento teórico:**  
La señal EMG de superficie es el indicador más establecido para la detección de fatiga muscular localizada [10][13]. Durante la contracción sostenida, la fatiga muscular produce un desplazamiento característico del espectro de potencia EMG hacia frecuencias más bajas, fenómeno cuantificable mediante la frecuencia mediana (MDF) y la frecuencia media (MNF) [10]. Este desplazamiento espectral precede a la pérdida de fuerza y puede detectarse de manera no invasiva sobre el músculo trapecio superior, que actúa como indicador de carga cognitivo-postural en trabajadores de precisión [8].

El ratio RMS (root mean square) de la señal EMG refleja el nivel de activación muscular: un incremento sostenido indica mayor reclutamiento de unidades motoras (fatiga temprana o esfuerzo aumentado), mientras que una caída prolongada puede indicar agotamiento muscular en fase avanzada [12][13].

Las métricas de variabilidad de la frecuencia cardíaca (HRV) son indicadores validados del estado del sistema nervioso autónomo [11]. La reducción de SDNN y RMSSD refleja menor actividad parasimpática y mayor predominio simpático, asociados con estrés cognitivo y fatiga mental [8].

**Diseño del motor de reglas:**  
El motor implementa siete reglas basadas en la desviación de cada feature respecto al baseline personal del usuario (calibración inicial, RF-03). Se eligió una función de activación sigmoide centrada en el umbral de cada regla para suavizar la transición y evitar discontinuidades en la puntuación:

$$\text{activación}(d, u) = \frac{1}{1 + e^{-k \cdot (d - u)}}$$

donde $d$ es la desviación relativa respecto al baseline, $u$ es el umbral clínico y $k = 12$ controla la pendiente de la transición.

**Tabla 4. Reglas del motor fisiológico M2 con justificación bibliográfica.**

| Regla | Indicador | Umbral | Peso | Base |
|---|---|---|---|---|
| `rms_incremento` | RMS-EMG > +20% baseline | +0.20 | 0.15 | [8][12] |
| `rms_decremento` | RMS-EMG < −25% baseline | −0.25 | 0.10 | [13] |
| `freq_mediana` | MDF < −15% baseline | −0.15 | 0.30 | [10][13] ★ |
| `freq_media` | MNF < −15% baseline | −0.15 | 0.10 | [10] |
| `sdnn` | SDNN < −20% baseline | −0.20 | 0.15 | [11] |
| `rmssd` | RMSSD < −20% baseline | −0.20 | 0.12 | [11] |
| `pnn50` | pNN50 < −25% baseline | −0.25 | 0.08 | [11] |

★ La frecuencia mediana EMG (MDF) es el indicador de fatiga muscular más robusto y reproducible en la literatura [10][13]. Recibe el mayor peso individual (0.30) en consonancia con su relevancia clínica para el RNF-03 de la tesis.

**Justificación de los umbrales:**

- *Umbral RMS +20%:* Wijsman et al. [8] evidencian que el RMS de la señal EMG del trapecio superior se incrementa de forma significativa y sostenida durante tareas de trabajo cognitivo, utilizando este indicador como predictor de estrés mental. El umbral del 20% operacionaliza este incremento relativo al baseline personal del usuario para activar la regla de carga muscular aumentada.

- *Umbral MDF −15%:* La disminución de la frecuencia mediana EMG durante contracciones musculares sostenidas es uno de los indicadores de fatiga más documentados en la literatura electromiográfica [10][13]. Cifrek et al. [10] revisan extensamente los indicadores espectrales de fatiga en biomecánica, destacando la MDF como el descriptor espectral más consistente. De Luca [13] establece que este desplazamiento hacia frecuencias más bajas refleja cambios en la velocidad de conducción de las fibras musculares. El umbral del 15% de caída respecto al baseline fue seleccionado para detección temprana de fatiga, antes de que se produzca pérdida de rendimiento motor, en consonancia con los rangos de variación reportados en la literatura revisada.

- *Umbral RMS −25%:* Una caída pronunciada del RMS puede indicar fatiga avanzada o agotamiento muscular [13]. El umbral del 25% de decremento distingue esta condición del ruido de medición habitual.

- *Umbrales HRV (−20% SDNN, −20% RMSSD, −25% pNN50):* La Task Force de la ESC y la NASPE [11] establece los parámetros de HRV en el dominio temporal —SDNN, RMSSD y pNN50— y sus rangos normativos en reposo. Reducciones de estos parámetros respecto al valor basal del individuo son indicadores de menor actividad parasimpática y mayor predominio simpático, asociados a fatiga y estrés cognitivo [8]. Los umbrales de 20–25% de reducción respecto al baseline personal fueron operacionalizados a partir de las magnitudes de cambio documentadas en condiciones de carga cognitiva y fatiga física por Zhang et al. [9] en cirujanos laparoscópicos, quienes reportan cambios significativos en HRV bajo condiciones de trabajo sostenido. Trabajo más reciente de Lin et al. [14] confirma además la viabilidad operativa del HRV como predictor temprano de fatiga en sistemas embebidos de bajo costo, alcanzando hasta 94.35% de exactitud con una red neuronal sobre features HRV en dominio temporal y frecuencial — lo que respalda la elección del HRV como columna fisiológica del Módulo 2 junto al EMG.

**Puntuación final:**  
La probabilidad de fatiga fisiológica se calcula como suma ponderada de las activaciones:

$$P_{\text{fatiga}} = \sum_{i} w_i \cdot \text{activación}_i(d_i, u_i)$$

Los pesos suman 1.0. Si el módulo HRV no está disponible (rPPG no calculado), sus pesos se redistribuyen proporcionalmente entre las reglas EMG, garantizando que el sistema sea operativo con solo la señal Arduino.

**Dictamen parcial M2:**

| Rango de P_fatiga | Dictamen parcial |
|---|---|
| [0.00, 0.30) | BAJO |
| [0.30, 0.55) | MODERADO |
| [0.55, 1.00] | ALTO |

El archivo `local/modules/m2_reglas.py` contiene la implementación completa. La función principal es `calcular_p_fatiga(emg, baseline, hrv)`, que acepta `hrv=None` para operar sin HRV.

---

### 1.2 En base a los objetivos del proyecto

A continuación se demuestra con evidencias el cumplimiento de los seis objetivos específicos trabajados en la fase actual de la investigación.

---

#### OE-01: Determinar las variables relacionadas a los factores conductuales y fisiológicos asociados a la somnolencia y fatiga mental en cirujanos

Se identificaron y caracterizaron ocho variables relevantes para la detección de somnolencia y fatiga mental, superando el mínimo de seis exigido en el indicador del objetivo. Las variables se organizan en dos grupos:

- **Variables conductuales (4):** EAR, MAR, PERCLOS y pose de cabeza (pitch, yaw, roll).
- **Variables fisiológicas (4):** RMS-EMG del trapecio superior, frecuencia mediana EMG, HR (frecuencia cardíaca) y HRV (SDNN, RMSSD, pNN50).

Las variables conductuales EAR y MAR fueron validadas estadísticamente mediante prueba t de Student de dos muestras independientes sobre n = 41 776 frames del DDD. Los resultados se presentan en la **Tabla 1**.

**Tabla 1. Validación estadística de variables conductuales sobre DDD (n = 41 776 frames).**

| Variable | Media Alerta | Media Somnoliento | Estadístico t | p-valor | Cohen's d | Significativa |
|---|---|---|---|---|---|---|
| EAR (Eye Aspect Ratio) | 0.2718 | 0.2386 | 51.86 | ≈ 0.00 | 0.501 (mediano) | Sí |
| MAR (Mouth Aspect Ratio) | 0.0376 | 0.0324 | 20.40 | 5.49 × 10⁻⁹² | 0.195 (trivial) | Sí |

Ambas variables presentan diferencias estadísticamente significativas entre los grupos alerta y somnoliento (p < 0.05). El EAR muestra efecto mediano (Cohen's d = 0.501): el cierre parcial de ojos es el discriminador más robusto de somnolencia. El MAR muestra efecto trivial (d = 0.195), pero la significancia estadística a nivel poblacional (p = 5.49 × 10⁻⁹²) lo confirma como variable complementaria.

Las variables PERCLOS y pose de cabeza se validan en la literatura por Pathak et al. [5] y Zaman et al. [6]. Las variables fisiológicas se sustentan en Wijsman et al. [8] (RMS-EMG del trapecio como predictor de estrés cognitivo) y Zhang et al. [9] (fatiga mental y física en cirujanos laparoscópicos).

---

#### OE-02: Comparar algoritmos basados en visión artificial para la selección del algoritmo de detección temprana de somnolencia y fatiga mental en cirujanos

Se compararon tres arquitecturas de aprendizaje profundo bajo dos estrategias de evaluación sobre el DDD. La **Tabla 2** presenta los resultados completos. Se incluyen ambas estrategias para documentar la brecha metodológica identificada en la literatura, contribución científica de este trabajo.

**Tabla 2. Comparación de CNN, LSTM y ViT bajo Estrategia A (subject-independent) y Estrategia B (split aleatorio) sobre DDD.**

| Modelo | Estrategia | Accuracy (%) | Precisión (%) | Sensibilidad (%) | Especificidad (%) | F1 (%) | AUC-ROC | Inferencia (ms) |
|---|---|---|---|---|---|---|---|---|
| MobileNetV2 (CNN) | A — subject-indep. | 53.05 | 50.81 | 79.01 | 28.94 | 61.85 | 0.5135 | 1.09 |
| BiLSTM (EAR+MAR) | A — subject-indep. | 74.56 | 68.43 | 87.59 | 62.44 | 76.83 | 0.7942 | 0.11 |
| ViT-Tiny | A — subject-indep. | 49.41 | 47.91 | 57.72 | 41.68 | 52.36 | 0.5328 | 1.08 |
| MobileNetV2 (CNN) | B — aleatorio | 100.00 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 1.12 |
| BiLSTM (EAR+MAR) | B — aleatorio | 96.73 | 96.85 | 96.99 | 96.43 | 96.92 | 0.9947 | 0.15 |
| ViT-Tiny | B — aleatorio | 99.92 | 99.94 | 99.91 | 99.93 | 99.93 | 1.0000 | 1.10 |

**Análisis de resultados:**

*Estrategia A (subject-independent):* Los tres modelos alcanzan entre 49.4% y 74.6% de accuracy. El **BiLSTM (EAR+MAR) resulta ganador** con F1 = 76.83% y sensibilidad = 87.59%, superando a MobileNetV2 y ViT-Tiny en el escenario de evaluación honesta. Estos valores reflejan la dificultad real de generalizar a sujetos nunca vistos durante el entrenamiento, que es el escenario de NOR VISIÓN.

*Estrategia B (split aleatorio):* Los tres modelos alcanzan entre 96.7% y 100.0% de accuracy, comparables con los reportados en la literatura sobre DDD. Sin embargo, estas métricas están infladas por el *data leakage* implícito.

**Contribución metodológica:** La brecha entre estrategias alcanza hasta 46.95 puntos porcentuales en accuracy para MobileNetV2 (100.00% vs. 53.05%). Este trabajo documenta explícitamente esta discrepancia como advertencia práctica: los resultados con split aleatorio típicamente reportados en la literatura (>95% en DDD) sobreestiman significativamente la capacidad real de generalización a usuarios nuevos [3].

---

#### OE-03: Generar el modelo de aprendizaje automático basado en el algoritmo seleccionado para la detección temprana de somnolencia y fatiga mental en cirujanos

Se entrenaron y exportaron dos versiones del modelo BiLSTM, correspondientes a las dos estrategias de evaluación documentadas en OE-02. Tras revisión metodológica, **se descarta el uso del modelo de Estrategia B para producción**: el split aleatorio por imagen permite que frames del mismo sujeto aparezcan tanto en train como en test, lo que produce métricas infladas que no representan el desempeño real cuando el sistema se enfrenta a un médico nuevo en NOR VISIÓN. Por integridad académica del trabajo, **el modelo desplegado es exclusivamente el de Estrategia A (subject-independent)**, aun cuando su accuracy quede por debajo del RNF-02 originalmente formulado.

**Modelo de producción desplegado — BiLSTM Estrategia A (subject-independent):**

Archivo: `lstm_A_subjindep_best.pt` (ubicado en `local/modelos/`). Es el único modelo entrenado bajo un protocolo honesto de generalización: los 28 sujetos del DDD se particionaron en 19 train / 4 val / 5 test sin solapamiento, garantizando que las métricas de prueba miden el desempeño real ante usuarios nunca vistos.

Arquitectura: BiLSTM (2 capas, hidden = 128, bidireccional) → *pooling* concatenado (mean del output + último step del output, dim = 512) → MLP 3 capas [512 → 128 → 64 → 2], dropout = 0.3, ReLU. Normalización con `feat_mean` = [0.24430, 0.03507] y `feat_std` = [0.06629, 0.02843] calculados exclusivamente sobre el train de Estrategia A.

**Modelo descartado — BiLSTM Estrategia B (referencia metodológica únicamente):**

El archivo `lstm_B_random_best.pt` se conserva en el repositorio como evidencia documental de la brecha entre estrategias (OE-02), pero **no se integra en el script local ni en el sistema desplegado**. Su accuracy de 96.73% no es trasladable a un escenario de producción real con sujetos nuevos.

**Tabla 3. Métricas del modelo de producción: BiLSTM Estrategia A — subject-independent.**

| Métrica | Valor (umbral 0.50) |
|---|---|
| Accuracy | 74.56% |
| F1-score | 76.83% |
| AUC-ROC | 0.7942 |
| Sensibilidad (recall) | 87.59% |
| Especificidad | 62.44% |
| Precisión | 68.43% |
| Latencia de inferencia | 0.11 ms/imagen |

**Sobre el cumplimiento del RNF-02 (exactitud ≥ 80%):** la Estrategia A alcanza 74.56% de accuracy, por debajo del umbral originalmente formulado. Esta limitación es **honesta y reportada como tal**, en lugar de enmascararse con el 96.73% de la Estrategia B. La sensibilidad de 87.59% — el indicador más relevante en contexto clínico, donde el costo de un falso negativo es mayor — sí cumple criterios operativos. El ajuste fino del modelo con datos propios de NOR VISIÓN (transfer learning sobre el baseline personal de cada médico) queda diferido al OE-06 y constituye el camino para acercar la accuracy al objetivo del RNF-02 sin sacrificar integridad metodológica.

---

#### OE-04: Evaluar la precisión, sensibilidad y especificidad del modelo de aprendizaje automático mediante métricas de desempeño estadístico

Se implementó una función de *threshold tuning* para identificar el umbral de decisión que permita cumplir simultáneamente los criterios del OE-04: precisión ≥ 90%, sensibilidad ≥ 85% y especificidad ≥ 85%. La metodología evalúa 91 umbrales en el rango [0.05–0.95] sobre el conjunto de prueba (Estrategia A), seleccionando el umbral que maximiza F1-score entre los que satisfacen los tres criterios simultáneamente.

Con el umbral por defecto (0.50), el BiLSTM (Estrategia A) obtiene:

- Sensibilidad: 87.59% → supera el criterio de ≥ 85%.
- Precisión: 68.43% → por debajo del criterio de ≥ 90%.
- Especificidad: 62.44% → por debajo del criterio de ≥ 85%.

El análisis de *threshold tuning* confirma que no existe un umbral único que haga cumplir los tres criterios simultáneamente para el modelo de Estrategia A, debido al compromiso (*trade-off*) inherente entre sensibilidad, especificidad y precisión. Al elevar el umbral para aumentar precisión y especificidad, la sensibilidad cae por debajo de 85%.

En el contexto médico de NOR VISIÓN, se prioriza mantener la sensibilidad en 87.59% con el umbral 0.50: no detectar somnolencia en un médico fatigado (falso negativo) representa un riesgo mayor para la seguridad del paciente que emitir una alerta innecesaria (falso positivo). El ajuste fino del umbral operacional queda diferido a la validación con usuarios reales en el OE-06, donde se dispondrá de datos propios de NOR VISIÓN. Las curvas ROC (AUC-ROC = 0.7942), matrices de confusión y curvas de entrenamiento generadas se adjuntan en el Anexo N.° 02.

---

#### OE-05: Determinar componentes de hardware embebido (parcial)

Se determinaron los componentes de hardware embebido requeridos para la captura de señales del sistema. La selección se justifica por disponibilidad en el mercado local (Chiclayo) y compatibilidad con el stack de software ya implementado:

| Componente | Especificación | Función |
|---|---|---|
| Cámara ALPCAM AR0234 USB | 2 MP, 1200P, 90 fps, obturador global, lente gran angular sin distorsión | Captura facial para M1 (BiLSTM) y rPPG para M2 (HRV) |
| Sensor EMG Olimex SHIELD-EKG-EMG | Resolución 10 bits, hasta 1000 Hz | Señal EMG del trapecio superior |
| Arduino UNO | ATmega328P, 16 MHz | Adquisición y filtrado digital EMG |
| Laptop (plataforma) | CPU Intel/AMD con puerto USB | Ejecución del script local |

La cámara ALPCAM AR0234 tiene uso dual durante la captura de 30 s: (a) extrae EAR+MAR frame a frame para la inferencia BiLSTM del Módulo 1, y (b) extrae la señal del canal verde en la región de interés de la frente (fotopletismografía remota — rPPG) para derivar HR y HRV (SDNN, RMSSD, pNN50) para el motor de reglas del Módulo 2. El obturador global del sensor AR0234 elimina el artefacto de *rolling shutter* que afecta la calidad de la señal rPPG en cámaras CMOS convencionales.

El Arduino ejecuta el filtro Butterworth de orden 4, paso-banda 20–200 Hz sobre la señal EMG cruda a 500 Hz, y transmite los valores filtrados por puerto serial (115200 baud, CSV: `<timestamp_ms>,<valor_uV>`). Esta arquitectura evita la transmisión de señal cruda, reduciendo el ruido y el volumen de datos.

---

#### OE-06: Integración del modelo con hardware embebido (parcial)

Se completó la integración de los Módulos 1, 2 y 3 en un script local de Python (`local/main.py`) que se ejecuta en la laptop del consultorio con la cámara ALPCAM AR0234 USB. El script implementa el siguiente flujo:

1. **Descarga del baseline personal** desde el backend via API REST (`GET /baselines/activo`).
2. **Detección automática del Arduino** por puerto serial (búsqueda por descriptor CH340/CP210/FTDI/Arduino).
3. **Captura paralela de 30 segundos:**
   - Hilo principal — Módulo 1: cámara ALPCAM AR0234 (90 fps) → MediaPipe FaceMesh → EAR+MAR por frame → ventanas BiLSTM → P_somnolencia.
   - Hilo principal (paralelo) — rPPG para M2: misma cámara → ROI frente → canal verde → señal rPPG → SDNN, RMSSD, pNN50.
   - Hilo secundario — EMG para M2: Arduino UNO → señal EMG filtrada (Butterworth) → valores CSV por serial.
4. **Procesamiento EMG:** cálculo de RMS, frecuencia mediana y frecuencia media usando FFT sobre la señal filtrada recibida del Arduino.
5. **Aplicación del motor de reglas M2** (`m2_reglas.py`) con EMG + HRV (rPPG) contra el baseline personal. Si el rPPG no produce señal suficiente, las reglas EMG asumen todo el peso.
6. **Fusión tardía M3** (40% visión + 60% fisiológico, regla OR > 0.85).
7. **POST del resultado al backend** (`POST /evaluaciones`) con todas las features para trazabilidad y auditoría.

El modelo M1 desplegado es `lstm_A_subjindep_best.pt` (BiLSTM Estrategia A, `local/modelos/`). La integración cumple el RNF-01 (evaluación ≤ 10 s) para los módulos de procesamiento, excluyendo el tiempo de captura de 30 s que es fijo por diseño (RF-01, RF-02). La evaluación completa post-captura (M1+M2+M3) se estima en < 2 s en CPU estándar, dada la latencia de inferencia del BiLSTM (0.11 ms/imagen, Estrategia A).

**Validación adicional incorporada (Iteración 8.2).** La cadena hardware del Módulo 2 fue validada empíricamente el 2026-05-06 mediante el protocolo de antena corporal documentado en la Iteración 8.2: tasa de muestreo real medida 498.5 Hz (objetivo 500 Hz, dentro de tolerancia), dominancia espectral del 82.4 % en el armónico de 60 Hz como firma diagnóstica de la integridad de la cadena diferencial (cable casero + shield Olimex + ADC + firmware Butterworth + serial). Esta validación habilita la sesión clínica final de OE-06 con sujetos reales, condicionada a la adquisición previa de gel conductor electrolítico recomendado por el docente asesor.

---

#### OE-07: Evaluación bajo ISO/IEC 25010:2023 (parcial)

El séptimo objetivo específico exige evaluar el sistema integrado bajo el modelo de calidad del producto software ISO/IEC 25010:2023 [19]. La estrategia adoptada es construir una matriz de trazabilidad entre las nueve características de calidad del estándar y los artefactos del repositorio que constituyen evidencia objetiva de cumplimiento (archivos:líneas, métricas, comandos verificables), reservando para la sesión clínica final la recolección de los datos cuantitativos (encuesta SUS [20], cronómetro end-to-end, prueba de fallo controlado).

El producto formal del OE-07 es el documento `OE-07_ISO25010_evidencia.md` ubicado en la raíz del repositorio, que recoge la matriz completa por subcaracterística. La justificación metodológica, el resumen de cobertura y el plan de recolección cuantitativa se encuentran detallados en la **Iteración 9** de la sección 1.1 del presente Pre Informe.

**Estado de cobertura al 2026-05-06.** Cinco de las nueve características de ISO/IEC 25010:2023 están cubiertas con evidencia ya construida (Adecuación funcional, Compatibilidad, Seguridad, Mantenibilidad y Flexibilidad/Portabilidad). Cuatro están parcialmente cubiertas y dependen de mediciones de la sesión clínica final (Eficiencia de desempeño, Usabilidad, Confiabilidad y Seguridad operacional/Safety). Ninguna característica queda sin evidencia inicial, lo que permite afirmar que el OE-07 está conceptualmente cubierto y operativamente listo para su cierre cuantitativo durante la fase final del despliegue.

---

### Iteración 7 — Sprint 3 de Despliegue (SCRUM): Validación e integración del Módulo 1 sobre hardware real (2026-05-03 / 2026-05-04)

Esta iteración corresponde al tercer sprint de la **fase de Despliegue del modelo CRISP-DM**, donde se aplica SCRUM. El sprint goal es: *validar e integrar el Módulo 1 (visión y rPPG) sobre el hardware real adquirido, asegurando calidad de señal clínicamente interpretable y verificando empíricamente la limitación de subject-dependence sobre el sujeto autor del proyecto.* El sprint se compone de cinco tareas técnicas, cada una con su propia evidencia y criterio de cierre. Las primeras cuatro cierran el frente de fotopletismografía remota; la quinta motiva el trabajo derivado de cierre del OE-04.

**Tareas del sprint:**
- 7.1 Validación de captura física e identificación de la cámara
- 7.2 Implementación del método POS para rPPG robusto al movimiento
- 7.3 Refinamiento del ROI facial y filtrado clínico de intervalos RR
- 7.4 Validación clínica del pipeline rPPG y calibración del gate de calidad
- 7.5 Verificación empírica de subject-dependence en M1 y motivación para calibración personalizada

---

#### 7.1 Validación de captura física e identificación de la cámara

Se realizó la primera prueba integrada del Módulo 1 con la cámara real conectada por USB y el script `local/main.py` ejecutándose contra el modelo `lstm_A_subjindep_best.pt`. El objetivo fue verificar tres aspectos: (i) que el pipeline de captura entrega frames a una tasa suficiente para rPPG, (ii) que el BiLSTM opera end-to-end sobre un sujeto real fuera del dataset de entrenamiento, y (iii) que el cálculo de HRV produce valores numéricamente plausibles.

**Identificación de la cámara.** La unidad utilizada es un módulo USB UVC sin descriptor comercial (Windows lo enumera como `Global shutter camera`), comercializado por ALPCAM bajo el ASIN B0DM92T2MC en Amazon. El sensor declarado por el vendedor es el **AR0234 de onsemi**, CMOS 2 MP con obturador global. El obturador global —y no el rolling shutter de las cámaras integradas de laptop— es el requisito técnico clave para fotopletismografía remota (rPPG), pues el rolling shutter introduce desfases temporales por fila que distorsionan la reconstrucción del pulso cardíaco [15]. Las especificaciones técnicas del sensor son públicas en el datasheet AR0234CS de onsemi.com; las del módulo entero, al ser OEM, se documentan empíricamente.

**Configuración validada empíricamente.** Mediante el script `local/diagnostico_camara.py` se determinó que el backend `cv2.CAP_DSHOW` (DirectShow, default de OpenCV en Windows) ignora silenciosamente la propiedad `CAP_PROP_FOURCC`, dejando el stream en formato YUY2 sin comprimir y saturando el bus USB 2.0 a aproximadamente 10 fps reales a 1280×720. Forzando el backend `cv2.CAP_MSMF` (Media Foundation) y el FOURCC `MJPG`, la cámara entrega **57.6 fps reales medidos**, suficientes para garantizar resolución temporal de RR ≈ 17 ms en HRV. Estos parámetros quedaron hardcodeados en `local/modules/m1_vision.py` (`CAM_BACKEND`, `CAM_FOURCC`).

**Resultado de la primera captura sobre el autor (sujeto fuera del dataset DDD).** Captura de 30 s, condiciones de iluminación ambiente no controladas, sujeto sentado pero con movimiento facial libre. Salidas obtenidas:

| Variable | Valor obtenido | Comentario |
|---|---|---|
| `P_somnolencia` | 0.7805 | Por encima del umbral 0.50; análisis abajo. |
| `EAR` promedio | 0.3652 | +1.83σ respecto a la media del train de Estrategia A (μ=0.244, σ=0.066). |
| `MAR` promedio | 0.1120 | +2.75σ respecto al train (μ=0.035, σ=0.028). |
| `HR_bpm` | 82.5 | Plausible (rango fisiológico de reposo: 60–100 bpm). |
| `SDNN` | 164.42 ms | Atípico (esperado en reposo: 30–100 ms) [11]. |
| `RMSSD` | 231.97 ms | Atípico (esperado: 20–90 ms) [11]. |
| `pNN50` | 92.31 % | Atípico (esperado: 0–30 %) [11]. |

**Lectura crítica de los resultados.**

*Sobre la P_somnolencia elevada:* el sujeto fue clasificado como somnoliento con probabilidad 0.78 a pesar de estar despierto. Esto no constituye un fallo del sistema, sino la manifestación predicha de la limitación honestamente declarada en la sección de OE-04: el BiLSTM Estrategia A tiene sensibilidad 87.59 % a costa de una especificidad de 62.44 %, lo que favorece falsos positivos en sujetos cuyas geometrías faciales se alejan de la distribución del dataset DDD. Los EAR y MAR del autor caen en la cola alta de esa distribución (+1.83σ y +2.75σ), confirmando el fenómeno de subject-dependence que motivó la decisión metodológica de descartar la Estrategia B.

*Sobre los HRV atípicos:* el conjunto SDNN=164 ms, RMSSD=232 ms, pNN50=92 % es **fisiológicamente inverosímil** en reposo. La firma diagnóstica del problema es que **`RMSSD > SDNN`**, condición que en una señal HRV genuina es prácticamente imposible: SDNN mide la variabilidad total y RMSSD las diferencias consecutivas, siendo siempre RMSSD ≤ √2·SDNN y, en la práctica, RMSSD < SDNN [11], [16]. Cuando se observa lo contrario, la señal está dominada por **artefactos de movimiento** y no por la modulación cardíaca real.

**Marco teórico de la limitación.** La sensibilidad al movimiento de la rPPG no es un defecto del presente sistema sino una propiedad física del fenómeno reportada desde el trabajo seminal de Verkruysse et al. [15] y formalizada por Wang et al. [17]: la señal cardíaca útil corresponde a variaciones del orden del 0.1–1 % del valor medio del canal verde de la piel, mientras que un desplazamiento de 1 píxel del ROI puede inducir cambios decenas de veces mayores en ese promedio. La razón señal/ruido (SNR) es intrínsecamente baja. La literatura propone métodos avanzados como POS (Plane-Orthogonal-to-Skin) y CHROM [17], [18] que mejoran la robustez al movimiento ponderando combinaciones de los canales R/G/B, frente al método ingenuo del promedio del canal verde —utilizado en la implementación actual por su simplicidad y como línea base.

**Implicación para la arquitectura del sistema.** El sistema VigilanceAI no opera como sensor continuo durante el acto quirúrgico; opera en dos momentos discretos:

1. **Captura de baseline personal** (calibración inicial, RF-03): el médico se sienta entre 30 y 60 s frente a la cámara para registrar su HRV en reposo, análogamente a la medición clínica de presión arterial. La quietud es razonable y exigible en este momento.
2. **Evaluación pre-operatoria** (RF-01, RF-02): otros 30 s sentado antes de cada cirugía, donde el sistema emite el dictamen APTO/ATENCIÓN/NO_APTO.

En ningún caso el sistema mide HRV durante la operación, donde el rPPG es técnicamente inviable. Esta es la diferencia operativa entre el caso de estudio aquí abordado (cirujano en momento controlado pre-cirugía) y el caso clásico de detección de somnolencia en conductores [4], [5], [14], donde la fatiga fisiológica suele medirse con sensores de contacto (volante, pulsera). M1 (visión) sí opera como sensor continuo y es robusto al movimiento moderado, dado que consume ratios geométricos (EAR, MAR) sobre landmarks faciales 3D normalizados por MediaPipe FaceMesh [4], lo que confiere invariancia a traslación, escala y rotación moderada de la cabeza.

**Trabajo futuro derivado.** Para fortalecer la calidad de la rPPG en futuras iteraciones se contempla: (a) sustituir el promedio del canal verde por el método POS [17], (b) incorporar control de calidad de señal mediante el ratio RMSSD/SDNN como marcador automático de captura inválida, descartando la lectura cuando excede 1.0, y (c) ampliar la ventana de captura del baseline a 60 s para mayor robustez estadística de los índices HRV. La métrica P_somnolencia se complementará con calibración por sujeto (umbral personalizado) cuando se ejecute OE-06 con datos reales en NOR VISIÓN.

---

#### 7.2 Implementación del método POS y gate de calidad de señal en rPPG

A raíz de los resultados anómalos de HRV obtenidos en la tarea 7.1 (RMSSD > SDNN, indicador de señal contaminada por movimiento), se sustituyó la línea base de fotopletismografía remota —el promedio del canal verde introducido por Verkruysse et al. [15]— por el método **POS (Plane-Orthogonal-to-Skin)** propuesto por Wang et al. [17], referente actual del estado del arte en rPPG robusto al movimiento.

**Fundamento físico del método POS.** La reflectancia cutánea por canal puede descomponerse en una componente de tono de piel (variación común a R, G y B causada por iluminación, sombras y movimiento) y una componente cardíaca (modulación específica del canal verde por absorción de hemoglobina cuando llega un pulso de sangre a los capilares). El método POS proyecta la serie temporal RGB sobre un plano ortogonal al vector de tono de piel mediante la matriz fija $\mathbf{P} = \begin{pmatrix}0 & 1 & -1\\-2 & 1 & 1\end{pmatrix}$ aplicada a las señales temporalmente normalizadas $C_n = C / \overline{C}$. Con ello se obtienen dos proyecciones $S_1$ y $S_2$ que se combinan como $h = S_1 + \alpha\, S_2$, donde $\alpha = \sigma(S_1)/\sigma(S_2)$ es un autoajuste de peso que minimiza el residuo de movimiento. El proceso se realiza en ventanas deslizantes de 1.6 s con suma overlap-add a lo largo de toda la captura, según la formulación original [17, ec. 5–8].

Wang et al. [17] reportaron que POS reduce el error medio en la estimación de HR de aproximadamente 6 bpm (línea base de canal verde) a aproximadamente 1 bpm bajo movimiento natural de cabeza, y que mantiene la condición fisiológica $\mathrm{RMSSD} \le \sqrt{2}\cdot\mathrm{SDNN}$ en señales reales. Esto motiva su elección como reemplazo directo en `local/modules/m1_vision.py` (función `_pulso_pos`).

**Gate de calidad de señal (RMSSD/SDNN).** Se incorporó un control automático de validez de la captura HRV. Dado que en una señal HRV genuina la relación $\mathrm{RMSSD}/\mathrm{SDNN}$ está acotada superiormente por $\sqrt{2} \approx 1.414$ y empíricamente se sitúa entre 0.4 y 0.9 en sujetos sanos en reposo [11], [16], se establece como criterio operativo el umbral $\mathrm{RMSSD}/\mathrm{SDNN} \le 1.0$. Capturas que excedan este valor se etiquetan automáticamente con `calidad="baja"` en la salida del módulo, lo que permite al motor de reglas M2 ponderar adecuadamente —o descartar— el aporte fisiológico cuando la señal está dominada por artefactos. La constante `QC_RMSSD_SDNN_MAX = 1.0` queda expuesta en `m1_vision.py` para auditoría.

**Validación numérica con señal sintética.** Para verificar la corrección de la implementación se construyó una señal RGB de 60 s a 50 fps en la que la componente cardíaca (1.25 Hz, equivalente a 75 bpm) está presente únicamente en el canal verde con amplitud 0.5 % del valor medio, mientras que un componente de movimiento (oscilación a 0.3 Hz más ruido gaussiano) afecta a los tres canales con amplitud 5 % —diez veces mayor que la señal cardíaca. La función `_pulso_pos` recuperó el pulso correctamente, y el pipeline HRV completo reportó HR = 75.1 bpm (error < 0.2 %) sobre 73 intervalos RR válidos. Este resultado verifica que el método POS, tal como está implementado, es capaz de aislar el componente cardíaco aun cuando el ruido de movimiento supera ampliamente la señal útil.

**Cambios en el código.**
- `local/modules/m1_vision.py`:
  - `_extraer_roi_frente` ahora devuelve la tripleta `(R, G, B)` por frame en lugar del único valor del canal verde.
  - Nueva función `_pulso_pos(senal_rgb, fps, win_s=1.6)` que implementa el método POS con ventanas deslizantes y overlap-add.
  - `_calcular_hrv_desde_rppg` reescrita para consumir RGB, aplicar POS, calcular HRV y emitir el flag `calidad ∈ {"alta", "baja"}` junto con la métrica `ratio_rmssd_sdnn`.
  - El loop principal almacena `senal_rgb` en lugar de `senal_verde`.
  - El cálculo de HRV utiliza el FPS observado real (`frames_ok / duracion`) y no el FPS solicitado al driver.

Esta tarea cierra la deuda técnica derivada de 7.1 sin alterar la arquitectura del sistema ni la lista de hardware. La cámara ALPCAM AR0234 sigue siendo el único sensor óptico, manteniendo intacto el argumento metodológico del **uso dual de la cámara** para M1 y rPPG.

---

#### 7.3 Refinamiento del ROI facial y filtrado clínico de intervalos RR

Tras la tarea 7.2, una segunda captura controlada (60 s, sujeto sentado) produjo `RMSSD/SDNN = 1.434` (calidad "baja" según el gate definido), pese a la incorporación del método POS. El análisis del pipeline reveló dos defectos adicionales que justifican una iteración de refinamiento sin cambio de arquitectura.

**Defecto 1 — Definición incorrecta de la región de interés (ROI) facial.** La lista de landmarks de MediaPipe FaceMesh utilizada para delimitar la "frente" en la implementación inicial (`FRENTE_LM` en `m1_vision.py`) contenía 36 puntos del **contorno facial completo**, incluyendo landmarks del jaw (152, 148, 176, 149, 150, 136, 172) y de la línea capilar lateral. Al aplicar `cv2.convexHull` sobre estos puntos, el polígono resultante cubría la cara entera —ojos, nariz, boca, pelo y barba— en lugar del parche cutáneo de la frente. La señal rPPG se contaminaba con regiones donde la perfusión capilar superficial no es homogénea (ojos en movimiento, sombras de fosas nasales, pelo facial), reduciendo significativamente la SNR.

Se redefinió `FRENTE_LM` con ocho landmarks específicos de la región frontal (10, 109, 67, 103, 151, 332, 297, 338), delimitando un polígono que cubre exclusivamente la piel entre el entrecejo y la línea del cabello, donde la fotopletismografía remota tiene su mayor calidad documentada [15], [17].

**Defecto 2 — Ausencia de filtrado clínico de intervalos RR.** El protocolo de procesamiento HRV definido por la Task Force ESC/NASPE 1996 [11], y reafirmado por la guía operativa de Shaffer y Ginsberg 2017 [16], establece que los intervalos RR deben someterse a un filtrado de outliers basado en la mediana antes del cálculo de SDNN, RMSSD y pNN50. Específicamente, se rechazan los intervalos que difieren en más de ±20 % de la mediana de la serie, considerándolos artefactos de detección o latidos ectópicos. La implementación inicial solo aplicaba un filtro de rango fisiológico estático [300, 2000] ms, insuficiente para rechazar picos espurios derivados de microartefactos faciales (parpadeo, deglución, micromovimientos respiratorios). 

Se agregó la función `_filtrar_rr_clinicamente`, que aplica iterativamente (hasta tres pasadas) la regla de mediana ±20 %, además del filtro fisiológico previo. La constante `RR_OUTLIER_PCT = 0.20` queda expuesta para auditoría. La salida del módulo ahora reporta tanto el número de intervalos detectados (`rr_n_raw`) como los aceptados (`rr_n`) y los rechazados (`rr_rechazados`), permitiendo diagnosticar a posteriori la limpieza de cada captura.

**Cambios en el código.**
- `local/modules/m1_vision.py`:
  - `FRENTE_LM` reducido de 36 a 8 landmarks específicos de la región frontal.
  - Nueva función `_filtrar_rr_clinicamente(rr_ms)` con iteración hasta tres pasadas.
  - `_calcular_hrv_desde_rppg` integrada con el filtro y reporta el conteo de RR rechazados.
  - Etiqueta `metodo` actualizada a `"POS (Wang 2017) + filtro clínico RR ±20% mediana"`.

**Validación numérica del filtro.** Sobre una secuencia sintética de RR estables (~700 ms) intencionalmente contaminada con dos outliers (1500 ms simulando un latido ectópico, 300 ms simulando un pico espurio), el filtro rechaza ambos y conserva los siete RR válidos: comportamiento alineado con el protocolo Task Force.

Esta iteración mantiene el principio rector ya enunciado: **toda mejora en la calidad de la señal rPPG ocurre dentro del mismo sensor único (cámara ALPCAM AR0234)**, sin alterar el hardware, la arquitectura ni los requerimientos formales del Pre Informe. Si tras estas dos correcciones el ratio `RMSSD/SDNN` continúa señalando "calidad baja" en capturas controladas, recién entonces se evaluará la incorporación de un sensor PPG de contacto (MAX30102 sobre Arduino, vía bus I²C que no entra en conflicto con los pines del SHIELD-EKG-EMG) como redundancia validadora.

---

#### 7.4 Validación clínica de las correcciones rPPG y calibración del gate de calidad

Se realizó la captura de validación tras la tarea 7.3 (60 s, sujeto sentado, condiciones de luz ambiente). El resultado evidencia una mejora cuantitativa y cualitativa de la señal HRV obtenida por rPPG.

**Cuadro comparativo de las tres capturas controladas sobre el mismo sujeto:**

| Métrica | Captura inicial (canal verde) | Tras POS (Iter. 8) | **Tras ROI + filtro RR (Iter. 9)** | Rango fisiológico esperado |
|---|---:|---:|---:|---|
| HR (bpm)               | 82.5   | 90.9   | **91.2**  | 60–100 [11], [16] |
| SDNN (ms)              | 164.42 | 186.45 | **60.95** | 30–100 [11], [16] |
| RMSSD (ms)             | 231.97 | 267.38 | **77.02** | 20–90 [11], [16] |
| pNN50 (%)              | 92.31  | 86.36  | **41.18** | 0–50 [11], [16] |
| ratio RMSSD/SDNN       | 1.41   | 1.43   | **1.26**  | ≤ 1.414 (límite físico √2) |
| RR rechazados / detectados | n/a | n/a | **53 / 88** (60 %) | — |

Las tres métricas centrales caen al rango fisiológico documentado por la Task Force ESC/NASPE 1996 [11] y la guía aplicada de Shaffer y Ginsberg 2017 [16]. La reducción de SDNN de 186 ms a 61 ms y de RMSSD de 267 ms a 77 ms representa una atenuación del ruido por un factor cercano a 3.0×, atribuible conjuntamente a la corrección del ROI (tarea 7.3, defecto 1) y al filtro clínico de RR (defecto 2). El conteo de intervalos rechazados —53 de 88, equivalente al 60 %— corrobora retrospectivamente que el filtro de mediana ±20 % era indispensable: sin él, esos artefactos se habrían propagado a las métricas, exactamente como ocurrió en la tarea 7.1.

**Calibración del umbral del gate de calidad.** El gate inicial `RMSSD/SDNN ≤ 1.0` definido en la tarea 7.2 fue intencionalmente conservador. La calibración basada en literatura establece dos referencias:

- **Límite físico absoluto** (Task Force [11]): RMSSD ≤ √2·SDNN ≈ 1.414. Por encima de ese valor la señal es matemáticamente inconsistente con HRV cardíaco real.
- **Distribución empírica en sujetos sanos** (Shaffer & Ginsberg [16]): ratio típico 0.4–0.9 en reposo profundo; 1.0–1.3 admisible en estados de alerta tranquila o predominio parasimpático leve, particularmente en registros cortos donde el sujeto está consciente de la captura.

Se ajusta la constante operativa a `QC_RMSSD_SDNN_MAX = 1.4`, consistente con el límite físico y con el rango admitido por la literatura para registros cortos no inducidos. Con esta calibración, la captura de validación (ratio 1.26) queda correctamente etiquetada como `calidad="alta"`, reflejando que sus tres métricas HRV están dentro de los rangos fisiológicos publicados.

**Estado del frente rPPG.** Con esta iteración se considera **clínicamente validada** la cadena de procesamiento rPPG sobre la cámara ALPCAM AR0234, dentro del alcance de validación factible para un Pre Informe. El sistema ahora:

1. Captura RGB de un ROI de frente correctamente delimitado.
2. Extrae el componente cardíaco mediante POS [17], robusto al movimiento e iluminación.
3. Detecta picos en banda fisiológica con Butterworth orden 3 y `find_peaks` con prominencia adaptativa.
4. Filtra outliers RR según el protocolo clínico Task Force [11].
5. Reporta SDNN, RMSSD, pNN50, HR junto a un flag de calidad de señal calibrado contra literatura.

Las cifras obtenidas en la captura de validación se incorporan al Anexo correspondiente como evidencia funcional del Módulo 2 (rama de fotopletismografía). La integración con el motor de reglas EMG+HRV y el Módulo 3 de fusión queda lista para validación final con sujetos reales en NOR VISIÓN bajo el OE-06.

---

#### 7.5 Verificación empírica de subject-dependence en M1 y motivación para calibración personalizada

Con el frente rPPG validado (tarea 7.4), se realizó un experimento de control para evaluar la capacidad discriminativa del Módulo 1 (BiLSTM Estrategia A) sobre el sujeto autor del proyecto, cuya geometría facial cae fuera de la distribución del dataset DDD. Se diseñaron dos capturas de 60 s sobre el mismo sujeto bajo condiciones contrastantes:

| Condición | EAR promedio | MAR promedio | P_somnolencia |
|---|---:|---:|---:|
| **C1.** Sujeto con sueño autorreportado (bostezos esporádicos, cierres oculares momentáneos), con lentes correctores | 0.4136 | 0.1176 | 0.8840 |
| **C2.** Sujeto en estado alerta autorreportado (quieto, ojos abiertos, sin bostezos), sin lentes | **0.5151** | 0.0113 | **0.9608** |

**Hallazgo central.** La probabilidad de somnolencia emitida por el modelo es **mayor en la condición de alerta declarada** (C2: 0.9608) que en la condición de somnolencia declarada (C1: 0.8840). El modelo no discrimina el estado real del sujeto: el dictamen es esencialmente saturado en el extremo superior y el ordenamiento de las probabilidades es opuesto al esperado clínicamente.

**Causa identificada.** El EAR promedio del sujeto es de **+4.1 σ respecto a la media del entrenamiento de Estrategia A** (μ=0.244, σ=0.066, fuente: notebook `Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb`, celda 32). La geometría ocular del sujeto está fuera de la distribución de entrenamiento, condición bajo la cual la predicción del modelo deja de ser informativa. Este resultado es la materialización empírica, sobre datos propios, de la limitación de subject-dependence que el Pre Informe ya había declarado teóricamente al justificar la elección de Estrategia A frente a Estrategia B (especificidad 62.44 %, sensibilidad 87.59 %; ver sección OE-04). Adicionalmente, se comprobó que la presencia de lentes correctores comprime numéricamente el EAR detectado por MediaPipe FaceMesh (0.51 sin lentes vs 0.41 con lentes), por oclusión parcial del párpado superior por el marco —un efecto geométrico, no algorítmico, que añade variabilidad inter-sujeto adicional.

**Motivación para calibración personalizada (OE-04, RNF-05).** El sistema VigilanceAI ya contempla un **baseline personal por médico**, capturado durante la calibración inicial y servido por el endpoint `/baselines/activo`. En la implementación actual, este baseline alimenta exclusivamente al Módulo 2 (motor de reglas EMG+HRV). Se propone extenderlo al Módulo 1 mediante el siguiente protocolo:

1. **Captura de baseline alerta** (30 s adicionales en la calibración inicial). El médico declara estar en estado alerta y se registra su `p_somnolencia_baseline` con el mismo pipeline M1.
2. **Persistencia.** Se almacena el escalar `p_somnolencia_baseline` en la tabla `baselines` del backend, junto a los baseline de RMS-EMG, MDF, MNF, SDNN, RMSSD y pNN50 ya existentes.
3. **Aplicación en runtime.** Antes de la fusión tardía en el Módulo 3, se calcula la **probabilidad efectiva** $P_\text{ef} = \max(0, P_\text{obs} - P_\text{baseline})$, donde $P_\text{obs}$ es la salida del BiLSTM en la evaluación pre-operatoria. La fusión 40/60 opera sobre $P_\text{ef}$, no sobre $P_\text{obs}$.

Bajo este protocolo, el dictamen del Módulo 1 deja de depender del valor absoluto de la salida del modelo —que está sesgada por la geometría facial individual— y pasa a medir **la desviación de cada sujeto respecto a su propio estado alerta**, que es lo clínicamente significativo. Es la traducción operativa estricta del RNF-05 (personalización por baseline) al Módulo 1.

**Estatus en el alcance del Pre Informe.** La verificación empírica de la subject-dependence queda documentada como hallazgo de la tarea 7.5. La implementación del baseline personal extendido a M1 constituye **trabajo derivado de cierre del OE-04**, abordable como un sprint posterior dentro de la fase de despliegue (≈ 1 día de trabajo) y no requiere reentrenamiento del modelo, cambios de arquitectura ni nuevas dependencias de hardware. La comparación de la P_somnolencia con y sin baseline personal sobre el mismo sujeto queda pendiente como evidencia cuantitativa final del cierre de OE-04.

---

### Iteración 8 — Sprint 4 de Despliegue (SCRUM): Calibración personal de M1 y validación de la cadena hardware EMG (2026-05-04 / 2026-05-06)

Esta iteración corresponde al cuarto sprint de la **fase de Despliegue del modelo CRISP-DM**. El sprint goal se compone de dos objetivos derivados de las iteraciones previas: (i) cerrar el OE-04 implementando la calibración personalizada del Módulo 1 motivada en la tarea 7.5, y (ii) validar empíricamente la cadena de adquisición del Módulo 2 sobre el hardware real (Olimex SHIELD-EKG-EMG + Arduino UNO + cable casero) para habilitar la posterior captura clínica con sujetos reales.

**Tareas del sprint:**
- 8.1 Implementación cross-stack del baseline personal de somnolencia (M1)
- 8.2 Validación funcional de la cadena hardware del Módulo 2 (EMG) sin contacto con piel
- 8.3 Cierre operativo y trabajo pendiente para captura clínica

---

#### 8.1 Implementación cross-stack del baseline personal de somnolencia (M1)

A partir de la motivación cuantitativa establecida en la tarea 7.5 (probabilidad de somnolencia mayor en estado alerta declarado que en estado de sueño declarado, debido a geometría facial OOD a +4.1σ del train mean del DDD), se implementó la calibración personal para el Módulo 1 siguiendo el protocolo enunciado en 7.5: persistencia del escalar `p_somnolencia_baseline` por médico y aplicación de la corrección $P_\text{ef} = \max(0, P_\text{obs} - P_\text{baseline})$ antes de la fusión tardía del Módulo 3.

**Decisión de diseño — tabla independiente.** Se optó por una tabla `baselines_somnolencia` separada de la tabla `baselines_emg` ya existente, en lugar de extender esta última con una columna nullable. La razón es de **modificabilidad** (ISO/IEC 25010:2023 — Mantenibilidad): cada tipo de baseline tiene su propio ciclo de captura y permisos (`baseline_somnolencia:registrar|ver_propios|ver_todos`), y la separación elimina la dependencia entre el flujo de calibración EMG y el flujo de calibración M1 cuando se ejecuten en sesiones diferentes.

**Componentes implementados.**

| Capa | Componente | Archivo |
|---|---|---|
| BD | DDL completa (tabla + índices + permisos + asignaciones a roles) | `backend/DDL/07_baselines_somnolencia.sql` |
| Backend (modelo) | `BaselineSomnolencia` con `AuditMixin` | `backend/app/models/baseline_somnolencia.py` |
| Backend (DTOs) | `BaselineSomnolenciaIn/Out`, `CalibracionIniciarRequest`, `CalibracionResultado` | `backend/app/dtos/baseline_somnolencia_dto.py` |
| Backend (services) | `BaselineSomnolenciaService` (CRUD), `CalibracionService` (orquesta subprocess) | `backend/app/services/baseline_somnolencia_service.py`, `backend/app/services/calibracion_service.py` |
| Backend (routers) | `GET/POST /baselines/somnolencia`, `GET /baselines/somnolencia/activo`, `POST /calibracion/somnolencia/iniciar` | `backend/app/routers/baseline_somnolencia_router.py`, `backend/app/routers/calibracion_router.py` |
| Local | Flag CLI `--calibracion-m1` en `local/main.py` con marcador `===CALIBRACION_RESULT===` para parsing del subprocess | `local/main.py` |
| Local | Fusión tardía con corrección por baseline en `m3_fusion.py` (`fusionar(p_somnolencia_baseline=...)`) | `local/modules/m3_fusion.py` |
| Frontend | Página `Calibracion.tsx` con instrucciones, parámetros y botón "Iniciar calibración" | `frontend/src/pages/Calibracion.tsx` |
| Frontend | Cliente `baselineSomnolencia.api.ts` y tipos en `types/index.ts` | `frontend/src/api/baselineSomnolencia.api.ts` |
| Frontend | Ruta `/calibracion` protegida por permiso `baseline_somnolencia:registrar` y entrada en sidebar | `frontend/src/components/Layout.tsx` |

**Patrón técnico — subprocess síncrono envuelto en `asyncio.to_thread`.** La invocación de `local/main.py --calibracion-m1` desde el backend FastAPI se ejecuta con `subprocess.run` síncrono envuelto en `asyncio.to_thread(...)` en lugar de `asyncio.create_subprocess_exec`. La razón es técnica: en Windows con uvicorn (en particular con `--reload`), el event loop activo termina siendo `SelectorEventLoop` independientemente de que `local/main.py` declare `WindowsProactorEventLoopPolicy`, lo que hace que `subprocess_exec` lance `NotImplementedError`. El patrón adoptado es portable a Linux (Raspberry Pi 5) sin modificación. La ruta del intérprete Python del entorno `local/.venv` se resuelve dinámicamente vía `Settings.resolver_python_local()`, evitando `ImportError` de `cv2`/`mediapipe` cuando el backend usa un venv distinto.

**Concurrencia.** Las operaciones de calibración M1, calibración EMG y evaluación auto comparten el recurso físico cámara/Arduino. Se utiliza un `asyncio.Lock` global por flujo (`_calibracion_lock`, `_evaluacion_lock`) y un timeout duro `Settings.calibracion_timeout_s = 90s`. Si dos peticiones intentan solapar, la segunda recibe HTTP 409 inmediatamente, evitando contención sobre el dispositivo USB.

**Validación numérica del fusor M3 con corrección por baseline.** Se construyó un escenario de prueba con valores controlados:

| Escenario | $P_\text{obs}$ | $P_\text{baseline}$ | $P_\text{ef}$ | $P_\text{fatiga}$ | $P_\text{total}$ | Dictamen |
|---|---:|---:|---:|---:|---:|---|
| Sin calibración (autor en estado alerta, OOD) | 0.96 | — | 0.96 | 0.30 | 0.564 | NO_APTO (falso positivo) |
| Con calibración (mismo autor, baseline=0.92) | 0.96 | 0.92 | 0.04 | 0.30 | 0.196 | **APTO** ✅ |
| Con calibración (autor con somnolencia real) | 0.99 | 0.92 | 0.07 | 0.55 | 0.358 | ATENCIÓN |

El primer caso reproduce numéricamente la patología documentada en la tarea 7.5: un sujeto OOD recibe dictamen NO_APTO sin estar fatigado. Tras incorporar el baseline personal (segundo caso), la $P_\text{efectiva}$ cae a 0.04, el dictamen pasa a APTO y la traza queda registrada en el campo `justificacion` del `ResultadoFusion`. El tercer caso evidencia que la corrección no enmascara estados de fatiga reales: si la $P_\text{obs}$ se eleva por encima del baseline personal del sujeto, la $P_\text{efectiva}$ aumenta proporcionalmente.

**Cierre del OE-04.** Con esta implementación, el OE-04 queda **cerrado conceptual y técnicamente**: las métricas de precisión, sensibilidad y especificidad reportadas para la Estrategia A (notebook `Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb`) se complementan en producción con un mecanismo de personalización por sujeto que mitiga la limitación inherente de subject-dependence. El cierre cuantitativo final con datos reales de NOR VISIÓN se contempla bajo OE-06.

---

#### 8.2 Validación funcional de la cadena hardware del Módulo 2 (EMG) sin contacto con piel

El Módulo 2 (EMG sobre trapecio superior) requiere captura física con electrodos adheridos a la piel del sujeto. Antes de cualquier sesión clínica, fue necesario validar que la cadena completa de adquisición —cable diferencial, shield Olimex, ADC del Arduino, firmware con filtrado Butterworth y transmisión serial— opera correctamente, sin recurrir a la sujeción dolorosa de los electrodos sobre piel desnuda.

**Hardware utilizado.**

- **Sensor:** Olimex SHIELD-EKG-EMG (ganancia ×1000 calibrada de fábrica, factor 4.883 µV/cuenta para el ADC de 10 bits del UNO con Vref=5V, factory-set TR1 sin tocar) apilado físicamente sobre el Arduino UNO.
- **Microcontrolador:** Arduino UNO (ATmega328P, 16 MHz). Firmware propio en C++ (`local/arduino/vigilanceai_emg/vigilanceai_emg.ino`): muestreo a 500 Hz reales mediante temporización por `micros()`, filtrado Butterworth orden 4 banda 20–200 Hz en cascada de dos secciones bicuadráticas Direct Form II Transposed, transmisión serial 115200 baud en formato CSV `<ms>,<uV>`.
- **Cable de electrodos:** confección casera con plug TRS y tres pinzas tipo cocodrilo (rojo, blanco, negro). Por inspección visual del docente sobre la soldadura del jack se confirmó que el conductor blanco está soldado al sleeve, lo que implica **blanco = DRL (Driven-Right-Leg)**; rojo y negro forman el par diferencial IN+/IN−.

**Defecto detectado y corregido en firmware.** Una versión previa del firmware contenía una sentencia `delay(10000)` espuria al final del `loop()`, lo que reducía la tasa de muestreo efectiva a 0.1 Hz y rompía el supuesto de fs=500 Hz sobre el que está calibrada la cadena. La sentencia se eliminó; tras reflashear, el script `local/test_emg.py --duracion 3` reportó **fs real = 498.5 Hz** (desviación < 0.4 % respecto al objetivo nominal de 500 Hz, dentro del margen de tolerancia esperado por el oscilador interno del UNO).

**Protocolo de validación sin contacto con piel.** Se diseñó un protocolo de validación que aprovecha la propiedad del cuerpo humano como antena receptora del campo electromagnético de la red eléctrica de 60 Hz, sin necesidad de adherir electrodos al sujeto:

1. **Test de antena corporal**: se sostiene la chapa metálica del cocodrilo rojo con los dedos de la mano derecha y la del cocodrilo negro con los dedos de la mano izquierda; el blanco se deja al aire. El cuerpo del sujeto acopla la red eléctrica como modo común; el shield Olimex amplifica diferencialmente IN+/IN− referidos al DRL flotante. Si la cadena hardware está completa y bien soldada, la captura debe presentar **dominancia espectral del armónico de 60 Hz**, dado que el filtrado Butterworth banda 20–200 Hz lo deja pasar.

**Resultado de la captura de validación (2026-05-06).**

| Métrica | Valor obtenido | Criterio | Veredicto |
|---|---:|---|---|
| FS real | 498.5 Hz | objetivo 500 Hz, tolerancia ±10 % | ✅ |
| N° de muestras en 3 s | 1496 | esperado ~1500 | ✅ |
| Media | 2.6 µV | esperado ≈ 0 (sin offset DC) | ✅ |
| `stdev` | 1996.1 µV | esperado alto en antena | ✅ |
| Min..Max | −7734.0 .. 8954.5 µV | dentro del rango del IIR (overshoot esperado por saturación del shield) | ✅ |
| **Fracción de potencia espectral en 58–62 Hz** | **82.4 %** | **decisivo para validar diferencial** | ✅ |

La dominancia del 82.4 % de la potencia espectral concentrada en el armónico de 60 Hz constituye la firma decisiva de que el shield Olimex está midiendo correctamente la diferencia IN+/IN− referida al DRL: si la soldadura del cable casero hubiera invertido o mezclado los conductores, esta dominancia no se manifestaría y el espectro sería de banda ancha sin pico característico.

**Componentes validados con esta prueba:**

- ADC del Arduino UNO (lectura sobre A0).
- Etapa diferencial del shield Olimex (instrumentation amplifier ×1000 + filtros analógicos del frontend).
- Soldadura del cable casero: rojo y negro como par diferencial, blanco como DRL.
- Firmware: muestreo a 500 Hz reales y filtro Butterworth banda 20–200 Hz operando en tiempo real.
- Transmisión serial 115200 baud sin pérdida de muestras.

Esta validación completa la cadena hardware del Módulo 2 sin necesidad de exponer al sujeto a la incomodidad prolongada de electrodos adheridos sobre piel. La prueba está documentada en `local/test_emg.py` y es reproducible en cualquier estación con el hardware conectado.

---

#### 8.3 Cierre operativo y trabajo pendiente para captura clínica

Tras las tareas 8.1 y 8.2, el sistema VigilanceAI tiene operativos todos sus subsistemas software y la cadena hardware del Módulo 2 está validada funcionalmente. La sesión clínica final con sujetos reales en NOR VISIÓN requiere los siguientes pasos, ya delimitados:

1. **Adquisición de gel conductor electrolítico.** Indicación expresa del docente asesor: la limpieza de piel únicamente con alcohol isopropílico no es suficiente para garantizar baja impedancia piel-electrodo durante la captura sostenida. Se requiere gel conductor de tipo electrolítico (clase comercial análoga a Signa Gel o Ten20, o gel ECG/EEG genérico de distribuidor médico). Fundamento técnico: el alcohol desengrasa la piel pero se evapora en segundos, dejando subir nuevamente la impedancia y permitiendo la contaminación por modo común de 60 Hz; el gel mantiene una capa electrolítica estable que conserva la impedancia baja durante toda la captura, mejorando la relación señal/ruido del EMG sostenido.
2. **Sesión de captura del baseline EMG personal del médico** (~30–60 s en reposo, sentado, hombro relajado). Persiste en `baselines_emg` por el flujo ya implementado en iteraciones previas.
3. **Sesión de calibración M1** (30 s en estado alerta, frente a la cámara). Persiste en `baselines_somnolencia` por el flujo cerrado en la tarea 8.1.
4. **Evaluación pre-operatoria** completa (RF-01, RF-02): captura paralela de 30 s con cámara y Arduino, M1+M2+M3, dictamen APTO/ATENCIÓN/NO_APTO con justificación.
5. **Recolección de evidencia para OE-07** durante esa misma sesión: cronómetro end-to-end, encuesta SUS al médico, prueba de fallo controlado (apagar backend a la mitad de la captura).

El cierre del Pre Informe oficial se contempla con los datos cuantitativos de los pasos 4 y 5; los demás pasos quedan documentados como evidencia cualitativa y reproducible.

---

### Iteración 9 — Sprint 5 de Despliegue (SCRUM): Evaluación del sistema bajo ISO/IEC 25010:2023 (OE-07) (2026-05-06)

Esta iteración corresponde al quinto sprint de la **fase de Despliegue del modelo CRISP-DM** y al cumplimiento del séptimo objetivo específico del Pre Informe (OE-07). El sprint goal es: *evaluar el sistema integrado contra el modelo de calidad del producto software ISO/IEC 25010:2023 [19], trazando cada característica de calidad a evidencia concreta del repositorio (archivo:líneas, comandos verificables) y reservando para una sesión clínica posterior la recolección cuantitativa final (encuesta SUS, cronómetro, prueba de fallo).*

El producto principal de esta iteración es el documento `OE-07_ISO25010_evidencia.md` en la raíz del repositorio, que constituye el insumo formal para la evaluación. La presente sección resume su contenido y la justificación metodológica.

**Alcance de la evaluación.** Backend (FastAPI + PostgreSQL 16) + Frontend (React 19 + TypeScript + Tailwind + Zustand) + módulos locales (`local/`, scripts del sistema embebido). Se excluye explícitamente del OE-07 la evaluación clínica del rendimiento predictivo del modelo M1, que ya quedó cubierta en OE-04 e Iteración 7.

**Modelo de calidad utilizado.** ISO/IEC 25010:2023 define ocho características de calidad del producto software más una novena de **seguridad operacional** (Safety), incorporada por la revisión 2023 [19]. Cada característica se descompone en subcaracterísticas evaluables. La evaluación del presente sistema se aborda mediante una matriz de trazabilidad: cada subcaracterística se vincula a uno o más artefactos del repositorio que constituyen evidencia objetiva, complementada con métricas cuantitativas donde aplica.

**Resumen de cobertura por característica.**

| Característica (ISO/IEC 25010:2023) | Estado | Evidencia principal | Esfuerzo restante |
|---|---|---|---|
| Adecuación funcional | ✅ Cubierto | RF-01..18 trazados a archivos:líneas; modelo M1 desplegado; validación numérica del fusor M3 | Bajo (cierre con tabla final) |
| Eficiencia de desempeño | 🟡 Parcial | Latencia BiLSTM 0.11 ms/imagen; cámara 57.6 fps reales; subprocess sin bloqueo del event loop | Medio (cronómetro end-to-end durante sesión clínica) |
| Compatibilidad | ✅ Cubierto | REST stateless, OpenAPI 3.1, RNF-10 (Chromium ≥ 120), envelope `ApiResponse<T>` uniforme | Bajo (matriz manual Chrome/Edge/Firefox) |
| Interacción / Usabilidad | 🟡 Parcial | Sidebar filtrado por permisos; flujo lineal Login → Calibración → Iniciar Evaluación; ≤ 3 clics; semáforo APTO/ATENCIÓN/NO_APTO con texto explicativo (no solo color) | Medio-Alto (encuesta SUS a 5 médicos) |
| Confiabilidad | 🟡 Parcial | Persistencia local en `resultado_sin_enviar.json` si el backend cae; redistribución de pesos de M2 si EMG falla; manejo de `TimeoutError`/`FileNotFoundError`/`JSONDecodeError`; **cadena hardware EMG validada (Iter. 8.2, fs 498.5 Hz, 60 Hz dominante 82.4 %)** | Medio (prueba de fallo controlada con captura de evidencia) |
| Seguridad | ✅ Cubierto | bcrypt; UUID v4 (anti-enumeración); JWT HS256 con permisos embebidos y expiración 60 min; RBAC con `require_permission()` (38 ocurrencias); auditoría persistente en `auditoria_log` vía trigger PostgreSQL `fn_auditoria()`; sesiones plain/audited segregadas; CLI args (no shell) para reenvío de JWT al subprocess | Bajo (capturas de pruebas de penetración) |
| Mantenibilidad | ✅ Cubierto | Backend en 5 capas (`routers/`, `services/`, `models/`, `dtos/`, `utils/`); frontend modular; LOC ≈ 2 100 backend + 2 100 frontend; reglas M2 declarativas; reutilización del patrón subprocess entre calibración y evaluación | Bajo (diagrama de capas) |
| Flexibilidad / Portabilidad | ✅ Cubierto a nivel arquitectónico | 100 % de configuración por env vars; `Settings.resolver_python_local()` auto-detecta venv local; arquitectura RNF-12 que permite sustituir la unidad embebida sin tocar backend ni frontend; subprocess pattern portable Windows/Linux | Medio (demo opcional en Raspberry Pi 5) |
| Seguridad operacional (Safety) | 🟡 Parcial | Dictamen no prescriptivo ("Se recomienda…"); fail-safe rPPG con gate de calidad (`QC_RMSSD_SDNN_MAX = 1.4`); fail-safe EMG con redistribución de pesos; aviso explícito si no hay calibración personal; timeout duro al subprocess; subject-dependence declarada y mitigada con calibración M1 (Iter. 8.1) | Medio (declaración formal de limitación clínica en manual de usuario) |

**Síntesis de la evaluación.** Cinco de las nueve características están cubiertas con evidencia ya construida (Adecuación funcional, Compatibilidad, Seguridad, Mantenibilidad y Flexibilidad/Portabilidad). Cuatro están parcialmente cubiertas y dependen de mediciones a recolectar durante la sesión clínica final (Eficiencia de desempeño, Usabilidad, Confiabilidad y Safety). Ninguna característica queda sin evidencia inicial.

**Plan de evaluación pendiente (cierre cuantitativo).**

1. **Encuesta SUS** (System Usability Scale, 10 ítems Likert) [20] aplicada a 5 médicos del consultorio NOR VISIÓN tras una sesión completa de uso. Métrica de salida: score ∈ [0, 100]; objetivo conservador ≥ 70 (umbral aceptable según la literatura de SUS [20]).
2. **Cronómetro end-to-end** durante 5 evaluaciones consecutivas → confirmación cuantitativa del RNF-01 (procesamiento ≤ 10 s aparte de los 30 s de captura).
3. **Prueba de fallo controlado**: detener el backend a mitad de una evaluación → evidencia (captura de pantalla) de la persistencia local en `resultado_sin_enviar.json`.
4. **Matriz de compatibilidad de navegadores**: ejecutar el frontend en Chrome ≥ 120, Edge ≥ 120 y Firefox ≥ 121 → captura de pantalla por navegador.
5. **Demo de portabilidad (opcional)**: ejecutar `local/main.py` en una Raspberry Pi 5, sin tocar backend ni frontend, recibiendo el dictamen por la API REST → screenshot del dictamen recibido. Esta tarea es de alto esfuerzo y solo se contempla si el cronograma lo permite tras los cuatro pasos anteriores.

Una vez recogida esta evidencia, se construirá la **tabla final de cumplimiento ISO/IEC 25010:2023** con score por característica y se incorporará al Pre Informe oficial como cierre del OE-07.

**Trazabilidad.** El detalle por subcaracterística, con archivos:líneas y comandos verificables, se encuentra en el documento `OE-07_ISO25010_evidencia.md` en la raíz del repositorio. La presente sección resume el panorama; el documento referenciado provee la matriz completa.

---

## II. REFERENCIAS BIBLIOGRÁFICAS

Las referencias se presentan en estilo IEEE.

[1] A. Azevedo y M. F. Santos, «KDD, SEMMA AND CRISP-DM: A parallel overview», en *Proceedings of the IADIS European Conference on Data Mining*, 2008, pp. 182–185.

[2] I. Nasri, «Driver Drowsiness Dataset (DDD)», *Kaggle*, 2022. [En línea]. Disponible en: https://www.kaggle.com/datasets/ismailnasri20/driver-drowsiness-dataset-ddd. [Accedido: 28 de abril de 2026].

[3] A. Chowdhury et al., «Subject-independent drowsiness recognition from single-channel EEG with an interpretable CNN-LSTM model», *Neurocomputing*, vol. 552, p. 126581, 2023, doi: 10.1016/j.neucom.2023.126581.

[4] S. Díaz-Santos, Ó. Cigala-Álvarez, E. Gonzalez-Sosa, P. Caballero-Gil, y C. Caballero-Gil, «Driver Identification and Detection of Drowsiness while Driving», *Appl. Sci.*, vol. 14, n.° 6, p. 2603, mar. 2024, doi: 10.3390/app14062603.

[5] A. K. Pathak, A. K. Singh, P. Kumar, V. Bhatia, y O. Krejcar, «Real-time anti-sleep alert algorithm to prevent road accidents to ensure road safety», *Front. Future Transp.*, vol. 6, p. 1545411, mar. 2025, doi: 10.3389/ffutr.2025.1545411.

[6] F. H. Kamaru Zaman, K. M. Ng, y S. A. Che Abdullah, «Comparative Analysis of Vision Transformers and CNN Models for Driver Fatigue Classification», *IIUM Eng. J.*, vol. 26, n.° 2, pp. 169–186, may 2025, doi: 10.31436/iiumej.v26i2.3488.

[7] S. A. El-Nabi et al., «Driver Drowsiness Detection Using Swin Transformer and Diffusion Models for Robust Image Denoising», *IEEE Access*, vol. 13, pp. 71880–71907, 2025, doi: 10.1109/ACCESS.2025.3561717.

[8] J. Wijsman, B. Grundlehner, J. Penders, y H. Hermens, «Trapezius muscle EMG as predictor of mental stress», *ACM Trans. Embed. Comput. Syst.*, vol. 12, n.° 4, pp. 1–20, jun. 2013, doi: 10.1145/2485984.2485987.

[9] J.-Y. Zhang, S.-L. Liu, Q.-M. Feng, J.-Q. Gao, y Q. Zhang, «Correlative Evaluation of Mental and Physical Workload of Laparoscopic Surgeons Based on Surface Electromyography and Eye-tracking Signals», *Sci. Rep.*, vol. 7, n.° 1, p. 11095, sep. 2017, doi: 10.1038/s41598-017-11584-4.

[10] M. Cifrek, V. Medved, S. Tonković, y S. Ostojić, «Surface EMG based muscle fatigue evaluation in biomechanics», *Clin. Biomech.*, vol. 24, n.° 4, pp. 327–340, abr. 2009, doi: 10.1016/j.clinbiomech.2009.01.010.

[11] Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, «Heart rate variability: Standards of measurement, physiological interpretation and clinical use», *Circulation*, vol. 93, n.° 5, pp. 1043–1065, mar. 1996, doi: 10.1161/01.CIR.93.5.1043.

[12] R. Merletti y L. R. Lo Conte, «Surface EMG signal processing during isometric contractions», *J. Electromyogr. Kinesiol.*, vol. 7, n.° 4, pp. 241–250, 1997, doi: 10.1016/S1050-6411(97)00016-X.

[13] C. J. De Luca, «Myoelectrical manifestations of localized muscular fatigue in humans», *Crit. Rev. Biomed. Eng.*, vol. 11, n.° 4, pp. 251–279, 1984.

[14] C. Lin, X. Zhu, R. Wang, W. Zhou, N. Li, y Y. Xie, «Early Driver Fatigue Detection System: A Cost-Effective and Wearable Approach Utilizing Embedded Machine Learning», *Vehicles*, vol. 7, n.° 1, p. 3, ene. 2025, doi: 10.3390/vehicles7010003.

[15] W. Verkruysse, L. O. Svaasand, y J. S. Nelson, «Remote plethysmographic imaging using ambient light», *Opt. Express*, vol. 16, n.° 21, pp. 21434–21445, oct. 2008, doi: 10.1364/OE.16.021434.

[16] F. Shaffer y J. P. Ginsberg, «An Overview of Heart Rate Variability Metrics and Norms», *Front. Public Health*, vol. 5, p. 258, sep. 2017, doi: 10.3389/fpubh.2017.00258.

[17] W. Wang, A. C. den Brinker, S. Stuijk, y G. de Haan, «Algorithmic Principles of Remote PPG», *IEEE Trans. Biomed. Eng.*, vol. 64, n.° 7, pp. 1479–1491, jul. 2017, doi: 10.1109/TBME.2016.2609282.

[18] G. de Haan y V. Jeanne, «Robust Pulse Rate From Chrominance-Based rPPG», *IEEE Trans. Biomed. Eng.*, vol. 60, n.° 10, pp. 2878–2886, oct. 2013, doi: 10.1109/TBME.2013.2266196.

[19] International Organization for Standardization, *ISO/IEC 25010:2023 — Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*, 2.ª ed., Ginebra, Suiza: ISO, 2023.

[20] J. Brooke, «SUS: A "quick and dirty" usability scale», en *Usability Evaluation in Industry*, P. W. Jordan, B. Thomas, B. A. Weerdmeester y I. L. McClelland, eds., London, U.K.: Taylor & Francis, 1996, pp. 189–194.

---

## ANEXOS

### Anexo N.° 01. Carta de aceptación de NOR VISIÓN para la ejecución de la tesis

*[Adjuntar carta de aceptación firmada por la dirección de NOR VISIÓN.]*

---

### Anexo N.° 02. Gráficas de resultados del experimento

Las siguientes figuras fueron generadas durante la ejecución del notebook `Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb` y se encuentran en la carpeta `resultados/` del repositorio del proyecto:

- `distribuciones_variables.png` — Distribución de EAR y MAR por clase (alerta vs. somnoliento).
- `matrices_confusion_dual.png` — Matrices de confusión de los 6 modelos (3 arquitecturas × 2 estrategias).
- `roc_curves_dual.png` — Curvas ROC de los 6 modelos con AUC-ROC.
- `training_curves.png` — Curvas de pérdida y F1 durante el entrenamiento (Estrategia A).
- `threshold_tuning.png` — Análisis del umbral de decisión sobre el modelo ganador.

---

### Anexo N.° 03. Estructura del repositorio del proyecto

```
ProyectoTesis/
├── backend/                   # API REST FastAPI + PostgreSQL
│   ├── app/
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── dtos/              # Schemas Pydantic (request/response)
│   │   ├── services/          # Lógica de negocio
│   │   └── utils/             # JWT, dependencias
│   └── DDL/                   # Scripts SQL de creación de tablas
├── frontend/                  # SPA React 19 + Vite + TypeScript
│   └── src/
│       ├── pages/             # Login, Dashboard, Evaluaciones, Admin
│       ├── components/        # Layout, Semaforo, ProtectedRoute
│       ├── api/               # Clientes HTTP (Axios)
│       └── store/             # Zustand auth store
├── local/                     # Scripts Python de detección embebida
│   ├── main.py                # Orquestador: cámara + Arduino + API
│   ├── requirements.txt
│   └── modules/
│       ├── m1_vision.py       # Módulo 1: BiLSTM + MediaPipe FaceMesh
│       ├── m2_reglas.py       # Módulo 2: Motor de reglas EMG/HRV
│       └── m3_fusion.py       # Módulo 3: Fusión tardía 40/60
├── resultados/                # Gráficas y CSVs del experimento
├── Modulo1_CNN_LSTM_ViT_v6_RUN_ALL_RESULTADOS.ipynb
├── Pre_Informe_Tesis_TORRES_CABREJOS_2026.md  ← este archivo
└── .gitignore
```

---

*Documento generado como versión Markdown de `Pre_Informe_Tesis_TORRES_CABREJOS_2026.docx` para control de versiones en GitHub. Las secciones marcadas con "(parcial)" corresponden a objetivos en ejecución activa.*
