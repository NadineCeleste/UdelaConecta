"""contrato: requisitos estructurados; nueva tabla informe_postulacion

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSONB nativo en PostgreSQL. En otros motores (por ejemplo SQLite en tests) es JSON plano.
JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("contrato", sa.Column("requisitos", JsonType, nullable=True))
    op.execute("UPDATE contrato SET requisitos = '[]' WHERE requisitos IS NULL")
    op.alter_column("contrato", "requisitos", nullable=False)

    op.create_table(
        "informe_postulacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contrato_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_email", sa.String(length=255), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("modelo", sa.String(length=60), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contrato_id"], ["contrato.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contrato_id", "estudiante_email", name="uq_informe_postulacion"),
    )
    op.create_index("ix_informe_postulacion_contrato_id", "informe_postulacion", ["contrato_id"])
    op.create_index(
        "ix_informe_postulacion_estudiante_email", "informe_postulacion", ["estudiante_email"]
    )


def downgrade() -> None:
    op.drop_index("ix_informe_postulacion_estudiante_email", table_name="informe_postulacion")
    op.drop_index("ix_informe_postulacion_contrato_id", table_name="informe_postulacion")
    op.drop_table("informe_postulacion")
    op.drop_column("contrato", "requisitos")
