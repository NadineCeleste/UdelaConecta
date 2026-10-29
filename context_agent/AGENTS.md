# Udela Conecta — contexto para IA

Frontend en **Angular 20** (standalone components, rxjs, zone.js) de una bolsa de trabajo para estudiantes y graduados de la Universidad de la Ciudad de Buenos Aires. Conecta estudiantes (desarrolladores) con empresas (gerentes) a través de proyectos y contratos. El título del HTML es "Huntech". Idioma del código y los comentarios: español.

## Documentación relacionada

Leer según la tarea:

| Archivo | Cuándo leerlo |
|---|---|
| [`context_front.md`](./context_front.md) | Contexto completo del frontend (componentes, servicios, modelos, API). Antes de tocar código |
| [`audit_front.md`](./audit_front.md) | Auditoría general con hallazgos priorizados (S-, B-, Q-, P-, A-, T-, D-) y plan de arreglo. Antes de corregir un error o refactorizar |
| [`endpoint.md`](./endpoint.md) | Auditoría detallada de los endpoints: inventario, flujos, hallazgos E-xx y API propuesta. Antes de tocar servicios HTTP o coordinar con el backend |
| [`CLAUDE.md`](./CLAUDE.md) | Solo importa este archivo (`@AGENTS.md`) para Claude Code |
| [`../README.md`](../README.md) | README del repo (vacío por ahora) |
| [`../AGENTS.md`](../AGENTS.md), [`../CLAUDE.md`](../CLAUDE.md) | Puntos de entrada en la raíz: remiten a este archivo para que los agentes lo carguen al abrir el repo |

## Comandos

```bash
npm install     # instalar dependencias (Node 24 / npm 11 probados)
npm start       # ng serve -> http://localhost:4200
npm run build   # ng build
npm test        # ng test (jasmine/karma)
```

## Estado actual (importante)

- **No hay backend en este repo.** `src/app/environments/environment.ts` apunta a `http://127.0.0.1:3000/api/`. Sin esa API, todas las pantallas que piden datos fallan; la landing sí carga.
- **`src/app/servicios/AuthService.ts` es un mock.** El original no está en el repo. Cualquier email y contraseña inician sesión y el usuario se guarda en `localStorage` (`mock_user`). Los comentarios del código mencionan Supabase (`app.ts`, `authGuard.ts`), pero no hay dependencia ni configuración de Supabase. No se sabe qué usaba el servicio real. Si aparece el original, reemplazar solo ese archivo y mantener la misma interfaz.
- `environment.gests` es una lista de emails (vacía por ahora) que `navbar.ts` usa para activar el flag `isgests`.

## Estructura (`src/app`)

| Carpeta | Contenido |
|---|---|
| `componentes/` | home, navbar, profile, contratos, contrato-detail, miproyecto, portfolio-component, alertas, spinner |
| `views/` | formularios: `formcreateproyect`, `formcreatecontract` |
| `servicios/` | `users`, `contrato`, `miproyecto`, `portfolioService`, `alertService`, `loading-service`, `AuthService` (mock), `guards/authGuard` |
| `models/` | `users/` (usuario, desarrollador, gerente, institucion-educativa), `contrato`, `proyectos`, `cards/` |
| `environments/` | `environment.ts` (apiUrl, bucketUrl, gests) |

## Rutas (`app.routes.ts`)

Públicas: `''` y `home` (Home). Con `authGuard` (requiere sesión): `contratos`, `profile`, `profile/:email`, `miproyecto`, `formcreateproyect[/:email]`, `formcreatecontract[/:project_id]`. Los componentes se cargan con `loadComponent` (lazy).

## Roles y modelo de datos

Hay tres tipos de usuario, cada uno en su propia tabla del backend: `desarrollador`, `gerente`, `institucion_educativa`. Tras el login, `Users.checkUserExists(email)` consulta `GET usuario/:email`, que devuelve `{ data: { existe: 0|1, tabla } }`; un 404 se traduce a "no existe". Con la tabla, `getUsuarioByEmailAndTable` trae el perfil completo y `createUserByRole` lo crea.

## API esperada (relativa a `environment.apiUrl`)

- Usuarios: `GET usuario/:email`, `GET usuario/:email/:tabla`, `PUT usuario/:email`, `POST :rol` (desarrollador | gerente | institucion_educativa), `GET desarrolladores`
- Contratos: `GET contratos`, `GET contratoslibres`, `GET contratos/:emailGerente`, `POST contrato`, `PUT contrato/:id` (postulaciones), `PUT contrato/asignar/:idContrato`, `DELETE contrato/:id`
- Proyectos: `GET proyecto/:email`, `POST proyecto`, `PUT proyecto/:email_gerente`
- Portfolio: `GET portfolio/:email`, `POST createportfolio/:email`, `PUT updateportfolio/:email`, `DELETE deleteportfolio/:email`. Las imágenes se suben y borran directo en `environment.bucketUrl`.

## Convenciones

- Componentes standalone; servicios con `providedIn: 'root'` y `HttpClient` inyectado por constructor. `provideHttpClient()` está en `app.config.ts`.
- Respuestas tipadas con `*Response` (`ContratoResponse`, `ProyectoResponse`, `PostulacionResponse`).
- Notificaciones con `AlertService` (`success | error | info | warning | confirm`); `confirm` resuelve una promesa booleana. El spinner visible depende de `App.cargandoData`; `LoadingService` existe pero ningún template lo muestra.
- Tema claro/oscuro guardado en `localStorage` (`theme`).
- Prettier: `printWidth` 100, comillas simples.
