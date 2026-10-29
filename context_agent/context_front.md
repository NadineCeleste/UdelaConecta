# Contexto del frontend — Udela Conecta

> Documento de referencia para agentes de IA y desarrolladores. Describe **cómo está hecho hoy** el frontend, no cómo debería estar. Para problemas y mejoras, ver [`audit_front.md`](./audit_front.md).
> Última revisión: 2026-10-29 · commit base `2cc9f54`.

---

## 1. Resumen

| | |
|---|---|
| **Qué es** | Bolsa de trabajo que conecta estudiantes y graduados IT de la Universidad de la Ciudad de Buenos Aires (IFTS N°11) con empresas. Marca visible: **HunTech** / **Udela Conecta**. |
| **Stack** | Angular **20.3** (standalone components, control flow `@if`/`@for` mezclado con `*ngIf`/`*ngFor`), RxJS 7.8, zone.js 0.15, TypeScript 5.9 en modo `strict`, `strictTemplates`. |
| **Build** | `@angular/build:application` (esbuild + Vite dev server). |
| **Tests** | Karma + Jasmine (hoy no compilan, ver auditoría). |
| **Backend** | **No existe todavía.** El front espera una API REST en `http://127.0.0.1:3000/api/`. |
| **Auth** | `AuthService` **simulado** (mock). Los comentarios del código sugieren que originalmente se usó Supabase, pero no hay dependencia ni configuración. |
| **Storage de imágenes** | Bucket tipo S3 vía `fetch` directo (`environment.bucketUrl`, hoy vacío). |
| **Idioma** | Código, comentarios y UI en español (rioplatense). |

---

## 2. Cómo correrlo

```bash
npm install
npm start          # ng serve → http://localhost:4200 (configuración development)
npm run build      # ng build → producción: HOY FALLA por presupuestos de CSS
npm test           # ng test → HOY NO COMPILA (profile.spec.ts importa ./perfil)
```

### Qué se ve sin backend

`app.html` decide qué mostrar según la sesión, **no** el router:

| Estado | Qué se renderiza |
|---|---|
| `cargandoData === true` | Solo `<app-spinner>` |
| Sin `userEmail` | La **landing** embebida en `app.html` (hero, secciones, modales de login/registro/recuperación). El `<router-outlet>` **no** se renderiza. |
| Con `userEmail` pero sin `usuarioRol` | **Selector de rol** (desarrollador / gerente) → `handleCreateUser()` |
| Con `userEmail` y `usuarioRol` | `<app-navbar>` + `<router-outlet>` (la app real) |

Sin backend: la landing funciona. Al iniciar sesión (cualquier email/contraseña con el mock), `checkUserExists` falla → se trata como "no existe" → aparece el selector de rol → crear el usuario falla. **Las pantallas internas (contratos, perfil, etc.) no son alcanzables sin API.**

---

## 3. Arquitectura

```
src/
├── index.html              # fuentes Google (Crimson Text, Outfit, Inter) + Material Icons
├── main.ts                 # bootstrapApplication(App, appConfig)
├── styles.css              # estilos globales (132 líneas)
└── app/
    ├── app.ts / .html / .css   # componente raíz: sesión, landing, modales, selector de rol
    ├── app.config.ts           # provideRouter(routes), provideHttpClient(), zone coalescing
    ├── app.routes.ts
    ├── environments/environment.ts
    ├── componentes/            # componentes de UI y páginas
    ├── views/                  # formularios de alta/edición
    ├── servicios/              # servicios HTTP, estado, alertas, guard
    └── models/                 # clases de dominio (todas con campos opcionales)
public/
└── favicon.ico                 # único asset existente
```

- **Todos los componentes son standalone.** No hay NgModules.
- **No hay interceptors, store (NgRx/signals store) ni resolvers.**
- **Estado global:** `Users.userProfile$` (`BehaviorSubject<any>`) contiene el perfil del usuario logueado con `{ ...datosDeTabla, email, rol }`. Todos los componentes se suscriben a él.
- `App` usa `ViewEncapsulation.None`: sus 2.151 líneas de CSS son globales.
- Inyección mixta: algunos componentes usan `constructor(private x: X)`, otros `inject(X)`.

---

## 4. Flujo de sesión

```
AuthService.userEmail$ ──► App.inicializarDatos()
                            │
                            ├─ email == null → usuarioRol = ''  → landing
                            │
                            └─ email → Users.checkUserExists(email)      GET usuario/:email
                                        │   (404 se traduce a {existe:0})
                                        ├─ existe == 1 → usuarioRol = data.tabla
                                        │               Users.getUsuarioByEmailAndTable  GET usuario/:email/:tabla
                                        │               Users.setUserProfile({...data, email, rol: tabla})
                                        │               → navbar + router-outlet
                                        │
                                        └─ existe == 0 → selector de rol
                                                        App.handleCreateUser()           POST :rol  {email}
                                                        → vuelve a inicializarDatos()
```

- **Roles** (= nombre de tabla en el backend): `desarrollador`, `gerente`, `institucion_educativa` (este último aparece en modelos y en `updateUserByRole`, pero no hay UI para él).
- **`authGuard`** (`servicios/guards/authGuard.ts`): `await authService.session` → si `data.session` existe deja pasar; si no, redirige a `/`.
- **Navbar** redirige a `/home` cuando aparece un usuario y la URL es `/` o `/home`.
- **Logout:** `App.logout()` (navega a `/`) y `Navbar.logout()` (`window.location.href = '/'`).
- **`environment.gests`:** lista de emails "administradores". Si el usuario está en la lista, `Navbar.isgests = true` y aparecen los links `/dashboard` y `/whitelist-email` (rutas que **no existen**).

### `AuthService` (mock) — interfaz que el resto del código espera

| Miembro | Tipo / retorno |
|---|---|
| `user$` | `Observable<User \| null>` |
| `userEmail$` | `Observable<string \| null>` (distinctUntilChanged) |
| `session` | getter → `Promise<{ data: { session: { user } \| null } }>` |
| `signIn(email, pass)` / `signUp(email, pass)` | `Promise<{ data: { user, session }, error }>` |
| `signInWithSocial(provider)` | ídem (mock: loguea `demo@udelar.test`) |
| `resetPassword(email)` | `Promise<{ error }>` |
| `signOut()` | `Promise<void>` |

Persistencia del mock: `localStorage['mock_user']`. **Cualquier reemplazo real debe respetar esta interfaz** (es la forma de la API de Supabase JS).

---

## 5. Rutas (`app.routes.ts`)

| Path | Componente | Guard | Carga |
|---|---|---|---|
| `''` | `Home` | — | eager |
| `home` | `Home` | — | lazy |
| `contratos` | `Contratos` | `authGuard` | lazy |
| `profile` | `ProfileComponent` | `authGuard` | lazy |
| `profile/:email` | `ProfileComponent` (perfil ajeno, solo lectura) | `authGuard` | lazy |
| `miproyecto` | `Miproyecto` | `authGuard` | lazy |
| `formcreateproyect` | `Formcreateproyect` | `authGuard` | lazy |
| `formcreateproyect/:email` | `Formcreateproyect` | `authGuard` | lazy |
| `formcreatecontract` | `Formcreatecontract` | `authGuard` | lazy |
| `formcreatecontract/:project_id` | `Formcreatecontract` | `authGuard` | lazy |

No hay ruta comodín (`**`) ni página 404. Query params usados: `contratos?id=<contratoId>` (preselecciona contrato), `profile?tab=ofertas`. Fragmentos: navbar navega a `/contratos#<seccion>`.

---

## 6. Componentes

### `App` — `app/app.ts` (raíz)
- **Responsabilidad:** orquesta sesión, landing, modales de login / registro / recuperación, selector de rol, tema oscuro, spinner global.
- **Estado:** `cargandoData` (spinner global), `userEmail`, `usuarioRol`, `selectedRole`, `showLoginModal`, `showRegisterModal`, `showForgotPasswordModal`, `confirmationSent`, `resetSent`, `isModoOscuro`, campos `login_*`, `signup_*`, `reset_email`, `searchKeyword`, `searchLocation`.
- **Métodos:** `inicializarDatos`, `checkUserExists`, `getUser`, `handleLogin`, `handleSignUp`, `handleCreateUser`, `handleResetPassword`, `handleSocialLogin('google')`, `logout`, `toggle*Modal`, `closeModals`, `toggleModoOscuro`, `scrollTo(id)`, `handleSearch(tag?)`.
- **Servicios:** `Users`, `AuthService`, `AlertService`, `Router`.

### `Navbar` — `componentes/navbar/`
- Menú principal (responsive), dropdowns por rol, toggle de tema, logout, botón "volver".
- **Mini libro 3D** "¿Qué es HunTech?" (`bookPages`, `bookSpreads`, `bookNext/Prev`, modal).
- `isOnContratos` y `activeFragment` según `NavigationEnd`.
- Outputs `onLogin`, `onRegister` (declarados, no usados por `App`).

### `Home` — `componentes/home/`
- Landing interna (para usuarios logueados): tabs `desarrolladores | empresas`, FAQ acordeón, carrusel de `perks`, links institucionales.
- `irAContratos()` / `irAlPerfil()` navegan a `/profile` según rol; si el rol no corresponde, `alert()` nativo.

### `Contratos` — `componentes/contratos/`
- Listado de ofertas + panel de detalle (`<app-contrato-detail>`).
- **Desarrollador:** `GET contratoslibres`. **Gerente:** `GET contratos/:emailGerente`.
- Normaliza `seniority_deseado` y `postulaciones` (CSV → array) con `toArray()`.
- Clasifica en `createCards()`:
  - `contratosAsignados` — `esta_ocupado` (para devs, solo los propios: `pasante_email === perfil.email`)
  - `contratosPendientes` — el usuario ya se postuló
  - `contratosDisponibles` — el resto
- Filtros: texto (`busqueda` sobre `titulo`), `filtroModalidad`, `filtroSeniority`; `limpiarFiltros()`; drawer de filtros en mobile.
- Mantiene el contrato seleccionado al recargar (por `id`); usa `?id=` para preselección.

### `ContratoDetail` — `componentes/contrato-detail/`
- **Inputs:** `contrato`, `email`, `rol`. **Output:** `contratoAssigned: Contrato | null`.
- **Desarrollador:** `postularse(contrato, email)` → `PUT contrato/:id {postulaciones: email}` y luego `PUT contrato/:id {id, tiene_postulaciones: true}`.
- **Gerente:** lista `postulacionesNormalizadas`, modal por postulante, `verPerfilPostulante()` → `/profile/:email`, `asignarPostulante()` → `PUT contrato/asignar/:id {pasante_email}`.

### `ProfileComponent` — `componentes/profile/`
- **Perfil propio** (desde `userProfile$`) o **ajeno** (`/profile/:email` → `isOwnProfile = false`, consulta `checkUserExists` + `getUsuarioByEmailAndTable`).
- Secciones (`seccionActiva`): `info`, habilidades, idiomas, CV, portfolio, `ofertas` (gerente). Sidebar colapsable.
- **Desarrollador:** edición de datos personales, habilidades (`{nombre, nivel}`), idiomas (`{nombre, nivel}`), disponibilidad (`is_disponible`), CV (solo selección local, no se sube), portfolio (`<app-portfolio-component>`).
- **Gerente:** datos + proyecto (`perfil.proyecto`, de `GET proyecto/:email`), `buscando_devs`, listado de ofertas (`cargarOfertas`) con eliminación (`DELETE contrato/:id` previa confirmación).
- Validaciones de UI: `permitirSoloLetras`, `soloNumeros`, fecha de nacimiento entre 18 y 100 años (`calcularLimitesFechas`).
- `handleUpdate()` transforma al formato del backend (ver §8).

### `PortfolioComponent` — `componentes/portfolio-component/`
- **Input:** `emailDesarrollador`.
- Portfolio fijo de **3 proyectos** (`titulo1..3`, `descripcion1..3`, `repositorio1..3`, `imagenes1..3`), cada uno con **hasta 3 imágenes**.
- Crear (`guardarPortfolio` → `POST createportfolio/:email`), editar (`editarPortfolio` → `PUT updateportfolio/:email`), borrar todo (`eliminarTodoElPortfolio` → DELETE de cada imagen en el bucket + `DELETE deleteportfolio/:email`).
- Imágenes: `FileReader` para previews, subida con `PortfolioService.uploadImage` (PUT directo al bucket). Arrays siempre normalizados a 3 posiciones (`''` si vacío).

### `Miproyecto` — `componentes/miproyecto/`
- Muestra el proyecto del gerente (`GET proyecto/:email`) con links para editarlo (`/formcreateproyect/:email`) o crear contrato (`/formcreatecontract/:id`).

### `Formcreateproyect` — `views/formcreateproyect/`
- Si el gerente ya tiene proyecto → modo edición (`PUT proyecto/:email_gerente`); si no → modo alta (`POST proyecto`). Template-driven forms con `required` / `minlength=3`.

### `Formcreatecontract` — `views/formcreatecontract/`
- Alta de contrato: `tipo`, `titulo`, `descripcion`, `modalidad` (`remoto | presencial | hibrido`), `seniority_deseado` (multi: `Trainee | Junior | Semisenior | Senior`), `start_date`, `end_date`. `POST contrato`. Cancelar → `/profile?tab=ofertas`.

### `Alertas` — `componentes/alertas/`
- Renderiza toasts y el modal de confirmación de `AlertService`. Se monta una vez en `app.html`.

### `Spinner` — `componentes/spinner/`
- Overlay de carga. `spinner.ts` reexporta `SpinnerComponent` como `Spinner`.

---

## 7. Servicios (`app/servicios/`)

Todos con `providedIn: 'root'`. Base URL: `environment.apiUrl`.

| Servicio | Archivo | Métodos |
|---|---|---|
| `Users` | `users.ts` | `checkUserExists`, `getUsuarioByEmailAndTable`, `createUserByRole`, `updateUserByRole`, `getAllDesarrolladores`, `setUserProfile`, `getUserProfileValue`, `userProfile$` |
| `ContratoService` | `contrato.ts` | `getContratos`, `getContratosLibres`, `getContratosByEmailGerente`, `postContrato`, `updateContrato`, `postularseAContrato`, `asignarPostulante`, `deleteContrato` |
| `ProyectoService` | `miproyecto.ts` | `getProyectoPorEmail`, `postProyecto`, `editProyecto` |
| `PortfolioService` | `portfolioService.ts` | `getPortfolioByEmail`, `existsPortfolio`, `createPortfolio`, `updatePortfolio`, `deletePortfolio`, `uploadImage`, `deleteImage`, `deleteAllImagesFromPortfolio` |
| `AlertService` | `alertService.ts` | `success`, `error`, `info`, `warning` (toasts con timeout), `confirm(msg, title): Promise<boolean>` |
| `LoadingService` | `loading-service.ts` | `isLoading` (signal), `showLoader`, `hideLoader` — *ningún template lee `isLoading`* |
| `AuthService` | `AuthService.ts` | mock, ver §4 |
| `authGuard` | `guards/authGuard.ts` | `CanActivateFn` asíncrono |

---

## 8. Modelos y mapeo front ↔ back

### Clases (`app/models/`, todos los campos opcionales)

- **`Usuario`**: `id, email, descripcion, nombre, apellido, name`
  - **`Desarrollador`** extends: `fecha_nacimiento, rol, skills[], created_at, verificado`
  - **`Gerente`** extends: `id_proyecto`
  - **`InstitucionEducativa`** extends: (sin campos)
- **`userExistsByEmailResponse`**: `{ message, data: { existe: 0|1, tabla } }`
- **`Contrato`**: `id:number, tipo, titulo, descripcion, tiene_postulaciones, postulaciones:string[], esta_ocupado, pasante_email, proyecto_id:string, start_date, end_date, modalidad, seniority_deseado:string[]`
- **`ContratoResponse`**: `{ message, count, data: Contrato[] }` · **`PostulacionResponse`**: `{ message, data: Contrato }`
- **`Proyecto`**: `id, nombre, description, info_link, buscando_devs (default true), contratos[], id_gerente, email_gerente`
- **`ProyectoResponse`**: `{ message, count, data: Proyecto[] }`
- **`Portfolio`** (en `portfolioService.ts`): `id, titulo1..3, descripcion1..3, repositorio1..3, imagenes1..3: string[]`
- **`Card` / `ContratoCard`**: tipos de tarjeta (legacy).

### Campos que el perfil usa pero no están en los modelos
`telefono`, `puesto_actual`, `habilidades`, `idiomas`, `is_disponible`, `proyecto` (gerente), `rol`.

### Transformaciones
| Front | Back | Dónde |
|---|---|---|
| `perfil.posicion` | `puesto_actual` | `profile.ts` (`ngOnInit` / `handleUpdate`) |
| `habilidades[{nombre, nivel}]` | `habilidades[{nombre_habilidad, nivel_habilidad}]` | ídem |
| `idiomas[{nombre, nivel}]` | `idiomas[{nombre_idioma, nivel_idioma}]` | ídem |
| `postulaciones: string[]` | puede llegar como string CSV | `contratos.ts`, `contrato-detail.ts` |
| `seniority_deseado: string[]` | puede llegar como CSV, JSON `[...]` o array Postgres `{...}` | `contratos.ts`, `profile.ts` |
| `imagenesN: string[]` | siempre 3 posiciones, `''` si vacío | `portfolioService.ts`, `portfolio-component.ts` |

Niveles: habilidades `principiante | …` (default `principiante`); idiomas `A1 - Principiante | …` (default `A1 - Principiante`).

---

## 9. Contrato de API esperado

Base: `environment.apiUrl` = `http://127.0.0.1:3000/api/`. Sin headers de autenticación. Los emails van en el path **sin codificar**.

| Método | Path | Body | Respuesta esperada | Llamado desde |
|---|---|---|---|---|
| GET | `usuario/:email` | — | `{data:{existe, tabla}}`, 404 si no existe | `Users.checkUserExists` |
| GET | `usuario/:email/:tabla` | — | `{data: perfil}` | `Users.getUsuarioByEmailAndTable` |
| POST | `:rol` (`desarrollador`/`gerente`/`institucion_educativa`) | `{email}` | — | `Users.createUserByRole` |
| PUT | `usuario/:email` | perfil completo | — | `Users.updateUserByRole` |
| GET | `desarrolladores` | — | lista | `Users.getAllDesarrolladores` (sin uso) |
| GET | `contratos` | — | `ContratoResponse` | `ContratoService.getContratos` (sin uso) |
| GET | `contratoslibres` | — | `ContratoResponse` (`esta_ocupado = false`) | Contratos (dev) |
| GET | `contratos/:emailGerente` | — | `ContratoResponse` | Contratos, Profile (gerente) |
| POST | `contrato` | `Contrato` | `ContratoResponse` | Formcreatecontract |
| PUT | `contrato/:id` | `Contrato` parcial | `PostulacionResponse` | ContratoDetail |
| PUT | `contrato/:id` | `{postulaciones: email}` | `PostulacionResponse` | ContratoDetail (postularse) |
| PUT | `contrato/asignar/:id` | `{pasante_email}` | `ContratoResponse` | ContratoDetail (asignar) |
| DELETE | `contrato/:id` | — | — | Profile (ofertas) |
| GET | `proyecto/:email` | — | `ProyectoResponse` | Profile, Miproyecto, Formcreateproyect |
| POST | `proyecto` | `Proyecto` | `ProyectoResponse` | Formcreateproyect |
| PUT | `proyecto/:email_gerente` | `Proyecto` | `ProyectoResponse` | Formcreateproyect, Profile |
| GET | `portfolio/:email` | — | `{message, data: Portfolio}` | PortfolioComponent |
| POST | `createportfolio/:email` | Portfolio (sin id) | — | PortfolioComponent |
| PUT | `updateportfolio/:email` | Portfolio (sin id) | — | PortfolioComponent |
| DELETE | `deleteportfolio/:email` | — | — | PortfolioComponent |
| PUT | `${bucketUrl}/portfolios/<timestamp>_<nombre>` | archivo binario | 2xx | `PortfolioService.uploadImage` |
| DELETE | `<url de imagen>` | — | 2xx | `PortfolioService.deleteImage` |

---

## 10. UI y estilos

- **Tema oscuro:** clase `dark-theme` en `<body>`, persistida en `localStorage['theme']` (`'dark' | 'light'`). La gestionan tanto `App` como `Navbar`.
- **Fuentes:** `index.html` carga Crimson Text, Outfit e Inter; varios CSS hacen `@import` de Plus Jakarta Sans + Inter.
- **Íconos:** Material Icons y Material Icons Outlined (`<span class="material-icons-outlined">nombre</span>`).
- **CSS:** `app.css` (global por `ViewEncapsulation.None`), `styles.css` (global) y CSS por componente (algunos de 20–40 KB).
- **Assets:** se sirven desde `public/` (hoy solo `favicon.ico`). El código referencia `assets/logo-ifts11.jpg` y `/assets/ifts-navbar.jpg`, que no existen.
- **Feedback al usuario:** siempre vía `AlertService` (excepto `Home`, que usa `alert()`).

---

## 11. Convenciones y gotchas para agentes

1. **Escribir en español** (nombres de métodos, variables, comentarios y textos de UI), siguiendo el estilo existente (`mostrarTodosLosContratos`, `cargarOfertas`, `rolActual`, `perfil`).
2. **El perfil se lee de `Users.userProfile$`**, nunca de `AuthService`. El rol está en `perfil.rol`.
3. **Respetar la interfaz de `AuthService`** (§4) si se reemplaza el mock.
4. **Normalizar CSV ↔ array** siempre que se lean `postulaciones` o `seniority_deseado`.
5. **Archivos con nombres no estándar:** `servicios/AuthService.ts` (PascalCase), `servicios/miproyecto.ts` (exporta `ProyectoService`), `servicios/contrato.ts` (exporta `ContratoService`), `servicios/users.ts` (exporta `Users`), `componentes/alertas/alertas..css` (doble punto).
6. **Formularios:** template-driven con `[(ngModel)]` + `NgForm`; `Profile` importa `ReactiveFormsModule` pero no lo usa.
7. **Carga:** el spinner que realmente se ve es `App.cargandoData`; `LoadingService` no tiene efecto visual.
8. **Al agregar rutas**, protegerlas con `authGuard` y cargarlas con `loadComponent`.
9. **Prettier** (`package.json`): `printWidth: 100`, `singleQuote: true`, parser `angular` para `.html`. No hay ESLint.
10. **No commitear** claves de Supabase ni URLs de bucket reales en `environment.ts`.
