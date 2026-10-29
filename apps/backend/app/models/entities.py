import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB nativo en PostgreSQL y JSON plano en SQLite (tests)
JsonType = JSON().with_variant(JSONB(), "postgresql")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _tres_vacias() -> list[str]:
    return ["", "", ""]


class Base(DeclarativeBase):
    pass


class AuthUser(Base):
    __tablename__ = "auth_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Solo se activa desde la base (Adminer/SQL): registrarse con un email no da permisos
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Bloqueo temporal tras varios intentos fallidos de login
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Estudiante(Base):
    __tablename__ = "estudiante"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(120), default="")
    apellido: Mapped[str | None] = mapped_column(String(120), default="")
    name: Mapped[str | None] = mapped_column(String(240), default="")
    descripcion: Mapped[str | None] = mapped_column(Text, default="")
    telefono: Mapped[str | None] = mapped_column(String(60), default="")
    genero: Mapped[str | None] = mapped_column(String(30), default="")
    fecha_nacimiento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    puesto_actual: Mapped[str | None] = mapped_column(String(150), default="")
    rol: Mapped[str] = mapped_column(String(50), default="estudiante")
    is_disponible: Mapped[bool] = mapped_column(Boolean, default=True)
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    skills: Mapped[list] = mapped_column(JsonType, default=list)
    habilidades: Mapped[list] = mapped_column(JsonType, default=list)
    idiomas: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Gerente(Base):
    __tablename__ = "gerente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(120), default="")
    apellido: Mapped[str | None] = mapped_column(String(120), default="")
    name: Mapped[str | None] = mapped_column(String(240), default="")
    descripcion: Mapped[str | None] = mapped_column(Text, default="")
    telefono: Mapped[str | None] = mapped_column(String(60), default="")
    genero: Mapped[str | None] = mapped_column(String(30), default="")
    fecha_nacimiento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    puesto_actual: Mapped[str | None] = mapped_column(String(150), default="")
    id_proyecto: Mapped[str | None] = mapped_column(String(64), nullable=True)
    habilidades: Mapped[list] = mapped_column(JsonType, default=list)
    idiomas: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class InstitucionEducativa(Base):
    __tablename__ = "institucion_educativa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(150), default="")
    apellido: Mapped[str | None] = mapped_column(String(150), default="")
    name: Mapped[str | None] = mapped_column(String(240), default="")
    descripcion: Mapped[str | None] = mapped_column(Text, default="")
    telefono: Mapped[str | None] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Proyecto(Base):
    __tablename__ = "proyecto"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str | None] = mapped_column(Text, default="")
    info_link: Mapped[str | None] = mapped_column(String(500), default="")
    buscando_devs: Mapped[bool] = mapped_column(Boolean, default=True)
    id_gerente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_gerente: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    contratos: Mapped[list["Contrato"]] = relationship(
        "Contrato", back_populates="proyecto", cascade="all, delete-orphan", lazy="selectin"
    )


class Contrato(Base):
    __tablename__ = "contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo: Mapped[str | None] = mapped_column(String(100), default="")
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, default="")
    tiene_postulaciones: Mapped[bool] = mapped_column(Boolean, default=False)
    postulaciones: Mapped[list] = mapped_column(JsonType, default=list)
    esta_ocupado: Mapped[bool] = mapped_column(Boolean, default=False)
    pasante_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proyecto_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("proyecto.id", ondelete="CASCADE"), nullable=True, index=True
    )
    start_date: Mapped[str | None] = mapped_column(String(30), default="")
    end_date: Mapped[str | None] = mapped_column(String(30), default="")
    modalidad: Mapped[str | None] = mapped_column(String(60), default="remoto")
    seniority_deseado: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    proyecto: Mapped[Proyecto | None] = relationship("Proyecto", back_populates="contratos")


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    titulo1: Mapped[str] = mapped_column(String(255), default="")
    descripcion1: Mapped[str] = mapped_column(Text, default="")
    repositorio1: Mapped[str] = mapped_column(String(500), default="")
    imagenes1: Mapped[list] = mapped_column(JsonType, default=_tres_vacias)
    titulo2: Mapped[str] = mapped_column(String(255), default="")
    descripcion2: Mapped[str] = mapped_column(Text, default="")
    repositorio2: Mapped[str] = mapped_column(String(500), default="")
    imagenes2: Mapped[list] = mapped_column(JsonType, default=_tres_vacias)
    titulo3: Mapped[str] = mapped_column(String(255), default="")
    descripcion3: Mapped[str] = mapped_column(Text, default="")
    repositorio3: Mapped[str] = mapped_column(String(500), default="")
    imagenes3: Mapped[list] = mapped_column(JsonType, default=_tres_vacias)


# Tablas de perfil: el nombre es el que devuelve GET usuario/:email en "tabla"
TABLAS_PERFIL: dict[str, type[Base]] = {
    "estudiante": Estudiante,
    "gerente": Gerente,
    "institucion_educativa": InstitucionEducativa,
}
