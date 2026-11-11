# Contexto del backend — Udela Conecta

> Documento de referencia para agentes de IA y desarrolladores. Describe **cómo está hecho hoy** el backend (`apps/backend/`). Cómo se orquesta con Nx y Docker está en [`orquestacion.md`](./orquestacion.md). Cómo correrlo, en [`../apps/backend/README.md`](../apps/backend/README.md).
> Fecha: 2026-11-11 · Última migración: `0004`.

---

## 1. Resumen

API REST en **FastAPI 0.115** + **SQLAlchemy 2.0 async** (driver `asyncpg`) sobre **PostgreSQL 16**, con migraciones **Alembic** y autenticación **JWT propia** (PyJWT + bcrypt). Reemplaza al backend externo y al bucket S3 que usaba el frontend. Mantiene las mismas rutas y los mismos sobres de respuesta que el front ya consumía (ver [`endpoint.md`](./endpoint.md)).

- Puerto: `3000`. Prefijos: `/api/*` (JSON) y `/storage/*` (imágenes).
- Documentación interactiva: `http://localhost:3000/docs` (Swagger) y `/redoc`.
- Dependencias: Poetry (`pyproject.toml` + `poetry.lock`, `package-mode = false`). Python `^3.12`; las imágenes de Docker usan 3.13.

## 2. Estructura

```
apps/backend/
  pyproject.toml / poetry.lock   dependencias (main + dev: pytest, pytest-asyncio, httpx)
  requirements.txt               las mismas dependencias directas en formato pip
  project.json                   proyecto Nx "backend" (serve, migrate, seed, test)
  alembic.ini, alembic/          env.py async + versions/0001..0004
  app/
    main.py                      FastAPI, CORS, routers, GET /api/health
    core/
      config.py                  Settings (pydantic-settings) desde variables de entorno
      database.py                engine async, AsyncSessionLocal, get_db (una transacción por request)
      security.py                bcrypt, JWT, CurrentUser, get_current_user(_optional), exigir_mismo_usuario
      storage.py                 rutas seguras, dueño de cada archivo, lista blanca de formatos
    dominio/compatibilidad.py    comparador determinista en Python puro (sin IA)
    models/entities.py           las 8 tablas + TABLAS_PERFIL
    schemas/
      auth.py                    requests Pydantic (Credenciales, EmailRequest, AsignarRequest…)
      serializacion.py           a_dict (fila → dict) y aplicar_cambios (dict → fila, con coerción)
    routers/                     auth, usuarios, proyectos, contratos, postulaciones, portfolio, storage, chat
    seeds/seed_demo.py           datos demo idempotentes (incluye requisitos)
  tests/                         pytest + httpx ASGITransport sobre SQLite en memoria
```

## 3. Ciclo de un request

1. **CORS** (`main.py`): orígenes de `CORS_ORIGINS`, separados por coma.
2. **Router**: cada recurso tiene su `APIRouter`. Todos menos `auth` y `storage` declaran `dependencies=[Depends(get_current_user)]`, así que **sin token responden 401** antes de entrar al endpoint.
3. **`get_current_user`** (`core/security.py`): lee `Authorization: Bearer`, decodifica el JWT y **vuelve a buscar el usuario en `auth_users`**. Si no existe o `is_active` es falso, responde 401. Devuelve `CurrentUser(id, email)`; el email sale de la base, no del token.
4. **`get_db`** (`core/database.py`): abre una `AsyncSession`. Si el endpoint termina bien hace `commit`, y si lanza una excepción (incluida `HTTPException`) hace `rollback`. FastAPI cachea la dependencia por request, así que el router y el endpoint comparten la misma sesión.
5. **Endpoint**: valida dueño o rol, aplica cambios con `aplicar_cambios` y responde con `a_dict`.

Hay dos lugares que hacen `commit` explícito antes de terminar:
- `auth.login`: guarda el contador de intentos fallidos antes de lanzar el 401, porque si no el rollback lo perdería.
- `portfolio.update/delete`: confirma la base antes de borrar archivos del disco.

## 4. Modelo de datos (`app/models/entities.py`)

Las listas se guardan en **JSONB** en Postgres y en JSON en SQLite (los tests), con el tipo `JsonType = JSON().with_variant(JSONB(), "postgresql")`.

| Tabla | Clave | Columnas relevantes |
|---|---|---|
| `auth_users` | `id` UUID (str) | `email` único, `password_hash` (bcrypt), `is_active`, `is_admin`, `failed_logins`, `locked_until`, `created_at` |
| `estudiante` | `id` int | `email` único, `nombre`, `apellido`, `name`, `descripcion`, `telefono`*, `genero`, `fecha_nacimiento`*, `puesto_actual`, `rol` (=`estudiante`), `is_disponible`, `verificado`, `skills`, `habilidades`, `idiomas` (JSON) |
| `gerente` | `id` int | `email` único, mismos datos personales, `puesto_actual`, `id_proyecto`, `habilidades`, `idiomas` |
| `institucion_educativa` | `id` int | `email` único, `nombre`, `apellido`, `name`, `descripcion`, `telefono` |
| `proyecto` | `id` UUID (str) | `nombre`, `description`, `info_link`, `buscando_devs`, `id_gerente`, `email_gerente` **único** (un proyecto por gerente). Relación `contratos` con `cascade="all, delete-orphan"` |
| `contrato` | `id` int | `tipo`, `titulo`, `descripcion`, **`requisitos` (JSONB, lista de `{nombre, nivel_minimo, exigencia, tipo}`, NOT NULL default `[]`)**, `tiene_postulaciones`, `postulaciones` (lista de emails), `esta_ocupado`, `pasante_email`, `proyecto_id` (FK `ON DELETE CASCADE`), `start_date`, `end_date`, `modalidad`, `seniority_deseado` (lista) |
| `portfolio` | `id` int | `email` único, `titulo1..3`, `descripcion1..3`, `repositorio1..3`, `imagenes1..3` (siempre 3 posiciones, `""` si están vacías) |
| `informe_postulacion` | `id` int | `contrato_id` (FK `ON DELETE CASCADE`), `estudiante_email`, `texto` (Text), `modelo` (60), `estado` (`pendiente`/`generado`/`fallback`), `creado_en`, `actualizado_en`; **único** `(contrato_id, estudiante_email)`; índices por contrato y email |

\* Campos privados: solo los recibe el dueño del perfil (`CAMPOS_PRIVADOS` en `routers/usuarios.py`).

- **Roles:** no hay columna de rol en `auth_users`. El rol es **la tabla de perfil** donde está el email; `TABLAS_PERFIL = {"estudiante", "gerente", "institucion_educativa"}` mapea el nombre de la tabla al modelo. En la UI, `estudiante` se muestra como "Estudiante / graduado". Antes de la migración `0003` se llamaba `desarrollador`.
- **Fechas** (`fecha_nacimiento`, `start_date`, `end_date`): se guardan como `String(30)` en formato `YYYY-MM-DD`, tal como las manda el front.

### Migraciones (`alembic/versions/`)

| Revisión | Contenido |
|---|---|
| `0001` | Esquema inicial: las 7 tablas, índices únicos de email |
| `0002` | `auth_users.is_admin`, `failed_logins`, `locked_until` |
| `0003` | Renombra `desarrollador` → `estudiante` (tabla, índice, PK, secuencia y valores de `rol`); tiene `downgrade` |
| `0004` | `contrato.requisitos` JSONB NOT NULL default `[]` y tabla `informe_postulacion` con unique `(contrato_id, estudiante_email)`; tiene `downgrade` |

`alembic/env.py` es async y toma `DATABASE_URL` de `Settings`. Regla: **todo cambio en `entities.py` va con una migración nueva**. Después hay que correr `alembic check`, que debe decir "No new upgrade operations detected".

- **Compatibilidad:** `app/dominio/compatibilidad.py` no importa nada del backend; recibe el perfil (`habilidades`/`skills`) y la lista `requisitos`. Solo cuentan técnicas `excluyente`/`deseable`; `se_aprende` y `blanda` se muestran aparte. El porcentaje no se persiste: se recalcula en cada request.
- **Requisitos:** al crear o editar un contrato, `sanitizar_requisitos` normaliza nombres, niveles y exigencias y descarta ítems inválidos. La respuesta de `GET contratos*` incluye `requisitos`.

## 5. Endpoints

Todas las respuestas usan el sobre `{ message, data }` y, en listados, `count`. Los errores son `{ detail: "mensaje en español" }` (formato estándar de FastAPI); el front muestra `err.error.detail`.

### Auth (`/api/auth`, sin token)

| Método y ruta | Comportamiento |
|---|---|
| `POST register` `{email, password}` | Valida el email (`email-validator`) y una contraseña de 6 a 72 bytes. Responde 201 con `{data: {user, session: {user, access_token, token_type}}, error: null}`. 409 si el email ya existe |
| `POST login` | Mismo sobre. 401 si las credenciales son incorrectas. Tras `LOGIN_MAX_INTENTOS` (5) fallos seguidos bloquea `LOGIN_BLOQUEO_MINUTOS` (15) y responde 429. Un login correcto reinicia el contador |
| `POST social` | 501 "todavía no está disponible" |
| `POST reset-password` | 200 genérico (no revela si el email existe); no envía mail porque no hay SMTP |

`user` = `{id, email, is_admin}`. El token dura `JWT_EXPIRE_MINUTES` (7 días) y no hay refresh.

### Usuarios (`/api`, con token)

| Método y ruta | Comportamiento |
|---|---|
| `GET usuario/:email` | `{data: {existe: 1, tabla}}`, o **404** con `{data: {existe: 0, tabla: null}}` (el front traduce el 404 a "no tiene perfil") |
| `GET usuario/:email/:tabla` | Perfil completo. `tabla` validada contra `TABLAS_PERFIL` (400 si no está). Sin `telefono`/`fecha_nacimiento` si no es el propio perfil |
| `PUT usuario/:email` | Solo el propio email (403). Busca la tabla por email y aplica **solo columnas conocidas**. `posicion` → `puesto_actual`; normaliza `habilidades`/`idiomas`. No editables: `id`, `email`, `created_at`, `rol`, `verificado`, `id_proyecto` |
| `POST estudiante` / `POST gerente` / `POST institucion_educativa` `{email}` | Crea el perfil del propio email. 409 si ya tiene perfil en cualquier tabla. Rutas generadas en un loop sobre `TABLAS_PERFIL` |
| `GET estudiantes` | Lista de estudiantes (con los campos privados filtrados) |

### Proyectos

| Método y ruta | Comportamiento |
|---|---|
| `GET proyecto/:email` | `data: [proyecto]` o `[]`. `contratos` se devuelve como lista de ids (string) |
| `POST proyecto` | Solo un gerente (403) y una sola vez (409). El dueño sale del token; si el body trae `email_gerente`, tiene que coincidir. Actualiza `gerente.id_proyecto` |
| `PUT proyecto/:email_gerente` | Solo el propio email |

### Contratos

| Método y ruta | Comportamiento |
|---|---|
| `GET contratos`, `GET contratoslibres` (`esta_ocupado = false`), `GET contratos/:emailGerente` | `data` es un array. `contratoslibres` agrega `mi_resultado` si el token es de estudiante. `contratos/:emailGerente` agrega `resultados_postulantes` solo al gerente dueño |
| `POST contrato` | `proyecto_id` tiene que existir (404) y ser del gerente del token (403); `titulo` es obligatorio. Los campos de estado (`postulaciones`, `tiene_postulaciones`, `esta_ocupado`, `pasante_email`) se ignoran: el contrato nace libre. `requisitos` se sanitiza |
| `PUT contrato/:id` | Con `{postulaciones: email}`: postulación. Exige el propio email (403), perfil de **estudiante** (403) y contrato libre (409); no duplica (409). Cualquier otro campo, solo el gerente dueño. `tiene_postulaciones` lo deriva el servidor. Bloquea la fila (`SELECT … FOR UPDATE`). Devuelve un objeto, no un array. `requisitos` se sanitiza |
| `PUT contrato/asignar/:id` `{pasante_email}` | Solo el dueño. El email tiene que estar en `postulaciones` (400) y el contrato libre (409). Marca `esta_ocupado`. Bloquea la fila. `data[0]` |
| `DELETE contrato/:id` | Solo el dueño |

La ruta `asignar/{id}` está declarada **antes** que `/{id}` para que no se tapen. El orden en `contratos.py` es `/contratos` → `/contratoslibres` → `/contratos/{email_gerente}` para que `contratoslibres` no se interprete como un email.

### Informe de compatibilidad y orientación (`routers/postulaciones.py`, prefijo `/api`)

| Método y ruta | Comportamiento |
|---|---|
| `GET mis-postulaciones` | Solo estudiante (403 si no tiene perfil). Devuelve `{message, count, data: [{contrato, resultado, orientacion|null}]}` ordenado por `Contrato.id.desc()` |
| `GET postulaciones/:contrato_id/orientacion` | Solo el estudiante postulado. 404 si no existe el contrato, 403 si no se postuló. `orientacion` es `null` si todavía no se generó |
| `POST postulaciones/:contrato_id/orientacion` | Genera/regenera. 400 si la oferta no tiene requisitos. Llama a n8n con `{contrato_id, email, oferta, compatibles, a_capacitar, se_aprenden, blandas, coincidencia}`. Valida el texto (no vacío, ≤600, sin frases de rechazo) y guarda fallback si n8n falla o responde inválido. Upsert por `(contrato_id, estudiante_email)` |
| `POST automatizacion/postulaciones/:contrato_id/:email/orientacion` | Para n8n. Exige `X-Udela-Secret`; guarda un texto ya validado |
| `GET automatizacion/digests` | Para n8n. Exige `X-Udela-Secret`. Por estudiante, ofertas libres no postuladas con `coincidencia > 60`, top 3: `{email, nombre, ofertas:[{contrato_id, titulo, coincidencia, faltantes}]}` |

- El secreto se compara con `hmac.compare_digest`. Si `N8N_AUTOMATION_SECRET` está vacío, responde 503; si no coincide, 403.
- `MAX_TEXTO_ORIENTACION = 600`; `ESTADOS_INFORME = {"pendiente", "generado", "fallback"}`; `FRASES_RECHAZO` incluye variantes de “no calificás”, “rechazado”, “no sos apto”, etc.
- La empresa **no** recibe el texto de orientación: `resultados_postulantes` solo lleva el resultado determinista y datos mínimos (email, nombre). No incluye teléfono, fecha de nacimiento ni género.

### Portfolio

| Método y ruta | Comportamiento |
|---|---|
| `GET portfolio/:email` | `{data: portfolio}` o 404 |
| `POST createportfolio/:email` | Propio email; 409 si ya existe; normaliza las imágenes a 3 posiciones |
| `PUT updateportfolio/:email` | Propio email. Las imágenes que dejan de usarse se borran del storage **después** del commit |
| `DELETE deleteportfolio/:email` | Propio email. Borra la fila y después sus imágenes |

### Storage (`/storage/portfolios/:nombre`, fuera de `/api`)

Reemplaza al bucket S3. El front hace `PUT`/`DELETE` con `fetch` sobre la URL de la imagen y agrega el token a mano.

| Método | Comportamiento |
|---|---|
| `GET` | Público. Tipo de contenido tomado de la **lista blanca por extensión**, con `X-Content-Type-Options: nosniff` y `Content-Security-Policy: default-src 'none'; sandbox` |
| `PUT` (body crudo) | Token. Solo `.png .jpg .jpeg .gif .webp`, con firma del contenido verificada (*magic bytes*); si no, 415. Máximo `MAX_IMAGE_BYTES` (413); 400 si está vacío. Si el archivo existe y es de otro usuario, 403 |
| `DELETE` | Token; solo el dueño |

- **Archivos:** se guardan en `STORAGE_DIR/portfolios/`. El dueño se registra en un archivo oculto al lado, `.<nombre>.owner`. Los nombres que empiezan con `.` o contienen `/ \ \0` se rechazan, y se verifica que la ruta resuelta no salga de la carpeta.
- **Por qué la lista blanca:** el `Content-Type` lo elige el cliente. Sin ella, un `.html` o `.svg` servido desde el mismo dominio ejecutaría scripts y podría robar el token de `localStorage`.

### Chat (`POST /api/chat`, token opcional)

Puerta hacia el workflow de n8n del asistente ("Udela Conecta – Chatbot"). El front nunca habla con n8n.

| Paso | Comportamiento |
|---|---|
| Entrada | `{mensaje (1..1000), session_id (1..100)}`; un mensaje solo con espacios da 422. Otros campos del body se ignoran |
| Modo | Lo decide `get_current_user_optional`: sin token `invitado`, con token `usuario` + `{email, rol}` (rol = tabla de `buscar_perfil`, `""` si no tiene perfil). Un token inválido da 401 |
| Límite | `CHAT_MENSAJES_POR_MINUTO` por usuario o IP, en memoria de cada worker (429) |
| n8n | `POST N8N_CHAT_WEBHOOK_URL` con el header `X-Udela-Secret: N8N_CHAT_SECRET` y `{mensaje, session_id, modo, usuario, datos_url, token_herramientas}` (`token_herramientas` es `null` para invitados). Sin configuración: 503. Error, timeout o respuesta sin `respuesta`: 502 |
| Salida | `{message, data: {respuesta}}` |

El workflow tiene tres agentes (invitado, estudiante y empresa) y un Switch por `modo` y `rol`: `gerente` va al agente de empresa, cualquier otro usuario logueado al de estudiante y, ante cualquier valor raro, cae en invitado. La memoria de conversación vive en n8n por `session_id`; el widget genera uno nuevo al iniciar o cerrar sesión.

### Datos del asistente (`/api/chat/datos/*`, `routers/chat_datos.py`)

Endpoints de solo lectura que usan las herramientas HTTP del workflow. Devuelven resúmenes cortos (textos recortados, máximo 10 resultados) y nunca `telefono` ni `fecha_nacimiento`.

- **Token:** `create_chat_token(user_id, email)` firma un JWT con `aud="udela-chat"` que dura `CHAT_TOKEN_MINUTOS`. La dependencia `get_usuario_chat` exige esa audiencia, así que el token de sesión normal da 401 acá y el del asistente da 401 en el resto de la API (`decode_access_token` rechaza tokens con `aud`). El usuario sale siempre del token, nunca de un parámetro.

| Endpoint | Quién | Devuelve |
|---|---|---|
| `GET ofertas?texto=&modalidad=` | Público | Ofertas libres, sin postulantes ni pasante. La búsqueda ignora tildes, mayúsculas y palabras vacías ("de", "oferta"…) y también mira el nombre del proyecto |
| `GET mi-perfil` | Token del asistente | Rol, nombre, descripción, skills, idiomas, disponibilidad y portfolio (o el proyecto, si es gerente), más `faltantes` |
| `GET mis-postulaciones` | Estudiante (si no, 403) | Ofertas en las que se postuló con estado: `en revisión`, `asignado a vos` o `cubierto por otra persona` |
| `GET mis-ofertas` | Gerente | Sus ofertas con id, estado, cantidad de postulantes y pasante |
| `GET postulantes/{contrato_id}` | Gerente dueño de la oferta | Resumen de cada postulante. Si la oferta no existe o es de otra empresa: 404 (no revela cuáles existen) |
| `GET candidatos?skills=` | Gerente | Estudiantes disponibles ordenados por coincidencias con las skills (sin distinguir tildes ni mayúsculas) |

El agente invitado solo tiene la herramienta de ofertas; el de estudiante tiene ofertas, perfil y postulaciones, y el de empresa tiene perfil, sus ofertas, postulantes y candidatos. El workflow exportado (sin ids de credenciales) está en `infra/n8n/udela-chatbot.json`; se importa en n8n y se le asignan las credenciales `Udela-Secret` (Header Auth) y `DeepSeek account`. El n8n del VPS no llega a `localhost`, así que las herramientas solo funcionan contra producción.

### Otros

`GET /api/health` → `{status: "ok"}`. No pide token y se usa para chequear que el servicio está vivo.

## 6. Utilidades a reutilizar

| Función | Dónde | Para qué |
|---|---|---|
| `get_current_user` / `CurrentUser` | `core/security.py` | Usuario autenticado en un endpoint |
| `exigir_mismo_usuario(email, user)` | `core/security.py` | 403 si el recurso no es del token; devuelve el email normalizado |
| `normalizar_email` | `core/security.py` | `strip().lower()`: usarlo siempre al comparar emails |
| `aplicar_cambios(obj, datos, excluir)` | `schemas/serializacion.py` | Aplica solo columnas conocidas. Convierte `"true"/"false"` a bool, strings a int y CSV o JSON a lista, y trunca strings al largo de la columna |
| `a_dict(obj)` | `schemas/serializacion.py` | Fila → dict (fechas en ISO) |
| `buscar_perfil(db, email)` | `routers/usuarios.py` | `(tabla, perfil)` en cualquiera de las tablas de perfil |
| `comparar(perfil, requisitos)` | `dominio/compatibilidad.py` | Resultado determinista: coincidencia, nivel, listas y checklist. No toca la base ni la red |
| `sanitizar_requisitos(lista)` | `dominio/compatibilidad.py` | Normaliza y descarta requisitos inválidos antes de guardar |
| `texto_fallback(resultado)` | `dominio/compatibilidad.py` | Orientación determinista cuando n8n/IA no está disponible |
| `ruta_segura`, `tipo_por_extension`, `borrar_por_url` | `core/storage.py` | Manejo seguro de archivos |

## 7. Configuración (`core/config.py`)

Se lee de variables de entorno (y de `.env` si existe). La tabla completa con valores por defecto está en el README del backend. Los puntos clave:

- `JWT_SECRET_KEY` es **obligatoria**: si tiene menos de 32 caracteres o contiene `CAMBIAR`, el backend no arranca. Así se evita levantar producción con el valor de ejemplo.
- `DATABASE_URL` usa el driver async: `postgresql+asyncpg://…`.
- `CORS_ORIGINS`: en Docker local la arma el compose a partir de `FRONTEND_PORT`. En el VPS front y API comparten dominio, así que casi no se usa.
- `CHAT_DATOS_URL`: URL pública de `/api/chat/datos` para las herramientas de n8n; `setup-env.sh` la arma con el subdominio.
- `N8N_CHAT_WEBHOOK_URL` / `N8N_CHAT_SECRET`: opcionales; sin ellas el asistente responde 503 y el resto de la API funciona igual. En local van en `infra/local/.env.chat` (fuera de git).
- `N8N_ORIENTACION_WEBHOOK_URL`: opcional; sin ella `POST orientación` guarda fallback (no falla).
- `N8N_AUTOMATION_SECRET`: secreto compartido con n8n para `X-Udela-Secret` en orientación y digests. En local, `udela-local-secret` (`.env.local`, solo desarrollo).
- `N8N_ORIENTACION_TIMEOUT_SEGUNDOS`: timeout de la llamada a n8n (30 s por defecto).

## 8. Seed (`app/seeds/seed_demo.py`)

Idempotente y basado en datos: las listas `ESTUDIANTES` y `EMPRESAS` describen cada cuenta con su perfil, su portfolio, su proyecto y sus ofertas. Cada registro se busca por su clave natural (email, email del gerente o título de la oferta dentro del proyecto) y solo se crea si falta. Así, sumar una oferta a la lista y volver a correrlo la agrega a una base existente sin tocar lo que los usuarios cambiaron. Excepción deliberada: si una oferta existente quedó con `requisitos` vacíos (bases creadas antes de la migración `0004`), el seed los completa desde la lista sin pisar los requisitos que ya tenga cargados la empresa. `esta_ocupado` y `tiene_postulaciones` se derivan de `pasante_email` y `postulaciones`.

Crea 6 estudiantes y 4 empresas con 11 ofertas (9 libres), pensadas para que el asistente tenga qué responder: modalidades remota, híbrida y presencial, seniority de Trainee a Semisenior, postulaciones cruzadas, dos ofertas asignadas y una estudiante no disponible y sin portfolio. **Las 11 ofertas tienen requisitos** cargados con `_requisitos(...)`; los perfiles tienen habilidades declaradas para que el comparador devuelva resultados variados (0–100 %).

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

Contraseña de todos: `Udela1234!`. Corre en el arranque si `AUTO_SEED=true` (local sí, producción no).

## 9. Tests (`apps/backend/tests/`)

- **Herramientas:** pytest + `pytest-asyncio` (`asyncio_mode = auto`) + httpx `ASGITransport`.
- **Base:** `conftest.py` crea una SQLite en memoria (`StaticPool`) por test, reemplaza `get_db` y apunta `STORAGE_DIR` a una carpeta temporal.
- **Ayudante:** `registrar_usuario(email, rol)` devuelve los headers con el token.
- **Contenido:** 86 tests en 8 archivos:
  - `test_auth_usuarios.py`: registro, login, bloqueo, admin, privacidad y perfiles;
  - `test_proyectos_contratos.py`: dueño, postulación y asignación;
  - `test_portfolio_storage.py`: CRUD, imágenes y rechazo de archivos ejecutables;
  - `test_chat.py`: modo según el token (el body no lo cambia), secreto hacia n8n, validación, 502/503 y límite de mensajes. n8n se simula con `httpx.MockTransport` en `routers.chat._transporte`.
  - `test_chat_datos.py`: cada endpoint de `/api/chat/datos`, permisos por rol, 404 en ofertas ajenas, token vencido o con otra audiencia, y que no salgan `telefono` ni `fecha_nacimiento`.
  - `test_compatibilidad.py`: 12 tests del dominio (0 %, 100 %, nivel parcial, sinónimos, `se_aprende`, blandas, sin requisitos, duplicados, sanitización y fallback).
  - `test_postulaciones_informe.py`: 16 tests de API (historial, fallback, integración n8n, upsert, texto inválido/largo, 403 entre estudiantes y gerente, resultados de empresa, sin requisitos, privacidad, secreto y digests).
  - `test_seed.py`: el seed no duplica, completa ofertas que falten y requisitos vacíos sin pisar los que editó la empresa, y sus ofertas sirven para la búsqueda del asistente (sin tildes ni palabras vacías).
- **Límite:** SQLite ignora `FOR UPDATE`, así que los bloqueos de fila no se prueban acá. Sí se probaron contra Postgres en Docker.

Comandos: `npx nx test backend` o `cd apps/backend && poetry run pytest -v`. Sin dependencias locales, con la imagen ya construida:

```bash
docker run --rm -v "$PWD/apps/backend:/app" -w /app \
  --entrypoint python udela-local-backend:latest -m pytest -q
```

## 10. Cómo extender

- **Endpoint nuevo:** agregarlo al router del recurso (o crear `routers/<recurso>.py` e incluirlo en el loop de `main.py`). Usar `Depends(get_current_user)`, validar dueño con `exigir_mismo_usuario` y escribir con `aplicar_cambios`. Mantener el sobre `{message, data}` y los mensajes de error en español. Agregar tests.
- **Columna o tabla nueva:** editar `entities.py`, crear `alembic/versions/000N_<descripcion>.py` con `revision`/`down_revision`, correr `npx nx run backend:migrate` y `alembic check`.
- **Rol nuevo:** modelo nuevo y su entrada en `TABLAS_PERFIL`; el `POST /<rol>` se genera solo.

## 11. Limitaciones conocidas

- No hay refresh token: al vencer (7 días), el interceptor del front cierra la sesión y lleva al inicio.
- Login con Google: 501. Recuperar contraseña: no envía mail.
- El bloqueo de login es por cuenta, no por IP: alguien puede dejar bloqueada a otra persona 15 minutos.
- `is_admin` solo muestra links en la UI; no hay endpoints de administración.
- `GET contratos` muestra a cualquier usuario logueado los emails de los postulantes.
- Las imágenes viven en el volumen `storage` del servidor, no en un servicio de objetos. El backup del VPS las incluye (`infra/vps/backup-db.sh`).
