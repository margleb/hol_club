"""rename users.intent to users.temperature

Revision ID: 0004_user_temperature
Revises: 0003_drop_user_language
Create Date: 2026-02-07 17:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_user_temperature"
down_revision: Union[str, None] = "0003_drop_user_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "intent",
        existing_type=sa.String(length=16),
        new_column_name="temperature",
        existing_nullable=True,
    )
    op.execute(
        "UPDATE users SET temperature = 'cold' "
        "WHERE temperature IS NULL OR temperature = ''"
    )
    op.alter_column(
        "users",
        "temperature",
        existing_type=sa.String(length=16),
        nullable=False,
        server_default=sa.text("'cold'"),
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "temperature",
        existing_type=sa.String(length=16),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "users",
        "temperature",
        existing_type=sa.String(length=16),
        new_column_name="intent",
        existing_nullable=True,
    )
