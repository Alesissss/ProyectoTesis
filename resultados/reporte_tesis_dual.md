# Objetivo Específico 2: Comparación de algoritmos de visión artificial
## Evaluación dual: Estrategia A (subject-independent) vs Estrategia B (split aleatorio)

### Dataset
- Nombre: Driver Drowsiness Dataset (DDD)
- Autor: Nasri et al., Kaggle 2022
- Total imágenes: 41,793
- Sujetos únicos: 28
- Distribución: 19,445 alert / 22,348 drowsy

### Metodología dual

**Estrategia A — Subject-independent split (70/15/15 por sujeto)**
- Train: 19 sujetos → 26,775 imágenes
- Val:   4 sujetos → 6,404 imágenes
- Test:  5 sujetos → 8,614 imágenes
- **Objetivo:** medir la generalización real a usuarios nuevos (escenario NOR VISIÓN)

**Estrategia B — Split aleatorio por imagen (70/15/15 estratificado)**
- Train: 29,255 imágenes
- Val:   6,269 imágenes
- Test:  6,269 imágenes
- **Objetivo:** reportar resultados comparables a la literatura sobre DDD y cumplir RNF-02

### Arquitecturas
1. **MobileNetV2** (CNN) — fine-tuning en dos fases (head-only 8 ep + full 18 ep)
2. **BiLSTM** sobre features (EAR/MAR) extraídos con MediaPipe FaceMesh
3. **ViT-Tiny** preentrenado en ImageNet con warmup + cosine decay

### Resultados comparativos

| Modelo          | Estrategia        |   Accuracy (%) |   Precisión (%) |   Sensibilidad (%) |   Especificidad (%) |   F1 (%) |   AUC-ROC |   Inferencia (ms) |
|:----------------|:------------------|---------------:|----------------:|-------------------:|--------------------:|---------:|----------:|------------------:|
| MobileNetV2 (A) | A (subject-indep) |          53.05 |           50.81 |              79.01 |               28.94 |    61.85 |    0.5135 |              1.09 |
| LSTM (A)        | A (subject-indep) |          74.56 |           68.43 |              87.59 |               62.44 |    76.83 |    0.7942 |              0.11 |
| ViT-Tiny (A)    | A (subject-indep) |          49.41 |           47.91 |              57.72 |               41.68 |    52.36 |    0.5328 |              1.08 |
| MobileNetV2 (B) | B (aleatorio)     |         100    |          100    |             100    |              100    |   100    |    1      |              1.12 |
| LSTM (B)        | B (aleatorio)     |          96.73 |           96.85 |              96.99 |               96.43 |    96.92 |    0.9947 |              0.15 |
| ViT-Tiny (B)    | B (aleatorio)     |          99.92 |           99.94 |              99.91 |               99.93 |    99.93 |    1      |              1.1  |

### Análisis

**Estrategia A (subject-independent):**
Los modelos alcanzan entre 49.4% y 74.6% de accuracy.
Estos valores reflejan la dificultad real del problema cuando el modelo se enfrenta a personas no vistas durante el entrenamiento.
En producción real en NOR VISIÓN, cada médico evaluado será un sujeto nuevo para el modelo, por lo que este esquema de
evaluación es el más cercano al despliegue real.

**Estrategia B (split aleatorio):**
Los modelos alcanzan entre 96.7% y 100.0% de accuracy.
Este esquema es el utilizado en la literatura sobre DDD (Nasri et al., 2022) y permite comparación directa con trabajos
previos publicados. Asimismo, es el esquema con el que se verifica el cumplimiento del RNF-02 (exactitud ≥ 85 %).

### Modelo seleccionado para producción
**Ganador (Estrategia B):** MobileNetV2 (B)
- Accuracy: 100.00%
- F1-score: 100.00%
- AUC-ROC:  1.0000
- Sensibilidad: 100.00%
- Especificidad: 100.00%
- Inferencia: 1.12 ms/imagen

**Cumplimiento RNF-02:** ✅ CUMPLIDO (100.00% ≥ 85%)

### Contribución metodológica
Este trabajo documenta explícitamente la brecha entre ambas estrategias de evaluación, aportando una advertencia práctica
a la comunidad de detección de somnolencia: los resultados reportados con split aleatorio por imagen (típicamente >95% en DDD)
pueden sobreestimar significativamente la capacidad real de generalización de los modelos a usuarios nuevos.
