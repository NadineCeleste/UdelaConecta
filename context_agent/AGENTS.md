# Udela Conecta — contexto para IA

Monorepo **Nx** de una bolsa de trabajo para estudiantes y graduados de la Universidad de la Ciudad de Buenos Aires. Conecta estudiantes y graduados (rol `estudiante`) con empresas (gerentes) a través de proyectos y contratos. El título del HTML es "Huntech". Idioma del código y los comentarios: español.

- `apps/frontend`: **Angular 20** (standalone components, rxjs, zone.js).
- `apps/backend`: **FastAPI** + **SQLAlchemy 2.0 async** (asyncpg) + **Alembic** sobre **PostgreSQL 16**, con JWT propio.
- `infra/local`: todo el stack en Docker con hot-reload. `infra/vps`: producción (Caddy + Nginx + FastAPI + Postgres).

## Documentación relacionada

Leer según la tarea:

| Archivo | Cuándo leerlo |
|---|---|
| [`context_front.md`](./context_front.md) | Contexto completo del frontend (componentes, servicios, modelos, API). Antes de tocar código del front |
| [`audit_front.md`](./audit_front.md) | Auditoría general con hallazgos priorizados (S-, B-, Q-, P-, A-, T-, D-), su estado y el plan de arreglo. Antes de corregir un error o refactorizar |
| [`endpoint.md`](./endpoint.md) | Auditoría detallada de los endpoints: inventario, flujos, hallazgos E-xx y API propuesta. Antes de tocar servicios HTTP o el backend |
| [`backend.md`](./backend.md) | Contexto completo del backend: ciclo de un request, modelo de datos, migraciones, cada endpoint con sus reglas de autorización, utilidades a reutilizar, tests y cómo extender. Antes de tocar `apps/backend` |
| [`orquestacion.md`](./orquestacion.md) | Nx (proyectos, targets, cache, comandos), Docker local con hot-reload, producción en VPS (Caddy, Nginx, workers, backups) y problemas frecuentes. Antes de tocar `nx.json`, `project.json`, `package.json` o `infra/` |
| [`../apps/backend/README.md`](../apps/backend/README.md) | Backend: estructura, variables de entorno, reglas de autorización, migraciones y usuarios demo |
| [`CLAUDE.md`](./CLAUDE.md) | Solo importa este archivo (`@AGENTS.md`) para Claude Code |
| [`../README.md`](../README.md) | README del repo: narrativa del producto (problemática, solución, cómo funciona para cada rol) |
| [`../AGENTS.md`](../AGENTS.md), [`../CLAUDE.md`](../CLAUDE.md) | Puntos de entrada en la raíz: remiten a este archivo para que los agentes lo carguen al abrir el repo |

Las rutas `src/...` que aparecen en los documentos de auditoría corresponden a `apps/frontend/src/...`.

## Comandos

```bash
npm install            # dependencias del workspace (Node 24 / npm 11 probados)
npm start              # stack local en Docker en primer plano (postgres, backend, frontend, adminer)
npm run local:up       # lo mismo en segundo plano; local:down / local:logs / local:ps
npm run serve:front    # solo el front, fuera de Docker (nx serve frontend)
npm run build          # nx build frontend --configuration=production -> dist/apps/frontend/browser
npm run test:front     # Karma/Jasmine en ChromeHeadless
npm run test:back      # pytest (requiere: cd apps/backend && poetry install)
npx nx run backend:migrate  # alembic upgrade head (también backend:seed y backend:serve; no usar "nx migrate", que actualiza Nx)
npm run vps:up         # producción; requiere infra/vps/.env.vps (copiar de .env.vps.example)
```

Stack local: front `http://localhost:4200`, API `http://localhost:3000/api/`, Swagger `http://localhost:3000/docs`, Adminer `http://localhost:8080`, Postgres `localhost:5432` (Postgres y Adminer solo escuchan en `127.0.0.1`). Los puertos del host se cambian con `FRONTEND_PORT`, `POSTGRES_HOST_PORT` y `ADMINER_PORT`. Si se cambia `package.json`, recrear el volumen de `node_modules` con `docker compose -f infra/local/docker-compose.yml down -v`.

Usuarios demo (los crea el seed cuando `AUTO_SEED=true`): `dev@udelaconecta.edu.ar` y `empresa@udelaconecta.edu.ar`, contraseña `Udela1234!`.

## Estado actual (importante)

- **Autenticación real.** `servicios/AuthService.ts` llama a `/api/auth/{login,register,social,reset-password}` y guarda `auth_user` + `auth_token` en `localStorage`; su interfaz pública es la del servicio original. `servicios/interceptors/auth.interceptor.ts` agrega `Authorization: Bearer` a las llamadas a la API y cierra la sesión ante un 401. El login social responde 501 (no implementado) y reset-password no envía mail (no hay SMTP).
- **Autorización en el backend:** todo `/api/*` salvo `/api/auth/*` exige token, y las escrituras validan que el email del recurso sea el del token (ver el README del backend).
- **Imágenes:** `environment.bucketUrl` apunta a `/storage` del backend. `portfolioService` hace `PUT`/`DELETE` con `fetch` y agrega el token a mano.
- Los comentarios del código todavía mencionan Supabase (`app.ts`, `authGuard.ts`); es historia, no hay dependencia.
- **Admin:** `navbar.ts` activa `isgests` con `user.is_admin` (columna `auth_users.is_admin`, solo se cambia desde la base). Ya no existe `environment.gests`.
- **Login:** 5 intentos fallidos seguidos bloquean la cuenta 15 minutos (429).
- **Privacidad:** `telefono` y `fecha_nacimiento` solo los recibe el dueño del perfil.

## Estructura del frontend (`apps/frontend/src/app`)

| Carpeta | Contenido |
|---|---|
| `componentes/` | home, navbar, profile, contratos, contrato-detail, miproyecto, portfolio-component, alertas, spinner |
| `views/` | formularios: `formcreateproyect`, `formcreatecontract` |
| `servicios/` | `users`, `contrato`, `miproyecto`, `portfolioService`, `alertService`, `loading-service`, `AuthService`, `guards/authGuard`, `interceptors/auth.interceptor` |
| `models/` | `users/` (usuario, estudiante, gerente, institucion-educativa), `contrato`, `proyectos`, `cards/` |
| `environments/` | `environment.ts` (dev: `http://localhost:3000/api/`) y `environment.prod.ts` (`/api/`, `/storage`, por `fileReplacements`) |

## Rutas (`app.routes.ts`)

Públicas: `''` y `home` (Home). Con `authGuard` (requiere sesión): `contratos`, `profile`, `profile/:email`, `miproyecto`, `formcreateproyect[/:email]`, `formcreatecontract[/:project_id]`. Los componentes se cargan con `loadComponent` (lazy).

## Roles y modelo de datos

Hay tres tipos de usuario, cada uno en su propia tabla: `estudiante`, `gerente`, `institucion_educativa`. En pantalla el rol `estudiante` se muestra como "Estudiante / graduado"; antes se llamaba `desarrollador` (migración `0003`). Las credenciales están aparte, en `auth_users`. Tras el login, `Users.checkUserExists(email)` consulta `GET usuario/:email`, que devuelve `{ data: { existe: 1, tabla } }` o un 404 que el front traduce a "no existe". Con la tabla, `getUsuarioByEmailAndTable` trae el perfil completo y `createUserByRole` lo crea. Las tablas restantes son `proyecto` (uno por gerente), `contrato` y `portfolio`. Los modelos están en `apps/backend/app/models/entities.py`.

## API (relativa a `environment.apiUrl`)

- Auth: `POST auth/login`, `POST auth/register`, `POST auth/social`, `POST auth/reset-password`
- Usuarios: `GET usuario/:email`, `GET usuario/:email/:tabla`, `PUT usuario/:email`, `POST :rol` (estudiante | gerente | institucion_educativa), `GET estudiantes`
- Contratos: `GET contratos`, `GET contratoslibres`, `GET contratos/:emailGerente`, `POST contrato`, `PUT contrato/:id` (postulaciones), `PUT contrato/asignar/:idContrato`, `DELETE contrato/:id`
- Proyectos: `GET proyecto/:email`, `POST proyecto`, `PUT proyecto/:email_gerente`
- Portfolio: `GET portfolio/:email`, `POST createportfolio/:email`, `PUT updateportfolio/:email`, `DELETE deleteportfolio/:email`
- Storage (fuera de `/api`): `GET|PUT|DELETE /storage/portfolios/:nombre`

## Convenciones

- Front: componentes standalone; servicios con `providedIn: 'root'` y `HttpClient` inyectado por constructor. `provideHttpClient(withInterceptors([authInterceptor]))` en `app.config.ts`. Respuestas tipadas con `*Response` (`ContratoResponse`, `ProyectoResponse`, `PostulacionResponse`).
- Notificaciones con `AlertService` (`success | error | info | warning | confirm`); `confirm` resuelve una promesa booleana. El spinner visible depende de `App.cargandoData`; `LoadingService` existe pero ningún template lo muestra.
- Tema claro/oscuro guardado en `localStorage` (`theme`).
- Prettier: `printWidth` 100, comillas simples.
- Backend: un router por recurso en `app/routers/`. Las escrituras usan `aplicar_cambios` (`app/schemas/serializacion.py`), que aplica solo columnas conocidas y convierte tipos. Todo cambio de esquema va con una migración nueva en `alembic/versions/` (verificar con `alembic check`).
