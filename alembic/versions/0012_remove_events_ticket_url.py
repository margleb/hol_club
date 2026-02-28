"""remove events ticket url

Revision ID: 0012_remove_events_ticket_url
Revises: 0011_remove_profile_adv_stats
Create Date: 2026-02-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_remove_events_ticket_url"
down_revision: Union[str, None] = "0011_remove_profile_adv_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("events", "ticket_url")


def downgrade() -> None:
    op.add_column(
        "events",
        sa.Column("ticket_url", sa.String(length=1024), nullable=True),
    )
