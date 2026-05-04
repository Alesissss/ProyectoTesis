-- ============================================================
-- 07_baselines_somnolencia.sql
-- Baseline personal de M1 (visión / somnolencia) — separado de baselines_emg
--
-- Diseño: tabla independiente para no acoplar el lifecycle del baseline de
-- somnolencia (capturable solo con cámara) al baseline EMG (que requiere el
-- sensor Olimex + Arduino). Cada usuario tiene a lo más un baseline activo
-- por tipo, y cada uno se actualiza independientemente.
--
-- Motivación documentada en Pre Informe → Iteración 7, tarea 7.5
-- (verificación empírica de subject-dependence en M1).
-- ============================================================

CREATE TABLE IF NOT EXISTS baselines_somnolencia (
    id_baseline      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario       UUID            NOT NULL REFERENCES usuarios(id_usuario) ON DELETE RESTRICT,

    -- Salida del BiLSTM en estado alerta declarado (P_obs base del sujeto)
    p_somnolencia    DOUBLE PRECISION NOT NULL,

    -- Métricas conductuales auxiliares (para diagnóstico y trazabilidad)
    ear_promedio     DOUBLE PRECISION NULL,
    mar_promedio     DOUBLE PRECISION NULL,
    duracion_s       DOUBLE PRECISION NULL,
    frames_procesados INTEGER         NULL,

    -- Control de versión
    activo           BOOLEAN         NOT NULL DEFAULT TRUE,

    -- Auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baselines_somn_usuario ON baselines_somnolencia(id_usuario);
CREATE INDEX IF NOT EXISTS idx_baselines_somn_activo
    ON baselines_somnolencia(id_usuario, activo) WHERE activo = TRUE;

COMMENT ON COLUMN baselines_somnolencia.p_somnolencia IS
    'P_somnolencia del sujeto en estado alerta declarado, capturada con BiLSTM A. '
    'Usada por M3 para corrección personalizada: P_efectiva = max(0, P_obs - p_somnolencia).';
COMMENT ON COLUMN baselines_somnolencia.activo IS 'TRUE = baseline vigente; FALSE = histórico';
COMMENT ON COLUMN baselines_somnolencia.estado_registro IS 'FALSE = soft-delete';

-- ============================================================
-- Permisos para el nuevo recurso
-- ============================================================
INSERT INTO permisos (codigo_permiso, descripcion) VALUES
    ('baseline_somnolencia:registrar',  'Registrar una nueva calibración de somnolencia (M1)'),
    ('baseline_somnolencia:ver_propios','Ver sus propios baselines de somnolencia'),
    ('baseline_somnolencia:ver_todos',  'Ver los baselines de somnolencia de todos los usuarios')
ON CONFLICT (codigo_permiso) DO NOTHING;

-- Médico: registrar y ver los suyos
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'medico'
  AND  p.codigo_permiso IN (
       'baseline_somnolencia:registrar',
       'baseline_somnolencia:ver_propios'
  )
ON CONFLICT DO NOTHING;

-- Administrador: todo lo del médico + ver todos
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'administrador'
  AND  p.codigo_permiso IN (
       'baseline_somnolencia:registrar',
       'baseline_somnolencia:ver_propios',
       'baseline_somnolencia:ver_todos'
  )
ON CONFLICT DO NOTHING;

-- Superadmin: todo (re-ejecutar el bulk del 05_seed_data sigue válido)
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'superadmin'
  AND  p.codigo_permiso LIKE 'baseline_somnolencia:%'
ON CONFLICT DO NOTHING;
