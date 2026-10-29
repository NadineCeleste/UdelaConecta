"""Renombra el rol desarrollador a estudiante (tabla, índice, secuencia y valores de rol)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _renombrar(origen: str, destino: str) -> None:
    op.rename_table(origen, destino)
    op.execute(f"ALTER INDEX ix_{origen}_email RENAME TO ix_{destino}_email")
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER INDEX {origen}_pkey RENAME TO {destino}_pkey")
        op.execute(f"ALTER SEQUENCE {origen}_id_seq RENAME TO {destino}_id_seq")
    op.execute(f"UPDATE {destino} SET rol = '{destino}' WHERE rol = '{origen}'")


def upgrade() -> None:
    _renombrar("desarrollador", "estudiante")


def downgrade() -> None:
    _renombrar("estudiante", "desarrollador")
