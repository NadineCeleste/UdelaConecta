# Backend — Udela Conecta

FastAPI + SQLAlchemy 2.0 async (asyncpg) + Alembic sobre PostgreSQL 16. Implementa las rutas que consume `apps/frontend` (ver `context_agent/endpoint.md`) más la autenticación JWT y el storage de imágenes. El contexto completo (arquitectura, modelo y endpoints) está en [`context_agent/backend.md`](../../context_agent/backend.md); Nx y Docker, en [`context_agent/orquestacion.md`](../../context_agent/orquestacion.md).

## Correr

Con Docker (recomendado), desde la raíz: `npm run local:up`. El contenedor corre `alembic upgrade head`, aplica el seed si `AUTO_SEED=true` y levanta uvicorn con `--reload`.

Sin Docker (requiere un Postgres accesible):

```bash
cd apps/backend
poetry install
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))') DATABASE_URL=postgresql+asyncpg://udela:udela_local_pass@localhost:5432/udelaconecta STORAGE_DIR=./storage
poetry run alembic upgrade head
poetry run python -m app.seeds.seed_demo
poetry run uvicorn app.main:app --reload --port 3000
```

Tests: `poetry run pytest -v` (o `npx nx test backend`). Usan SQLite en memoria, no necesitan Postgres.

## Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://udela:udela_local_pass@postgres:5432/udelaconecta` | Conexión |
| `JWT_SECRET_KEY` | — (obligatoria) | Firma de los tokens; mínimo 32 caracteres y sin el valor de ejemplo, si no el backend no arranca |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / 7 días | |
| `STORAGE_DIR` | `/app/storage` (en Docker: `/data/storage`) | Carpeta de las imágenes |
| `PUBLIC_STORAGE_BASE_URL` | `http://localhost:3000/storage` | Base de la URL que devuelve la subida |
| `MAX_IMAGE_BYTES` | 5 MB | Tamaño máximo por imagen |
| `LOGIN_MAX_INTENTOS` | 5 | Intentos fallidos seguidos antes de bloquear la cuenta |
| `LOGIN_BLOQUEO_MINUTOS` | 15 | Duración del bloqueo (el login responde 429) |
| `CORS_ORIGINS` | `http://localhost:4200` | Orígenes permitidos, separados por coma |
| `AUTO_SEED` | `false` | Si el entrypoint corre el seed |
| `WEB_CONCURRENCY` | 4 | Workers de uvicorn en producción |

## Estructura

```
app/
  main.py              FastAPI, CORS, routers, GET /api/health
  core/                config, database (get_db), security (JWT, bcrypt, dependencias), storage
  models/entities.py   tablas (JSONB en Postgres, JSON en SQLite)
  schemas/             requests de Pydantic y serialización/aplicación de cambios
  routers/             auth, usuarios, proyectos, contratos, portfolio, storage
  seeds/seed_demo.py   datos demo idempotentes
alembic/versions/      migraciones (0001 esquema inicial, 0002 bloqueo de login y admin, 0003 desarrollador → estudiante)
tests/                 pytest + httpx
```

## Autorización

Todo `/api/*` exige `Authorization: Bearer <token>`, salvo `/api/auth/*`. Las reglas de dueño usan el email del token:

- `PUT usuario/:email`, `POST :rol`, `PUT proyecto/:email`, `createportfolio`/`updateportfolio`/`deleteportfolio`: solo sobre el propio email.
- `POST proyecto`: solo un gerente, y una sola vez; el dueño sale del token.
- `POST contrato`: el `proyecto_id` tiene que ser del gerente del token.
- `PUT contrato/:id`: `{postulaciones: email}` solo con el propio email; da 409 si ya está postulado o el contrato está ocupado. `tiene_postulaciones` lo calcula el servidor. Cualquier otro campo, solo el gerente dueño.
- `PUT contrato/asignar/:id` y `DELETE contrato/:id`: solo el gerente dueño; solo se puede asignar a alguien que se postuló.
- `/storage/portfolios/:nombre`: `GET` es público; `PUT` y `DELETE` exigen token, y solo quien subió el archivo puede pisarlo o borrarlo. Solo se aceptan `.png`, `.jpg`, `.jpeg`, `.gif` y `.webp` cuyo contenido coincida con el formato (415 si no); se sirven con `X-Content-Type-Options: nosniff` y `Content-Security-Policy: default-src 'none'; sandbox`.
- Postularse (`PUT contrato/:id` con `postulaciones`) exige perfil de estudiante; postulación y asignación bloquean la fila del contrato.

`PUT usuario/:email` ignora los campos que no son columnas (el front manda el perfil completo). Copia `posicion` a `puesto_actual` y normaliza `habilidades`/`idiomas` al formato `{nombre_habilidad, nivel_habilidad}` / `{nombre_idioma, nivel_idioma}`.

- `telefono` y `fecha_nacimiento` solo se devuelven al dueño del perfil (`GET usuario/:email/:tabla`, `GET estudiantes`).
- Administradores: `auth_users.is_admin` viaja en `data.user` del login. Registrarse no lo activa; se cambia desde la base, por ejemplo en Adminer: `UPDATE auth_users SET is_admin = true WHERE email = '...';`. Para destrabar una cuenta bloqueada: `UPDATE auth_users SET locked_until = NULL, failed_logins = 0 WHERE email = '...';`.

## Usuarios demo

`dev@udelaconecta.edu.ar` (estudiante con portfolio) y `empresa@udelaconecta.edu.ar` (gerente con el proyecto "Plataforma FinTech Udela" y 3 contratos: uno libre, uno con postulación y uno asignado). La contraseña de los dos es `Udela1234!`.
