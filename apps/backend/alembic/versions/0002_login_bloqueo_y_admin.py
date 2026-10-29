"""auth_users: bloqueo por intentos fallidos y flag de administrador

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column(
        "auth_users", sa.Column("failed_logins", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("auth_users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("auth_users", "locked_until")
    op.drop_column("auth_users", "failed_logins")
    op.drop_column("auth_users", "is_admin")
