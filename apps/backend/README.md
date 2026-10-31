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
| `N8N_CHAT_WEBHOOK_URL` | vacía | Webhook de producción del workflow del asistente en n8n. Vacía: `POST /api/chat` responde 503 |
| `N8N_CHAT_SECRET` | vacía | Valor del header `X-Udela-Secret` (el mismo de la credencial Header Auth de n8n) |
| `N8N_CHAT_TIMEOUT_SEGUNDOS` | 60 | Espera máxima de la respuesta de n8n (si no, 502) |
| `CHAT_MENSAJES_POR_MINUTO` | 20 | Límite por usuario o IP, por worker (429) |
| `CHAT_DATOS_URL` | vacía | URL pública de `/api/chat/datos` que se le pasa a n8n para sus herramientas (n8n tiene un respaldo con la de producción) |
| `CHAT_TOKEN_MINUTOS` | 5 | Duración del token de solo lectura que reciben las herramientas del asistente |

En local, las dos variables de n8n van en `infra/local/.env.chat` (opcional y fuera de git), que el compose carga si existe.

## Estructura

```
app/
  main.py              FastAPI, CORS, routers, GET /api/health
  core/                config, database (get_db), security (JWT, bcrypt, dependencias), storage
  models/entities.py   tablas (JSONB en Postgres, JSON en SQLite)
  schemas/             requests de Pydantic y serialización/aplicación de cambios
  routers/             auth, usuarios, proyectos, contratos, portfolio, storage, chat, chat_datos
  seeds/seed_demo.py   datos demo idempotentes
alembic/versions/      migraciones (0001 esquema inicial, 0002 bloqueo de login y admin, 0003 desarrollador → estudiante)
tests/                 pytest + httpx
```

## Autorización

Todo `/api/*` exige `Authorization: Bearer <token>`, salvo `/api/auth/*`, `POST /api/chat` (el token es opcional: sin él responde el asistente de invitados) y `/api/chat/datos/*`, que no acepta el token de sesión sino el token corto del asistente (`aud=udela-chat`) y es de solo lectura (`ofertas` es pública). Detalle en [`context_agent/n8n.md`](../../context_agent/n8n.md). Las reglas de dueño usan el email del token:

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

Todos con la contraseña `Udela1234!`. Hay 6 estudiantes y 4 empresas con 11 ofertas (9 libres), variadas en modalidad, seniority y skills, para probar la plataforma y el asistente:

| Email | Rol | Qué tiene |
|---|---|---|
| `dev@udelaconecta.edu.ar` | Estudiante | Angular, Python y SQL; portfolio de 2 proyectos; postulada en FinTech y SaludConecta, asignada a "QA de la app móvil" |
| `lucas.fernandez@udelaconecta.edu.ar` | Estudiante | React y TypeScript; portfolio de 3 proyectos; postulado en SaludConecta |
| `camila.rios@udelaconecta.edu.ar` | Estudiante | Python, Pandas, SQL y Power BI; postulada a las dos ofertas de datos |
| `tomas.acosta@udelaconecta.edu.ar` | Estudiante | Flutter y Dart; postulado en RutaSur |
| `julieta.medina@udelaconecta.edu.ar` | Estudiante | Docker, Linux y GitHub Actions; postulada en AgroData y RutaSur |
| `martina.sosa@udelaconecta.edu.ar` | Estudiante | QA y análisis funcional; no disponible (asignada en RutaSur) y sin portfolio |
| `empresa@udelaconecta.edu.ar` | Empresa | Plataforma FinTech Udela: 4 ofertas (frontend, backend, QA asignada y data analyst) |
| `agrotech@udelaconecta.edu.ar` | Empresa | AgroData Pampa: Python para IoT y Data Engineer |
| `salud@udelaconecta.edu.ar` | Empresa | SaludConecta: frontend React y soporte/QA |
| `logistica@udelaconecta.edu.ar` | Empresa | RutaSur Logística: Flutter, DevOps y analista funcional (asignada) |

