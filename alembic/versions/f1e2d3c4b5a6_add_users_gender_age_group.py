"""add gender and age_group to users

Revision ID: f1e2d3c4b5a6
Revises: c2d3e4f5a6b7
Create Date: 2026-01-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("gender", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("age_group", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "age_group")
    op.drop_column("users", "gender")
