"""drop user language column

Revision ID: 0003_drop_user_language
Revises: 0002_drop_unused_user_columns
Create Date: 2026-02-07 16:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_drop_user_language"
down_revision: Union[str, None] = "0002_drop_unused_user_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "language")


def downgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(length=10), nullable=True))
