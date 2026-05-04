-- ============================================================
-- 02_tables.sql
-- Creación de todas las tablas del sistema VigilanceAI
-- Orden: roles → permisos → rol_permiso → usuarios
--        → baselines_emg → evaluaciones → auditoria_log
-- ============================================================

-- -----------------------------------------------------------
-- ROLES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id_rol           SERIAL          PRIMARY KEY,
    nombre_rol       VARCHAR(50)     NOT NULL UNIQUE,
    descripcion      TEXT,
    -- campos de auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  roles               IS 'Roles del sistema: médico, administrador, superadmin';
COMMENT ON COLUMN roles.estado_registro IS 'FALSE = soft-delete';

-- -----------------------------------------------------------
-- PERMISOS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS permisos (
    id_permiso       SERIAL          PRIMARY KEY,
    codigo_permiso   VARCHAR(100)    NOT NULL UNIQUE,
    descripcion      TEXT,
    -- campos de auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE permisos IS 'Permisos atómicos del sistema (e.g. evaluacion:registrar)';

-- -----------------------------------------------------------
-- ROL_PERMISO  (N:N)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS rol_permiso (
    id_rol           INTEGER         NOT NULL REFERENCES roles(id_rol)    ON DELETE RESTRICT,
    id_permiso       INTEGER         NOT NULL REFERENCES permisos(id_permiso) ON DELETE RESTRICT,
    PRIMARY KEY (id_rol, id_permiso),
    -- campos de auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- USUARIOS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario       UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre           VARCHAR(100)    NOT NULL,
    apellido         VARCHAR(100)    NOT NULL,
    email            VARCHAR(255)    NOT NULL UNIQUE,
    password_hash    VARCHAR(255)    NOT NULL,
    id_rol           INTEGER         NOT NULL REFERENCES roles(id_rol) ON DELETE RESTRICT,
    -- campos de auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email   ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_id_rol  ON usuarios(id_rol);

COMMENT ON COLUMN usuarios.estado_registro IS 'FALSE = cuenta deshabilitada (soft-delete)';

-- -----------------------------------------------------------
-- BASELINES_EMG
-- Calibración inicial por usuario; activo = TRUE solo en el más reciente
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS baselines_emg (
    id_baseline      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario       UUID            NOT NULL REFERENCES usuarios(id_usuario) ON DELETE RESTRICT,
    -- features EMG
    rms_emg          DOUBLE PRECISION NOT NULL,
    freq_mediana     DOUBLE PRECISION NOT NULL,
    freq_media       DOUBLE PRECISION NOT NULL,
    -- features HRV
    sdnn             DOUBLE PRECISION,
    rmssd            DOUBLE PRECISION,
    pnn50            DOUBLE PRECISION,
    -- control de versión de baseline
    activo           BOOLEAN         NOT NULL DEFAULT TRUE,
    -- campos de auditoría
    estado_registro  BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro UUID            NULL,
    fecha_registro   TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baselines_usuario ON baselines_emg(id_usuario);
CREATE INDEX IF NOT EXISTS idx_baselines_activo  ON baselines_emg(id_usuario, activo) WHERE activo = TRUE;

COMMENT ON COLUMN baselines_emg.activo IS 'TRUE = baseline vigente; FALSE = histórico';
COMMENT ON COLUMN baselines_emg.estado_registro IS 'FALSE = soft-delete';

-- -----------------------------------------------------------
-- EVALUACIONES
-- El script local (edge) envía el JSON ya procesado
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluaciones (
    id_evaluacion           UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario              UUID            NOT NULL REFERENCES usuarios(id_usuario)     ON DELETE RESTRICT,
    id_baseline_usado       UUID            NULL     REFERENCES baselines_emg(id_baseline) ON DELETE SET NULL,
    -- Módulo 1 — visión conductual
    p_somnolencia           DOUBLE PRECISION NOT NULL
                            CHECK (p_somnolencia   BETWEEN 0.0 AND 1.0),
    -- Módulo 2 — fisiológico
    p_fatiga_fisiologica    DOUBLE PRECISION NOT NULL
                            CHECK (p_fatiga_fisiologica BETWEEN 0.0 AND 1.0),
    -- Módulo 3 — fusión
    p_total                 DOUBLE PRECISION NOT NULL
                            CHECK (p_total         BETWEEN 0.0 AND 1.0),
    dictamen                VARCHAR(20)     NOT NULL
                            CHECK (dictamen IN ('APTO', 'ATENCION', 'NO_APTO')),
    umbral_usado            DOUBLE PRECISION NOT NULL DEFAULT 0.50,
    -- Features crudas recibidas del script local
    features_conductuales   JSONB,
    features_emg            JSONB,
    features_hrv            JSONB,
    -- Metadatos adicionales (extensible sin cambio de esquema)
    metadatos               JSONB,
    duracion_captura_s      INTEGER         NOT NULL DEFAULT 30,
    -- campos de auditoría
    estado_registro         BOOLEAN         NOT NULL DEFAULT TRUE,
    usuario_registro        UUID            NULL,
    fecha_registro          TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evaluaciones_usuario   ON evaluaciones(id_usuario);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_dictamen  ON evaluaciones(dictamen);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_fecha     ON evaluaciones(fecha_registro DESC);

COMMENT ON TABLE  evaluaciones IS 'Resultados enviados por el script local (edge computing). El backend NO procesa, solo persiste.';
COMMENT ON COLUMN evaluaciones.dictamen IS 'APTO | ATENCION | NO_APTO';

-- -----------------------------------------------------------
-- AUDITORIA_LOG
-- Llenada exclusivamente por triggers; nunca por la aplicación
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria_log (
    id_log              BIGSERIAL       PRIMARY KEY,
    nombre_tabla        VARCHAR(100)    NOT NULL,
    operacion           VARCHAR(10)     NOT NULL CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE')),
    id_registro         TEXT,
    registro_anterior   JSONB,
    registro_nuevo      JSONB,
    usuario_accion      UUID,                       -- usuario de la app (del JWT)
    usuario_bd          VARCHAR(100)    NOT NULL DEFAULT current_user,  -- usuario de la BD
    fecha_accion        TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auditoria_tabla    ON auditoria_log(nombre_tabla);
CREATE INDEX IF NOT EXISTS idx_auditoria_registro ON auditoria_log(id_registro);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha    ON auditoria_log(fecha_accion DESC);

COMMENT ON TABLE auditoria_log IS 'Log de auditoría poblado por triggers. Nunca modificar directamente.';
