-- ============================================================
-- 01_extensions.sql
-- Habilitar extensiones necesarias de PostgreSQL
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid(), crypt()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- uuid_generate_v4() (respaldo)
