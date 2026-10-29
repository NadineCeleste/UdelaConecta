import os
import tempfile

# La configuración se lee al importar la app: definirla antes
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-solo-para-pytest-0123456789")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="udela-storage-")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture
async def sesiones():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield fabrica
    await engine.dispose()


@pytest.fixture
async def client(sesiones):
    async def get_db_test():
        async with sesiones() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = get_db_test
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def registrar(client: AsyncClient, email: str, rol: str | None = None) -> dict:
    """Registra la cuenta (y opcionalmente el perfil) y devuelve los headers con el token."""
    res = await client.post("/api/auth/register", json={"email": email, "password": "Secreta123"})
    assert res.status_code == 201, res.text
    headers = {"Authorization": f"Bearer {res.json()['data']['session']['access_token']}"}
    if rol:
        res = await client.post(f"/api/{rol}", json={"email": email}, headers=headers)
        assert res.status_code == 201, res.text
    return headers


@pytest.fixture
def registrar_usuario(client):
    async def _registrar(email: str, rol: str | None = None) -> dict:
        return await registrar(client, email, rol)

    return _registrar
