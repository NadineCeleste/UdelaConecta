"""Esquema inicial: auth, perfiles, proyectos, contratos y portfolios

Revision ID: 0001
Revises:
Create Date: 2026-10-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _creado() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def _perfil_base(largo_nombre: int) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(largo_nombre), nullable=True),
        sa.Column("apellido", sa.String(largo_nombre), nullable=True),
        sa.Column("name", sa.String(240), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(60), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _creado(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_users_email", "auth_users", ["email"], unique=True)

    op.create_table(
        "desarrollador",
        *_perfil_base(120),
        sa.Column("genero", sa.String(30), nullable=True),
        sa.Column("fecha_nacimiento", sa.String(30), nullable=True),
        sa.Column("puesto_actual", sa.String(150), nullable=True),
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column("is_disponible", sa.Boolean(), nullable=False),
        sa.Column("verificado", sa.Boolean(), nullable=False),
        sa.Column("skills", JsonType, nullable=False),
        sa.Column("habilidades", JsonType, nullable=False),
        sa.Column("idiomas", JsonType, nullable=False),
        _creado(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_desarrollador_email", "desarrollador", ["email"], unique=True)

    op.create_table(
        "gerente",
        *_perfil_base(120),
        sa.Column("genero", sa.String(30), nullable=True),
        sa.Column("fecha_nacimiento", sa.String(30), nullable=True),
        sa.Column("puesto_actual", sa.String(150), nullable=True),
        sa.Column("id_proyecto", sa.String(64), nullable=True),
        sa.Column("habilidades", JsonType, nullable=False),
        sa.Column("idiomas", JsonType, nullable=False),
        _creado(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gerente_email", "gerente", ["email"], unique=True)

    op.create_table(
        "institucion_educativa",
        *_perfil_base(150),
        _creado(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_institucion_educativa_email", "institucion_educativa", ["email"], unique=True)

    op.create_table(
        "proyecto",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("info_link", sa.String(500), nullable=True),
        sa.Column("buscando_devs", sa.Boolean(), nullable=False),
        sa.Column("id_gerente", sa.String(64), nullable=True),
        sa.Column("email_gerente", sa.String(255), nullable=False),
        _creado(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proyecto_email_gerente", "proyecto", ["email_gerente"], unique=True)

    op.create_table(
        "contrato",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(100), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tiene_postulaciones", sa.Boolean(), nullable=False),
        sa.Column("postulaciones", JsonType, nullable=False),
        sa.Column("esta_ocupado", sa.Boolean(), nullable=False),
        sa.Column("pasante_email", sa.String(255), nullable=True),
        sa.Column("proyecto_id", sa.String(64), nullable=True),
        sa.Column("start_date", sa.String(30), nullable=True),
        sa.Column("end_date", sa.String(30), nullable=True),
        sa.Column("modalidad", sa.String(60), nullable=True),
        sa.Column("seniority_deseado", JsonType, nullable=False),
        _creado(),
        sa.ForeignKeyConstraint(["proyecto_id"], ["proyecto.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contrato_proyecto_id", "contrato", ["proyecto_id"])

    op.create_table(
        "portfolio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        *[
            col
            for n in (1, 2, 3)
            for col in (
                sa.Column(f"titulo{n}", sa.String(255), nullable=False),
                sa.Column(f"descripcion{n}", sa.Text(), nullable=False),
                sa.Column(f"repositorio{n}", sa.String(500), nullable=False),
                sa.Column(f"imagenes{n}", JsonType, nullable=False),
            )
        ],
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_email", "portfolio", ["email"], unique=True)


def downgrade() -> None:
    for tabla in ("portfolio", "contrato", "proyecto", "institucion_educativa", "gerente",
                  "desarrollador", "auth_users"):
        op.drop_table(tabla)
