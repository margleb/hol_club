"""drop unused user profile geo/timezone columns

Revision ID: 0002_drop_unused_user_columns
Revises: 0001_initial
Create Date: 2026-02-07 16:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_drop_unused_user_columns"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "tz_region")
    op.drop_column("users", "tz_offset")
    op.drop_column("users", "longitude")
    op.drop_column("users", "latitude")


def downgrade() -> None:
    op.add_column("users", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("tz_offset", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("tz_region", sa.String(length=50), nullable=True))
