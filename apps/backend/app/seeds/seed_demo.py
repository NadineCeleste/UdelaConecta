"""Datos de demo idempotentes: se puede correr muchas veces sin duplicar nada.

    python -m app.seeds.seed_demo
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


async def _cuenta(db: AsyncSession, email: str) -> None:
    if not await db.scalar(select(AuthUser).where(AuthUser.email == email)):
        db.add(AuthUser(email=email, password_hash=hash_password(PASSWORD_DEMO)))


async def seed(db: AsyncSession) -> None:
    await _cuenta(db, EMAIL_DEV)
    await _cuenta(db, EMAIL_GERENTE)

    if not await db.scalar(select(Estudiante).where(Estudiante.email == EMAIL_DEV)):
        db.add(Estudiante(
            email=EMAIL_DEV,
            nombre="Valentina",
            apellido="Gómez",
            name="Valentina Gómez",
            descripcion="Estudiante avanzada de Ingeniería en Sistemas. Me gusta el frontend y las APIs.",
            telefono="1155550101",
            genero="femenino",
            fecha_nacimiento="2001-04-12",
            puesto_actual="Desarrolladora Full Stack Trainee",
            is_disponible=True,
            habilidades=[
                {"nombre_habilidad": "Angular", "nivel_habilidad": "intermedio"},
                {"nombre_habilidad": "Python", "nivel_habilidad": "intermedio"},
                {"nombre_habilidad": "SQL", "nivel_habilidad": "principiante"},
            ],
            idiomas=[
                {"nombre_idioma": "Español", "nivel_idioma": "C2 - Nativo"},
                {"nombre_idioma": "Inglés", "nivel_idioma": "B2 - Intermedio alto"},
            ],
        ))

    gerente = await db.scalar(select(Gerente).where(Gerente.email == EMAIL_GERENTE))
    if gerente is None:
        gerente = Gerente(
            email=EMAIL_GERENTE,
            nombre="Martín",
            apellido="Pereyra",
            name="Martín Pereyra",
            descripcion="Líder técnico de la plataforma FinTech.",
            telefono="1155550202",
            puesto_actual="CTO",
        )
        db.add(gerente)
        await db.flush()

    proyecto = await db.scalar(select(Proyecto).where(Proyecto.email_gerente == EMAIL_GERENTE))
    if proyecto is None:
        proyecto = Proyecto(
            nombre="Plataforma FinTech Udela",
            description="Billetera virtual para la comunidad universitaria: pagos, becas y beneficios.",
            info_link="https://udelaconecta.edu.ar",
            buscando_devs=True,
            id_gerente=str(gerente.id),
            email_gerente=EMAIL_GERENTE,
        )
        db.add(proyecto)
        await db.flush()
    gerente.id_proyecto = proyecto.id

    if not await db.scalar(select(Contrato.id).where(Contrato.proyecto_id == proyecto.id).limit(1)):
        db.add_all([
            Contrato(
                proyecto_id=proyecto.id,
                tipo="Pasantía",
                titulo="Frontend Angular para el panel de pagos",
                descripcion="Maquetado y consumo de API del panel de usuarios.",
                modalidad="remoto",
                seniority_deseado=["Trainee", "Junior"],
                start_date="2026-11-01",
                end_date="2027-04-30",
            ),
            Contrato(
                proyecto_id=proyecto.id,
                tipo="Pasantía",
                titulo="Backend FastAPI de conciliaciones",
                descripcion="Endpoints de conciliación bancaria y tests de integración.",
                modalidad="hibrido",
                seniority_deseado=["Junior"],
                postulaciones=[EMAIL_DEV],
                tiene_postulaciones=True,
                start_date="2026-11-15",
                end_date="2027-05-15",
            ),
            Contrato(
                proyecto_id=proyecto.id,
                tipo="Contrato",
                titulo="QA de la app móvil",
                descripcion="Casos de prueba y automatización con Playwright.",
                modalidad="presencial",
                seniority_deseado=["Semisenior"],
                postulaciones=[EMAIL_DEV],
                tiene_postulaciones=True,
                esta_ocupado=True,
                pasante_email=EMAIL_DEV,
                start_date="2026-10-01",
                end_date="2027-03-31",
            ),
        ])

    if not await db.scalar(select(Portfolio).where(Portfolio.email == EMAIL_DEV)):
        db.add(Portfolio(
            email=EMAIL_DEV,
            titulo1="Bolsa de trabajo Huntech",
            descripcion1="Frontend en Angular 20 con componentes standalone.",
            repositorio1="https://github.com/udelaconecta/huntech",
            titulo2="API de turnos",
            descripcion2="FastAPI + PostgreSQL con autenticación JWT.",
            repositorio2="https://github.com/udelaconecta/turnos-api",
        ))


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)
        await db.commit()
    print("Seed de demo aplicado")


if __name__ == "__main__":
    asyncio.run(main())
