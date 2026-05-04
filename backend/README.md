# VigilanceAI — Backend (FastAPI)

Sistema de detección de somnolencia y fatiga mental. El backend **no procesa** señales ni video; recibe el JSON ya calculado por el script local (edge computing) y lo persiste.

---

## Requisitos previos

| Herramienta | Versión mínima |
|-------------|---------------|
| Python | 3.11 |
| PostgreSQL | 16 |
| pip | 23+ |

---

## Instalación

```bash
# 1. Clonar / posicionarse en la carpeta
cd backend

# 2. Crear entorno virtual y activarlo
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración

```bash
# 4. Copiar la plantilla de variables de entorno
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS
```

Editar `.env` con los valores reales:

```env
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/vigilanceai
JWT_SECRET=<secreto generado con: python -c "import secrets; print(secrets.token_hex(32))">
```

---

## Base de datos

### Crear la base de datos en PostgreSQL

```sql
CREATE DATABASE vigilanceai;
```

### Ejecutar los scripts DDL en orden

```bash
psql -U postgres -d vigilanceai -f DDL/01_extensions.sql
psql -U postgres -d vigilanceai -f DDL/02_tables.sql
psql -U postgres -d vigilanceai -f DDL/03_audit_function.sql
psql -U postgres -d vigilanceai -f DDL/04_audit_triggers.sql
psql -U postgres -d vigilanceai -f DDL/05_seed_data.sql
psql -U postgres -d vigilanceai -f DDL/06_seed_superuser.sql
```

| Script | Contenido |
|--------|-----------|
| `01_extensions.sql` | Extensiones `pgcrypto` y `uuid-ossp` |
| `02_tables.sql` | Tablas: `roles`, `permisos`, `rol_permiso`, `usuarios`, `baselines_emg`, `evaluaciones`, `auditoria_log` |
| `03_audit_function.sql` | Función PL/pgSQL `fn_auditoria()` que lee `app.current_user_id` |
| `04_audit_triggers.sql` | Triggers `AFTER INSERT/UPDATE/DELETE` en todas las tablas de negocio |
| `05_seed_data.sql` | Roles (`superadmin`, `administrador`, `medico`), 10 permisos y asignaciones |
| `06_seed_superuser.sql` | Usuario inicial: `superadmin@norvision.pe` / `VigilanceAI#2026!` |

> **⚠️ Cambiar la contraseña del superusuario después del primer login.**

---

## Migraciones con Alembic

Alembic gestiona la evolución del esquema. Los DDL del paso anterior son la referencia SQL; Alembic es la herramienta de migración programática.

```bash
# Generar la migración inicial (después de aplicar los DDL)
alembic revision --autogenerate -m "initial_schema"

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Ver el estado actual
alembic current

# Revertir la última migración
alembic downgrade -1
```

> Los triggers y funciones PL/pgSQL **no** son autogenerados por Alembic; viven en los scripts DDL y deben aplicarse manualmente o mediante una migración custom con `op.execute()`.

---

## Levantar el servidor

```bash
# Desarrollo (con recarga automática)
uvicorn main:app --reload --port 8000

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI interactivo |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/` | Health check |

---

## Arquitectura limpia

```
Backend/
├── DDL/                    Scripts SQL (orden de ejecución: 01 → 06)
├── alembic/                Migraciones programáticas
│   └── versions/           Archivos de migración generados
├── app/
│   ├── config.py           Variables de entorno (Pydantic-Settings)
│   ├── data/
│   │   └── database.py     Motor async, AuditedAsyncSession, fábricas de sesión
│   ├── models/             Entidades SQLAlchemy ORM (mapeo a tablas)
│   ├── dtos/               Esquemas Pydantic v2 (Request / Response)
│   ├── services/           Lógica de negocio (sin conocer FastAPI)
│   ├── routers/            Endpoints FastAPI (equivalente a Controllers en C#)
│   └── utils/
│       ├── jwt_handler.py      Crear y decodificar tokens JWT
│       ├── password_handler.py Hash y verificación bcrypt
│       └── dependencies.py     get_current_user, require_permission, get_db
├── main.py                 Punto de entrada: app FastAPI + CORS + routers
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## Patrón de auditoría (equivalente a SaveChangesAsync en EF Core)

```
Request autenticado
    │
    ▼
dependencies.py → get_db()
    │   AuditedAsyncSession.set_audit_user(user_id)
    │   → SELECT set_config('app.current_user_id', uid, TRUE)
    │
    ▼
Service → db.commit()
    │
    ▼
PostgreSQL trigger fn_auditoria()  [AFTER INSERT/UPDATE/DELETE]
    │   lee current_setting('app.current_user_id', TRUE)
    │   escribe en auditoria_log con OLD / NEW automático
    ▼
auditoria_log (nunca tocada por la aplicación directamente)
```

---

## Endpoints disponibles

### Autenticación (`/auth`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/login` | Obtener JWT |

### Usuarios (`/usuarios`)
| Método | Ruta | Permiso requerido |
|--------|------|------------------|
| GET | `/usuarios/me` | Cualquier usuario autenticado |
| GET | `/usuarios` | `usuario:ver_todos` |
| POST | `/usuarios` | `usuario:gestionar` |
| PUT | `/usuarios/{id}` | `usuario:gestionar` |
| DELETE | `/usuarios/{id}` | `usuario:gestionar` (soft-delete) |

### Evaluaciones (`/evaluaciones`)
| Método | Ruta | Permiso requerido |
|--------|------|------------------|
| POST | `/evaluaciones` | `evaluacion:registrar` |
| GET | `/evaluaciones/mis-evaluaciones` | `evaluacion:ver_propias` |
| GET | `/evaluaciones` | `evaluacion:ver_todas` |
| GET | `/evaluaciones/{id}` | `evaluacion:ver_propias` |

### Baselines EMG (`/baselines`)
| Método | Ruta | Permiso requerido |
|--------|------|------------------|
| POST | `/baselines` | `baseline:registrar` |
| GET | `/baselines/activo` | `baseline:ver_propios` |
| GET | `/baselines/historial` | `baseline:ver_propios` |

---

## Roles y permisos por defecto

| Permiso | médico | administrador | superadmin |
|---------|--------|--------------|------------|
| `evaluacion:registrar` | ✅ | ✅ | ✅ |
| `evaluacion:ver_propias` | ✅ | ✅ | ✅ |
| `evaluacion:ver_todas` | ❌ | ✅ | ✅ |
| `baseline:registrar` | ✅ | ✅ | ✅ |
| `baseline:ver_propios` | ✅ | ✅ | ✅ |
| `baseline:ver_todos` | ❌ | ✅ | ✅ |
| `usuario:gestionar` | ❌ | ✅ | ✅ |
| `usuario:ver_todos` | ❌ | ✅ | ✅ |
| `rol:gestionar` | ❌ | ❌ | ✅ |
| `log:ver` | ❌ | ✅ | ✅ |
