-- ============================================================
-- 05_seed_data.sql
-- Datos iniciales: roles, permisos y asignación rol_permiso
-- ============================================================

-- -----------------------------------------------------------
-- ROLES
-- -----------------------------------------------------------
INSERT INTO roles (nombre_rol, descripcion) VALUES
    ('superadmin',    'Acceso total al sistema sin restricciones'),
    ('administrador', 'Gestión de usuarios, visualización global y configuración'),
    ('medico',        'Registro de evaluaciones y consulta de historial propio')
ON CONFLICT (nombre_rol) DO NOTHING;

-- -----------------------------------------------------------
-- PERMISOS  (código : descripción)
-- -----------------------------------------------------------
INSERT INTO permisos (codigo_permiso, descripcion) VALUES
    ('evaluacion:registrar',      'Enviar JSON de evaluación al sistema'),
    ('evaluacion:ver_propias',    'Ver sus propias evaluaciones'),
    ('evaluacion:ver_todas',      'Ver las evaluaciones de todos los médicos'),
    ('baseline:registrar',        'Registrar una nueva calibración EMG'),
    ('baseline:ver_propios',      'Ver sus propios baselines'),
    ('baseline:ver_todos',        'Ver los baselines de todos los usuarios'),
    ('usuario:gestionar',         'Crear, editar y deshabilitar cuentas de usuario'),
    ('usuario:ver_todos',         'Listar todos los usuarios'),
    ('rol:gestionar',             'Asignar/revocar permisos a roles'),
    ('log:ver',                   'Consultar el log de auditoría')
ON CONFLICT (codigo_permiso) DO NOTHING;

-- -----------------------------------------------------------
-- ROL_PERMISO
-- -----------------------------------------------------------

-- médico: puede registrar evaluaciones + ver las suyas + calibrar
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'medico'
  AND  p.codigo_permiso IN (
       'evaluacion:registrar',
       'evaluacion:ver_propias',
       'baseline:registrar',
       'baseline:ver_propios'
  )
ON CONFLICT DO NOTHING;

-- administrador: todo lo del médico + visión global + gestión de usuarios + logs
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'administrador'
  AND  p.codigo_permiso IN (
       'evaluacion:registrar',
       'evaluacion:ver_propias',
       'evaluacion:ver_todas',
       'baseline:registrar',
       'baseline:ver_propios',
       'baseline:ver_todos',
       'usuario:gestionar',
       'usuario:ver_todos',
       'log:ver'
  )
ON CONFLICT DO NOTHING;

-- superadmin: todos los permisos
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM   roles r, permisos p
WHERE  r.nombre_rol = 'superadmin'
ON CONFLICT DO NOTHING;
