# Auditoría del frontend — Udela Conecta

> **Monorepo (2026-10-29):** el frontend se movió a `apps/frontend/`. Toda ruta `src/...` de este documento ahora es `apps/frontend/src/...`; `angular.json` fue reemplazado por `apps/frontend/project.json` (Nx). El backend está en `apps/backend/`.

> **Rol renombrado (2026-10-29):** `desarrollador` pasó a llamarse `estudiante` en todo el sistema: tabla, valor de `rol`, `POST estudiante` y `GET estudiantes` (antes `POST desarrollador` y `GET desarrolladores`), y en la UI se muestra "Estudiante / graduado". Este documento describe el estado anterior y conserva el nombre viejo.



> **Asistente (2026-10-31):** nuevo componente `componentes/chatbot` y servicio `chat.service.ts`, con specs propios. No resuelve ni modifica hallazgos de esta auditoría. Ver [`n8n.md`](./n8n.md).

## Estado tras la migración a monorepo (2026-10-29)

| Hallazgo | Estado | Cómo |
|---|---|---|
| S-01 | ✅ Resuelto | JWT propio (`/api/auth/*`) + `authInterceptor`; el backend exige token y valida dueño en cada escritura |
| S-06 | 🟡 Mitigado | El backend rechaza las acciones de otro rol o de otro dueño; la UI todavía deja entrar por URL (falta `roleGuard`) |
| S-02 | 🟡 Mitigado | El bucket se reemplazó por `/storage/portfolios/*` del backend: subir/borrar exige token y solo el dueño puede pisar o borrar |
| S-03 | 🟡 Mitigado | El servidor acepta solo PNG/JPG/GIF/WEBP por extensión y firma del contenido, hasta 5 MB, y los sirve con `nosniff` + CSP `sandbox` (el front sigue sin validar antes de subir) |
| S-04 | ✅ Resuelto | `encodeURIComponent` en los parámetros de path de los servicios |
| S-07 | ✅ Resuelto | Se eliminó el mock; la sesión es `auth_user` + `auth_token` |
| B-01 | ✅ Resuelto | `paramMap.get('project_id')` y botón "Nueva oferta" con `rutaNuevaOferta` (sin proyecto lleva a crear proyecto) |
| B-03, B-04, B-06, B-07 | ✅ Resuelto | Ver diffs en `miproyecto.ts`, `profile.ts`, `app.ts` |
| B-05 | ✅ Resuelto | Una sola llamada (`PUT contrato/:id` con `postulaciones`); el servidor deduplica, bloquea la fila, valida el email del token y deriva `tiene_postulaciones` |
| P-01 | ✅ Resuelto | Budgets ajustados e inlining de fuentes desactivado; `nx build frontend` pasa (quedan avisos de CSS de más de 25 kB) |
| Q-11 | ✅ Resuelto | `environment.prod.ts` con `fileReplacements` |
| T-01 | ✅ Resuelto | Specs actualizados; `nx test frontend` pasa (8 tests) |

### Hallazgos de la auditoría posterior a la migración (2026-10-29)

| Hallazgo | Estado | Cómo |
|---|---|---|
| XSS persistente por `/storage` (un `.html`/`.svg` con `Content-Type: image/*` se servía como ejecutable en el mismo dominio) | ✅ Resuelto | Lista blanca de extensiones, verificación de *magic bytes*, tipo servido desde la lista blanca, `nosniff` y CSP `sandbox` |
| El perfil de un gerente sin proyecto rompía el template (`perfil.proyecto.*`) | ✅ Resuelto | Bloques con `*ngIf="perfil.proyecto"` y tarjeta "Crear proyecto" |
| Carrera en postulación y asignación (se perdían postulaciones simultáneas) | ✅ Resuelto | `SELECT ... FOR UPDATE` del contrato |
| Gerentes o instituciones podían postularse | ✅ Resuelto | La postulación exige perfil de desarrollador |
| Borrar el portfolio se trababa si fallaba el borrado de una imagen | ✅ Resuelto | El front solo llama a `deleteportfolio`; el servidor limpia las imágenes |
| Producción arrancaba con el `JWT_SECRET_KEY` de ejemplo | ✅ Resuelto | Validación: mínimo 32 caracteres y sin `CAMBIAR` |
| El backup no incluía las imágenes | ✅ Resuelto | `backup-db.sh` también archiva el volumen `storage` |
| Nombres de archivo con `#`, `?`, `%` o acentos rompían la URL | ✅ Resuelto | Se reemplazan por `_` antes de subir |
| Imágenes borradas antes del commit del portfolio | ✅ Resuelto | Commit explícito antes de tocar el disco |
| Un 401 dejaba al usuario en la ruta protegida | ✅ Resuelto | El interceptor navega a `/` |
| Spinner trabado si fallaba la carga del perfil | ✅ Resuelto | try/catch con alerta en `app.ts` |
| Postgres y Adminer locales accesibles desde la red | ✅ Resuelto | Publicados solo en `127.0.0.1` |
| Sin límite de intentos en `/api/auth/login` | ✅ Resuelto | 5 fallos seguidos bloquean la cuenta 15 min (429); migración `0002` |
| `GET desarrolladores` expone teléfono y fecha de nacimiento a cualquier usuario logueado | ✅ Resuelto | `telefono` y `fecha_nacimiento` solo se devuelven al dueño del perfil; el contacto es por email |
| `environment.gests` por email: cualquiera puede registrar `admin@...` | ✅ Resuelto | Se eliminó `environment.gests`; el flag sale de `auth_users.is_admin`, que solo se activa desde la base |
| E-24 (cualquier error del portfolio se mostraba como "no tiene") | ✅ Resuelto | Solo el 404 es "no tiene"; otro error muestra "No se pudo cargar" con botón Reintentar |

> Fecha: 2026-10-29 · Commit base: `2cc9f54` · Alcance: todo `src/`, configuración (`angular.json`, `tsconfig*`, `package.json`) y dependencias.
> Contexto del proyecto: [`context_front.md`](./context_front.md).
> Las referencias `archivo:línea` son relativas a `src/app/` salvo que se indique otra ruta.

---

## 1. Resumen ejecutivo

El frontend tiene una **base visual amplia** (landing, perfil, portfolio, contratos, libro 3D, tema oscuro) y un **modelo de dominio razonable**. Pero **no está listo para producción**: el build de producción falla, los tests no compilan, no existe backend ni autenticación real, y hay errores funcionales en flujos centrales (crear contrato, postularse, guardar perfil de gerente).

### Verificaciones ejecutadas

| Verificación | Resultado |
|---|---|
| `ng serve` (development) | ✅ Compila y levanta |
| `ng build` (production) | ❌ **Falla**: 7 errores de presupuesto (CSS de componentes y fuentes inlined > 8 KB) y bundle inicial 541 KB > 500 KB (warning) |
| `ng test` | ❌ **No compila**: `componentes/profile/profile.spec.ts` importa `./perfil` (no existe) |
| `npm audit` | ✅ 0 vulnerabilidades |
| `npm outdated` | ⚠️ Angular 20.3 vs 22.2 disponible (2 majors atrás); TypeScript 5.9 vs 7.0 |

### Puntaje por área (1 = crítico, 5 = sólido)

| Área | Puntaje | Comentario |
|---|:---:|---|
| Seguridad | 1 | Sin auth real ni tokens; bucket escribible desde el navegador |
| Correctitud funcional | 2 | Varios flujos centrales rotos o con condiciones de carrera |
| Arquitectura | 2 | Estado global `any`, lógica duplicada, componentes gigantes |
| Calidad de código | 2 | `any` extendido, código comentado, `console.log`, nombres inconsistentes |
| Build / rendimiento | 2 | Build de producción falla; CSS sobredimensionado; fuentes duplicadas |
| Accesibilidad | 2 | Botones e imágenes sin etiquetas; `(click)` en elementos no interactivos |
| Testing | 1 | 3 specs, ninguno compila ni pasaría |
| DX / documentación | 2 | README vacío, sin linter ni CI; entornos sin configurar |

### Top 10 acciones

1. **Arreglar el build de producción** (A-01): subir o ajustar presupuestos, o partir CSS y quitar `@import` de fuentes.
2. **Arreglar `formcreatecontract`** (B-01): el contrato se crea sin `proyecto_id`.
3. **Definir la autenticación real** y enviar token en un interceptor (S-01).
4. **Mover la subida y borrado de imágenes a URLs prefirmadas** desde el backend (S-02).
5. **Unificar la postulación** en un solo endpoint atómico (B-05).
6. **Corregir `profile.ts:343`** (B-04): la actualización del gerente no espera ni reporta errores.
7. **Cancelar suscripciones** con `takeUntilDestroyed` (Q-01).
8. **Reparar los tests** y agregar al menos tests de servicios y del guard (T-01, T-02).
9. **Tipar `userProfile$`** y normalizar datos en los servicios, no en los componentes (Q-03, Q-04).
10. **Agregar ESLint + CI** con build y tests (D-02).

---

## 2. Escala de severidad

| Severidad | Criterio |
|---|---|
| 🔴 **Crítica** | Bloquea producción, expone datos o rompe un flujo central |
| 🟠 **Alta** | Error funcional visible o riesgo de seguridad relevante |
| 🟡 **Media** | Deuda técnica que genera errores o dificulta mantener |
| 🟢 **Baja** | Estilo, limpieza, mejoras menores |

---

## 3. Seguridad

### S-01 🔴 Sin autenticación real ni autorización en las llamadas HTTP
- **Dónde:** `servicios/AuthService.ts` (mock), `app.config.ts` (sin interceptors), todos los servicios HTTP.
- **Qué pasa:** ninguna petición envía token. La identidad viaja como email en el path (`PUT usuario/:email`, `DELETE contrato/:id`, `PUT updateportfolio/:email`). El mock acepta cualquier credencial.
- **Impacto:** si el backend se implementa siguiendo este contrato, **cualquiera podría modificar o borrar datos de cualquier usuario** conociendo su email o el id de un contrato. El `authGuard` solo protege la navegación, no los datos.
- **Recomendación:** definir el proveedor de auth (Supabase u otro), agregar un `HttpInterceptorFn` que adjunte `Authorization: Bearer <jwt>`, y que el backend derive el usuario del token, no del path. Registrar con `provideHttpClient(withInterceptors([authInterceptor]))`.

### S-02 🔴 Escritura y borrado directo al bucket desde el navegador
- **Dónde:** `servicios/portfolioService.ts:62-76` (`uploadImage`, PUT) y `:126-139` (`deleteImage`, DELETE).
- **Qué pasa:** el front hace `fetch(PUT/DELETE)` a `${bucketUrl}/portfolios/...` sin credenciales.
- **Impacto:** para que funcione, el bucket debe permitir **escritura y borrado anónimos**: cualquiera puede subir contenido arbitrario (malware, contenido ilegal, costos de almacenamiento) o borrar imágenes ajenas.
- **Recomendación:** que el backend emita **URLs prefirmadas** de corta duración (PUT) y haga el DELETE del lado servidor validando al dueño.

### S-03 🟠 Sin validación de archivos antes de subir
- **Dónde:** `componentes/portfolio-component/portfolio-component.ts:163-187`, `componentes/profile/profile.ts:175-203`.
- **Qué pasa:** no se valida tipo MIME, extensión ni tamaño. El nombre de archivo original se usa en la key (`file.name.replace(/\s/g, '_')`).
- **Recomendación:** aceptar solo `image/jpeg|png|webp`, limitar tamaño (por ejemplo 2 MB), sanear el nombre o usar un UUID. Validar también en el backend.

### S-04 🟠 Emails en URLs sin codificar
- **Dónde:** `servicios/users.ts:24,57,92`, `servicios/contrato.ts:29`, `servicios/miproyecto.ts:27,40`, `servicios/portfolioService.ts:31,52,79,148`.
- **Impacto:** emails con `+`, `#`, `/` o `%` rompen la ruta o apuntan a otro recurso (por ejemplo `a#b@x.com` se corta en el `#`).
- **Recomendación:** `encodeURIComponent(email)` en todos los paths, o mejor, no usar el email como identificador en la URL.

### S-05 🟡 Links de usuario con `target="_blank"` y sin validar el esquema
- **Dónde:** `componentes/portfolio-component/portfolio-component.html:38,51,63` (`[href]="portfolio.repositorioN"`), `componentes/home/home.html:114,127,140,153,166`.
- **Qué pasa:** falta `rel="noopener noreferrer"`. Angular sanitiza `javascript:` en `[href]`, pero no se valida que el repositorio sea `https://`.
- **Recomendación:** agregar `rel="noopener noreferrer"` y validar URL `https?://` al guardar el portfolio.

### S-06 🟡 Autorización por rol solo en la UI
- **Dónde:** `app.routes.ts` (un único `authGuard` para todo), `componentes/home/home.ts:93-106`.
- **Qué pasa:** un desarrollador puede entrar a `/formcreatecontract` o `/miproyecto` escribiendo la URL.
- **Recomendación:** `roleGuard` que lea `userProfile$` (rol) y backend que valide permisos.

### S-07 🟢 Datos de sesión del mock en `localStorage`
- **Dónde:** `servicios/AuthService.ts:51`.
- **Nota:** aceptable para el mock; con auth real, preferir el manejo de sesión del proveedor y no guardar datos personales extra en `localStorage`.

---

## 4. Errores funcionales

### B-01 🔴 El contrato se crea sin `proyecto_id`
- **Dónde:** `views/formcreatecontract/formcreatecontract.ts:46-49`; rutas en `app.routes.ts` (`formcreatecontract/:project_id`); llamadas en `componentes/profile/profile.html:502,586` y `componentes/miproyecto/miproyecto.html:28`.
- **Qué pasa:** el componente lee `paramMap.get('id')` y `get('nombre')`, pero la ruta define `:project_id`, así que siempre obtiene `null`. Además, `profile.html` pasa `perfil.proyecto` (**un objeto**) como parámetro: la URL queda `/formcreatecontract/[object Object]`.
- **Impacto:** todos los contratos se envían con `proyecto_id: null`. El encabezado muestra `nombre: null`.
- **Recomendación:** leer `paramMap.get('project_id')` y pasar `perfil.proyecto?.id` desde el perfil. Para el nombre, usar query param o pedirlo al servicio.

### B-02 🟠 Links a rutas inexistentes y sin página 404
- **Dónde:** `componentes/navbar/navbar.html:67-75` (`/dashboard`, `/whitelist-email`), `app.routes.ts` (sin `**`).
- **Impacto:** navegar a esas rutas lanza `NG04002: Cannot match any routes` y la navegación no ocurre.
- **Recomendación:** crear las rutas o quitar los links, y agregar `{ path: '**', redirectTo: '' }` o un componente 404.

### B-03 🟠 `Miproyecto` lanza TypeError si el perfil no está cargado
- **Dónde:** `componentes/miproyecto/miproyecto.ts:50`.
- **Qué pasa:** `this.mostrarProyecto(this.perfil.email)` se ejecuta fuera de la suscripción. Si `userProfile$` todavía emite `null`, `perfil` es `null` y lanza `Cannot read properties of null`.
- **Recomendación:** llamar a `mostrarProyecto` dentro de la suscripción (`filter(Boolean)` + `switchMap`), como ya hace `Formcreateproyect`.

### B-04 🟠 Guardar perfil de gerente: la segunda petición no se espera
- **Dónde:** `componentes/profile/profile.ts:343`.
- **Qué pasa:** `await lastValueFrom(A) && lastValueFrom(B)`: solo se espera `A`. `B` (actualizar usuario) queda como promesa suelta; si falla, el error no se captura y aun así se muestra "Perfil actualizado con éxito". Si `A` devuelve un valor falsy, `B` ni siquiera se ejecuta.
- **Recomendación:** `await Promise.all([lastValueFrom(A), lastValueFrom(B)])` o dos `await` en secuencia.

### B-05 🟠 La postulación usa dos PUT parciales no atómicos
- **Dónde:** `componentes/contrato-detail/contrato-detail.ts:71-100`, `servicios/contrato.ts:45-49`.
- **Qué pasa:** primero `PUT contrato/:id {postulaciones: email}` y luego `PUT contrato/:id {id, tiene_postulaciones: true}`. Depende de que el backend haga *append* (no reemplazo) en el primero y *merge* en el segundo. Dos desarrolladores postulándose a la vez pueden pisarse. Si falla el segundo PUT, el usuario no recibe aviso (solo `console.error`). Tampoco se recarga la lista padre, así que el contrato sigue en "disponibles".
- **Recomendación:** un endpoint `POST contrato/:id/postulaciones` que agregue el email y marque `tiene_postulaciones` en el servidor. Emitir un evento al padre para refrescar.

### B-06 🟠 Crear usuario sin rol sigue adelante
- **Dónde:** `app.ts:224-243`.
- **Qué pasa:** si `!selectedRole` muestra un warning pero **no hace `return`**: ejecuta `POST ${apiUrl}` (rol vacío).
- **Recomendación:** `if (!this.selectedRole) { this.alertService.warning(...); this.cargandoData = false; return; }`.

### B-07 🟡 Suscripción duplicada tras crear usuario
- **Dónde:** `app.ts:119` y `:234`.
- **Qué pasa:** `handleCreateUser` vuelve a llamar a `inicializarDatos()`, que crea otra suscripción a `userEmail$` y sobrescribe `authSub` sin cancelar la anterior. Cada login posterior dispara las peticiones dos (o más) veces.
- **Recomendación:** suscribirse una sola vez. Tras crear el usuario, re-ejecutar solo la consulta (por ejemplo con un `Subject` de refresco) o cancelar `authSub` antes.

### B-08 🟡 Mensajes de registro incorrectos
- **Dónde:** `app.ts:208-213`.
- **Qué pasa:** cuando hace falta confirmar el email (`data.user && !data.session`), igual se muestra "Sesión iniciada correctamente".
- **Recomendación:** mensaje según el caso ("Revisá tu email para confirmar la cuenta").

### B-09 🟡 `loading` queda en `true`
- **Dónde:** `componentes/profile/profile.ts:220-223` (`guardarHabilidad`) y `:244-247` (`guardarIdioma`).
- **Qué pasa:** se pone `loading = true` y si el nombre está vacío se hace `return` sin resetearlo, así que el formulario queda deshabilitado o con spinner.
- **Recomendación:** validar antes de activar `loading` (en realidad estas operaciones son locales y no necesitan `loading`).

### B-10 🟡 Filtro "no postulados" sin efecto
- **Dónde:** `componentes/contratos/contratos.ts:170-185`.
- **Qué pasa:** filtra `contratosDisponiblesCopia` por "el usuario no se postuló", pero `createCards` ya mandó los postulados a `contratosPendientes`, así que el resultado es idéntico. Además, cualquier `filtrarContratos()` posterior pisa el estado del toggle.
- **Recomendación:** eliminar el toggle o redefinir qué se quiere filtrar.

### B-11 🟡 Fechas en UTC
- **Dónde:** `componentes/profile/profile.ts:165,169,394`, `views/formcreatecontract/formcreatecontract.ts:102`.
- **Qué pasa:** `new Date().toISOString().split('T')[0]` usa UTC. En Argentina (UTC-3), desde las 21:00 da **la fecha del día siguiente**. Lo mismo afecta los límites de edad.
- **Recomendación:** construir la fecha local (`getFullYear`/`getMonth`/`getDate` con padding) o usar `formatDate(new Date(), 'yyyy-MM-dd', 'es-AR')`.

### B-12 🟡 Imágenes y links rotos
- **Dónde:** `componentes/home/home.html:166` (`href=""` con `target="_blank"`). *(Las dos imágenes inexistentes del hero y del libro del navbar se quitaron el 2026-10-29.)*
- **Qué pasa:** El link vacío abre una pestaña con la misma app.
- **Recomendación:** agregar los archivos en `public/assets/` y completar o quitar el link.

### B-13 🟡 `alert()` nativo en `Home`
- **Dónde:** `componentes/home/home.ts:97,104`.
- **Recomendación:** usar `AlertService.warning(...)` como el resto de la app.

### B-14 🟡 El CV no se sube
- **Dónde:** `componentes/profile/profile.ts:175-180`.
- **Qué pasa:** el archivo se guarda en `archivoCV` pero ningún método lo envía.
- **Recomendación:** implementar la subida o indicar en la UI que está pendiente.

### B-15 🟢 Usuario social del mock con dominio ajeno
- **Dónde:** `servicios/AuthService.ts:36` (`demo@udelar.test`; *udelar* es otra universidad).
- **Recomendación:** usar `demo@udelaconecta.test` o similar.

---

## 5. Arquitectura y calidad de código

### Q-01 🟠 Suscripciones sin cancelar (fugas de memoria)
- **Dónde:** `componentes/contratos/contratos.ts:64,78`, `componentes/profile/profile.ts:72`, `componentes/home/home.ts:62`, `componentes/navbar/navbar.ts:117,140`, `componentes/miproyecto/miproyecto.ts:41`, `views/formcreateproyect/formcreateproyect.ts:64`.
- **Impacto:** cada visita a una página agrega una suscripción a `userProfile$` que nunca se libera: reacciones duplicadas, peticiones repetidas y memoria creciente.
- **Recomendación:** `takeUntilDestroyed(this.destroyRef)` (Angular 16+), `async` pipe o `toSignal()`.

### Q-02 🟡 Lógica duplicada
- **Tema oscuro:** `app.ts:97-114` y `componentes/navbar/navbar.ts:98-101,207-219`. Extraer a un `ThemeService`.
- **Logout:** `app.ts:245-267` y `componentes/navbar/navbar.ts:198-201` (este último recarga toda la página con `window.location.href`).
- **Normalización CSV ↔ array:** `componentes/contratos/contratos.ts:211-217,307-316`, `componentes/contrato-detail/contrato-detail.ts:104-124`, `componentes/profile/profile.ts:363-386` (este con lógica distinta: soporta JSON y `{...}`). Centralizar en `ContratoService` con un `map()`.
- **Apertura de formulario del portfolio:** `abrircrearPortfolio` y `abrireditarPortfolio` (`portfolio-component.ts:56-110`) repiten el armado de `formData`.
- **Crear vs editar portfolio:** `guardarPortfolio` y `editarPortfolio` son casi idénticos.

### Q-03 🟡 Tipado débil
- `Users.userProfile$` es `BehaviorSubject<any>`. Todo componente usa `perfil: any`.
- `userExistsByEmailResponse` (`models/users/usuario.ts:10`) existe pero `checkUserExists` devuelve `Observable<any>`.
- Errores tipados como `string` en `error: (error: string) =>` cuando son `HttpErrorResponse` (`contratos.ts:128`, `profile.ts:144`, formularios). Por eso los mensajes concatenan `'... ' + error` y muestran `[object Object]`.
- **Recomendación:** interfaces `PerfilDesarrollador | PerfilGerente` con discriminante `rol`, `HttpErrorResponse` en los handlers y eliminar `any` progresivamente.

### Q-04 🟡 Modelos inconsistentes con el uso real
- `Proyecto.description` (inglés) vs. `descripcion` en el resto.
- `ContratoCard.pasante_id: number` vs. `Contrato.pasante_email: string`.
- `Contrato.id: number` vs. `Contrato.proyecto_id: string` vs. `Proyecto.id: string`.
- `Usuario` tiene `nombre` **y** `name`.
- Campos usados pero no declarados: `telefono`, `puesto_actual`, `habilidades`, `idiomas`, `is_disponible`, `rol`, `proyecto`.
- Modelos como `class` con campos opcionales en lugar de `interface`.

### Q-05 🟡 `LoadingService` sin efecto visual
- **Dónde:** `servicios/loading-service.ts`; usado en `contratos.ts:100,132` y `miproyecto.ts:58,68`.
- **Qué pasa:** ningún template lee `isLoading()`. El único spinner visible depende de `App.cargandoData`. Además `hideLoader()` está en `complete`, que no se ejecuta si hay error.
- **Recomendación:** renderizar `@if (loading.isLoading()) { <app-spinner/> }` en `app.html` y llamar a `hideLoader` en `finalize()`.

### Q-06 🟡 Estilos de `Alertas` no aplicados
- **Dónde:** `componentes/alertas/alertas..css` (doble punto, 251 líneas) y `alertas.ts:5-9` (sin `styleUrl`).
- **Recomendación:** renombrar a `alertas.css` y declarar `styleUrl`. Verificar si los estilos están duplicados en `app.css`.

### Q-07 🟡 Componentes demasiado grandes
- `home.html` 719 líneas / `home.css` 2.203; `profile.html` 603 / `profile.css` 1.864 / `profile.ts` 440; `app.html` 422 / `app.css` 2.151; `navbar.css` 1.407.
- `App` mezcla landing, 3 modales, selector de rol y orquestación de sesión.
- **Recomendación:** extraer `LandingComponent`, `AuthModalsComponent`, `RoleSelectorComponent`; dividir `Profile` en subcomponentes por sección (`ProfileInfo`, `ProfileSkills`, `ProfileLanguages`, `ProfileOffers`).

### Q-08 🟢 Inyección inconsistente y dependencias sobrantes
- Mezcla de `constructor(private …)` e `inject()`.
- `Contratos` inyecta `Users` dos veces (`contratos.ts:53` y `:57`).
- `ProyectoService` inyecta `Users` y declara `user`, `rol` sin usarlos (`miproyecto.ts:14-16`).
- Imports sin uso: `Input` (`contratos.ts:1`), `inject` (varios), `ActivatedRoute` en `ContratoDetail`, `ReactiveFormsModule`/`FormBuilder` en `Profile`, `skip`, `take`, `filter`, `tap`, `Usuario`, `LoadingService` en `app.ts:6-11`.
- Outputs `onLogin`/`onRegister` en `Navbar` no conectados.

### Q-09 🟢 APIs deprecadas
- `.toPromise()` en `portfolio-component.ts:43,149,225` → usar `lastValueFrom`.
- `event.which` / `event.keyCode` en `profile.ts:290` → usar `event.key`.
- Mezcla de `*ngIf`/`*ngFor` con `@if`/`@for` en el mismo proyecto.

### Q-10 🟢 Limpieza
- Código comentado en casi todos los archivos (`app.ts:71,89,117,122`, `contratos.ts:184,201-206,219`, `formcreatecontract.ts:57-71`, `portfolioService.ts:152-160`, etc.).
- `console.log` de depuración en producción (`app.ts:146,232,259`, `contrato-detail.ts:51`, `formcreateproyect.ts:87,94`, etc.).
- Variables sin uso: `dataParaEnviar` (`formcreateproyect.ts:111,134`), `canvas`, `title`, `searchLocation` en `App`, `contratosCards`.
- `Spinner` duplicado: `spinner.ts` solo reexporta `spinner.component.ts`.

### Q-11 🟡 Configuración de entornos
- `environment.ts` vive en `src/app/environments/` (lo estándar es `src/environments/`).
- No hay `environment.prod.ts` ni `fileReplacements` en `angular.json`: producción usaría `127.0.0.1`.
- `bucketUrl` vacío: `uploadImage` haría PUT a `/portfolios/...` del propio host.

---

## 6. Build y rendimiento

### P-01 🔴 El build de producción falla
- **Resultado real de `ng build`:**
  - ❌ `portfolio-component.css` 10,87 KB, `home.css` 31,93 KB, `profile.css` 27,81 KB, `navbar.css` 22,44 KB (límite de error 8 KB).
  - ❌ Tres `@import` de Google Fonts inlined de 31–51 KB cada uno (`app.css:1`, `contratos.css:1`, `contrato-detail.css:1`).
  - ⚠️ `formcreatecontract.css` 6,69 KB (warning > 4 KB).
  - ⚠️ Bundle inicial 541,54 KB (límite 500 KB).
- **Recomendación inmediata:** quitar los `@import` de fuentes de los CSS de componentes (ya se cargan, en parte, en `index.html`) y ajustar `anyComponentStyle` a un valor realista (por ejemplo warning 16 KB / error 40 KB) **mientras** se refactoriza el CSS.

### P-02 🟡 Fuentes duplicadas e inconsistentes
- `index.html` carga Crimson Text, Outfit e Inter; los CSS importan Plus Jakarta Sans + Inter (dos variantes de pesos distintas). Inter se descarga varias veces y en build se inlinea más de 100 KB de CSS de fuentes.
- **Recomendación:** definir una sola familia tipográfica y cargarla una vez en `index.html` (o self-hosting).

### P-03 🟡 Detección de cambios
- Ningún componente usa `ChangeDetectionStrategy.OnPush`.
- Getters recalculados en cada ciclo: `postulacionesNormalizadas` (`contrato-detail.ts:104`), `imagenes1Validas..3` (`portfolio-component.ts:326-334`), `isProfileEmpty`, `esSoloPerfil`.
- 18 bucles `*ngFor`/`@for` y solo 9 con `track`/`trackBy`.
- **Recomendación:** `OnPush` + signals o `computed()`; `track item.id` en todos los `@for`.

### P-04 🟢 Imágenes del portfolio
- Previews con `FileReader.readAsDataURL` (base64 en memoria). Preferible `URL.createObjectURL` y revocarlo luego.
- Subidas secuenciales (`for…await`, `portfolio-component.ts:244-247`). Pueden paralelizarse con `Promise.all`.

### P-05 🟢 Dependencias
- Angular 20.3 con 22.2 disponible; TypeScript 5.9 vs 7.0; zone.js 0.15 vs 0.16. Sin vulnerabilidades conocidas (`npm audit`: 0).
- Evaluar migrar a **zoneless** (`provideZonelessChangeDetection`) junto con signals.

---

## 7. Accesibilidad y UX

### A-01 🟠 Controles sin nombre accesible
- Hay botones cuyo contenido es solo un ícono o símbolo (por ejemplo los `&times;` de cierre de modales en `app.html`) y solo 26 atributos `aria-*` en todo el proyecto. Conviene revisar los botones uno por uno.
- **Recomendación:** `aria-label="Cerrar"` y similares; `aria-hidden="true"` en los íconos decorativos.

### A-02 🟠 Elementos no interactivos con `(click)`
- 18 `(click)` en `div`/`span`/`li`/`i`; `<a (click)>` sin `href` en `app.html` ("¿Olvidaste tu contraseña?", "Volver al login"), con `role="button"` pero sin `tabindex` ni manejo de teclado.
- **Impacto:** inaccesibles con teclado o lector de pantalla.
- **Recomendación:** usar `<button type="button">`.

### A-03 🟡 Imágenes sin `alt`
- `componentes/portfolio-component/portfolio-component.html:36,48,60,97,122,147`.

### A-04 🟡 Modales
- Sin `role="dialog"`, `aria-modal`, foco inicial, trampa de foco ni cierre con `Escape` (modales de `app.html`, libro 3D en `navbar.html`, modal de postulante en `contrato-detail.html`, confirmación de `Alertas`).

### A-05 🟡 Formularios
- Inputs de email sin `type="email"` ni `autocomplete` (`app.html` login, registro y recuperación). Los de contraseña sin `autocomplete="current-password"` / `"new-password"`.
- Login y registro sin validación de longitud de contraseña ni formato de email en el front.
- Errores de validación visibles solo en `formcreateproyect`.

### A-06 🟢 Idioma del documento
- `index.html:2` declara `lang="en"` y todo el contenido está en español. Afecta lectores de pantalla y SEO. Usar `lang="es"` (o `es-AR`).

### A-07 🟢 UX
- Errores de API que se muestran como `"Error ..., " + error` → `[object Object]` (`contrato-detail.ts:66,98`, `profile.ts:146`).
- Al eliminar oferta o portfolio no hay feedback de éxito (`profile.ts:420-424`, `portfolio-component.ts:290-294`).
- `Formcreatecontract` no valida `end_date >= start_date`.

---

## 8. Testing

### T-01 🔴 La suite no compila
- **Resultado real:** `TS2307: Cannot find module './perfil'` en `componentes/profile/profile.spec.ts:3` (el componente es `ProfileComponent` en `./profile`).
- Aun corrigiendo eso:
  - `app.spec.ts:21` espera un `<h1>` con `'Hello, udela'` que no existe (spec del scaffold original).
  - Ningún spec provee `provideHttpClient()`/`provideHttpClientTesting()` ni `provideRouter([])`, así que `App`, `Home` y `ProfileComponent` fallarían por `NG0201: No provider for HttpClient`.

### T-02 🟠 Cobertura prácticamente nula
- 3 specs (todos *should create*), ninguno de servicios, guard, normalización de datos ni flujos.
- **Recomendación mínima:** tests de `Users.checkUserExists` (manejo de 404), `authGuard`, la normalización CSV ↔ array, `ContratoService` (paths) y `Contratos.createCards` (clasificación).

---

## 9. DX, documentación y proceso

### D-01 🟡 Documentación
- `README.md` vacío (1 byte). Sin instrucciones de entorno, backend ni despliegue (hoy cubierto parcialmente por `context_agent/`).

### D-02 🟡 Sin linter ni CI
- No hay ESLint (`@angular-eslint`), ni hooks de pre-commit, ni pipeline que corra build y tests. Los errores P-01 y T-01 habrían sido detectados.
- **Recomendación:** `ng add @angular-eslint/schematics`, GitHub Actions con `npm ci && npm run build && npm test -- --watch=false --browsers=ChromeHeadless`.

### D-03 🟢 Convenciones de nombres
- Archivos: `AuthService.ts` (PascalCase), `portfolioService.ts`, `alertService.ts` (camelCase), `loading-service.ts` (kebab), `miproyecto.ts` exporta `ProyectoService`.
- Clases: `Users` (servicio en plural, sin sufijo), `ContratoService`, `Navbar`, `ProfileComponent`, `SpinnerComponent` (mezcla con y sin sufijo).
- Mezcla de español e inglés: `formcreateproyect`, `description`, `handleLogin`, `mostrarTodosLosContratos`.
- **Recomendación:** fijar una convención en `AGENTS.md` y aplicarla al ir tocando archivos.

### D-04 🟢 Historia de git
- Un commit borró `README.md`; el `AuthService` original nunca fue versionado. Conviene documentar dónde vive el código de auth y el backend.

---

## 10. Plan de remediación

### Fase 1 — Rápidos (menos de 1 h cada uno)
| ID | Acción |
|---|---|
| P-01 | Quitar `@import` de fuentes de los CSS y ajustar presupuestos → build de producción en verde |
| T-01 | Corregir el import de `profile.spec.ts`, borrar el test de `'Hello, udela'`, agregar providers de testing |
| B-01 | `paramMap.get('project_id')` y pasar `perfil.proyecto?.id` |
| B-03 | Mover `mostrarProyecto` dentro de la suscripción |
| B-04 | `Promise.all` en la actualización del gerente |
| B-06 | `return` cuando no hay rol |
| B-09 | Validar antes de `loading = true` |
| B-02 | Ruta `**` y quitar o crear `/dashboard`, `/whitelist-email` |
| B-13, A-06, Q-06 | `AlertService` en Home, `lang="es"`, renombrar `alertas..css` |
| S-04 | `encodeURIComponent` en los servicios |

### Fase 2 — Corto plazo (1–2 semanas)
| ID | Acción |
|---|---|
| S-01 | Auth real + interceptor de token (coordinado con el backend) |
| S-02, S-03 | URLs prefirmadas y validación de archivos |
| B-05 | Endpoint atómico de postulación |
| Q-01 | `takeUntilDestroyed` en todas las suscripciones |
| Q-02, Q-05 | `ThemeService`, logout único, normalización en servicios, spinner con `LoadingService` |
| Q-11 | `src/environments/` + `environment.prod.ts` + `fileReplacements` |
| D-02 | ESLint + CI |
| T-02 | Tests de servicios, guard y clasificación de contratos |
| A-01, A-02, A-05 | Etiquetas accesibles, `<button>` en vez de `(click)` en `div`, inputs de email y contraseña correctos |

### Fase 3 — Estructural
| ID | Acción |
|---|---|
| Q-03, Q-04 | Tipado del perfil y modelos como interfaces alineadas con la API |
| Q-07 | Partir `App`, `Home` y `Profile` en subcomponentes |
| S-06 | `roleGuard` por ruta |
| P-02, P-03 | Una familia tipográfica, `OnPush` + signals, `track` en todos los bucles |
| P-05 | Migrar a Angular 22 y evaluar zoneless |
| A-04 | Modales accesibles (o Angular CDK `Dialog`) |
