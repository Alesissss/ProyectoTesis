-- ============================================================
-- 06_seed_superuser.sql
-- Inserta el superusuario inicial del sistema.
-- IMPORTANTE: Cambiar la contraseña después del primer login.
--
-- Contraseña por defecto: VigilanceAI#2026!
-- Hash generado con pgcrypto bcrypt (rounds=12).
-- Compatible con passlib[bcrypt] de Python.
-- ============================================================

INSERT INTO usuarios (
    id_usuario,
    nombre,
    apellido,
    email,
    password_hash,
    id_rol
)
SELECT
    gen_random_uuid(),
    'Super',
    'Admin',
    'superadmin@norvision.pe',
    crypt('VigilanceAI#2026!', gen_salt('bf', 12)),
    r.id_rol
FROM roles r
WHERE r.nombre_rol = 'superadmin'
ON CONFLICT (email) DO NOTHING;

-- Verificar inserción
SELECT
    u.id_usuario,
    u.nombre || ' ' || u.apellido AS nombre_completo,
    u.email,
    r.nombre_rol,
    u.fecha_registro
FROM  usuarios u
JOIN  roles    r ON r.id_rol = u.id_rol
WHERE u.email = 'superadmin@norvision.pe';
