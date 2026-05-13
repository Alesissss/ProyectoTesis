export type Dictamen = 'APTO' | 'ATENCION' | 'NO_APTO'

export interface TokenData {
  sub: string
  email: string
  nombre: string
  apellido: string
  rol: string
  permisos: string[]
  exp: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

// Coincide con UsuarioListResponse / UsuarioResponse del backend
export interface Usuario {
  id_usuario: string
  nombre: string
  apellido: string
  email: string
  nombre_rol: string   // campo real devuelto por el backend
  estado_registro: boolean
  fecha_registro?: string
}

// Coincide con UsuarioCreateRequest del backend (id_rol es el PK entero de la tabla roles)
export interface UsuarioCreate {
  nombre: string
  apellido: string
  email: string
  password: string
  id_rol: number
}

// Coincide con UsuarioUpdateRequest del backend
export interface UsuarioUpdate {
  nombre?: string
  apellido?: string
  email?: string
  password?: string
  id_rol?: number
}

// ── Evaluaciones ──────────────────────────────────────────────────────────────
// Campos libres enviados por el script local (schema flexible → JSONB en BD)
export interface FeaturesConductuales {
  ear_promedio: number
  mar_promedio: number
  perclos: number
  blink_rate: number
  head_pitch: number
  head_yaw: number
  microsleep_count: number
  video_duration_s: number
  [key: string]: unknown
}

export interface FeaturesEMG {
  rms_mean: number
  rms_std: number
  mnf_mean: number
  mnf_std: number
  fatigue_slope: number
  canales_usados: number[]
  [key: string]: unknown
}

export interface FeaturesHRV {
  sdnn: number
  rmssd: number
  lf_hf_ratio: number
  mean_rr: number
  pnn50: number
  [key: string]: unknown
}

// Coincide exactamente con EvaluacionRequest del backend
export interface EvaluacionCreate {
  p_somnolencia: number
  p_fatiga_fisiologica: number
  p_total: number
  dictamen: Dictamen
  umbral_usado?: number
  features_conductuales?: Record<string, unknown>
  features_emg?: Record<string, unknown>
  features_hrv?: Record<string, unknown>
  metadatos?: Record<string, unknown>
  duracion_captura_s?: number
  id_baseline_usado?: string | null
}

// Coincide con EvaluacionResponse del backend
export interface Evaluacion {
  id_evaluacion: string
  id_usuario: string
  p_somnolencia: number
  p_fatiga_fisiologica: number
  p_total: number
  dictamen: Dictamen
  umbral_usado: number
  features_conductuales?: Record<string, unknown>
  features_emg?: Record<string, unknown>
  features_hrv?: Record<string, unknown>
  duracion_captura_s: number
  metadatos?: Record<string, unknown>
  estado_registro: boolean
  fecha_registro: string
}

// Vista resumida (EvaluacionResumenResponse del backend)
export interface EvaluacionResumen {
  id_evaluacion: string
  dictamen: Dictamen
  p_total: number
  fecha_registro: string
}

// ── Evaluación automatizada (subprocess) ──────────────────────────────────────
// Cámaras disponibles devueltas por GET /dispositivos/camaras
export interface CamaraDisponible {
  index: number
  backend: string         // "DSHOW" | "MSMF"
  width: number
  height: number
  profile: string | null  // "alpcam" | "gopro" | "webcam" | null
  label: string           // texto humano para el dropdown
}

// Coincide con EvaluacionIniciarRequest del backend
export interface EvaluacionIniciarRequest {
  duracion_s?: number
  camera_profile?: string | null
  camara_id?: number | null
  puerto_arduino?: string | null
}

// Coincide con EvaluacionIniciarResultado del backend
export interface EvaluacionIniciarResultado {
  evaluacion: Evaluacion
  duracion_real_s: number
  frames_procesados: number
  fps_observado?: number | null
  n_muestras_emg: number
  hrv_disponible: boolean
  justificacion: string[]
}

// ── Baselines EMG ─────────────────────────────────────────────────────────────
// Coincide con BaselineCreateRequest del backend
export interface BaselineCreate {
  rms_emg: number
  freq_mediana: number
  freq_media: number
  sdnn?: number | null
  rmssd?: number | null
  pnn50?: number | null
}

// Coincide con BaselineResponse del backend
export interface Baseline {
  id_baseline: string
  id_usuario: string
  rms_emg: number
  freq_mediana: number
  freq_media: number
  sdnn?: number | null
  rmssd?: number | null
  pnn50?: number | null
  activo: boolean
  fecha_registro: string
}

// Coincide con RolResponse del backend
export interface Rol {
  id_rol: number
  nombre_rol: string
  descripcion?: string | null
}

// ── Baseline de somnolencia (M1) ──────────────────────────────────────────────
// Coincide con BaselineSomnolenciaResponse del backend
export interface BaselineSomnolencia {
  id_baseline: string
  id_usuario: string
  p_somnolencia: number
  ear_promedio?: number | null
  mar_promedio?: number | null
  duracion_s?: number | null
  frames_procesados?: number | null
  activo: boolean
  fecha_registro: string
}

export interface CalibracionIniciarRequest {
  duracion_s?: number
  camera_profile?: string | null
  camara_id?: number | null
  puerto_arduino?: string | null
}

// Coincide con BaselineM2Resumen del backend
export interface BaselineM2Resumen {
  id_baseline?: string | null
  rms_emg?: number | null
  freq_mediana?: number | null
  freq_media?: number | null
  sdnn?: number | null
  rmssd?: number | null
  pnn50?: number | null
  emg_valido: boolean
  emg_ratio_60hz?: number | null
  emg_motivo?: string | null
  arduino_detectado: boolean
  n_muestras_emg: number
}

// Coincide con CalibracionResultadoResponse del backend
export interface CalibracionResultado {
  baseline: BaselineSomnolencia
  baseline_m2?: BaselineM2Resumen | null
  duracion_real_s: number
  frames_procesados: number
  ventanas_inferidas: number
  fps_observado?: number | null
}
