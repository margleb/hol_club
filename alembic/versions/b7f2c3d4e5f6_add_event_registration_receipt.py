"""add event registration receipt

Revision ID: b7f2c3d4e5f6
Revises: 1c7b1c2f4a77
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f2c3d4e5f6"
down_revision: Union[str, None] = "1c7b1c2f4a77"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column("receipt", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "receipt")
