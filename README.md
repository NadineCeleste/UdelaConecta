# HunTech · Udela Conecta

**La bolsa de trabajo IT de la Universidad de la Ciudad de Buenos Aires.** Una plataforma que conecta a estudiantes y graduados de la universidad con empresas que buscan talento para dar sus primeros pasos en el mundo laboral tecnológico.

> *Una herramienta de Udela Ciudad, hecha por estudiantes para estudiantes.*

---

## La problemática

Conseguir el **primer empleo IT** es el escalón más difícil de la carrera. Quien estudia sistemas o desarrollo de software suele quedar atrapado en un círculo conocido:

- **Las ofertas piden experiencia, y la experiencia solo se consigue trabajando.** Los avisos "junior" exigen años de trayectoria que un estudiante todavía no puede tener.
- **El talento de la universidad no se ve.** Los proyectos que se hacen en la cursada (apps, APIs, sistemas completos) quedan en un repositorio o en una entrega, sin llegar a quien está contratando.
- **Las búsquedas generales no están pensadas para quien recién empieza.** En los portales masivos un perfil sin experiencia compite con miles de postulantes y queda afuera en los primeros filtros.
- **Falta orientación.** Cómo armar un CV, qué preguntan en una entrevista junior o cómo mostrar un portfolio son cosas que se aprenden a prueba y error.

Del otro lado, las **empresas** que quieren sumar perfiles junior no tienen un canal directo con la universidad: dependen de agencias, de procesos largos o de filtrar cientos de postulaciones sin saber de dónde viene cada candidato.

## La solución

HunTech es un espacio propio de la universidad donde **el conocimiento que se comparte en las aulas se transforma en una herramienta real de inserción laboral**.

- **Para estudiantes y graduados:** un perfil profesional con habilidades, idiomas, disponibilidad y un **portfolio de hasta tres proyectos** con descripción, link al repositorio e imágenes. Desde ahí se exploran las ofertas publicadas y se postulan con un clic.
- **Para empresas:** un proceso simple para llegar directo al talento de la universidad, **sin intermediarios ni comisiones**. La empresa crea su cuenta, describe su proyecto, publica ofertas (tipo de puesto, modalidad, seniority buscado, fechas), ve quién se postuló y asigna al candidato elegido.
- **Orientación para el primer empleo:** la página reúne consejos para armar el CV, las preguntas más frecuentes en entrevistas junior y cómo presentar un portfolio en GitHub.

### Cómo funciona

**Si sos estudiante o graduado**
1. Te registrás y elegís el perfil *Estudiante / graduado*.
2. Completás tu perfil y cargás tu portfolio.
3. Explorás las ofertas disponibles y te postulás.
4. La empresa revisa tu perfil y, si te elige, el contrato queda asignado a vos.

**Si sos una empresa**
1. Registrás tu empresa (perfil *Empresa / Reclutador*).
2. Creás el proyecto de tu empresa y publicás ofertas.
3. Recibís postulaciones de alumnos y graduados de la universidad.
4. Elegís al candidato y coordinan la entrevista.

También existe el perfil *Institución educativa*, pensado para que la universidad y sus institutos participen de la plataforma; por ahora no tiene funciones propias.

## Por qué HunTech

- **Un canal propio de la universidad:** el objetivo es que quienes se postulan sean alumnos y graduados de la Universidad de la Ciudad de Buenos Aires.
- **Pensado para el primer empleo:** perfiles trainee y junior, sin competir contra el mercado entero.
- **Proyectos antes que años de experiencia:** el portfolio permite mostrar lo que cada uno ya construyó.
- **Proceso transparente:** la empresa sabe quién se postuló, cuándo y con qué perfil, y el postulante ve el estado de sus postulaciones.
- **Impacto en la comunidad:** cada contratación ayuda a un estudiante a dar su primer paso profesional.

## Stack tecnológico

| Capa | Tecnologías |
|---|---|
| **Frontend** | Angular 20 (componentes standalone), TypeScript 5.9, RxJS 7.8 |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2 (async con asyncpg), Pydantic 2 |
| **Base de datos** | PostgreSQL 16, migraciones con Alembic |
| **Autenticación** | JWT propio (PyJWT) y contraseñas con bcrypt |
| **Monorepo** | Nx 24 (`apps/frontend` y `apps/backend`), npm para JavaScript y Poetry para Python |
| **Tests** | Karma + Jasmine (frontend), pytest + httpx (backend) |
| **Infraestructura** | Docker Compose; en producción Caddy (HTTPS automático), Nginx y uvicorn con varios workers |

## Arquitectura

```
                    ┌──────────────────────────────┐
  Navegador  ──────►│ Caddy (HTTPS)                │
                    │  /          → Nginx (Angular)│
                    │  /api/*     → FastAPI        │──► PostgreSQL 16
                    │  /storage/* → FastAPI        │    (red interna)
                    └──────────────────────────────┘
```

```
apps/
  frontend/   Angular: componentes, servicios, modelos
  backend/    FastAPI: routers, modelos, migraciones, tests
infra/
  local/      Docker para desarrollo (hot-reload)
  vps/        Docker para producción (Caddy + Nginx + FastAPI + Postgres)
context_agent/  documentación técnica
```

## Instalación para uso local

### Requisitos

- [Git](https://git-scm.com/)
- [Docker](https://docs.docker.com/get-docker/) con Docker Compose v2 (Docker Desktop o Docker Engine)
- [Node.js](https://nodejs.org/) 24 y npm 11 (probados), para los comandos de Nx y los tests del frontend
- Opcional: Python 3.12+ y [Poetry](https://python-poetry.org/) 2, si se quiere correr el backend o sus tests fuera de Docker

### Opción A: todo con Docker (recomendada)

```bash
git clone https://github.com/NadineCeleste/UdelaConecta.git
cd UdelaConecta
npm install
npm start
```

`npm start` construye y levanta la base de datos, el backend, el frontend y Adminer. La primera vez tarda unos minutos. El backend aplica las migraciones y carga datos de prueba solo; los cambios en el código se recargan sin reiniciar nada.

| Servicio | URL |
|---|---|
| Aplicación | http://localhost:4200 |
| API | http://localhost:3000/api/ |
| Documentación de la API (Swagger) | http://localhost:3000/docs |
| Adminer (administrar la base) | http://localhost:8080 · servidor `postgres`, usuario `udela`, contraseña `udela_local_pass`, base `udelaconecta` |

**Usuarios de prueba** (contraseña `Udela1234!`):
- `dev@udelaconecta.edu.ar`: estudiante con portfolio y una postulación.
- `empresa@udelaconecta.edu.ar`: empresa con un proyecto y tres ofertas.

Si algún puerto ya está ocupado, se puede cambiar al levantar:

```bash
FRONTEND_PORT=4201 POSTGRES_HOST_PORT=5433 ADMINER_PORT=8081 npm run local:up
```

### Comandos útiles

| Comando | Qué hace |
|---|---|
| `npm start` | Levanta todo en primer plano (Ctrl+C para cortar) |
| `npm run local:up` / `npm run local:down` | Levanta en segundo plano / baja todo (los datos se conservan) |
| `npm run local:logs` | Muestra los logs de todos los servicios |
| `npm run test:front` | Tests del frontend (necesita Chrome) |
| `npm run test:back` | Tests del backend (necesita Poetry; ver opción B) |
| `npm run build` | Build de producción del frontend |

Para empezar de cero, borrando la base y las imágenes locales: `docker compose -f infra/local/docker-compose.yml --env-file infra/local/.env.local down -v`.

### Opción B: sin Docker

Necesita un PostgreSQL 16 propio corriendo en `localhost:5432`, con la base `udelaconecta` y un usuario con permisos sobre ella.

```bash
# Backend
cd apps/backend
poetry install
export DATABASE_URL=postgresql+asyncpg://<usuario>:<contraseña>@localhost:5432/udelaconecta
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
export STORAGE_DIR=./storage
poetry run alembic upgrade head
poetry run python -m app.seeds.seed_demo
poetry run uvicorn app.main:app --reload --port 3000

# Frontend (en otra terminal, desde la raíz del repo)
npm install
npm run serve:front
```

## Local y producción: dos entornos distintos

Los dos entornos usan Docker Compose, pero cada uno tiene su propio archivo, sus propias variables y sus propios comandos. **`npm start` es solo para desarrollo local**: no se usa en el servidor.

| | Local (desarrollo) | VPS (producción) |
|---|---|---|
| Archivo de Compose | `infra/local/docker-compose.yml` | `infra/vps/docker-compose.prod.yml` |
| Variables | `infra/local/.env.local` (viene en el repo, solo para desarrollo) | `infra/vps/.env.vps` (se crea a mano y **nunca se sube a git**) |
| Levantar | `npm start` (primer plano) o `npm run local:up` | `npm run vps:up` o `./infra/vps/deploy.sh` |
| Bajar / logs | `npm run local:down` / `npm run local:logs` | `npm run vps:down` / `npm run vps:logs` |
| Frontend | `ng serve` con recarga automática | Build de producción servido por Nginx |
| Backend | Un proceso con `--reload` y el código montado | FastAPI con 4 workers, imagen cerrada y usuario sin privilegios |
| Entrada | Un puerto por servicio (4200, 3000, 8080, 5432) | Solo Caddy en 80/443, con HTTPS automático |
| Base de datos | Accesible en `127.0.0.1` y administrable con Adminer | Sin puertos expuestos, solo accesible dentro de Docker |
| Datos de prueba | Se cargan solos (`AUTO_SEED=true`) | No se cargan (`AUTO_SEED=false`) |

Los scripts `npm run ...` son atajos de `docker compose`. Por ejemplo, `npm start` equivale a:

```bash
docker compose -f infra/local/docker-compose.yml --env-file infra/local/.env.local up --build
```

## Despliegue en un servidor (VPS)

En el servidor solo hacen falta **Git y Docker** (con Compose v2); Node no es necesario si se usa `deploy.sh`.

```bash
git clone https://github.com/NadineCeleste/UdelaConecta.git
cd UdelaConecta
cp infra/vps/.env.vps.example infra/vps/.env.vps
nano infra/vps/.env.vps        # completar las variables (ver abajo)
./infra/vps/deploy.sh
```

Variables principales de `infra/vps/.env.vps`:
- `DOMAIN`: el dominio del sitio (por ejemplo `huntech.com.ar`); Caddy obtiene el certificado HTTPS solo. Con `:80` sirve por HTTP, sin certificado.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `DATABASE_URL`, con la misma contraseña en los dos lugares.
- `JWT_SECRET_KEY`: se genera con `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`. Si se deja el valor de ejemplo, el backend no arranca.

`deploy.sh` verifica que exista `.env.vps`, hace `git pull`, reconstruye y levanta los contenedores en segundo plano, borra imágenes viejas y muestra el estado. Para actualizar el sitio después de cada cambio en `main`, alcanza con volver a correrlo. Los contenedores se reinician solos si se caen o si se reinicia el servidor.

**Backups:** `./infra/vps/backup-db.sh 14` guarda la base y las imágenes subidas en `infra/vps/backups/` y borra los de más de 14 días. Conviene programarlo con cron, por ejemplo todos los días a las 3:

```
0 3 * * * /ruta/al/repo/infra/vps/backup-db.sh 14
```

Más detalles (variables de entorno, problemas frecuentes y cada servicio de los dos entornos) en [`context_agent/orquestacion.md`](./context_agent/orquestacion.md) y [`apps/backend/README.md`](./apps/backend/README.md).

## De dónde nace

Detrás de HunTech hay un grupo de estudiantes de la Universidad de la Ciudad de Buenos Aires que decidió transformar una problemática común en una solución real, con un objetivo claro: **acompañar a nuestros pares a dar sus primeros pasos dentro del mundo laboral IT.**

## Equipo

Todo el equipo está formado por estudiantes de la **Universidad de la Ciudad de Buenos Aires**. Estas son las personas que contribuyen al proyecto:

<a href="https://github.com/NadineCeleste/UdelaConecta/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=NadineCeleste/UdelaConecta" alt="Contribuidores de Udela Conecta" />
</a>

---

📄 La documentación técnica del proyecto (arquitectura, backend, orquestación y auditorías) está en [`context_agent/`](./context_agent/AGENTS.md).
