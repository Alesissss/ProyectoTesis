
# Resultados del Objetivo Específico 2: Comparación de algoritmos de visión artificial

## Dataset utilizado
- **Nombre:** Driver Drowsiness Dataset (DDD)
- **Autor:** Ismail Nasri (Kaggle, 2022)
- **Fuente:** https://www.kaggle.com/datasets/ismailnasri20/driver-drowsiness-dataset-ddd
- **Total de imágenes:** 41,793
- **Distribución:** 19,445 alert / 22,348 drowsy
- **Sujetos únicos:** 28 (A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, ZA, ZB, ZC)

## Metodología de split
- **Split subject-independent** (los 28 sujetos se reparten disjuntamente):
  - Train: 19 sujetos → 26,775 imágenes
  - Val:   4 sujetos → 6,404 imágenes
  - Test:  5 sujetos → 8,614 imágenes
- **Justificación:** garantiza que el test mide generalización a personas nunca vistas, evitando la sobreestimación típica de los splits aleatorios (Chowdhury et al. 2023).

## Arquitecturas evaluadas

### 1. CNN — MobileNetV2 (transfer learning en dos fases)
- Backbone preentrenado en ImageNet1k
- **Fase 1** (8 épocas, lr=1e-3): solo head entrenable
- **Fase 2** (18 épocas, lr=3e-5): fine-tuning completo
- Optimizador AdamW, cosine LR, label smoothing 0.1, class weights
- Mixed precision training (AMP)

### 2. LSTM — sobre features temporales por sujeto
- Features extraídos con **MediaPipe FaceMesh** (EAR promedio + MAR)
- Secuencias construidas por sujeto con **sliding window** (SEQ_LEN=20, STRIDE=5)
- Normalización con estadísticos del train (sin data leakage)
- Arquitectura: **BiLSTM 2 capas** (hidden=128) → mean+last pooling → MLP
- Selección del mejor por F1

### 3. ViT — Vision Transformer Tiny
- Preentrenado en ImageNet (vía `timm`)
- Optimizador AdamW (lr=3e-4, weight_decay=5e-4)
- **Warmup lineal** (3 épocas) + cosine decay
- 25 épocas con early stopping

## Evaluación
- Test set **completamente independiente por sujeto**
- **TTA (Test-Time Augmentation)** aplicado a CNN y ViT: original + flip horizontal, promedio de probabilidades

## Resultados comparativos

| name              |   accuracy |   precision |   recall |    f1 |    auc |   specificity |   inference_ms |
|:------------------|-----------:|------------:|---------:|------:|-------:|--------------:|---------------:|
| MobileNetV2 (CNN) |      53.05 |       50.81 |    79.01 | 61.85 | 0.5135 |         28.94 |           1.28 |
| LSTM (EAR+MAR)    |      74.56 |       68.43 |    87.59 | 76.83 | 0.7942 |         62.44 |           0.11 |
| ViT-Tiny          |      49.41 |       47.91 |    57.72 | 52.36 | 0.5328 |         41.68 |           1.07 |

## Modelo seleccionado
**Ganador:** LSTM (EAR+MAR)

- Accuracy:       **74.56%**
- F1-score:       **76.83%**
- AUC-ROC:        **0.7942**
- Sensibilidad:   **87.59%**
- Especificidad:  **62.44%**
- Precisión:      **68.43%**
- Latencia:       **0.11 ms/imagen**

Este modelo NO cumple con el RNF-02 (exactitud ≥ 85%) y será integrado como Módulo 1 del sistema multimodal.
