# Orquestación — Nx, Docker local y VPS

> Cómo se organiza el monorepo con **Nx** y cómo se levantan los servicios con **Docker Compose**, en desarrollo (`infra/local`) y en producción (`infra/vps`). El código de cada app está documentado en [`context_front.md`](./context_front.md) y [`backend.md`](./backend.md).
> Fecha: 2026-10-29 · Nx 24.0.2 · Angular 20.3 · Docker Compose v2.

---

## 1. Mapa del repo

```
UdelaConecta/
  nx.json, tsconfig.base.json, package.json   raíz del workspace Nx (npm)
  apps/
    frontend/   Angular 20   → proyecto Nx "frontend" (project.json)
    backend/    FastAPI      → proyecto Nx "backend"  (project.json, Poetry)
  infra/
    local/      docker-compose.yml + Dockerfiles .dev + .env.local   (desarrollo, hot-reload)
    vps/        docker-compose.prod.yml + Caddy + Nginx + scripts   (producción)
  context_agent/  documentación para agentes
```

No hay `angular.json`: Nx define el proyecto en `apps/frontend/project.json` y usa directo los executors de `@angular/build`. Tener los dos archivos haría que el proyecto quedara definido dos veces.

## 2. Nx

### 2.1 Configuración

- **`nx.json`:**
  - `defaultBase: main`.
  - `namedInputs.production` excluye `*.spec.ts`, `tsconfig.spec.json` y `tests/**`, así que tocar un test no invalida el cache del build.
  - `targetDefaults`: `build` y `test` tienen `cache: true`; `build` depende de `^build`.
- **`tsconfig.base.json`:** opciones estrictas compartidas (`strict`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature`, `noImplicitReturns`…). `apps/frontend/tsconfig.json` las extiende.
- **Paquetes:** `nx@24.0.2` y `@nx/angular@24.0.2`; el peer de esa versión admite `@angular/build` >=20 <23.
- **Daemon y Nx Cloud:** en Docker se desactivan con `NX_DAEMON=false` y `NX_NO_CLOUD=true`. Afuera de Docker el daemon funciona normal.

### 2.2 Proyectos y targets

`npx nx show projects` lista `frontend` y `backend`.

| Proyecto | Target | Executor | Qué hace |
|---|---|---|---|
| `frontend` | `build` | `@angular/build:application` | Genera `dist/apps/frontend/browser`. Configuración por defecto: `production` (reemplaza `environment.ts` por `environment.prod.ts`, hashing, budgets, `fonts: false`). También existe `development` |
| | `serve` | `@angular/build:dev-server` | `0.0.0.0:4200` con `poll: 2000` (necesario para detectar cambios dentro de Docker). Por defecto `development` |
| | `test` | `@angular/build:karma` | Karma + Jasmine |
| `backend` | `serve` | `nx:run-commands` | `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000` |
| | `migrate` | `nx:run-commands` | `poetry run alembic upgrade head` |
| | `seed` | `nx:run-commands` | `poetry run python -m app.seeds.seed_demo` |
| | `test` | `nx:run-commands` | `poetry run pytest -v` |

Los targets del backend corren con `cwd: apps/backend`. Nx no conoce Python: solo ejecuta los comandos de Poetry, así que antes hay que correr `cd apps/backend && poetry install`.

**Budgets del front (producción):**
- `initial`: aviso a partir de 750 kB, error a partir de 1.5 MB.
- `anyComponentStyle`: aviso a partir de 25 kB, error a partir de 50 kB.
- Hoy salen avisos por `home.css`, `profile.css` y `app.css`, que pesan más de 25 kB, pero el build no falla.

### 2.3 Comandos

| Comando | Equivale a |
|---|---|
| `npm run serve:front` | `nx serve frontend` (solo el front, fuera de Docker) |
| `npm run build` | `nx build frontend --configuration=production` |
| `npm run watch` | build de desarrollo en modo watch |
| `npm test` | `nx run-many -t test -p frontend backend` |
| `npm run test:front` | `nx test frontend --watch=false --browsers=ChromeHeadless` (si Chrome no está en el PATH: `CHROME_BIN=/usr/bin/google-chrome`) |
| `npm run test:back` | `nx test backend` |
| `npx nx run backend:migrate` / `backend:seed` / `backend:serve` | targets del backend |
| `npx nx show project <p>` | ver los targets resueltos |
| `npx nx graph` | grafo del workspace |

**Precauciones:**
- `npx nx migrate` **no** corre las migraciones de la base: es el comando de Nx para actualizar Nx. Para la base: `npx nx run backend:migrate`.
- **Cache:** si un `test` o un `build` responde al instante con "cached", es porque no cambiaron sus inputs. Para forzar la ejecución: `--skip-nx-cache`. Para ver la salida completa: `--output-style=static`.
- `npm run ng …` es un alias de `nx` (`"ng": "nx"`), así que `npm run ng serve frontend` también funciona.

## 3. Docker local (`infra/local`)

Todo el stack corre en contenedores con **hot-reload**: el código del host se monta como volumen, así que editar un archivo actualiza el front o el backend sin reconstruir la imagen.

```
navegador ──► :4201/:4200 frontend (nx serve) ──(HTTP desde el navegador)──► :3000 backend (uvicorn --reload)
                                                                                   │
                         adminer :8080 ──────────────────────────────────► postgres :5432 (red interna)
```

El front llama a la API desde el **navegador** (`environment.ts` → `http://localhost:3000/api/`), no desde el contenedor. Por eso el backend publica el puerto 3000 y el CORS incluye el origen del front.

### 3.1 Servicios (`docker-compose.yml`, proyecto `udela-local`)

| Servicio | Imagen / build | Puerto del host | Volúmenes | Notas |
|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | `127.0.0.1:${POSTGRES_HOST_PORT:-5432}` | `pgdata` | Healthcheck `pg_isready` cada 5 s |
| `backend` | `Dockerfile.backend.dev` (python:3.13-slim + Poetry, dependencias en el sistema) | `3000` | `../../apps/backend:/app` (código), `storage:/data/storage` | Espera a que `postgres` esté *healthy*. `CORS_ORIGINS` se arma con `FRONTEND_PORT` |
| `frontend` | `Dockerfile.frontend.dev` (node:24-alpine, usuario `node`, `npm ci` en la imagen) | `${FRONTEND_PORT:-4200}` | `../..:/workspace` (todo el repo), `frontend_node_modules:/workspace/node_modules` | `npx nx serve frontend --poll 2000`. El volumen de `node_modules` evita usar el del host |
| `adminer` | `adminer:latest` | `127.0.0.1:${ADMINER_PORT:-8080}` | — | Servidor por defecto: `postgres` |

Postgres y Adminer solo escuchan en `127.0.0.1` porque la contraseña de desarrollo es conocida.

### 3.2 Arranque del backend (`entrypoint.backend.sh`)

1. `alembic upgrade head`: aplica las migraciones pendientes.
2. Si `AUTO_SEED=true`, corre `python -m app.seeds.seed_demo` (idempotente).
3. `exec uvicorn app.main:app --reload --host 0.0.0.0 --port 3000`.

### 3.3 Variables (`.env.local`, versionado y solo para desarrollo)

`POSTGRES_USER/PASSWORD/DB`, `DATABASE_URL`, `JWT_SECRET_KEY` (de desarrollo, más de 32 caracteres), `STORAGE_DIR=/data/storage` (fuera de `/app` para que no aparezca dentro del código montado), `PUBLIC_STORAGE_BASE_URL`, `AUTO_SEED=true`.

Los puertos del host se cambian con variables de entorno al levantar, no en `.env.local`:

```bash
POSTGRES_HOST_PORT=5433 FRONTEND_PORT=4201 ADMINER_PORT=8081 npm run local:up
```

### 3.4 Comandos

| Comando | Qué hace |
|---|---|
| `npm start` | Levanta todo en primer plano, con `--build` |
| `npm run local:up` / `local:down` | En segundo plano / bajar (conserva los volúmenes) |
| `npm run local:logs` / `local:ps` | Logs en vivo / estado |
| `docker compose -f infra/local/docker-compose.yml --env-file infra/local/.env.local down -v` | Baja y **borra los volúmenes** (base, imágenes y `node_modules`) |
| `docker exec udela-local-backend alembic upgrade head` | Aplicar una migración nueva sin reiniciar |
| `docker restart udela-local-backend` | Reiniciar el backend |

### 3.5 Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `port is already allocated` (5432, 4200, 8080) | Otro proceso usa el puerto: cambiar `POSTGRES_HOST_PORT` / `FRONTEND_PORT` / `ADMINER_PORT`. Si se cambia el puerto del front, el CORS se ajusta solo |
| El front no toma una dependencia nueva de `package.json` | El volumen `frontend_node_modules` quedó con la versión anterior: `down -v` (o borrar solo ese volumen) y `local:up` |
| El backend queda caído después de editar varios archivos de golpe (`ImportError` en `docker logs udela-local-backend`) | `--reload` recargó a mitad del cambio: `docker restart udela-local-backend` |
| `JWT_SECRET_KEY debe ser aleatoria…` al arrancar | El secret tiene menos de 32 caracteres o contiene `CAMBIAR` |
| Hay dos instalaciones de Docker (Docker Desktop y el engine nativo) | Cada una tiene sus propios contenedores y volúmenes: `docker context show` dice cuál se está usando. `docker context use <nombre>` cambia la global; `DOCKER_CONTEXT=<nombre>` solo para un comando |

## 4. Producción en VPS (`infra/vps`)

```
Internet ──► Caddy :80/:443 (HTTPS automático con DOMAIN)
               ├─ /api/*      ──► backend:3000   (uvicorn, 4 workers, usuario no-root)
               ├─ /storage/*  ──► backend:3000
               └─ resto       ──► frontend:80    (nginx con el build de Angular)
                                       backend ──► postgres:5432 (sin puertos publicados)
                      todo en la red bridge udela_vps_net
```

Front, API y storage comparten dominio. Por eso `environment.prod.ts` usa rutas relativas (`/api/`, `/storage`) y no hace falta CORS.

### 4.1 Servicios (`docker-compose.prod.yml`, proyecto `udela-vps`)

| Servicio | Imagen / build | Notas |
|---|---|---|
| `caddy` | `caddy:2-alpine` | Publica 80, 443 y 443/udp. `Caddyfile` montado. Volúmenes `caddy_data` (certificados) y `caddy_config`. `request_body max_size 6MB`, compresión zstd/gzip |
| `frontend` | `Dockerfile.frontend`, multi-stage: node:24 con `npm ci` + `nx build frontend --configuration=production` → `nginx:stable-alpine` | `nginx.frontend.conf`: SPA con `try_files … /index.html`; assets con hash cacheados un año; `index.html` con `no-cache` |
| `backend` | `Dockerfile.backend`: python:3.13-slim, `poetry install --only main` y después desinstala Poetry. Copia solo `app/`, `alembic/` y `alembic.ini`. Usuario `udela` (uid 10001) | Volumen `storage:/data/storage`. Espera a `postgres` *healthy* |
| `postgres` | `postgres:16-alpine` | **Sin `ports`**: solo es accesible dentro de la red. Volumen `pgdata` |

`entrypoint.backend.sh` de producción:
1. corre `alembic upgrade head` **una sola vez**;
2. corre el seed solo si `AUTO_SEED=true`;
3. hace `exec uvicorn … --workers ${WEB_CONCURRENCY:-4} --proxy-headers --forwarded-allow-ips="*"`.

### 4.2 Variables (`infra/vps/.env.vps`, fuera de git)

Se copia de `.env.vps.example` y se completa:
- `DOMAIN`: `:80` sirve HTTP plano; con un dominio real, Caddy obtiene el certificado HTTPS solo.
- `POSTGRES_*` y `DATABASE_URL`.
- `JWT_SECRET_KEY`: generarla con `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`. **El valor de ejemplo hace que el backend no arranque.**
- `PUBLIC_STORAGE_BASE_URL=/storage`, `WEB_CONCURRENCY`, `AUTO_SEED=false`.

El compose usa `${VAR:?mensaje}`: si falta una variable obligatoria, `docker compose` falla antes de levantar nada.

### 4.3 Operación

| Tarea | Comando |
|---|---|
| Primer deploy | `cp infra/vps/.env.vps.example infra/vps/.env.vps` (completar) y `npm run vps:up` |
| Actualizar | `infra/vps/deploy.sh`: `git pull --ff-only`, `up -d --build`, `docker image prune -f` y `ps` |
| Logs / bajar | `npm run vps:logs` / `npm run vps:down` |
| Backup | `infra/vps/backup-db.sh [días]`: genera `pg_dump` comprimido y un `tar.gz` del volumen `storage` en `infra/vps/backups/` (fuera de git) y borra los de más de N días (por defecto 14). Para cron: `0 3 * * * /ruta/al/repo/infra/vps/backup-db.sh 14` |
| Validar la configuración | `docker compose -f infra/vps/docker-compose.prod.yml --env-file infra/vps/.env.vps config --quiet` |

## 5. Local y producción

Los dos usan Docker Compose, pero no son intercambiables: `npm start` y `local:*` solo levantan el entorno local; en el servidor se usan `vps:*` o `deploy.sh`.

| | Local (`infra/local`) | VPS (`infra/vps`) |
|---|---|---|
| Compose | `docker-compose.yml` + `.env.local` | `docker-compose.prod.yml` + `.env.vps` |
| Comandos | `npm start` (primer plano), `local:up/down/logs/ps` | `vps:up/down/logs` o `infra/vps/deploy.sh` (sin Node) |
| Front | `nx serve` con hot-reload | Build de producción servido por nginx |
| API base del front | `http://localhost:3000/api/` (`environment.ts`) | `/api/` (`environment.prod.ts`) |
| Backend | 1 proceso, `--reload`, código montado | 4 workers, imagen inmutable, usuario no-root |
| Postgres | Publicado en `127.0.0.1` | Sin puertos |
| Entrada | Puertos directos por servicio | Solo Caddy (80/443) |
| Seed | `AUTO_SEED=true` | `AUTO_SEED=false` |
| Secretos | `.env.local` versionado (solo para desarrollo) | `.env.vps` fuera de git |

## 6. `.dockerignore` y `.gitignore`

- **`.dockerignore`** deja fuera del contexto de build:
  - `node_modules`, `__pycache__`, `.pytest_cache`, `.venv`;
  - `.git`, `.nx`, `.angular`, `dist`;
  - `apps/backend/storage`, `infra/vps/.env.vps`, `infra/vps/backups`.
- **`.gitignore`** suma a eso:
  - `.nx/` y `dist/`;
  - los cachés de Python y `.venv/`;
  - `apps/backend/storage/`, `infra/vps/.env.vps` e `infra/vps/backups/`.
