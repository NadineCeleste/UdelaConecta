from sqlalchemy import func, select

from app.models import AuthUser, Contrato, Estudiante, Gerente, Portfolio, Proyecto
from app.seeds import seed_demo


async def contar(db, modelo) -> int:
    return await db.scalar(select(func.count()).select_from(modelo))


async def test_seed_es_idempotente(sesiones):
    for _ in range(2):
        async with sesiones() as db:
            await seed_demo.seed(db)
            await db.commit()

    async with sesiones() as db:
        assert await contar(db, AuthUser) == len(seed_demo.ESTUDIANTES) + len(seed_demo.EMPRESAS)
        assert await contar(db, Estudiante) == len(seed_demo.ESTUDIANTES)
        assert await contar(db, Gerente) == len(seed_demo.EMPRESAS)
        assert await contar(db, Proyecto) == len(seed_demo.EMPRESAS)
        assert await contar(db, Contrato) == sum(len(e["ofertas"]) for e in seed_demo.EMPRESAS)
        assert await contar(db, Portfolio) == sum(1 for e in seed_demo.ESTUDIANTES if e["portfolio"])

        # Las asignadas quedan ocupadas y las que tienen postulantes, marcadas
        for contrato in (await db.scalars(select(Contrato))).all():
            assert contrato.esta_ocupado == bool(contrato.pasante_email)
            assert contrato.tiene_postulaciones == bool(contrato.postulaciones)


async def test_seed_completa_ofertas_nuevas_sin_tocar_las_existentes(sesiones):
    async with sesiones() as db:
        await seed_demo.seed(db)
        await db.commit()

    async with sesiones() as db:
        # Simula una base vieja: falta una oferta y otra fue editada por el usuario
        borrar = await db.scalar(select(Contrato).where(Contrato.titulo == "Data Engineer Junior"))
        await db.delete(borrar)
        editada = await db.scalar(select(Contrato).where(Contrato.titulo == "Soporte técnico y QA manual"))
        editada.descripcion = "Cambiada por la empresa"
        await db.commit()

    async with sesiones() as db:
        await seed_demo.seed(db)
        await db.commit()

    async with sesiones() as db:
        assert await db.scalar(select(Contrato).where(Contrato.titulo == "Data Engineer Junior"))
        editada = await db.scalar(select(Contrato).where(Contrato.titulo == "Soporte técnico y QA manual"))
        assert editada.descripcion == "Cambiada por la empresa"


async def test_ofertas_del_seed_para_el_asistente(client, sesiones):
    async with sesiones() as db:
        await seed_demo.seed(db)
        await db.commit()

    async def titulos(**params) -> set[str]:
        res = await client.get("/api/chat/datos/ofertas", params=params)
        assert res.status_code == 200
        return {o["titulo"] for o in res.json()["data"]}

    # Sin tildes ni mayúsculas: "Híbrido" encuentra las guardadas como "hibrido"
    hibridas = await titulos(modalidad="Híbrido")
    assert "Desarrollador/a Mobile Flutter" in hibridas
    assert "Frontend React para turnos online" not in hibridas

    # Las palabras vacías no hacen que coincida todo
    flutter = await titulos(texto="ofertas de flutter")
    assert flutter == {"Desarrollador/a Mobile Flutter"}

    # Las asignadas no aparecen
    assert "Analista funcional trainee" not in await titulos()
