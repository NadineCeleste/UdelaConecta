# Auditoría de endpoints — Udela Conecta

> **Monorepo (2026-10-29):** el frontend se movió a `apps/frontend/`. Toda ruta `src/...` de este documento ahora es `apps/frontend/src/...`; `angular.json` fue reemplazado por `apps/frontend/project.json` (Nx). El backend está en `apps/backend/`.

> **Rol renombrado (2026-10-29):** `desarrollador` pasó a llamarse `estudiante` en todo el sistema: tabla, valor de `rol`, `POST estudiante` y `GET estudiantes` (antes `POST desarrollador` y `GET desarrolladores`), y en la UI se muestra "Estudiante / graduado". Este documento describe el estado anterior y conserva el nombre viejo.



## Estado tras implementar el backend (2026-10-29)

El backend vive en `apps/backend/` (FastAPI + PostgreSQL). Mantiene las 19 rutas del inventario con los mismos sobres de respuesta.

| Hallazgo | Estado | Cómo |
|---|---|---|
| E-01, E-12 (escritura), E-17, E-23 | ✅ Resuelto | Token obligatorio en `/api/*` (salvo `/api/auth/*`); el dueño sale del token |
| E-03 | ✅ Resuelto | `encodeURIComponent` en los servicios |
| E-10 | ✅ Resuelto | `app.ts` distingue error de servidor de "no existe" |
| E-11, E-24 | ✅ Resuelto | La API responde 404 explícito y el front solo trata el 404 como "no tiene" |
| E-16 | ✅ Resuelto | Una sola llamada; postulación idempotente en el servidor (409 si ya está postulado u ocupado), con bloqueo de fila y solo para desarrolladores |
| E-18, E-21 | ✅ Resuelto | `project_id` correcto; guardado de gerente con `Promise.all` |
| E-26, E-27, E-28 | 🟡 Mitigado | `/storage` autenticado con dueño, solo PNG/JPG/GIF/WEBP verificados por contenido y servidos con `nosniff` + CSP `sandbox`; borrar o editar el portfolio limpia en el servidor las imágenes que ya no se usan |

> Fecha: 2026-10-29 · Commit base: `3e29250` · Alcance: los 4 servicios HTTP de `src/app/servicios/` (`users.ts`, `contrato.ts`, `miproyecto.ts`, `portfolioService.ts`), sus modelos (`models/`) y todos los componentes que los llaman.
> Relacionado: [`context_front.md`](./context_front.md) (contexto), [`audit_front.md`](./audit_front.md) (auditoría general del frontend).
> Las referencias `archivo:línea` son relativas a `src/app/`.
>
> **Limitación:** el backend no está en el repo. Todo lo que sigue se deduce de cómo el frontend construye las peticiones y consume las respuestas. Lo que depende del backend se marca como *supuesto*.

---

## 1. Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Rutas distintas del backend | **19** |
| Llamadas al backend en código (métodos de servicio) | **20** (`PUT contrato/:id` se usa desde dos métodos) |
| Operaciones directas al bucket (fuera de la API) | **2** (`PUT` y `DELETE` de imágenes) |
| **Total de llamadas HTTP** | **22** |
| Rutas definidas pero nunca usadas | 2 (`GET contratos`, `GET desarrolladores`) |
| Peticiones con autenticación | **0** |
| Rutas que usan el email como identificador en el path | 11 de 19 |
| Rutas con verbo en el nombre (`create`, `update`, `delete`) | 3 |

### Puntaje del diseño de la API (1 = crítico, 5 = sólido)

| Aspecto | Puntaje | Comentario |
|---|:---:|---|
| Seguridad | 1 | Sin auth; identidad por email en el path; bucket anónimo |
| Consistencia REST | 2 | Tres estilos de ruta mezclados, singular/plural, verbos en rutas |
| Contratos de datos | 2 | `data` a veces array, a veces objeto; formatos de campo variables |
| Atomicidad | 1 | Postulación y borrado de portfolio en varios pasos sin transacción |
| Manejo de errores | 2 | 404 usado como resultado normal; errores 500 tratados como "no existe" |
| Escalabilidad | 2 | Sin paginación ni filtros por query |

### Top 8 acciones

1. **Autenticación por token** y que el backend derive el usuario del token, no del path (E-01).
2. **Diferenciar 404 de errores reales** en `checkUserExists` y en `cargarPortfolio` (E-10, E-24).
3. **Endpoint atómico de postulación** `POST contratos/:id/postulaciones` (E-14).
4. **Unificar el sobre de respuesta** (`data` siempre objeto en recursos únicos, siempre array en colecciones) (E-05).
5. **Arreglar el `PUT proyecto` del gerente sin proyecto**, que lanza `TypeError` (E-19).
6. **Renombrar las rutas de portfolio** a `portfolio/:email` con los verbos HTTP (E-22).
7. **URLs prefirmadas para imágenes** y borrado del lado servidor (E-26).
8. **`encodeURIComponent` en todos los parámetros de path** (E-03).

---

## 2. Arquitectura general

```
 Componente ──► Servicio (HttpClient) ──► environment.apiUrl  ──► API REST (no está en el repo)
                    │                     http://127.0.0.1:3000/api/
                    │
                    └── fetch() ─────────► environment.bucketUrl ──► Bucket S3 (vacío hoy)
```

| Elemento | Estado |
|---|---|
| URL base | `environment.apiUrl` = `http://127.0.0.1:3000/api/` (`environments/environment.ts`). Única para los 4 servicios |
| Versionado | No hay (`/api/` sin `/v1/`) |
| Cliente | `HttpClient` de Angular. Imágenes con `fetch` nativo |
| Interceptores | Ninguno. `app.config.ts:12` solo tiene `provideHttpClient()` |
| Autenticación | Ninguna. No se envía `Authorization` ni cookies |
| Formato | JSON. Respuestas `{ message, count?, data }` |
| Timeouts / reintentos | No hay |
| Entornos | Un solo `environment.ts`; sin `environment.prod.ts` |
| Bucket | `bucketUrl: ''` → las subidas irían a `/portfolios/...` del propio host |

### Sobre de respuesta (tipos del front)

| Tipo | Definición | Usado en |
|---|---|---|
| `ContratoResponse` | `{ message?, count?, data: Contrato[] }` | GET de contratos, `POST contrato`, `PUT contrato/asignar` |
| `PostulacionResponse` | `{ message?, data?: Contrato }` | `PUT contrato/:id` |
| `ProyectoResponse` | `{ message?, count?, data: Proyecto[] }` | Todos los de proyecto |
| `userExistsByEmailResponse` | `{ message, data: { existe: 0\|1, tabla } }` | Declarado en `models/users/usuario.ts` pero **no usado**: `checkUserExists` devuelve `Observable<any>` |
| `{ message, data: Portfolio }` | Interfaz inline en `portfolioService.ts` | `GET portfolio/:email` |
| `any` | — | Resto de usuarios y portfolio |

---

## 3. Inventario completo

### 3.1 Usuarios — `servicios/users.ts`

| # | Método | Ruta | Función | Body | Respuesta esperada | Llamado desde |
|---|---|---|---|---|---|---|
| 1 | GET | `usuario/:email` | `checkUserExists` (`:23`) | — | `{ data: { existe, tabla } }`; **404 = no existe** | `app.ts:158`, `componentes/profile/profile.ts:82` |
| 2 | GET | `usuario/:email/:tabla` | `getUsuarioByEmailAndTable` (`:56`) | — | `{ data: perfil }` con `habilidades[]`, `idiomas[]`, `puesto_actual`, `telefono` | `app.ts:170`, `profile.ts:89` |
| 3 | POST | `:rol` | `createUserByRole` (`:63`) | `{ email }` | sin uso | `app.ts:230` |
| 4 | PUT | `usuario/:email` | `updateUserByRole` (`:71`) | perfil completo | sin uso (hace merge local con `tap`) | `profile.ts:328`, `profile.ts:343` |
| 5 | GET | `desarrolladores` | `getAllDesarrolladores` (`:109`) | — | — | **Nadie** (código muerto) |

### 3.2 Contratos — `servicios/contrato.ts`

| # | Método | Ruta | Función | Body | Respuesta esperada | Llamado desde |
|---|---|---|---|---|---|---|
| 6 | GET | `contratos` | `getContratos` (`:16`) | — | `ContratoResponse` | **Nadie** (código muerto) |
| 7 | GET | `contratoslibres` | `getContratosLibres` (`:22`) | — | `ContratoResponse` (filtra `esta_ocupado = false`, *supuesto*) | `componentes/contratos/contratos.ts:105` |
| 8 | GET | `contratos/:emailGerente` | `getContratosByEmailGerente` (`:28`) | — | `ContratoResponse` | `contratos.ts:107`, `profile.ts:360` |
| 9 | POST | `contrato` | `postContrato` (`:33`) | `Contrato` sin `id` | `ContratoResponse` (solo se lee `message`) | `views/formcreatecontract/formcreatecontract.ts:111` |
| 10a | PUT | `contrato/:id` | `updateContrato` (`:39`) | `{ id, tiene_postulaciones: true }` | `PostulacionResponse` (`data` **objeto**) | `componentes/contrato-detail/contrato-detail.ts:85` |
| 10b | PUT | `contrato/:id` | `postularseAContrato` (`:45`) | `{ postulaciones: email }` (string, no array) | ignorada | `contrato-detail.ts:73` |
| 11 | PUT | `contrato/asignar/:idContrato` | `asignarPostulante` (`:51`) | `{ pasante_email }` | `ContratoResponse` (`data` **array**, se lee `data[0]`) | `contrato-detail.ts:53` |
| 12 | DELETE | `contrato/:id` | `deleteContrato` (`:59`) | — | ignorada | `profile.ts:419` |

### 3.3 Proyectos — `servicios/miproyecto.ts`

| # | Método | Ruta | Función | Body | Respuesta esperada | Llamado desde |
|---|---|---|---|---|---|---|
| 13 | GET | `proyecto/:email` | `getProyectoPorEmail` (`:25`) | — | `ProyectoResponse`; se usa `data[0]` | `componentes/miproyecto/miproyecto.ts:59`, `views/formcreateproyect/formcreateproyect.ts:74`, `profile.ts:137` |
| 14 | POST | `proyecto` | `postProyecto` (`:31`) | `Proyecto` con `email_gerente` | `ProyectoResponse` (solo `message`) | `formcreateproyect.ts:115` |
| 15 | PUT | `proyecto/:email_gerente` | `editProyecto` (`:37`) | `Proyecto` completo | `ProyectoResponse` (solo `message`) | `formcreateproyect.ts:138`, `profile.ts:343` |

### 3.4 Portfolio — `servicios/portfolioService.ts`

| # | Método | Ruta | Función | Body | Respuesta esperada | Llamado desde |
|---|---|---|---|---|---|---|
| 16 | GET | `portfolio/:email` | `getPortfolioByEmail` (`:30`) | — | `{ message, data: Portfolio }` (`data` **objeto**) | `componentes/portfolio-component/portfolio-component.ts:43` |
| 17 | POST | `createportfolio/:email` | `createPortfolio` (`:44`) | 12 campos planos; `imagenesN` normalizado a 3 posiciones | ignorada | `portfolio-component.ts:225` |
| 18 | PUT | `updateportfolio/:email` | `updatePortfolio` (`:141`) | 12 campos planos (sin normalizar en el servicio, sí en el componente) | ignorada | `portfolio-component.ts:149` |
| 19 | DELETE | `deleteportfolio/:email` | `deletePortfolio` (`:78`) | — | ignorada | `portfolio-component.ts:289` |

`existsPortfolio` (`:34`) envuelve el #16 pero **nadie lo llama**.

### 3.5 Bucket (fuera de la API)

| # | Método | URL | Función | Llamado desde |
|---|---|---|---|---|
| B1 | PUT | `${bucketUrl}/portfolios/${Date.now()}_${file.name}` | `uploadImage` (`:62`) | `portfolio-component.ts:245` (en serie, una por archivo) |
| B2 | DELETE | URL guardada en la base | `deleteImage` (`:126`) vía `deleteAllImagesFromPortfolio` (`:88`) | `portfolio-component.ts:284` (en paralelo) |

---

## 4. Flujos que encadenan endpoints

### Login / alta de usuario (`app.ts`)
```
userEmail$ ─► GET usuario/:email ──┬─ existe=1 ─► GET usuario/:email/:tabla ─► setUserProfile({...data, email, rol: tabla})
                                   └─ existe=0 ─► selector de rol ─► POST :rol {email} ─► repite todo el flujo
```
Dos peticiones obligatorias en cada login. La primera solo sirve para averiguar la tabla.

### Perfil ajeno (`profile.ts:82-110`)
`GET usuario/:email` → `GET usuario/:email/:tabla`. Mismo par que el login, para cualquier email de la URL.

### Perfil de gerente (`profile.ts:137`, `:343`, `:360`)
`GET proyecto/:email` + `GET contratos/:email` al cargar. Al guardar: `PUT proyecto/:email` **y** `PUT usuario/:email`.

### Postulación (`contrato-detail.ts:71-100`)
`PUT contrato/:id {postulaciones}` → si OK → `PUT contrato/:id {id, tiene_postulaciones}`. Dos escrituras sobre el mismo recurso.

### Guardar portfolio (`portfolio-component.ts:213-232`)
N × `PUT bucket` (en serie) → `POST createportfolio/:email` o `PUT updateportfolio/:email`.

### Borrar portfolio (`portfolio-component.ts:271-300`)
N × `DELETE bucket` (en paralelo) → `DELETE deleteportfolio/:email`.

---

## 5. Escala de severidad

| Severidad | Criterio |
|---|---|
| 🔴 **Crítica** | Expone o corrompe datos, o rompe un flujo central |
| 🟠 **Alta** | Error funcional visible o riesgo de seguridad relevante |
| 🟡 **Media** | Inconsistencia de contrato que genera errores o dificulta mantener |
| 🟢 **Baja** | Nombres, limpieza, mejoras menores |

---

## 6. Hallazgos transversales

### E-01 🔴 Ningún endpoint está autenticado
- **Dónde:** `app.config.ts:12` (sin interceptor), los 4 servicios.
- **Qué pasa:** la identidad viaja en el path (`PUT usuario/:email`, `PUT updateportfolio/:email`, `DELETE contrato/:id`). Ver S-01 de `audit_front.md`.
- **Impacto:** cualquier cliente que conozca un email o un id puede leer, modificar o borrar datos ajenos.
- **Recomendación:** `HttpInterceptorFn` que agregue `Authorization: Bearer <jwt>`. El backend obtiene el email del token y valida que el recurso le pertenezca. Las rutas de escritura sobre "lo mío" pasan a `me` (por ejemplo `PUT usuarios/me`).

### E-02 🟠 El email como identificador de recurso
- **Dónde:** 11 de 19 rutas (`usuario/*`, `contratos/:emailGerente`, `proyecto/:email*`, todo portfolio).
- **Impacto:** expone datos personales en logs de servidor, proxies e historial del navegador; impide que el usuario cambie de email sin romper relaciones; permite enumerar usuarios (`GET usuario/:email` responde 200/404 según exista).
- **Recomendación:** usar ids (UUID) en las rutas y `me` para el usuario actual. Si se mantiene el email, rate limit en `GET usuario/:email`.

### E-03 🟠 Parámetros de path sin codificar
- **Dónde:** `users.ts:24,57,92`, `contrato.ts:29`, `miproyecto.ts:27,40`, `portfolioService.ts:31,52,79,148`.
- **Qué pasa:** el email se concatena tal cual. `a+b@x.com` puede llegar como `a b@x.com`; `a#b@x.com` se corta en el `#`; un `/` cambia la ruta.
- **Recomendación:** `encodeURIComponent()` en cada parámetro, o un helper `path\`usuario/${email}\`` que lo haga.

### E-04 🟡 Tres estilos de ruta mezclados
| Estilo | Rutas |
|---|---|
| Recurso + id | `usuario/:email`, `contrato/:id`, `proyecto/:email`, `portfolio/:email` |
| Subrecurso o acción en el path | `usuario/:email/:tabla`, `contrato/asignar/:id` |
| Verbo o filtro en el nombre | `createportfolio`, `updateportfolio`, `deleteportfolio`, `contratoslibres` |

Además: singular y plural para el mismo recurso (`contrato` / `contratos`), `:rol` en la raíz, sin prefijo de versión. Ver propuesta en la sección 8.

### E-05 🟠 El campo `data` cambia de forma según el endpoint
- **Dónde:** modelos `models/contrato.ts`, `models/proyectos.ts`; consumo en `contrato-detail.ts:58,91`.
- **Qué pasa:**
  - `PUT contrato/asignar/:id` → `data` es array (`res.data[0]`).
  - `PUT contrato/:id` → `data` es objeto (`this.contrato = res.data`).
  - `GET proyecto/:email` → `data` es array aunque un gerente tiene un solo proyecto (`res.data[0]` en 3 componentes).
  - `GET portfolio/:email` → `data` es objeto.
- **Impacto:** si el backend devuelve array en el `PUT contrato/:id`, `this.contrato` pasa a ser un array y la vista se rompe en silencio.
- **Recomendación:** convención fija. Recurso único → `data: T`. Colección → `data: T[]` + `count`. Documentarlo en un OpenAPI.

### E-06 🟡 Formatos de campo inconsistentes que se normalizan en los componentes
- `postulaciones` y `seniority_deseado` llegan como array, CSV (`"a,b"`), JSON (`"[...]"`) o literal de Postgres (`"{a,b}"`). Se normaliza en tres lugares con lógica distinta: `contratos.ts:121-125`, `contrato-detail.ts:104-124`, `profile.ts:363-386`.
- Nombres distintos entre back y front: `puesto_actual` ↔ `posicion`, `nombre_habilidad`/`nivel_habilidad` ↔ `nombre`/`nivel`, `nombre_idioma`/`nivel_idioma` ↔ `nombre`/`nivel`. El mapeo se hace a mano en `profile.ts:97-108,128-135,303-319`.
- **Recomendación:** que el backend devuelva siempre arrays JSON. Mientras tanto, mapear una sola vez en el servicio con `map()` y exponer modelos del front tipados.

### E-07 🟡 Se usa `PUT` para actualizaciones parciales
- **Dónde:** `PUT contrato/:id` (#10a y #10b mandan 1–2 campos), `PUT contrato/asignar`.
- **Impacto:** semánticamente `PUT` reemplaza el recurso. Si el backend lo implementa así, `{ id, tiene_postulaciones: true }` borraría título, descripción, etc.
- **Recomendación:** `PATCH` para cambios parciales, `PUT` solo con el recurso completo.

### E-08 🟡 Sin paginación, orden ni filtros por query
- **Dónde:** `GET contratoslibres`, `GET contratos/:emailGerente`, `GET contratos`, `GET desarrolladores`.
- **Qué pasa:** se traen todos los registros. El filtrado por texto, modalidad y seniority se hace en el cliente (`contratos.ts` `filtrarContratos`). `ContratoResponse.count` existe pero no hay `page`/`limit`.
- **Recomendación:** `GET contratos?estado=libre&q=&modalidad=&page=&limit=` con `count` total.

### E-09 🟡 Manejo de errores HTTP pobre en los consumidores
- Los handlers tipan el error como `string` y lo concatenan: `'Error ..., ' + e` muestra `[object Object]` (`contrato-detail.ts:66,98`, `profile.ts:146`).
- Varias escrituras no avisan al usuario si fallan (solo `console.error`): 2.º PUT de postulación (`contrato-detail.ts:94`), `DELETE contrato` (`profile.ts:423`), `GET contratos` (`contratos.ts:128`), `GET proyecto` en `miproyecto.ts:66`.
- `hideLoader()` está en `complete`, que no corre si hay error: el loader queda activo (`contratos.ts:131`, `miproyecto.ts:68`).
- **Recomendación:** `HttpErrorResponse` en los handlers, un interceptor de errores que muestre `error.error.message` vía `AlertService`, y `finalize()` para el loader.

---

## 7. Hallazgos por endpoint

### 7.1 Usuarios

#### E-10 🔴 `GET usuario/:email`: un error 500 se trata como "usuario no existe"
- **Dónde:** `app.ts:156-164` (`checkUserExists` del componente).
- **Qué pasa:** el servicio convierte bien el 404 en `existe: 0` y relanza otros errores (`users.ts:32-39`), pero el componente atrapa **cualquier** error y devuelve `{ data: { existe: 0 } }`.
- **Impacto:** si la API cae o responde 500, a un usuario existente se le muestra el selector de rol. Si elige otro rol, `POST :rol` puede crearle un **segundo perfil en otra tabla**.
- **Recomendación:** en el componente, solo tratar como "no existe" el resultado del servicio; ante otros errores, mostrar un error y no ofrecer el selector. En el backend, unicidad del email entre las tres tablas.

#### E-11 🟠 `GET usuario/:email` responde 404 para un resultado esperado
- **Qué pasa:** la API usa 404 para "no hay usuario". El comentario de `users.ts:28-31` lo reconoce como un parche.
- **Impacto:** ensucia la consola y los logs con errores falsos y obliga a cada consumidor a interceptarlo.
- **Recomendación:** reemplazar los #1 y #2 por un único `GET usuarios/me` (con token) que devuelva `200 { rol, ...perfil }` o `404` solo si de verdad no tiene perfil. Elimina además una petición por login.

#### E-12 🟠 `GET usuario/:email/:tabla` expone la estructura interna y permite leer cualquier perfil
- **Qué pasa:** el cliente elige la tabla. Desde `/profile/:email` (`profile.ts:82-110`) cualquier usuario logueado lee el perfil completo de otro, incluidos `telefono` y `fecha_nacimiento`.
- **Riesgo (*supuesto*):** si el backend interpola `:tabla` en SQL sin lista blanca, es una inyección SQL.
- **Recomendación:** que el backend resuelva la tabla. Definir qué campos son públicos y devolver una vista reducida para perfiles ajenos (`GET usuarios/:id/publico`).

#### E-13 🟡 `POST :rol` en la raíz
- **Qué pasa:** la ruta es literalmente `POST desarrollador`, `POST gerente` o `POST institucion_educativa`, en el mismo nivel que `POST contrato` y `POST proyecto`. Si el backend la define como comodín `/:rol` (*supuesto*), según el orden de registro puede capturar `POST /contrato` y `POST /proyecto`.
- Otros problemas:
  - `rol` vacío llega como `POST ${apiUrl}` (B-06 de `audit_front.md`, `app.ts:226`).
  - El comentario de `users.ts:64` dice `'institucion'`, pero la tabla es `institucion_educativa`.
  - La respuesta no se usa: después se vuelve a correr todo el flujo de login (2 GET más).
- **Recomendación:** `POST usuarios { rol }` (email desde el token), validar `rol` contra una lista y devolver el perfil creado.

#### E-14 🟠 `PUT usuario/:email`: payload sin contrato y rol que no viaja
- **Dónde:** `users.ts:71-103`, `profile.ts:328,343`.
- **Qué pasa:**
  - `role` solo se usa para validar en el cliente; **no se envía en la URL**. El backend tiene que volver a averiguar la tabla por el email.
  - El desarrollador envía `...this.perfil` más campos mapeados: viajan también `posicion`, `email`, `rol`, `proyecto` y otros campos de UI.
  - El gerente envía `this.perfil` **sin mapear**: `habilidades` e `idiomas` van en formato del front (`nombre`/`nivel`) y el objeto `proyecto` va anidado.
  - Validación duplicada: `users.ts:82` ya cubre `!segment` y `:87` nunca se ejecuta.
  - El `tap` mezcla el payload (formato back) en `userProfile$` (que espera formato front): tras guardar, el estado global queda con `puesto_actual` y `nombre_habilidad` en vez de `posicion` y `nombre`.
- **Recomendación:** DTO explícito por rol (lista blanca de campos) y `PATCH usuarios/me`. Actualizar el estado con la respuesta del servidor, no con el payload.

#### E-15 🟢 `GET desarrolladores` no se usa
- **Dónde:** `users.ts:109-113`.
- **Recomendación:** borrarlo o, si habrá buscador de talento, rediseñarlo como `GET desarrolladores?skill=&disponible=&page=` con campos públicos.

### 7.2 Contratos

#### E-16 🔴 Postulación en dos `PUT` no atómicos
- **Dónde:** `contrato-detail.ts:71-100`, `contrato.ts:45-49`.
- **Qué pasa:** 1.º `PUT contrato/:id { postulaciones: "email" }` (un string, aunque el modelo dice `string[]`); el backend debe hacer *append* (*supuesto*). 2.º `PUT contrato/:id { id, tiene_postulaciones: true }`.
- **Impacto:** dos postulaciones simultáneas pueden pisarse; si el 2.º falla queda `tiene_postulaciones: false` con postulantes cargados y el usuario no se entera; nada impide postularse dos veces ni postularse a un contrato ocupado; un desarrollador podría mandar cualquier email. Ver B-05 de `audit_front.md`.
- **Recomendación:** `POST contratos/:id/postulaciones` (sin body; email desde el token). El servidor agrega, deduplica, marca `tiene_postulaciones` y devuelve 409 si ya está postulado u ocupado. Para retirarse: `DELETE contratos/:id/postulaciones/me`.

#### E-17 🟠 `PUT contrato/asignar/:id`: acción en el path y sin control de dueño
- **Qué pasa:** cualquiera puede asignar cualquier email a cualquier contrato. No se valida que el email esté entre los postulantes. Devuelve `data` array a diferencia del resto (E-05).
- **Recomendación:** `PATCH contratos/:id { pasante_email }` o `POST contratos/:id/asignacion`. El backend valida que el usuario sea el gerente dueño, que el email esté en `postulaciones` y marca `esta_ocupado`.

#### E-18 🟠 `POST contrato` se envía sin `proyecto_id`
- **Dónde:** `formcreatecontract.ts:46-49` (lee `paramMap.get('id')` pero la ruta es `:project_id`). Ver B-01 de `audit_front.md`.
- **Otros problemas:**
  - Si `start_date` está vacío se completa con la fecha UTC (`:102`), que puede ser el día siguiente en Argentina.
  - No se valida `end_date >= start_date` ni en el front ni (*supuesto*) en el back.
  - El cliente decide `proyecto_id`: un gerente podría crear contratos en proyectos ajenos.
- **Recomendación:** `POST proyectos/:id/contratos` (el proyecto va en la ruta y el backend valida el dueño) y devolver `201` con el contrato creado.

#### E-19 🟡 `GET contratoslibres` y `GET contratos/:emailGerente`: filtros como rutas
- `contratoslibres` es `GET contratos?estado=libre`.
- `contratos/:emailGerente` choca conceptualmente con `contrato/:id` (plural con email, singular con id). Un futuro `GET contratos/:id` sería ambiguo con `contratos/:emailGerente`.
- `GET contratos` (todos, `contrato.ts:16`) no se usa.
- **Recomendación:** `GET contratos?estado=libre`, `GET contratos?gerente=me`, `GET contratos/:id`.

#### E-20 🟡 `DELETE contrato/:id` sin feedback ni reglas
- **Dónde:** `profile.ts:419-424`.
- **Qué pasa:** al tener éxito solo filtra la lista local, sin mensaje. Si falla, solo `console.error`. No hay definición sobre qué pasa con un contrato con pasante asignado o con postulaciones (*supuesto*: borrado físico).
- **Recomendación:** responder `204`; que el backend devuelva `409` si está asignado, o usar borrado lógico (`estado = cancelado`). Mostrar éxito y error con `AlertService`.

### 7.3 Proyectos

#### E-21 🟠 Guardar perfil de gerente sin proyecto lanza `TypeError`
- **Dónde:** `profile.ts:343` → `miproyecto.ts:40`.
- **Qué pasa:** si el gerente no tiene proyecto, `perfil.proyecto` es `undefined` y `editProyecto` evalúa `proyecto.email_gerente` → `TypeError` antes de hacer la petición. Como está en el mismo `await ... && ...`, **el perfil del gerente tampoco se guarda** (y además el 2.º PUT nunca se espera, B-04 de `audit_front.md`).
- **Recomendación:** separar los dos guardados, saltar el del proyecto si no existe y usar `Promise.all`.

#### E-22 🟡 `GET proyecto/:email` devuelve array para un recurso único
- Se usa `res.data[0]` en tres lugares (`miproyecto.ts:62`, `formcreateproyect.ts:84`, `profile.ts:142`). Si el gerente no tiene proyecto, la API (*supuesto*) responde `200` con `data: []`, lo cual es correcto para colecciones pero no para "el proyecto del gerente".
- **Recomendación:** `GET proyectos/me` → `200 { data: Proyecto }` o `404`.

#### E-23 🟡 `POST proyecto` y `PUT proyecto/:email_gerente`: el dueño lo decide el cliente
- `email_gerente` va en el body (`formcreateproyect.ts:94`) y en la URL del PUT. Si `GET proyecto` falla, el componente pasa a modo alta **sin** cargar `email_gerente` (`:99-103`): el POST sale sin dueño.
- El PUT identifica el proyecto por email del gerente, no por id: impide que un gerente tenga más de un proyecto en el futuro.
- `Proyecto.description` (inglés) vs. `descripcion` en el resto de los modelos.
- **Recomendación:** `POST proyectos` (dueño desde el token) y `PATCH proyectos/:id`.

### 7.4 Portfolio

#### E-24 🟠 `GET portfolio/:email`: cualquier error equivale a "no tiene portfolio"
- **Dónde:** `portfolio-component.ts:41-54`, `portfolioService.ts:34-41`.
- **Qué pasa:** `catch { this.portfolio = null }`. Con la API caída, el desarrollador ve "crear portfolio" y, si lo crea, `POST createportfolio` puede fallar por duplicado o pisar datos (*supuesto*).
- Además, la existencia se infiere de `data.id || data.titulo1`: la API parece devolver `200` con un objeto vacío en vez de `404`.
- **Recomendación:** `404` explícito cuando no existe, y que el componente diferencie 404 de otros errores.

#### E-25 🟡 Rutas de portfolio con el verbo en el nombre
- `POST createportfolio/:email`, `PUT updateportfolio/:email`, `DELETE deleteportfolio/:email` repiten lo que ya dice el método HTTP. `GET portfolio/:email` sí sigue el estilo REST.
- La lógica es "upsert": crear y editar mandan el mismo payload.
- **Recomendación:** `GET|PUT|DELETE portfolios/:email` (o `portfolios/me`). Un `PUT` idempotente cubre crear y editar.

#### E-26 🔴 Imágenes: escritura y borrado anónimos en el bucket
- **Dónde:** `portfolioService.ts:62-76,126-139`. Ver S-02 de `audit_front.md`.
- **Qué pasa:** `fetch PUT/DELETE` sin credenciales; el bucket tiene que permitir ambas operaciones a cualquiera. La key usa el nombre original del archivo y no hay validación de tipo ni tamaño.
- **Recomendación:** `POST portfolios/me/imagenes` → devuelve URL prefirmada (PUT, 5 min, `Content-Type` y tamaño fijos); el borrado lo hace el backend al actualizar o borrar el portfolio.

#### E-27 🟠 Borrado de portfolio no atómico y en orden inverso al seguro
- **Dónde:** `portfolio-component.ts:271-300`.
- **Qué pasa:** primero se borran las imágenes del bucket y después el registro. Si falla el `DELETE deleteportfolio`, el portfolio queda en la base apuntando a imágenes que ya no existen. Si falla una sola imagen, `Promise.all` corta y el registro no se borra, pero las otras imágenes ya se borraron.
- `deleteImage` hace `DELETE` sobre **cualquier URL guardada en la base**: si un registro se manipula, el navegador de la víctima envía DELETE a un host arbitrario.
- **Recomendación:** un solo `DELETE portfolios/me`; el backend borra el registro y luego las imágenes (con reintento o tarea en segundo plano).

#### E-28 🟡 Editar portfolio deja imágenes huérfanas
- **Dónde:** `portfolio-component.ts:122-150`, `:240-260`.
- **Qué pasa:** al editar, las imágenes nuevas se suman a las existentes y se corta a 3 (`slice(0, 3)`); las que quedan afuera, o las que el usuario reemplaza, nunca se borran del bucket. `createPortfolio` normaliza en el servicio y `updatePortfolio` no: dos lugares con reglas distintas.
- **Recomendación:** que el backend compare imágenes antes/después y borre las que salen. Normalizar en un solo lugar.

#### E-29 🟢 Modelo de portfolio con campos numerados
- `titulo1..3`, `descripcion1..3`, `repositorio1..3`, `imagenes1..3`: 12 campos para lo que es una lista de 3 proyectos.
- **Recomendación:** `{ proyectos: [{ titulo, descripcion, repositorio, imagenes[] }] }` con máximo 3 validado en el servidor.

---

## 8. Propuesta de API unificada

Convenciones: prefijo `/api/v1`, recursos en plural, ids en el path, `me` para el usuario del token, filtros por query, `PATCH` para cambios parciales, `201`/`204`/`404`/`409` según corresponda.

| Hoy | Propuesta | Notas |
|---|---|---|
| `GET usuario/:email` + `GET usuario/:email/:tabla` | `GET usuarios/me` | Una sola petición; devuelve `rol` + perfil |
| `GET usuario/:email/:tabla` (ajeno) | `GET usuarios/:id` | Solo campos públicos |
| `POST :rol {email}` | `POST usuarios {rol}` | Email desde el token; `409` si ya existe |
| `PUT usuario/:email` | `PATCH usuarios/me` | DTO por rol |
| `GET desarrolladores` | `GET desarrolladores?skill=&page=` | O eliminar |
| `GET contratos` | `GET contratos` | Con paginación |
| `GET contratoslibres` | `GET contratos?estado=libre` | |
| `GET contratos/:emailGerente` | `GET contratos?gerente=me` | |
| `POST contrato` | `POST proyectos/:id/contratos` | Valida dueño del proyecto |
| `PUT contrato/:id {postulaciones}` + `PUT contrato/:id {tiene_postulaciones}` | `POST contratos/:id/postulaciones` | Atómico; `409` si duplicado u ocupado |
| — | `DELETE contratos/:id/postulaciones/me` | Retirar postulación (nuevo) |
| `PUT contrato/asignar/:id` | `PATCH contratos/:id {pasante_email}` | Valida que sea postulante |
| `DELETE contrato/:id` | `DELETE contratos/:id` | `204`; `409` si asignado |
| `GET proyecto/:email` | `GET proyectos/me` · `GET proyectos?gerente=:id` | `data` objeto |
| `POST proyecto` | `POST proyectos` | Dueño desde el token |
| `PUT proyecto/:email_gerente` | `PATCH proyectos/:id` | |
| `GET portfolio/:email` | `GET portfolios/:usuarioId` | `404` si no existe |
| `POST createportfolio` + `PUT updateportfolio` | `PUT portfolios/me` | Upsert idempotente |
| `DELETE deleteportfolio/:email` | `DELETE portfolios/me` | Borra registro + imágenes en el servidor |
| `PUT bucket` (directo) | `POST portfolios/me/imagenes` → URL prefirmada | |
| `DELETE bucket` (directo) | (lo hace el servidor) | |

Resultado: 19 rutas + 2 operaciones directas al bucket pasan a **18 rutas**, todas autenticadas, sin acceso directo al bucket ni peticiones encadenadas en el cliente.

---

## 9. Plan de remediación

### Fase 1 — Solo frontend (sin tocar el backend)
| ID | Acción |
|---|---|
| E-03 | `encodeURIComponent` en todos los parámetros de path |
| E-10 | En `app.ts`, no tratar errores ≠ 404 como "no existe" |
| E-21 | Separar guardado de proyecto y perfil del gerente; `Promise.all` |
| E-18 | `paramMap.get('project_id')` y fecha local por defecto |
| E-24 | Diferenciar 404 de otros errores al cargar el portfolio |
| E-09 | Tipar errores con `HttpErrorResponse`, `finalize()` para el loader, avisos de error en escrituras |
| E-14 | Actualizar `userProfile$` con datos en formato front, no con el payload |
| E-06 | Mover la normalización de `postulaciones`/`seniority_deseado` y el mapeo de habilidades/idiomas a los servicios |
| E-15, E-19 | Borrar `getContratos`, `getAllDesarrolladores` y `existsPortfolio` si no se van a usar |

### Fase 2 — Coordinado con el backend
| ID | Acción |
|---|---|
| E-01 | Auth con token + interceptor; validación de dueño en el servidor |
| E-16 | `POST contratos/:id/postulaciones` atómico |
| E-17 | Asignación validada contra postulantes y dueño |
| E-26, E-27, E-28 | URLs prefirmadas; borrado de imágenes en el servidor |
| E-05 | Convención única del sobre de respuesta |
| E-11, E-12 | `GET usuarios/me` y perfil público reducido |
| E-20 | Reglas de borrado de contratos y respuestas `204`/`409` |

### Fase 3 — Rediseño
| ID | Acción |
|---|---|
| E-04, E-25 | Migrar a la API unificada de la sección 8 bajo `/api/v1` (mantener las rutas viejas mientras tanto) |
| E-02 | Ids en lugar de emails en las rutas |
| E-07 | `PATCH` para cambios parciales |
| E-08 | Paginación y filtros por query |
| E-29 | Portfolio como lista de proyectos |
| — | Especificación OpenAPI como fuente de verdad, con tipos del front generados desde ella |
