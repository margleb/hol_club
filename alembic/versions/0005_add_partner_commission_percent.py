"""add users.commission_percent

Revision ID: 0005_partner_commission
Revises: 0004_user_temperature
Create Date: 2026-02-08 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_partner_commission"
down_revision: Union[str, None] = "0004_user_temperature"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "commission_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "commission_percent")
