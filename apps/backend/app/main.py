from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, contratos, portfolio, proyectos, storage, usuarios

app = FastAPI(
    title="Udela Conecta API",
    description="Backend de Udela Conecta: usuarios, proyectos, contratos y portfolios.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for modulo in (auth, usuarios, proyectos, contratos, portfolio, storage):
    app.include_router(modulo.router)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}
