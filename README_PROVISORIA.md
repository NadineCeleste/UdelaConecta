# README PROVISORIO — Udela Conecta

> **Rama:** `provisoria` (antes `feat/udela-site-despliegue`).
> **Base:** `feat/compatibilidad` (`79bf445`). La rama **no** se mergea a `main`.
> **Estado:** alternativa independiente funcionando en el servidor `.79` y en el n8n existente, verificada el 2026-11-11.
> **Este documento no reemplaza al [README.md](./README.md) principal.** El README principal describe el proyecto; este documento es el handoff técnico de la rama provisoria para que una IA pueda adaptar `main` sin romper la infraestructura, el servidor, el n8n ni los workflows existentes.
> **Workflows de la alternativa:** [`infra/n8n/provisoria/`](./infra/n8n/provisoria/). Los `infra/n8n/*.json` existentes (base de `main`) se preservan; si `main` tiene otra versión, se conserva la de `main`.

---

## 1. Para una IA: leer esto primero

Si se te pidió adaptar `main` a esta alternativa:

1. Leé este documento completo, el [README.md](./README.md) y `context_agent/AGENTS.md`.
2. Revisá `context_agent/n8n.md`, pero tené en cuenta que **quedó desactualizado**: describe DeepSeek y SMTP. La carpeta `infra/n8n/provisoria` usa **Gemini** y un digest **sin email**; los `infra/n8n/*.json` de la base siguen en DeepSeek/SMTP.
3. Inspeccioná primero `main`, `infra/vps`, `infra/local`, `infra/n8n` (workflows existentes de `main`), `infra/n8n/provisoria` (workflows de la alternativa), `apps/backend` y `apps/frontend`.
4. Creá una rama nueva desde `main`; **no mergees `provisoria`** ni pises la infraestructura existente.
5. Portá también los **26 archivos de front/back** de la base y la migración `0004` (Paso 1.5); después los cambios por archivo y por nodo, con backup previo de los workflows n8n. Los workflows de la alternativa están en `infra/n8n/provisoria/`; los `infra/n8n/*.json` existentes de `main` se preservan. No importes nada sobre el n8n vivo sin exportar antes.
6. No commitees secretos, no borres volúmenes, no toques el túnel de Cloudflare y no ejecutes `docker compose down -v`.
7. Verificá todo con la checklist de la sección 11 y reportá qué se preservó y qué se adaptó.

La rama `provisoria` es una **foto reproducible** de una alternativa que ya funciona. El servidor `.79`, la base de n8n, las credenciales, el túnel y los datos **no están en Git**.

---

## 2. Resumen ejecutivo

Esta rama agrega una alternativa de despliegue independiente y deja los workflows n8n que funcionan en una carpeta aditiva, sin reemplazar los existentes de `main`:

- Sitio propio con **Postgres propio**, **Caddy**, backend y storage, sin tocar el backend oficial.
- n8n existente y externo al compose del sitio.
- Los workflows de la alternativa están en `infra/n8n/provisoria/`; los `infra/n8n/*.json` existentes de `main` no se reemplazan.
- Chatbot y orientación de la carpeta `provisoria` con **Google Gemini**; los workflows existentes de `main` quedan en DeepSeek.
- `webhookId` explícito en los webhooks para que las rutas sean estables (`udela-chat`, `udela-orientacion`).
- Digest semanal **sin email y sin SMTP**: el nodo `emailSend` se eliminó y los mensajes quedan en el nodo `Reporte interno` de la ejecución de n8n.
- Sin cambios de código respecto de la base: la rama usa el código de `feat/compatibilidad`; frente a `main`, esa base aporta **26 archivos de front/back y la migración `0004`** (sección 3.2).

---

## 3. Archivos que cambia esta rama

Los cambios funcionales propios de `provisoria` son estos:

| Archivo | Cambio |
|---|---|
| `README_PROVISORIA.md` | Este handoff. |
| `README.md` | Solo un puntero al handoff; no se reemplazó el README principal. |
| `.gitignore` | Excepción para versionar `infra/udela-site/.env.example`. |
| `infra/udela-site/docker-compose.yml` | Compose independiente: Caddy + backend + Postgres + volúmenes propios. |
| `infra/udela-site/.env.example` | Variables necesarias, con placeholders; **sin secretos reales**. |
| `infra/n8n/provisoria/udela-chatbot.json` | Workflow de la alternativa: Gemini, credencial Gemini y `webhookId`. |
| `infra/n8n/provisoria/udela-orientacion.json` | Workflow de la alternativa: Gemini, `maxOutputTokens: 4096`, modelo `gemini-3.5-flash` en `Validar` y `webhookId`. |
| `infra/n8n/provisoria/udela-digest.json` | Workflow de la alternativa: sin `emailSend`; `Reporte interno` (`noOp`) en la rama “hay novedades”; nota sin SMTP. |

Los archivos `infra/n8n/udela-chatbot.json`, `infra/n8n/udela-orientacion.json` e `infra/n8n/udela-digest.json` **no cambian en esta rama respecto de la base**: son los workflows existentes de la línea de `main` (DeepSeek/SMTP) y se preservan. Si `main` tiene otra versión de esos archivos, comparar con `git diff main...provisoria -- infra/n8n/udela-*.json`; no pisar. La carpeta `infra/n8n/provisoria/` es aditiva.

Para ver exactamente lo propio de esta rama:

```bash
git diff feat/compatibilidad...provisoria -- \
  .gitignore infra/n8n/provisoria infra/udela-site README.md README_PROVISORIA.md
```

No uses `git diff main...provisoria` como si fueran solo estos archivos: la rama sale de `feat/compatibilidad`, así que el diff contra `main` incluye también el historial de esa base.

**No hay cambios en `apps/backend` ni en `apps/frontend` respecto de la base `feat/compatibilidad`.** Pero la base sí está adelante de `main`: aporta **26 archivos de front/back y la migración `0004`**, que hay que portar si `main` no los tiene (ver 3.2). El compose nuevo usa los Dockerfiles existentes de `infra/vps/`.

### 3.1 Carpeta canónica de workflows

La carpeta que debe leer la IA es `infra/n8n/provisoria/`:

| Archivo | Uso |
|---|---|
| `infra/n8n/provisoria/udela-chatbot.json` | Chatbot con Gemini y `webhookId`. |
| `infra/n8n/provisoria/udela-orientacion.json` | Orientación con Gemini y `webhookId`. |
| `infra/n8n/provisoria/udela-digest.json` | Digest semanal sin email. |

Importá esos tres JSON si vas a usar la variante Gemini. Si `main` usa DeepSeek, no los importes a ciegas: usá los `infra/n8n/udela-*.json` existentes y portá solo los cambios (`webhookId`, digest sin email), o reemplazá los nodos Gemini por los DeepSeek. En ningún caso pises los workflows existentes.

### 3.2 Cambios heredados de `feat/compatibilidad` (front/back y migración)

`provisoria` no solo agrega infraestructura y workflows: también hereda la base `feat/compatibilidad`, que está adelante de `main`. Si `main` no tiene esos cambios, hay que portarlos además de los 8 archivos propios.

`git diff --stat main...provisoria -- apps/backend apps/frontend` muestra **26 archivos**:

- Backend (15): `app/dominio/compatibilidad.py`, `app/routers/postulaciones.py`, cambios en `routers/contratos.py`, `models/entities.py`, `core/config.py`, `app/main.py`, `seeds/seed_demo.py`, `requirements.txt`, tests y la migración `alembic/versions/0004_requisitos_e_informes.py`.
- Frontend (11): `contrato-detail`, `contratos`, `formcreatecontract`, `models/contrato.ts` y `servicios/contrato.ts`.

La migración `0004` **no existe en `main`**. El entrypoint de `main` ejecuta `alembic upgrade head`, así que se aplica al desplegar; aun así, respaldá la base antes. La base sigue siendo la de `main`; no se crea otra.

```bash
git diff --stat main...provisoria -- apps/backend apps/frontend
git diff main...provisoria -- apps/backend apps/frontend
```

El diff completo contra `main` incluye además docs/context e `infra/local`/`infra/n8n` de la base; para la aplicación, los 26 archivos de front/back son los relevantes.

### 3.3 Secretos, `.env` y credenciales

- La rama **no contiene secretos**: ni `.env` real, ni API keys, ni passwords, ni valores de credenciales.
- Asume que `main` ya maneja su `.env`, su base, su n8n y sus credenciales de DeepSeek. No hay que copiar secretos de `.79`.
- `infra/udela-site/.env.example` es solo una **referencia de nombres**; no copiar valores.
- Los JSON de n8n referencian credenciales por ID/nombre de la instancia `.79`. En el n8n de `main` hay que **reasignar** esas credenciales a las existentes; no se importan valores.
- Si `main` ya tiene `.env`, conservalo y agregá solo las variables nuevas que falten (sección 8). No reemplaces `DATABASE_URL` si la base sigue siendo la de `main`.

---

## 4. Entorno que ya está funcionando (no versionado)

### 4.1 Servidor

| Dato | Valor actual |
|---|---|
| Host | `192.168.0.79` (`asustornas`) |
| Proyecto del sitio | `/mnt/asustor_data/25-DOCKER/udela-site` |
| Compose vivo | `docker-compose.yml` con contexto `./repo` |
| Contenedores | `udela-site-caddy`, `udela-site-backend`, `udela-site-db` |
| Puerto del sitio | `8083:80` |
| Frontend público | `https://udela.rsdev.dev` |
| Túnel | Proyecto `cloudflare-tunnel`; ruta `udela.rsdev.dev → http://192.168.0.79:8083` |
| Entrada | Sin puertos entrantes; solo túnel saliente de Cloudflare |
| Postgres del sitio | Volumen `udela-site_pgdata`; storage `udela-site_storage` |
| Red | `udela-site_udela_site_net` |

El servidor `.79` también tiene otros servicios ajenos a este proyecto (n8n, n8n-postgres, etc.). **No tocar** `cloudflare-tunnel` ni los servicios existentes.

### 4.2 n8n existente

| Dato | Valor actual |
|---|---|
| n8n | `http://192.168.0.79:5678`, versión `2.47.4` |
| Postgres de n8n | Contenedor `n8n-postgres`, base propia de n8n |
| Workflow chatbot | `7uuxfIoT8imbHS6Y` — “Udela Conecta – Chatbot”, 22 nodos |
| Workflow orientación | `1epPjy0Izn5lyoJN` — “Udela Conecta – Orientación de postulación”, 12 nodos |
| Workflow digest | `M786FTD5YW6Ra8uM` — “Udela Conecta – Digest de oportunidades”, 7 nodos |
| Credencial header auth | `Udela-Secret` (`AzvZGgZ1GBzJhT8m`), header `X-Udela-Secret` |
| Credencial Gemini | `Google Gemini account` (`pPSPPwkECDHd2vKi`), tipo `googlePalmApi` |
| Webhook chatbot | `POST /webhook/udela-chat`, `webhookId = d86c2ab1-8053-4fbe-ba83-b3fafb590449` |
| Webhook orientación | `POST /webhook/udela-orientacion`, `webhookId = 61b49f04-dc99-43f1-9464-ed9edf675f7b` |
| Schedule digest | Lunes 09:00, `America/Argentina/Buenos_Aires` |
| API pública | `/api/v1`, header `X-N8N-API-KEY` |

Los IDs de workflow y de credenciales son **referencias de esta instancia**, no secretos. En otra instancia hay que crear credenciales nuevas y ajustar los IDs; los JSON de `infra/n8n/provisoria/` solo referencian las credenciales por ID/nombre. Los `infra/n8n/*.json` del repo se preservan como están en la base (DeepSeek/SMTP); si `main` tiene otra versión, se conserva la de `main`. La carpeta `provisoria` es la que aporta la variante Gemini/sin email.

El compose de n8n vive fuera de este repo, en `/mnt/asustor_data/25-DOCKER/n8n/`. Tiene dos ajustes necesarios que **no** están en la rama:

- `UDELA_BACKEND_URL=http://192.168.0.79:8083`
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (para que el digest pueda leer `$env.UDELA_BACKEND_URL`)

Hay un backup del compose de n8n en `docker-compose.yml.bak.20261111`.

### 4.3 Backend y frontend del sitio

- Backend FastAPI con `uvicorn`, varios workers, `STORAGE_DIR=/data/storage`.
- Caddy sirve el build de Angular y hace proxy de `/api/*` y `/storage/*` a `backend:3000`.
- El frontend de producción usa rutas relativas (`/api/`, `/storage`), por eso un solo origen y sin CORS.
- Los endpoints relevantes:
  - `GET /api/health`
  - `POST /api/auth/login`
  - `POST /api/chat` (el backend decide el modo según el JWT)
  - `GET|POST /api/postulaciones/{contrato_id}/orientacion`
  - `GET /api/automatizacion/digests` (requiere `X-Udela-Secret`)
  - `GET /api/chat/datos/*` (token de 5 minutos)

### 4.4 Verificación hecha al cerrar la rama

- Frontend: `200`.
- `/api/health`: `200`.
- Login: `200`.
- Chat autenticado y chat invitado: `200` con respuesta real.
- Orientación: `200`, guardada, modelo `gemini-3.5-flash`.
- Webhooks de chat y orientación: `403` sin header (están registrados y exigen autenticación).
- Digest: `200` con `{"count":0,"data":[]}`.
- Workflow digest activo; `emailSend` ausente en draft y en versión publicada; `Reporte interno` presente.
- Key temporal de la API de n8n eliminada.
- Contenedores del sitio y `n8n`/`n8n-postgres` arriba.

Revalidar estos puntos antes de desplegar en otro entorno; el estado puede cambiar.

---

## 5. Invariantes: qué se debe preservar

Al adaptar `main`, preservar sin excepciones:

1. **La infraestructura existente de `main`**: `infra/vps`, `infra/local`, sus compose, Caddy, Postgres, volúmenes y dominios. La carpeta `infra/udela-site` es **adicional/alternativa**, no un reemplazo.
2. **El servidor `.79`**: no cambiar sus puertos, servicios, túnel ni `.env` mientras se prueba otra cosa. Para probar, usar otro proyecto/ puerto/entorno.
3. **El n8n y su Postgres**: no borrar workflows, credenciales, ejecuciones ni la base. Exportar antes de importar.
4. **Los workflows existentes en Git**: los `infra/n8n/*.json` de `main` no se tocan en esta rama y deben preservarse. Los workflows de la alternativa están en `infra/n8n/provisoria/`; importarlos/adaptarlos sin sobrescribir los existentes. Si `main` usa DeepSeek, se puede mantener DeepSeek reemplazando los nodos Gemini, o partir de los workflows de `main` y agregar solo los cambios (`webhookId`, digest sin email, conexiones).
5. **Los secretos**: `.env`, credenciales de n8n, API keys de Gemini, JWT, passwords de Postgres y secretos de webhooks **no se versionan**.
6. **Cloudflare**: el túnel y la ruta `udela.rsdev.dev` son externos al repo; no se tocan.
7. **Los volúmenes**: `udela-site_pgdata`, `udela-site_storage` y la base de n8n contienen datos; no usar `down -v`, `docker volume rm` ni recrear la base sin backup.

---

## 6. Receta para adaptar `main`

### Paso 0 — Enfoque recomendado: reutilizar y ampliar la infraestructura de `main`

La infraestructura de `main` ya maneja las variables de base de datos, n8n y DeepSeek. **No hace falta crear otra infraestructura completa**: usá esa base y amplíala.

- Conservá el `.env`, Postgres, n8n, credenciales y variables existentes de `main`.
- Agregá solo servicios, volúmenes, puertos o variables que falten; no dupliques DB ni n8n.
- Tomá `infra/udela-site/` como **referencia** de la alternativa independiente, no como obligación de copiar todo.
- Importá/adaptá los workflows de `infra/n8n/provisoria/`. Si `main` usa DeepSeek, mantené DeepSeek y reemplazá los nodos Gemini, o partí de los workflows de `main` y agregá solo los cambios. Si no hay DeepSeek, creá la credencial Gemini.
- El objetivo es que `main` siga funcionando; esta rama es la referencia, no un reemplazo.

### Paso 1 — Rama de trabajo y diagnóstico

```bash
git switch main
git switch -c feat/adaptar-provisoria
git log -1 --oneline
ls infra
```

Leer y registrar:

- `README.md` y `context_agent/AGENTS.md`.
- `context_agent/n8n.md` (recordar que está desactualizado en DeepSeek/SMTP).
- `infra/vps/docker-compose.prod.yml`, `infra/vps/Dockerfile.*`, `infra/vps/Caddyfile`.
- `infra/local/docker-compose.yml` y `infra/local/.env.local`.
- Los JSON actuales de `infra/n8n/` en `main`.

No continuar sin haber identificado qué infraestructura de `main` ya está en uso y cuáles son los workflows/credenciales vivos.

### Paso 1.5 — Portar front/back y migración (si `main` no los tiene)

La rama hereda de `feat/compatibilidad` **26 archivos** de `apps/backend`/`apps/frontend` y la migración `0004`. Si `main` no los tiene, copiar solo `infra/` deja la aplicación incompleta.

```bash
git diff --stat main...provisoria -- apps/backend apps/frontend
git diff main...provisoria -- apps/backend apps/frontend
```

Si `main` no tiene cambios propios en esas rutas, se puede traer el árbol completo y revisar:

```bash
git checkout provisoria -- apps/backend apps/frontend
```

Si `main` ya tiene cambios propios en front/back, **no usar ese checkout a ciegas**: hacer merge por archivo. Después:

- Revisar `apps/backend/alembic/versions/0004_requisitos_e_informes.py`; el entrypoint de `main` ejecuta `alembic upgrade head`. Respaldar la base antes; la base sigue siendo la de `main`.
- Ejecutar tests/build de `main` (`apps/backend` y `apps/frontend`) antes de desplegar.
- No tocar el `.env` ni las credenciales de `main`; solo agregar variables faltantes.

### Paso 2 — Portar la infraestructura sin pisar la existente

La referencia de infraestructura está en `infra/udela-site/` y los workflows en `infra/n8n/provisoria/`. Para llevarlos a `main`:

```bash
git checkout provisoria -- infra/udela-site infra/n8n/provisoria .gitignore
```

Los `infra/n8n/*.json` existentes no se copian ni se pisan; la carpeta `provisoria` es la que aporta los workflows de la alternativa.

Después revisar y adaptar:

- `docker-compose.yml` usa `context: ../..` (la raíz del repo) y los Dockerfiles de `infra/vps/`.
- Si `main` ya tiene un deploy en `infra/vps`, **no reemplazarlo**: agregar `infra/udela-site` como opción separada o fusionar solo lo que corresponda.
- Cambiar `container_name`, nombre de proyecto, puerto (`8083`) o red si se va a levantar en el mismo host que otra instancia.
- Si usás el compose de referencia, creá un `.env` local a partir de `.env.example`; si reutilizás `main`, usá su `.env` y no copies secretos. El `.env` no se commitea.
- Mantener `DOMAIN: ":80"` y el proxy de Caddy si se usa el túnel; si `main` tiene otro esquema de dominios, adaptar el `Caddyfile`/puerto, no romper el existente.

Validar el compose antes de levantar:

```bash
# Solo para el compose de referencia: crear un .env local; no copiar secretos de main.
# Si reutilizás main, usá su .env y no ejecutes este cp.
cp infra/udela-site/.env.example infra/udela-site/.env
docker compose -f infra/udela-site/docker-compose.yml config >/dev/null
```

### Paso 3 — n8n: backup, merge y publicación

**Antes de tocar el n8n vivo:**

1. Exportar/descargar los tres workflows actuales desde la UI de n8n (o con `n8n export:workflow` a un archivo) y guardar una copia fuera del repo.
2. Exportar/ respaldar la base de n8n o al menos los workflows y credenciales.
3. Comparar los nodos actuales de `main`/n8n con los de `infra/n8n/provisoria/`; no reemplazar a ciegas.

Para usar los JSON de `infra/n8n/provisoria/`:

- Son **plantillas de un solo workflow**, con `active: false`, pensadas para importar.
- Los `infra/n8n/*.json` existentes de `main` se preservan. Si `main` usa DeepSeek, podés mantener sus nodos LLM y portar solo los cambios (`webhookId`, digest sin email, conexiones); si preferís la variante Gemini, reemplazá los nodos DeepSeek por los Gemini de la carpeta.
- Incluyen los `webhookId`, los IDs de nodos y las referencias a credenciales; **no** incluyen la API key de Gemini ni los valores de las credenciales.
- Importar desde la UI (`Workflows → Import from file`) o con `n8n import:workflow --separate`; no importar el export crudo en array, porque el importador puede rechazarlo.
- Después de importar, **publicar** desde la UI o con `POST /api/v1/workflows/{id}/publish` usando una API key temporal. **No usar `n8n publish:workflow` por CLI**: actualiza la base pero no refresca el caché de webhooks del proceso vivo y los webhooks responden 404 hasta reiniciar.
- Verificar que el `webhookId` siga siendo el mismo y que las rutas `udela-chat`/`udela-orientacion` coincidan con las URLs del backend.
- Crear o asignar las credenciales:
  - `Udela-Secret`: Header Auth, header `X-Udela-Secret`.
  - `Google Gemini account`: `googlePalmApi`, si se usa la variante Gemini.
  - Si `main` ya tiene DeepSeek, usar la credencial DeepSeek existente y ajustar el modelo en el nodo `Validar` de orientación.
- En el entorno actual la misma credencial `Udela-Secret` la usan chat, orientación y digest. Asegurar que su valor coincida con `N8N_CHAT_SECRET` y `N8N_AUTOMATION_SECRET` del backend; si se usan secretos distintos, crear credenciales separadas o ajustar los workflows.
- Mantener `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` y `UDELA_BACKEND_URL` en el compose de n8n si el digest usa `$env.UDELA_BACKEND_URL`.

### Paso 4 — Variables de entorno

Si reutilizás la infraestructura de `main`, partí de su `.env` y agregá solo las variables que falten. El backend del compose de referencia lee `infra/udela-site/.env`; completar, como mínimo:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- `DATABASE_URL` con la misma password y host `postgres`.
- `JWT_SECRET_KEY`.
- `CORS_ORIGINS` con el dominio real.
- `N8N_CHAT_WEBHOOK_URL`, `N8N_ORIENTACION_WEBHOOK_URL`.
- `N8N_CHAT_SECRET`, `N8N_AUTOMATION_SECRET`.
- `CHAT_DATOS_URL` con una URL públicamente alcanzable por n8n.
- `CHAT_TOKEN_MINUTOS`, timeouts.

No copies el `.env` de `main` sin revisar; no commitees el `.env`; no imprimas sus valores en logs.

### Paso 5 — Deploy y verificación

Si reutilizás la infraestructura de `main`, ejecutá su compose y agregá solo los servicios nuevos. El comando siguiente es el del compose de referencia `infra/udela-site`:

```bash
cd infra/udela-site
docker compose --env-file .env up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8083/api/health
```

Luego:

- Abrir el frontend y verificar login/registro.
- Probar chat autenticado y chat invitado.
- Probar orientación.
- Probar webhooks sin header (deben dar `403`, no `404`).
- Probar el digest con el secreto en una variable de entorno, sin imprimirlo.
- Revisar en n8n que las ejecuciones lleguen y que el digest use `Reporte interno` (sin email).
- Confirmar que no hay un nodo `emailSend` en el workflow vivo.

### Paso 6 — Rollback

- `docker compose -f infra/udela-site/docker-compose.yml down` (sin `-v`).
- Restaurar los workflows n8n exportados antes del cambio; los `infra/n8n/*.json` existentes no se modifican.
- No borrar volúmenes ni la base; no tocar Cloudflare.
- La instancia vieja de `main`/`.79` debe seguir funcionando si no se modificó.

---

## 7. Detalle de los workflows n8n

### 7.1 Chatbot (`infra/n8n/provisoria/udela-chatbot.json`)

- 22 nodos; tres agentes: invitado, estudiante y empresa.
- Nodos LLM: `Gemini Invitado`, `Gemini Estudiante`, `Gemini Empresa` (`@n8n/n8n-nodes-langchain.lmChatGoogleGemini`).
- Credencial `Google Gemini account` (`googlePalmApi`).
- `maxOutputTokens`: 1200 invitado, 1600 estudiante y empresa en el estado actual.
- Webhook `Webhook Chat Udela` con `webhookId = d86c2ab1-8053-4fbe-ba83-b3fafb590449`, path `udela-chat`.
- No quedan nodos DeepSeek en este workflow de la carpeta `provisoria`; los `infra/n8n/*.json` existentes de `main` sí usan DeepSeek.
- Las herramientas HTTP siguen apuntando a `/api/chat/datos/*` con el token de 5 minutos.

### 7.2 Orientación (`infra/n8n/provisoria/udela-orientacion.json`)

- 12 nodos.
- `Gemini Orientación` (`lmChatGoogleGemini`), `maxOutputTokens: 4096`.
- El código del nodo `Validar` devuelve `modelo: 'gemini-3.5-flash'`.
- Webhook `Webhook Orientación` con `webhookId = 61b49f04-dc99-43f1-9464-ed9edf675f7b`, path `udela-orientacion`.
- No quedan nodos DeepSeek en este workflow; los `infra/n8n/*.json` existentes de `main` sí usan DeepSeek.
- Si se reutiliza DeepSeek en `main`, reemplazar `Gemini Orientación` por el nodo DeepSeek existente y actualizar el `Validar` con el modelo DeepSeek.
- El backend guarda el texto y el modelo en `informe_postulacion`; si el modelo se cambia, actualizar el `Validar` para que el valor guardado sea correcto.

### 7.3 Digest (`infra/n8n/provisoria/udela-digest.json`)

- 7 nodos.
- `Schedule` → `Obtener digests` → `Preparar mensajes` → `¿Hay novedades?`.
- Rama verdadera: `Reporte interno` (`noOp`).
- Rama falsa: `Sin novedades` (`noOp`).
- **No hay `emailSend`, no hay credencial SMTP, no hay `UDELA_DIGEST_FROM`.**
- Los mensajes preparados quedan visibles en la ejecución de n8n, en `Reporte interno`.
- El digest hace `GET /api/automatizacion/digests` con `X-Udela-Secret`.
- `count: 0` es un tema de datos, no de SMTP: el backend solo devuelve ofertas libres con más de 60% de coincidencia y el estudiante no debe haberse postulado. Con los datos de demo actuales no hay casos que superen ese umbral.

### 7.4 Importación y publicación

- Los JSON de `infra/n8n/provisoria/` tienen `active: false` y no tienen `id` de workflow; al importarlos se crean workflows nuevos.
- Los `infra/n8n/*.json` existentes de `main` no se tocan. Si querés conservar los IDs vivos, importá/adaptá sobre esos workflows desde la UI y publicá; no borres los originales.
- La importación CLI `--separate` espera un workflow por archivo; los JSON de la carpeta `provisoria` cumplen eso.
- Publicar siempre por UI o API pública; el CLI de publish no refresca webhooks.
- Tras publicar, probar `POST /webhook/udela-chat` y `POST /webhook/udela-orientacion` sin header: deben dar `403`, no `404`.

### 7.5 Ruta DeepSeek (si `main` conserva sus IA)

La carpeta `provisoria` usa Gemini. Para mantener DeepSeek en `main`:

1. Partí de los workflows DeepSeek de `main` (o de `infra/n8n/udela-*.json` de la base); no importes Gemini a ciegas.
2. Agregá `webhookId` a los nodos webhook para que las rutas sean estables: `udela-chat` y `udela-orientacion`. Los valores de referencia están en 7.1 y 7.2; si `main` ya tiene otros, mantené los suyos y verificá que las rutas coincidan con el backend.
3. En el digest, reemplazá `emailSend` por `Reporte interno` (`noOp`); conectá la rama verdadera del IF a `Reporte interno` y la falsa a `Sin novedades`. Eliminá la credencial SMTP y `UDELA_DIGEST_FROM`.
4. Mantené el nodo y la credencial DeepSeek existentes; en orientación, el `Validar` debe devolver el modelo DeepSeek real. No crees una credencial Gemini si `main` conserva DeepSeek.
5. Compará las conexiones con `infra/n8n/provisoria/` para no perder los cambios; publicá por UI/API y verificá que los webhooks den `403` sin header.

---

## 8. Variables de entorno del sitio

Referencia: `infra/udela-site/.env.example`. Los valores reales viven en el `.env` del servidor y no se versionan.

La rama no trae secretos. Si `main` ya tiene su `.env`, base, n8n y credenciales de DeepSeek, conservalos; usá esta tabla solo para detectar variables nuevas. El `DATABASE_URL` del ejemplo apunta al Postgres del compose independiente (`postgres`); si usás la base de `main`, conservá el `DATABASE_URL` de `main`.

| Variable | Para qué |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres propio del compose. |
| `DATABASE_URL` | Conexión asyncpg al servicio `postgres`; debe usar la misma password. |
| `JWT_SECRET_KEY` | Firma de sesiones. |
| `STORAGE_DIR` | Directorio de storage dentro del contenedor. |
| `PUBLIC_STORAGE_BASE_URL` | Prefijo público de archivos (`/storage`). |
| `CORS_ORIGINS` | Orígenes permitidos; incluir el dominio real. |
| `AUTO_SEED` | Dejar `false` en producción. |
| `WEB_CONCURRENCY` | Workers de uvicorn. |
| `N8N_CHAT_WEBHOOK_URL` / `N8N_ORIENTACION_WEBHOOK_URL` | URLs de los webhooks de n8n. |
| `N8N_CHAT_SECRET` / `N8N_AUTOMATION_SECRET` | Secretos compartidos con la credencial `Udela-Secret`. |
| `CHAT_DATOS_URL` | URL pública que el backend entrega a n8n para leer datos del chat. |
| `CHAT_TOKEN_MINUTOS` | Vigencia del token de lectura. |
| `N8N_CHAT_TIMEOUT_SEGUNDOS` / `N8N_ORIENTACION_TIMEOUT_SEGUNDOS` | Timeouts hacia n8n. |

Si `CHAT_DATOS_URL` no es alcanzable desde n8n, el chat con sesión falla aunque el webhook esté bien. Si los secretos no coinciden, n8n responde `403`.

---

## 9. Decisiones tomadas en esta alternativa

- El sitio nuevo tiene **Postgres propio**; no usa la base del backend oficial ni la de n8n.
- El n8n es el existente y queda **externo** al compose del sitio.
- El frontend y el backend se sirven desde el mismo origen (Caddy) para evitar CORS.
- El túnel de Cloudflare es la única entrada pública; no se abren puertos entrantes.
- Gemini reemplaza a DeepSeek por disponibilidad de cuota/API.
- El digest no depende de una cuenta de correo: se eliminó el envío y se conserva el reporte interno.
- La carpeta `infra/n8n/provisoria/` es aditiva: no reemplaza los `infra/n8n/*.json` de `main`; si se reutiliza DeepSeek, la IA adapta los nodos LLM.
- La infraestructura de `main` se reutiliza y amplía; `infra/udela-site/` es la referencia de la alternativa independiente, no un reemplazo obligatorio.
- La rama es **provisoria**: sirve para portar la alternativa a `main`, no para mergear directamente.

---

## 10. Limitaciones conocidas

- El digest devuelve `count: 0` con los datos de demo actuales por el umbral `> 60`; no es un fallo de SMTP.
- No hay backups automáticos de `udela-site_pgdata`, `udela-site_storage` ni de la base de n8n.
- No hay monitoreo/alertas ni CI/CD para este despliegue.
- No se hizo QA completo de todos los flujos (registro, portfolio, proyectos, storage, empresa).
- Los JSON de `infra/n8n/provisoria/` incluyen IDs de nodos/credenciales específicos de la instancia; al portarlos a otra instancia hay que recrear credenciales y revisar los IDs.
- Los `infra/n8n/*.json` de la base siguen en DeepSeek/SMTP; la carpeta `provisoria` no los reemplaza.
- `context_agent/n8n.md` y el README principal todavía describen DeepSeek/SMTP; este documento es la referencia del estado provisorio.
- La rama sale de `feat/compatibilidad`, no de `main`; para aislar los cambios propios usar el diff de la sección 3.
- El inventario de 26 archivos de front/back es el de la base `feat/compatibilidad`; si `main` tiene cambios propios en esas rutas, el merge es manual.
- La autenticación de la API de n8n usada para publicar fue una key temporal; ya fue eliminada. Si hace falta, crear una nueva y borrarla al terminar.

---

## 11. Checklist de aceptación para la IA

- [ ] Leí `README_PROVISORIA.md`, `README.md` y `context_agent/AGENTS.md`.
- [ ] Identifiqué la infraestructura existente de `main` y del servidor.
- [ ] Exporté/backupeé los workflows y la base de n8n antes de tocar nada.
- [ ] Creé una rama desde `main`; no mergeé `provisoria`.
- [ ] Porté los 26 archivos de front/back de la base (o verifiqué que `main` ya los tiene) y apliqué la migración `0004` con backup.
- [ ] Porté `infra/udela-site` como referencia y amplié la infraestructura de `main` sin reemplazar `infra/vps`/`infra/local` ni duplicar DB/n8n.
- [ ] Conservé el `.env` y las credenciales de `main`; agregué solo las variables faltantes y no commiteé secretos.
- [ ] Importé/adapté los workflows de `infra/n8n/provisoria` y preservé los `infra/n8n/*.json` existentes.
- [ ] Si `main` usa DeepSeek, mantuve DeepSeek y adapté los nodos LLM; si no, creé `Google Gemini account`.
- [ ] Creé/asigné `Udela-Secret` y la credencial LLM que corresponda.
- [ ] Publiqué desde UI/API, no con `n8n publish:workflow` CLI.
- [ ] Los webhooks dan `403` sin header y funcionan con el backend.
- [ ] Chat, orientación y digest responden.
- [ ] El digest no tiene `emailSend` ni SMTP.
- [ ] Frontend y `/api/health` responden `200`.
- [ ] No hay secretos en el diff.
- [ ] Probé el rollback sin borrar volúmenes.
- [ ] Actualicé la documentación de `main` (o dejé este handoff como referencia).

---

## 12. Referencias

- [README.md](./README.md) — README principal del proyecto.
- `context_agent/AGENTS.md` — contexto para agentes de IA.
- `context_agent/n8n.md` — workflows n8n (desactualizado en DeepSeek/SMTP).
- `context_agent/context_front.md`, `context_agent/audit_front.md`, `context_agent/endpoint.md`.
- `infra/vps/` — infraestructura de producción existente.
- `infra/local/` — entorno local.
- `feat/compatibilidad` — base de `provisoria`; aporta los 26 archivos de front/back y la migración `0004`.
- `infra/n8n/` — workflows existentes de la base (DeepSeek/SMTP); no se reemplazan.
- `infra/n8n/provisoria/` — workflows de la alternativa (Gemini, `webhookId`, digest sin email); importar desde acá.
- `infra/udela-site/` — compose y `.env.example` de la alternativa independiente; referencia para ampliar la infraestructura de `main`.
