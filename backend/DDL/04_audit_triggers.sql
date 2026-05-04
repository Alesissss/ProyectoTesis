-- ============================================================
-- 04_audit_triggers.sql
-- Aplicar el trigger de auditoría a cada tabla de negocio.
-- Ejecutar DESPUÉS de 03_audit_function.sql.
-- ============================================================

-- roles
DROP TRIGGER IF EXISTS trg_audit_roles ON roles;
CREATE TRIGGER trg_audit_roles
    AFTER INSERT OR UPDATE OR DELETE ON roles
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();

-- permisos
DROP TRIGGER IF EXISTS trg_audit_permisos ON permisos;
CREATE TRIGGER trg_audit_permisos
    AFTER INSERT OR UPDATE OR DELETE ON permisos
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();

-- rol_permiso
DROP TRIGGER IF EXISTS trg_audit_rol_permiso ON rol_permiso;
CREATE TRIGGER trg_audit_rol_permiso
    AFTER INSERT OR UPDATE OR DELETE ON rol_permiso
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();

-- usuarios
DROP TRIGGER IF EXISTS trg_audit_usuarios ON usuarios;
CREATE TRIGGER trg_audit_usuarios
    AFTER INSERT OR UPDATE OR DELETE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();

-- baselines_emg
DROP TRIGGER IF EXISTS trg_audit_baselines_emg ON baselines_emg;
CREATE TRIGGER trg_audit_baselines_emg
    AFTER INSERT OR UPDATE OR DELETE ON baselines_emg
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();

-- evaluaciones
DROP TRIGGER IF EXISTS trg_audit_evaluaciones ON evaluaciones;
CREATE TRIGGER trg_audit_evaluaciones
    AFTER INSERT OR UPDATE OR DELETE ON evaluaciones
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria();
