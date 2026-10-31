"""Datos de demo idempotentes: se puede correr muchas veces sin duplicar nada.

    python -m app.seeds.seed_demo

Cada registro se busca por su clave natural (email, email del gerente o título de la oferta
dentro del proyecto) y solo se crea si falta. Así, sumar una empresa o una oferta acá y volver
a correr el seed la agrega sin tocar lo que ya existe (ni lo que los usuarios cambiaron).
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import AuthUser, Contrato, Estudiante, Gerente, Portfolio, Proyecto

PASSWORD_DEMO = "Udela1234!"
EMAIL_DEV = "dev@udelaconecta.edu.ar"
EMAIL_GERENTE = "empresa@udelaconecta.edu.ar"

LUCAS = "lucas.fernandez@udelaconecta.edu.ar"
CAMILA = "camila.rios@udelaconecta.edu.ar"
TOMAS = "tomas.acosta@udelaconecta.edu.ar"
JULIETA = "julieta.medina@udelaconecta.edu.ar"
MARTINA = "martina.sosa@udelaconecta.edu.ar"


def _habilidades(*pares: tuple[str, str]) -> list[dict]:
    return [{"nombre_habilidad": nombre, "nivel_habilidad": nivel} for nombre, nivel in pares]


def _idiomas(*pares: tuple[str, str]) -> list[dict]:
    return [{"nombre_idioma": nombre, "nivel_idioma": nivel} for nombre, nivel in pares]


ESPANOL = ("Español", "C2 - Nativo")

ESTUDIANTES = [
    {
        "email": EMAIL_DEV,
        "nombre": "Valentina",
        "apellido": "Gómez",
        "descripcion": "Estudiante avanzada de Ingeniería en Sistemas. Me gusta el frontend y las APIs.",
        "telefono": "1155550101",
        "genero": "femenino",
        "fecha_nacimiento": "2001-04-12",
        "puesto_actual": "Desarrolladora Full Stack Trainee",
        "is_disponible": True,
        "habilidades": _habilidades(("Angular", "intermedio"), ("Python", "intermedio"), ("SQL", "principiante")),
        "idiomas": _idiomas(ESPANOL, ("Inglés", "B2 - Intermedio alto")),
        "portfolio": [
            ("Bolsa de trabajo Udela Conecta", "Frontend en Angular 20 con componentes standalone.",
             "https://github.com/NadineCeleste/UdelaConecta"),
            ("API de turnos", "FastAPI + PostgreSQL con autenticación JWT.",
             "https://github.com/udelaconecta/turnos-api"),
        ],
    },
    {
        "email": LUCAS,
        "nombre": "Lucas",
        "apellido": "Fernández",
        "descripcion": "Graduado de la Tecnicatura en Programación. Hice el frontend de dos apps de la "
        "cursada en React y quiero mi primer trabajo en un equipo de producto.",
        "telefono": "1155550303",
        "genero": "masculino",
        "fecha_nacimiento": "1999-09-03",
        "puesto_actual": "Desarrollador Frontend Junior (freelance)",
        "is_disponible": True,
        "habilidades": _habilidades(
            ("React", "intermedio"), ("TypeScript", "intermedio"), ("Node.js", "principiante"), ("CSS", "avanzado")
        ),
        "idiomas": _idiomas(ESPANOL, ("Inglés", "B1 - Intermedio")),
        "portfolio": [
            ("Agenda de turnos para un consultorio", "SPA en React con calendario, recordatorios y login.",
             "https://github.com/udelaconecta/agenda-consultorio"),
            ("Catálogo de la biblioteca", "React + API en Node.js con búsqueda por autor y materia.",
             "https://github.com/udelaconecta/catalogo-biblioteca"),
            ("Landing de la feria de empleo", "Sitio estático accesible y responsive.", ""),
        ],
    },
    {
        "email": CAMILA,
        "nombre": "Camila",
        "apellido": "Ríos",
        "descripcion": "Estudiante de Licenciatura en Ciencia de Datos. Me interesa el análisis de datos "
        "y armar tableros que ayuden a tomar decisiones.",
        "telefono": "1155550404",
        "genero": "femenino",
        "fecha_nacimiento": "2002-01-21",
        "puesto_actual": "",
        "is_disponible": True,
        "habilidades": _habilidades(
            ("Python", "avanzado"), ("Pandas", "intermedio"), ("SQL", "intermedio"), ("Power BI", "intermedio")
        ),
        "idiomas": _idiomas(ESPANOL, ("Inglés", "C1 - Avanzado"), ("Portugués", "A2 - Básico")),
        "portfolio": [
            ("Tablero de deserción estudiantil", "Análisis con Pandas y tablero en Power BI con datos abiertos.",
             "https://github.com/udelaconecta/desercion-tablero"),
        ],
    },
    {
        "email": TOMAS,
        "nombre": "Tomás",
        "apellido": "Acosta",
        "descripcion": "Estudiante de Ingeniería en Sistemas. Desarrollo apps móviles con Flutter desde hace un año.",
        "telefono": "1155550505",
        "genero": "masculino",
        "fecha_nacimiento": "2000-11-30",
        "puesto_actual": "",
        "is_disponible": True,
        "habilidades": _habilidades(("Flutter", "intermedio"), ("Dart", "intermedio"), ("Firebase", "principiante")),
        "idiomas": _idiomas(ESPANOL),
        "portfolio": [
            ("App de colectivos de la facultad", "Flutter + Firebase con horarios y avisos en tiempo real.",
             "https://github.com/udelaconecta/colectivos-app"),
            ("Lista de compras compartida", "Flutter con sincronización offline.", ""),
        ],
    },
    {
        "email": JULIETA,
        "nombre": "Julieta",
        "apellido": "Medina",
        "descripcion": "Estudiante de Redes y Sistemas Operativos. Me gusta automatizar despliegues y "
        "administrar servidores Linux.",
        "telefono": "1155550606",
        "genero": "femenino",
        "fecha_nacimiento": "2001-07-08",
        "puesto_actual": "Ayudante de laboratorio de redes",
        "is_disponible": True,
        "habilidades": _habilidades(
            ("Docker", "intermedio"), ("Linux", "avanzado"), ("GitHub Actions", "principiante"), ("Python", "principiante")
        ),
        "idiomas": _idiomas(ESPANOL, ("Inglés", "B2 - Intermedio alto")),
        "portfolio": [
            ("Pipeline de CI para proyectos de la cátedra", "GitHub Actions con tests, build de imágenes y deploy.",
             "https://github.com/udelaconecta/ci-catedra"),
            ("Monitoreo del laboratorio", "Docker Compose con Prometheus y Grafana.",
             "https://github.com/udelaconecta/monitoreo-lab"),
        ],
    },
    {
        "email": MARTINA,
        "nombre": "Martina",
        "apellido": "Sosa",
        "descripcion": "Graduada de Análisis de Sistemas. Hago QA y relevamiento de requerimientos.",
        "telefono": "1155550707",
        "genero": "femenino",
        "fecha_nacimiento": "1998-03-17",
        "puesto_actual": "Analista funcional en RutaSur Logística",
        "is_disponible": False,
        "habilidades": _habilidades(("Playwright", "intermedio"), ("Testing manual", "avanzado"), ("UML", "intermedio")),
        "idiomas": _idiomas(ESPANOL, ("Inglés", "B1 - Intermedio")),
        "portfolio": [],
    },
]

EMPRESAS = [
    {
        "email": EMAIL_GERENTE,
        "nombre": "Martín",
        "apellido": "Pereyra",
        "descripcion": "Líder técnico de la plataforma FinTech.",
        "telefono": "1155550202",
        "puesto_actual": "CTO",
        "proyecto": {
            "nombre": "Plataforma FinTech Udela",
            "description": "Billetera virtual para la comunidad universitaria: pagos, becas y beneficios.",
            "info_link": "https://udelaconecta.edu.ar",
        },
        "ofertas": [
            {
                "tipo": "Pasantía",
                "titulo": "Frontend Angular para el panel de pagos",
                "descripcion": "Maquetado y consumo de API del panel de usuarios.",
                "modalidad": "remoto",
                "seniority_deseado": ["Trainee", "Junior"],
                "start_date": "2026-11-01",
                "end_date": "2027-04-30",
            },
            {
                "tipo": "Pasantía",
                "titulo": "Backend FastAPI de conciliaciones",
                "descripcion": "Endpoints de conciliación bancaria y tests de integración.",
                "modalidad": "hibrido",
                "seniority_deseado": ["Junior"],
                "postulaciones": [EMAIL_DEV],
                "start_date": "2026-11-15",
                "end_date": "2027-05-15",
            },
            {
                "tipo": "Contrato",
                "titulo": "QA de la app móvil",
                "descripcion": "Casos de prueba y automatización con Playwright.",
                "modalidad": "presencial",
                "seniority_deseado": ["Semisenior"],
                "postulaciones": [EMAIL_DEV],
                "pasante_email": EMAIL_DEV,
                "start_date": "2026-10-01",
                "end_date": "2027-03-31",
            },
            {
                "tipo": "Pasantía",
                "titulo": "Data Analyst Trainee para riesgo crediticio",
                "descripcion": "Limpieza de datos de préstamos estudiantiles con Python y SQL, y tableros "
                "en Power BI para el equipo de riesgo. 20 horas semanales.",
                "modalidad": "remoto",
                "seniority_deseado": ["Trainee"],
                "postulaciones": [CAMILA],
                "start_date": "2026-12-01",
                "end_date": "2027-05-31",
            },
        ],
    },
    {
        "email": "agrotech@udelaconecta.edu.ar",
        "nombre": "Sofía",
        "apellido": "Benítez",
        "descripcion": "Responsable de tecnología de AgroData Pampa.",
        "telefono": "1155550808",
        "puesto_actual": "Head of Engineering",
        "proyecto": {
            "nombre": "AgroData Pampa",
            "description": "Sensores IoT y análisis de datos para que productores chicos de la provincia "
            "midan humedad del suelo y clima en tiempo real.",
            "info_link": "https://agrodata.example.com",
        },
        "ofertas": [
            {
                "tipo": "Pasantía",
                "titulo": "Desarrollador/a Python para sensores IoT",
                "descripcion": "Servicios en Python que reciben lecturas de sensores por MQTT, las validan "
                "y las guardan en PostgreSQL. Se valora haber usado Docker.",
                "modalidad": "hibrido",
                "seniority_deseado": ["Trainee", "Junior"],
                "postulaciones": [JULIETA],
                "start_date": "2026-11-15",
                "end_date": "2027-05-15",
            },
            {
                "tipo": "Contrato",
                "titulo": "Data Engineer Junior",
                "descripcion": "Pipelines de datos con Python y SQL para los tableros de los productores. "
                "Inglés técnico para leer documentación.",
                "modalidad": "remoto",
                "seniority_deseado": ["Junior"],
                "postulaciones": [CAMILA],
                "start_date": "2027-01-05",
                "end_date": "2027-12-20",
            },
        ],
    },
    {
        "email": "salud@udelaconecta.edu.ar",
        "nombre": "Diego",
        "apellido": "Luna",
        "descripcion": "Fundador de SaludConecta.",
        "telefono": "1155550909",
        "puesto_actual": "CEO",
        "proyecto": {
            "nombre": "SaludConecta",
            "description": "Turnos online y telemedicina para centros de salud barriales.",
            "info_link": "https://saludconecta.example.com",
        },
        "ofertas": [
            {
                "tipo": "Contrato",
                "titulo": "Frontend React para turnos online",
                "descripcion": "Nuevas pantallas de reserva de turnos en React y TypeScript, con foco en "
                "accesibilidad para adultos mayores.",
                "modalidad": "remoto",
                "seniority_deseado": ["Junior", "Semisenior"],
                "postulaciones": [LUCAS, EMAIL_DEV],
                "start_date": "2026-11-10",
                "end_date": "2027-11-10",
            },
            {
                "tipo": "Pasantía",
                "titulo": "Soporte técnico y QA manual",
                "descripcion": "Atención a los centros de salud, reproducción de errores y pruebas manuales "
                "antes de cada versión. Lunes a viernes de 9 a 13.",
                "modalidad": "presencial",
                "seniority_deseado": ["Trainee"],
                "start_date": "2026-11-01",
                "end_date": "2027-04-30",
            },
        ],
    },
    {
        "email": "logistica@udelaconecta.edu.ar",
        "nombre": "Carla",
        "apellido": "Domínguez",
        "descripcion": "Gerenta de sistemas de RutaSur Logística.",
        "telefono": "1155551010",
        "puesto_actual": "Gerenta de Sistemas",
        "proyecto": {
            "nombre": "RutaSur Logística",
            "description": "Seguimiento de envíos y ruteo de repartidores para comercios de la zona sur.",
            "info_link": "https://rutasur.example.com",
        },
        "ofertas": [
            {
                "tipo": "Pasantía",
                "titulo": "Desarrollador/a Mobile Flutter",
                "descripcion": "App de repartidores en Flutter: mapa de entregas, firma digital y modo sin conexión.",
                "modalidad": "hibrido",
                "seniority_deseado": ["Trainee", "Junior"],
                "postulaciones": [TOMAS],
                "start_date": "2026-12-01",
                "end_date": "2027-06-30",
            },
            {
                "tipo": "Contrato",
                "titulo": "DevOps Junior: Docker y CI/CD",
                "descripcion": "Mantener los pipelines de GitHub Actions, las imágenes Docker y los servidores "
                "Linux de staging y producción.",
                "modalidad": "remoto",
                "seniority_deseado": ["Junior"],
                "postulaciones": [JULIETA],
                "start_date": "2026-11-20",
                "end_date": "2027-11-20",
            },
            {
                "tipo": "Contrato",
                "titulo": "Analista funcional trainee",
                "descripcion": "Relevamiento con los comercios y documentación de requerimientos.",
                "modalidad": "presencial",
                "seniority_deseado": ["Trainee"],
                "postulaciones": [MARTINA],
                "pasante_email": MARTINA,
                "start_date": "2026-09-01",
                "end_date": "2027-02-28",
            },
        ],
    },
]


async def _cuenta(db: AsyncSession, email: str) -> None:
    if not await db.scalar(select(AuthUser).where(AuthUser.email == email)):
        db.add(AuthUser(email=email, password_hash=hash_password(PASSWORD_DEMO)))


async def _estudiante(db: AsyncSession, datos: dict) -> None:
    datos = dict(datos)
    proyectos = datos.pop("portfolio")
    await _cuenta(db, datos["email"])

    if not await db.scalar(select(Estudiante).where(Estudiante.email == datos["email"])):
        db.add(Estudiante(name=f"{datos['nombre']} {datos['apellido']}", **datos))

    if proyectos and not await db.scalar(select(Portfolio).where(Portfolio.email == datos["email"])):
        campos = {}
        for i, (titulo, descripcion, repositorio) in enumerate(proyectos, start=1):
            campos |= {f"titulo{i}": titulo, f"descripcion{i}": descripcion, f"repositorio{i}": repositorio}
        db.add(Portfolio(email=datos["email"], **campos))


async def _empresa(db: AsyncSession, datos: dict) -> None:
    datos = dict(datos)
    datos_proyecto = datos.pop("proyecto")
    ofertas = datos.pop("ofertas")
    email = datos["email"]
    await _cuenta(db, email)

    gerente = await db.scalar(select(Gerente).where(Gerente.email == email))
    if gerente is None:
        gerente = Gerente(name=f"{datos['nombre']} {datos['apellido']}", **datos)
        db.add(gerente)
        await db.flush()

    proyecto = await db.scalar(select(Proyecto).where(Proyecto.email_gerente == email))
    if proyecto is None:
        proyecto = Proyecto(**datos_proyecto, buscando_devs=True, id_gerente=str(gerente.id), email_gerente=email)
        db.add(proyecto)
        await db.flush()
    gerente.id_proyecto = proyecto.id

    existentes = set(
        (await db.scalars(select(Contrato.titulo).where(Contrato.proyecto_id == proyecto.id))).all()
    )
    for oferta in ofertas:
        if oferta["titulo"] in existentes:
            continue
        postulaciones = oferta.get("postulaciones", [])
        db.add(Contrato(
            proyecto_id=proyecto.id,
            **oferta,
            tiene_postulaciones=bool(postulaciones),
            esta_ocupado=bool(oferta.get("pasante_email")),
        ))


async def seed(db: AsyncSession) -> None:
    for estudiante in ESTUDIANTES:
        await _estudiante(db, estudiante)
    for empresa in EMPRESAS:
        await _empresa(db, empresa)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)
        await db.commit()
    print("Seed de demo aplicado")


if __name__ == "__main__":
    asyncio.run(main())
