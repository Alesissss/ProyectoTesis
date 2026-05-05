# OE-07 — Evaluación del sistema bajo ISO/IEC 25010:2023

**Tesis:** "Sistema embebido multimodal para la auto-detección de somnolencia y fatiga mental para prevenir negligencias médicas en un consultorio de Chiclayo"
**Autor:** Jorge Alexis Torres Cabrejos · USAT · 2026
**Alcance:** Backend (FastAPI + PostgreSQL 16) + Frontend (React 19 + TS + Tailwind) + módulos locales (`local/`).
**Estándar de referencia:** ISO/IEC 25010:2023 (modelo de calidad del producto software).
**Fecha:** 2026-05-04.

> Este documento traza cada característica de calidad contra la implementación
> real del sistema (archivos, líneas, comandos verificables). Es el insumo
> principal para el OE-07 del Pre Informe.

---

## Resumen ejecutivo

| Característica (ISO/IEC 25010:2023) | Estado de cobertura | Esfuerzo restante |
|---|---|---|
| Adecuación funcional | ✅ Cubierto con trazabilidad RF↔código | Bajo (tabla final de cierre) |
| Seguridad | ✅ Cubierto (bcrypt, UUID, JWT, RBAC, auditoría) | Bajo (capturas de pruebas) |
| Mantenibilidad | ✅ Cubierto (capas, modularidad, auditoría) | Bajo (diagrama) |
| Compatibilidad | ✅ Cubierto (REST stateless, navegadores ≥ Chromium 120) | Bajo (matriz de prueba manual) |
| Confiabilidad | 🟡 Parcial (manejo de errores, fallback offline) | Medio (prueba de fallo controlada) |
| Eficiencia de desempeño | 🟡 Parcial (latencias documentadas) | Medio (medición end-to-end con cronómetro) |
| Interacción / Usabilidad | 🟡 Parcial (≤5 clics, semáforo) | Medio-Alto (encuesta a usuarios reales) |
| Flexibilidad / Portabilidad | ✅ Cubierto a nivel arquitectónico (RNF-12) | Medio (demo de despliegue alternativo si hay tiempo) |
| Seguridad operacional (Safety) | 🟡 Parcial (avisos clínicos en dictamen) | Medio (declarar limitaciones de uso) |

---

## 1. Adecuación funcional (Functional Suitability)

**Subcaracterísticas:** completitud, corrección, adecuación.

### 1.1 Completitud — RF cumplidos

Los 18 RF del Pre Informe están operativos:

| RF | Descripción resumida | Evidencia (archivo:líneas o componente) |
|---|---|---|
| RF-01..03 | Autenticación con JWT, login/logout | `backend/app/routers/auth_router.py`, `backend/app/services/auth_service.py`, `frontend/src/pages/Login.tsx` |
| RF-04..06 | CRUD de usuarios y roles | `backend/app/routers/usuario_router.py`, `frontend/src/pages/Administracion.tsx` |
| RF-07 | Calibración personal sEMG | `backend/app/services/baseline_service.py` |
| RF-08 | Calibración personal de somnolencia M1 | `backend/app/routers/calibracion_router.py`, `frontend/src/pages/Calibracion.tsx` |
| RF-09..11 | Captura M1 (visión) + M2 (EMG/HRV) + M3 (fusión) | `local/main.py`, `local/modules/m1_vision.py`, `local/modules/m2_reglas.py`, `local/modules/m3_fusion.py` |
| RF-12 | Registro automático de evaluaciones | `backend/app/routers/evaluacion_router.py` (`POST /evaluaciones`) |
| RF-13 | Disparo de evaluación automática desde web (sin consola) | `backend/app/routers/evaluacion_router.py` (`POST /evaluaciones/iniciar`), `frontend/src/pages/EvaluacionAuto.tsx` |
| RF-14 | Visualización de dictamen tipo semáforo | `frontend/src/components/Semaforo.tsx` |
| RF-15..16 | Historial de evaluaciones (médico / admin) | `frontend/src/pages/MisEvaluaciones.tsx`, `EvaluacionDetalle.tsx` |
| RF-17 | Auditoría de operaciones | DDL `backend/DDL/03_audit_function.sql`, `04_audit_triggers.sql` |
| RF-18 | Persistencia de baselines y evaluaciones | DDL `backend/DDL/02_tables.sql`, `07_baselines_somnolencia.sql` |

### 1.2 Corrección

- Modelo M1 desplegado: `lstm_A_subjindep_best.pt` (Estrategia A, sujeto-independiente honesta). Métricas en `resultados/reporte_tesis.md`.
- Validación numérica del fusor M3 con escenarios sintéticos (memoria `project_subject_calibration.md`):
  - Sin baseline: P_obs=0.96, P_fatiga=0.30 → P_total=0.564 → `NO_APTO`.
  - Con baseline=0.92: P_efectiva=0.04 → P_total=0.196 → `APTO`. ✅
- rPPG (Wang 2017 POS) recupera HR=75.1 bpm sobre señal sintética cardíaca de 75 bpm.

### 1.3 Adecuación

Todas las pantallas exponen únicamente la funcionalidad permitida por el rol del usuario; el sidebar filtra ítems con `hasPermission()` (`frontend/src/components/Layout.tsx`).

---

## 2. Eficiencia de desempeño (Performance Efficiency)

**Subcaracterísticas:** comportamiento temporal, utilización de recursos, capacidad.

### 2.1 Comportamiento temporal

| Subsistema | Latencia medida / objetivo | Fuente |
|---|---|---|
| Inferencia BiLSTM por imagen | 0.11 ms | Notebook celda 31 |
| Captura M1 (cámara ALPCAM) | 30 s a 57.6 fps reales (USB 2.0) | `local/diagnostico_camara.py` (Iter. 10) |
| Procesamiento M2 (FFT 500 Hz × 30 s) | < 200 ms | Cálculo offline en `local/main.py:_procesar_senal_emg` |
| Fusión M3 + POST | < 500 ms | Por código (`fusionar` es aritmético, requests con timeout 15 s) |
| Endpoints REST CRUD (auth/usuarios/eval) | < 100 ms p95 esperados (async + UUID indexado) | A verificar con prueba de carga ligera |
| Pipeline end-to-end (RNF-01: < 10 s aparte de captura) | A medir con cronómetro durante la sustentación | — |

### 2.2 Utilización de recursos

- BiLSTM A: 1.2M parámetros, 4.8 MB en disco. Corre en CPU sin GPU.
- MediaPipe FaceMesh es el mayor consumidor (CPU-bound) → cuello de botella conocido para portar a Raspberry Pi.
- PostgreSQL 16: índices declarados en `__table_args__` de cada modelo SQLAlchemy + DDL alineados (no genera DROP INDEX en Alembic).

### 2.3 Capacidad

- El sistema está diseñado para **un médico por dispositivo embebido** (cámara + Arduino son recursos únicos). Concurrencia controlada por `asyncio.Lock` en `evaluacion_service.py` y `calibracion_service.py` (HTTP 409 si se intenta solapar).
- Backend multi-tenant lógico: cada médico ve solo sus evaluaciones (`evaluacion:ver_propias` filtra por `id_usuario` en `evaluacion_service.py:obtener_por_id`).

### 2.4 Decisión arquitectónica — invocación del subproceso local

El backend FastAPI no ejecuta directamente la captura: dispara `local/main.py` como subproceso aparte (justificado por RNF-12: el venv de `local/` con OpenCV/MediaPipe/PyTorch debe permanecer separado del venv del backend para que el portado a Raspberry/Jetson sea limpio).

**Patrón adoptado:** `subprocess.run` síncrono envuelto en `asyncio.to_thread(...)`, en lugar de `asyncio.create_subprocess_exec`.

| Aspecto | Implementación |
|---|---|
| Servicios afectados | `dispositivos_service.py:67`, `calibracion_service.py:119`, `evaluacion_service.py:206` |
| Razón técnica | En Windows, uvicorn (especialmente con `--reload`) crea su event loop **antes** de importar `main.py`, por lo que el `asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())` definido allí no afecta al loop ya construido. El loop activo termina siendo `SelectorEventLoop`, que no soporta `subprocess_exec` y lanza `NotImplementedError`. Verificado el 2026-05-05. |
| Costo de recursos | 1 worker del `ThreadPoolExecutor` por petición activa. El thread se libera al volver `subprocess.run`. No hay leak — el SO recolecta el proceso hijo y el worker vuelve al pool (default `min(32, cpu_count + 4)` workers, creados bajo demanda). |
| Concurrencia | El listado de cámaras está serializado por `_lock` (`asyncio.Lock`); calibración y evaluación, por `_calibracion_lock` y `_evaluacion_lock` respectivamente. Como mucho **un thread ocupado por flujo** simultáneamente. |
| Escalabilidad horizontal | El diseño asume 1 médico por unidad embebida. Si en el futuro se centralizara el procesamiento, conviene migrar a workers Celery/RQ para soltar al backend del ThreadPoolExecutor. |

**Trazabilidad ISO 25010 — Performance Efficiency / Resource Utilization:** el backend no permanece bloqueado durante la captura (la corutina cede el control al event loop mientras el thread espera al subproceso); puede seguir respondiendo a otras peticiones REST (login, listado de evaluaciones, etc.) en paralelo a una calibración o evaluación en curso.

---

## 3. Compatibilidad (Compatibility)

### 3.1 Coexistencia

- Todo el backend es REST stateless con JSON sobre HTTP. El frontend y el script local son clientes desacoplados que se comunican únicamente por la API REST.
- El script local no requiere instalación de nada en el frontend ni viceversa: pueden coexistir múltiples clientes contra la misma API.

### 3.2 Interoperabilidad

- API documentada automáticamente en OpenAPI 3.1 (`/docs`, `/redoc` de FastAPI).
- Esquema de respuesta uniforme `ApiResponse<T> = {status, message, data}` en todos los endpoints (`backend/app/dtos/common_dto.py`).
- Cumple RNF-10 (compatibilidad navegadores Chromium ≥ 120; React 19 + Vite 7).
- Hardware: ALPCAM AR0234 USB conformidad UVC; Arduino UNO con drivers CH340/CP210/FTDI auto-detectados (`local/main.py:_detectar_puerto_arduino`).

---

## 4. Interacción / Usabilidad (Interaction Capability)

| Subcaracterística | Evidencia |
|---|---|
| Reconocimiento de adecuación | Sidebar filtrado por permisos; iconos por sección (`Layout.tsx`) |
| Aprendizaje | Flujo lineal: Login → Calibración → Iniciar Evaluación. Instrucciones numeradas en cada página (`Calibracion.tsx`, `EvaluacionAuto.tsx`) |
| Operabilidad | Botón único "INICIAR EVALUACIÓN" disponible para el médico — RNF-06 (≤ 5 clics desde login: login → dashboard → iniciar evaluación = 3 clics) |
| Protección frente a error | Validaciones Pydantic en backend (HTTP 422 con detalle); `disabled` en UI durante captura para evitar doble click |
| Accesibilidad / inclusividad | Colores con suficiente contraste (verde APTO / amarillo ATENCIÓN / rojo NO_APTO) + texto explicativo, no solo color (`Semaforo.tsx`) |
| Estética | Tailwind + Sistema de diseño consistente |

**Pendiente:** encuesta SUS (System Usability Scale, 10 ítems Likert) a 5 médicos del consultorio NOR VISIÓN durante la prueba final, para obtener score numérico de usabilidad.

---

## 5. Confiabilidad (Reliability)

| Subcaracterística | Evidencia |
|---|---|
| Tolerancia a fallos | Si la cámara falla → `ResultadoM1` reporta `frames_procesados=0` y M3 emite justificación. Si EMG falla → M2 redistribuye pesos a las reglas HRV (`m2_reglas.py`). |
| Recuperabilidad | Si el backend no responde, el script local persiste el resultado en `resultado_sin_enviar.json` (`local/main.py`, líneas finales de `ejecutar`). |
| Disponibilidad | FastAPI corre con uvicorn worker async; el OOM o crash de un request no tumba el servidor. Excepciones no manejadas se interceptan en `backend/main.py:unhandled_exception_handler` y devuelven 500 estructurado. |
| Madurez | Manejo explícito de `TimeoutError`, `FileNotFoundError`, `JSONDecodeError` en `evaluacion_service.py:_ejecutar_subproceso`. |

**Pendiente:** prueba controlada de "qué pasa si el backend está caído" durante la captura — el flujo offline está implementado pero falta capturar evidencia (screenshot del archivo JSON resultante).

---

## 6. Seguridad (Security)

| Subcaracterística | Evidencia |
|---|---|
| **Confidencialidad** | Contraseñas almacenadas con bcrypt (`backend/app/utils/password_handler.py`); JWT firmado con HS256 y secreto en `.env` (`backend/app/utils/jwt_handler.py`). |
| **Integridad** | Tabla `auditoria_log` registra INSERT/UPDATE/DELETE de todas las tablas críticas vía trigger PostgreSQL `fn_auditoria()` (`backend/DDL/03_audit_function.sql`, `04_audit_triggers.sql`). |
| **No repudio** | El trigger lee `app.current_user_id` que la sesión SQLAlchemy auditada (`AuditedAsyncSession`) inyecta antes de cada query (`backend/app/data/database.py`). El JWT vincula la sesión al usuario. |
| **Trazabilidad / Accountability** | Todo evento queda en `auditoria_log` con `usuario_id`, `tabla`, `operacion`, `payload_anterior`, `payload_nuevo`, `timestamp`. |
| **Autenticidad** | JWT con expiración de 60 min (`Settings.jwt_expire_minutes`), permisos embebidos como lista en el payload, validados en cada request por `require_permission()` (`backend/app/utils/dependencies.py`). 38 ocurrencias de control de permiso a lo largo del backend + frontend. |
| **Resistencia** | IDs de usuario son UUID v4 (no enteros seriales) → previene enumeración. Pydantic valida y rechaza payloads malformados. CORS restringido a orígenes whitelisted (`Settings.allowed_origins`). |

**Hardening adicional implementado:**
- Sesiones separadas: `plain_session_factory` para `/auth/login` (sin auditoría posible porque aún no hay usuario) y `audited_session_factory` para todo lo demás.
- El flujo de calibración y evaluación auto reenvía el JWT al subprocess **vía CLI args**, nunca por env (`evaluacion_service.py`, `calibracion_service.py`); los args van como lista a `asyncio.create_subprocess_exec`, sin shell, lo que elimina el vector de command injection.
- Lock global asíncrono evita race conditions sobre el recurso cámara/Arduino.

---

## 7. Mantenibilidad (Maintainability)

| Subcaracterística | Evidencia |
|---|---|
| **Modularidad** | Backend en 5 capas: `routers/` → `services/` → `models/` ↔ `dtos/` + `utils/`. Frontend en `pages/`, `components/`, `api/`, `store/`, `types/`, `utils/`. Local en 3 módulos (`m1_vision`, `m2_reglas`, `m3_fusion`) + orquestador. |
| **Reusabilidad** | Componente `Semaforo.tsx` reutilizado por `EvaluacionDetalle` y `EvaluacionAuto`. `BaselineSomnolenciaService.registrar()` reutilizado por el endpoint manual y por `CalibracionService`. Helper `_resolver_main_path()` y patrón de subprocess replicado entre evaluación y calibración. |
| **Analizabilidad** | Auditoría completa (RF-17), logging estructurado en backend (`logging.getLogger(__name__)`), errores con stack trace en `unhandled_exception_handler`. |
| **Modificabilidad** | LOC reducido: backend `app/` ≈ 2 100 LOC Python, frontend `src/` ≈ 2 100 LOC TypeScript. Reglas M2 declaradas como tabla de 7 reglas con pesos sumando 1.0 → cambiar pesos no requiere refactor. |
| **Testabilidad** | DTOs Pydantic permiten construir fixtures sin tocar la BD. El motor M2 es funcional puro (`calcular_p_fatiga(emg, baseline, hrv)` → `ResultadoM2`), trivial de testear. |

**Métrica concreta:** la nueva funcionalidad "Iniciar Evaluación desde web" se implementó replicando el patrón de calibración: 1 archivo nuevo en frontend, +1 endpoint, +1 método en service, sin tocar la lógica clínica de M1/M2/M3. Esto demuestra modificabilidad.

---

## 8. Flexibilidad / Portabilidad (Flexibility)

ISO/IEC 25010:2023 fusiona aquí Adaptabilidad, Escalabilidad, Instalabilidad y Reemplazabilidad.

| Subcaracterística | Evidencia |
|---|---|
| **Adaptabilidad** | Configuración 100% por env vars: `DATABASE_URL`, `JWT_SECRET`, `LOCAL_MAIN_PATH`, `LOCAL_PYTHON`, `CALIBRACION_TIMEOUT_S`, `EVALUACION_TIMEOUT_S`, `ALLOWED_ORIGINS` (`backend/app/config.py`). Sin cambios de código entre dev/prod. |
| **Escalabilidad** | Backend FastAPI async puede correr detrás de Nginx con múltiples workers Uvicorn. PostgreSQL admite réplicas. RNF-12 obliga arquitectura para sustituir la "unidad de procesamiento local" sin tocar backend ni frontend. |
| **Instalabilidad** | Backend: `pip install -r requirements.txt` + DDL secuencial (01..07). Frontend: `npm install && npm run build` produce SPA estática. Local: `pip install -r local/requirements.txt`. |
| **Reemplazabilidad** | El script local es portable: Windows hoy (laptop NOR VISIÓN con cámara USB + Arduino), Raspberry Pi 5 / Jetson Nano mañana, sin tocar backend ni frontend (todo va por la misma API REST). El cuello de botella conocido es MediaPipe (CPU-bound). |

---

## 9. Seguridad operacional (Safety) — nueva en ISO/IEC 25010:2023

| Subcaracterística | Estado |
|---|---|
| **Restricción operacional** | El dictamen final no es prescriptivo: muestra `APTO / ATENCIÓN / NO_APTO` con justificación, pero **la decisión final es del médico**. La UI lo enuncia explícitamente en `Semaforo.tsx`: "Se recomienda…". |
| **Identificación de riesgos** | Documentación de subject-dependence (Iter. 11) → motiva la calibración personal obligatoria. RNF-05 fija la corrección por baseline. |
| **Fail-safe** | Si rPPG no es válido (gate de calidad RMSSD/SDNN > 1.4) → no contribuye al dictamen. Si EMG no llega → reglas se redistribuyen, no se "inventan" valores. |
| **Hazard warning** | El sistema avisa en logs y en la UI cuando NO hay calibración personal: "el dictamen NO aplicará corrección personalizada — recomendado calibrar primero" (`local/main.py`). |
| **Integración segura** | El subprocess se ejecuta con timeout duro y se mata (`proc.kill()`) si excede `evaluacion_timeout_s`. El JWT del médico se reenvía solo por args, no por env ni por shell. |

**Limitación declarada:** el sistema es una **ayuda a la decisión clínica**, no un reemplazo del juicio médico. Esta declaración debe figurar en el manual de usuario y en el consentimiento del estudio (OE-07 final).

---

## Plan de evaluación pendiente

Para cerrar el OE-07 con números concretos:

1. **Encuesta SUS** (System Usability Scale) a 5 médicos del consultorio NOR VISIÓN tras 1 sesión de uso → score ∈ [0, 100]. Objetivo: ≥ 70.
2. **Cronómetro end-to-end** durante 5 evaluaciones consecutivas → confirmar RNF-01 (< 10 s aparte de captura).
3. **Prueba de fallo controlado**: detener backend a la mitad de una evaluación → screenshot de `resultado_sin_enviar.json`.
4. **Matriz de compatibilidad**: ejecutar el frontend en Chrome 120+, Edge 120+, Firefox 121+ → screenshot de cada uno.
5. **Demo de portabilidad** (opcional, alto esfuerzo): correr `local/main.py` en una Raspberry Pi 5 (sin tocar backend ni frontend) → screenshot del dictamen recibido.

Una vez recogida esta evidencia, se construye la **tabla final de cumplimiento ISO/IEC 25010:2023** con score por característica y se incorpora al Pre Informe como Iteración 13 (cierre del OE-07).
