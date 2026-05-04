-- ============================================================
-- 03_audit_function.sql
-- Función genérica de auditoría disparada por los triggers.
-- Lee el usuario de aplicación desde la variable de sesión
-- 'app.current_user_id', que el backend setea al inicio
-- de cada transacción autenticada (equivalente a
-- SaveChangesAsync override en EF Core).
-- ============================================================

CREATE OR REPLACE FUNCTION fn_auditoria()
RETURNS TRIGGER AS $$
DECLARE
    v_usuario_accion    UUID;
    v_id_registro       TEXT;
    v_registro_anterior JSONB;
    v_registro_nuevo    JSONB;
BEGIN
    -- ── 1. Obtener el usuario de la aplicación desde session var ──
    BEGIN
        v_usuario_accion := NULLIF(
            current_setting('app.current_user_id', TRUE), ''
        )::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_usuario_accion := NULL;
    END;

    -- ── 2. Asignar OLD / NEW según la operación ──────────────────
    CASE TG_OP
        WHEN 'INSERT' THEN
            v_registro_anterior := NULL;
            v_registro_nuevo    := to_jsonb(NEW);
        WHEN 'UPDATE' THEN
            v_registro_anterior := to_jsonb(OLD);
            v_registro_nuevo    := to_jsonb(NEW);
        WHEN 'DELETE' THEN
            v_registro_anterior := to_jsonb(OLD);
            v_registro_nuevo    := NULL;
    END CASE;

    -- ── 3. Extraer PK del registro según la tabla ─────────────────
    DECLARE
        v_fila JSONB := COALESCE(v_registro_nuevo, v_registro_anterior);
    BEGIN
        v_id_registro := CASE TG_TABLE_NAME
            WHEN 'usuarios'      THEN v_fila ->> 'id_usuario'
            WHEN 'evaluaciones'  THEN v_fila ->> 'id_evaluacion'
            WHEN 'baselines_emg' THEN v_fila ->> 'id_baseline'
            WHEN 'roles'         THEN v_fila ->> 'id_rol'
            WHEN 'permisos'      THEN v_fila ->> 'id_permiso'
            WHEN 'rol_permiso'   THEN
                (v_fila ->> 'id_rol') || '-' || (v_fila ->> 'id_permiso')
            ELSE NULL
        END;
    END;

    -- ── 4. Insertar en auditoria_log ──────────────────────────────
    INSERT INTO auditoria_log (
        nombre_tabla,
        operacion,
        id_registro,
        registro_anterior,
        registro_nuevo,
        usuario_accion,
        usuario_bd
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        v_id_registro,
        v_registro_anterior,
        v_registro_nuevo,
        v_usuario_accion,
        current_user
    );

    -- ── 5. Retornar el registro correcto ─────────────────────────
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;

END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION fn_auditoria() IS
    'Trigger function genérica de auditoría. '
    'Lee app.current_user_id (seteada por el backend con set_config). '
    'SECURITY DEFINER garantiza acceso a auditoria_log independiente del rol.';
