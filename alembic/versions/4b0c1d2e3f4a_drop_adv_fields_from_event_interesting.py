"""drop adv fields from event interesting

Revision ID: 4b0c1d2e3f4a
Revises: 3a1b2c4d5e6f
Create Date: 2025-03-20 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b0c1d2e3f4a"
down_revision: Union[str, None] = "3a1b2c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("event_interesting", "adv_placement_date")
    op.drop_column("event_interesting", "adv_channel_username")
    op.drop_column("event_interesting", "adv_placement_price")


def downgrade() -> None:
    op.add_column(
        "event_interesting",
        sa.Column("adv_placement_price", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "event_interesting",
        sa.Column("adv_channel_username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_interesting",
        sa.Column("adv_placement_date", sa.String(length=32), nullable=True),
    )
