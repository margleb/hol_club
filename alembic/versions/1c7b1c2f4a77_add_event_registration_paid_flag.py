"""add event registration paid flag

Revision ID: 1c7b1c2f4a77
Revises: 9e5a1f5f0b1a
Create Date: 2025-03-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c7b1c2f4a77"
down_revision: Union[str, None] = "9e5a1f5f0b1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "is_paid")
