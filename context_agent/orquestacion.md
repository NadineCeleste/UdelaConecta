# Orquestación — Nx, Docker local y VPS

> Cómo se organiza el monorepo con **Nx** y cómo se levantan los servicios con **Docker Compose**, en desarrollo (`infra/local`) y en producción (`infra/vps`). El código de cada app está documentado en [`context_front.md`](./context_front.md) y [`backend.md`](./backend.md).
> Fecha: 2026-10-30 · Nx 24.0.2 · Angular 20.3 · Docker Compose v2.

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
    vps/        docker-compose.prod.yml + Caddy + scripts   (producción)
    n8n/        udela-chatbot.json: export del workflow del asistente (sin credenciales)
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

Para probar el asistente en local se crea `infra/local/.env.chat` (fuera de git, el compose lo carga solo si existe) con `N8N_CHAT_WEBHOOK_URL` y `N8N_CHAT_SECRET`. Sin ese archivo el chat responde "no disponible". El n8n del VPS no llega a `localhost`, así que las herramientas del asistente solo leen datos de producción. Detalle en [`n8n.md`](./n8n.md).

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
duckdns ──► https://www.duckdns.org/update cada 5 min (apunta DOMAIN a la IP del servidor)
Internet ──► Caddy :80/:443 (HTTPS automático con DOMAIN)
               ├─ /api/*      ──► backend:3000   (uvicorn, 4 workers, usuario no-root)
               ├─ /storage/*  ──► backend:3000
               └─ resto       ──► /srv           (build de Angular, servido por el mismo Caddy)
                                       backend ──► postgres:5432 (sin puertos publicados)
                      todo en la red bridge udela_vps_net
```

Front, API y storage comparten dominio. Por eso `environment.prod.ts` usa rutas relativas (`/api/`, `/storage`) y no hace falta CORS. No hay nginx: el mismo Caddy sirve los archivos del front.

**Detrás de un Caddy del host.** Si el servidor ya tiene un Caddy en 80/443 (por ejemplo, con n8n u otros sitios), el de Udela Conecta no puede tomar esos puertos. `setup-env.sh` lo deja con `DOMAIN=:80` (HTTP plano) y publicado solo en `127.0.0.1:8081`:

```
Internet ──► Caddy del host :80/:443 (HTTPS de todos los sitios)
               ├─ otro.dominio             ──► lo que ya sirviera
               └─ <subdominio>.duckdns.org ──► 127.0.0.1:8081 ──► Caddy de Udela (mismo enrutamiento de arriba)
```

### 4.1 Servicios (`docker-compose.prod.yml`, proyecto `udela-vps`)

| Servicio | Imagen / build | Notas |
|---|---|---|
| `duckdns` | `caddy:2-alpine` (solo usa su `wget`) | Llama a la API de DuckDNS con `DUCKDNS_SUBDOMAIN` y `DUCKDNS_TOKEN` cada 5 minutos; `ip=` vacío hace que DuckDNS tome la IP pública de origen. Está *healthy* mientras la última respuesta sea `OK`. El log muestra el resultado, no el token |
| `caddy` | `Dockerfile.caddy`, multi-stage: node:24 con `npm ci` + `nx build frontend --configuration=production` → `caddy:2-alpine` con el build en `/srv` y el `Caddyfile` incluido en la imagen (cambiarlo requiere rebuild, que `deploy.sh` ya hace) | Único punto de entrada: enruta `/api` y `/storage` al backend y sirve el front. SPA: las rutas que no son archivos vuelven a `index.html`; assets cacheados un año (404 si no existen); `index.html` con `no-cache`. Publica `CADDY_HTTP_PORT`/`CADDY_HTTPS_PORT` (80/443 por defecto). Volúmenes `caddy_data` (certificados) y `caddy_config`. `request_body max_size 6MB`, compresión zstd/gzip. Espera a `duckdns` *healthy* para pedir el certificado con el DNS ya actualizado |
| `backend` | `Dockerfile.backend`: python:3.13-slim, `poetry install --only main` y después desinstala Poetry. Copia solo `app/`, `alembic/` y `alembic.ini`. Usuario `udela` (uid 10001) | Volumen `storage:/data/storage`. Espera a `postgres` *healthy* |
| `postgres` | `postgres:16-alpine` | **Sin `ports`**: solo es accesible dentro de la red. Volumen `pgdata` |

`entrypoint.backend.sh` de producción:
1. corre `alembic upgrade head` **una sola vez**;
2. corre el seed solo si `AUTO_SEED=true`;
3. hace `exec uvicorn … --workers ${WEB_CONCURRENCY:-4} --proxy-headers --forwarded-allow-ips="*"`.

### 4.2 Variables (`infra/vps/.env.vps`, fuera de git)

Lo genera `infra/vps/setup-env.sh`: pide el subdominio y el token de DuckDNS y si cargar el seed, genera la contraseña de Postgres (32 caracteres alfanuméricos, para no romper la URI) y la clave JWT (64), arma `DOMAIN` y `CORS_ORIGINS` y escribe el archivo con permisos 600. Si ya existe, pide confirmación antes de sobrescribirlo. A mano, se copia de `.env.vps.example` y se completa:
- `DUCKDNS_SUBDOMAIN` (sin `.duckdns.org`) y `DUCKDNS_TOKEN`: obligatorias.
- `DOMAIN`: `<subdominio>.duckdns.org`; Caddy obtiene el certificado HTTPS solo. Con `:80` sirve HTTP plano.
- `CADDY_HTTP_PORT` / `CADDY_HTTPS_PORT`: dónde se publica Caddy en el host (por defecto `80` y `443`). Si el servidor ya tiene otro proxy en 80/443, `setup-env.sh` los pone en `127.0.0.1:<puerto>` y `127.0.0.1:<puerto+1>` con `DOMAIN=:80`; el proxy del host termina el HTTPS y reenvía el dominio a `127.0.0.1:<puerto>`. El backend no depende del esquema de la request (el storage usa la ruta relativa `/storage`), así que el doble proxy no le afecta.
- `POSTGRES_*` y `DATABASE_URL`.
- `JWT_SECRET_KEY`: generarla con `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`. **El valor de ejemplo hace que el backend no arranque.**
- `PUBLIC_STORAGE_BASE_URL=/storage`, `WEB_CONCURRENCY`, `AUTO_SEED=false`.
- `N8N_CHAT_WEBHOOK_URL` y `N8N_CHAT_SECRET` (opcionales): webhook de producción del asistente en n8n y el valor del header `X-Udela-Secret`. `setup-env.sh` los pide; vacíos, el chat responde "no disponible".
- `CHAT_DATOS_URL`: `https://<subdominio>.duckdns.org/api/chat/datos`, desde donde leen las herramientas del asistente. `setup-env.sh` la completa sola.

El Caddyfile confía en los proxies de rangos privados (`trusted_proxies static private_ranges`) para que, detrás del Caddy del host, `X-Forwarded-For` conserve la IP real del visitante; el límite de mensajes del asistente la usa.

El compose usa `${VAR:?mensaje}`: si falta una variable obligatoria, `docker compose` falla antes de levantar nada.

### 4.3 Operación

| Tarea | Comando |
|---|---|
| Primer deploy | `infra/vps/setup-env.sh` y `infra/vps/deploy.sh` (o `npm run vps:up` si hay Node) |
| Sumar el sitio al Caddy del host (solo en ese modo) | Agregar `<subdominio>.duckdns.org { reverse_proxy 127.0.0.1:8081 }` a `/etc/caddy/Caddyfile`, `caddy validate --config /etc/caddy/Caddyfile` y `systemctl reload caddy`. Hacerlo después del deploy, con el DNS ya actualizado |
| Ver la actualización de DuckDNS | `docker logs udela-vps-duckdns`: cada línea termina en `OK` o `KO` (`KO` = subdominio o token incorrectos) |
| Ver el certificado | Servidor vacío: `docker logs udela-vps-caddy`. Detrás del Caddy del host: `journalctl -u caddy`. Buscar `certificate obtained successfully` |
| Hacer admin a un usuario | `docker exec -it udela-vps-db psql -U udela_prod -d udelaconecta_prod -c "update auth_users set is_admin = true where email = '…';"` |
| Actualizar | `infra/vps/deploy.sh`: `git pull --ff-only`, `up -d --build`, `docker image prune -f` y `ps` |
| Logs / bajar | `npm run vps:logs` / `npm run vps:down` |
| Backup | `infra/vps/backup-db.sh [días]`: genera `pg_dump` comprimido y un `tar.gz` del volumen `storage` en `infra/vps/backups/` (fuera de git) y borra los de más de N días (por defecto 14). Para cron: `0 3 * * * /ruta/al/repo/infra/vps/backup-db.sh 14` |
| Validar la configuración | `docker compose -f infra/vps/docker-compose.prod.yml --env-file infra/vps/.env.vps config --quiet` |

### 4.4 Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `port is already allocated` en `udela-vps-caddy` | Otro programa ocupa 80/443 (`ss -tlnp \| grep -E ':(80\|443)\b'`). Si es un Caddy del host, regenerar `.env.vps` con `setup-env.sh` respondiendo que sí a esa pregunta |
| Caddy no arranca y `duckdns` queda *unhealthy* | DuckDNS responde `KO`: subdominio o token incorrectos en `.env.vps`. Caddy depende de `duckdns` *healthy* |
| Certificado inválido en el navegador | El DNS no apuntaba al servidor cuando se pidió el certificado. Verificar con `nslookup` y reiniciar el Caddy que corresponda |
| `exec /usr/local/bin/entrypoint.sh: no such file or directory` | Los `.sh` llegaron con CRLF (copiados desde Windows o checkout sin `.gitattributes`). El repo los fuerza a LF; clonar con git |
| `setup-env.sh` termina sin crear `.env.vps` | Versiones anteriores al arreglo de `aleatorio()`: con `pipefail`, el SIGPIPE de `tr` cortaba el script. Actualizar el repo |
| Un nginx del sistema toma el puerto 80 al reiniciar | No se usa: `systemctl disable --now nginx` o desinstalarlo |

## 5. Local y producción

Los dos usan Docker Compose, pero no son intercambiables: `npm start` y `local:*` solo levantan el entorno local; en el servidor se usan `vps:*` o `deploy.sh`.

| | Local (`infra/local`) | VPS (`infra/vps`) |
|---|---|---|
| Compose | `docker-compose.yml` + `.env.local` | `docker-compose.prod.yml` + `.env.vps` |
| Comandos | `npm start` (primer plano), `local:up/down/logs/ps` | `vps:up/down/logs` o `infra/vps/deploy.sh` (sin Node) |
| Front | `nx serve` con hot-reload | Build de producción servido por Caddy |
| API base del front | `http://localhost:3000/api/` (`environment.ts`) | `/api/` (`environment.prod.ts`) |
| Backend | 1 proceso, `--reload`, código montado | 4 workers, imagen inmutable, usuario no-root |
| Postgres | Publicado en `127.0.0.1` | Sin puertos |
| Entrada | Puertos directos por servicio | Solo Caddy: 80/443, o `127.0.0.1:8081` detrás del Caddy del host |
| Dominio | `localhost` | `<subdominio>.duckdns.org`, actualizado por el servicio `duckdns` |
| Seed | `AUTO_SEED=true` | `AUTO_SEED=false` |
| Secretos | `.env.local` versionado (solo para desarrollo) | `.env.vps` fuera de git |

## 6. `.dockerignore`, `.gitignore` y `.gitattributes`

- **`.dockerignore`** deja fuera del contexto de build:
  - `node_modules`, `__pycache__`, `.pytest_cache`, `.venv`;
  - `.git`, `.nx`, `.angular`, `dist`;
  - `apps/backend/storage`, `infra/vps/.env.vps`, `infra/vps/backups`.
- **`.gitignore`** suma a eso:
  - `.nx/` y `dist/`;
  - los cachés de Python y `.venv/`;
  - `apps/backend/storage/`, `infra/vps/.env.vps` e `infra/vps/backups/`.
- **`.gitattributes`** fuerza `eol=lf` en los `*.sh`. Con `core.autocrlf=true` en Windows, el checkout los dejaba con CRLF; al construir las imágenes desde esa copia, el shebang quedaba `#!/bin/sh\r` y el contenedor no arrancaba.
