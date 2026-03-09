"""add event publish target

Revision ID: 0016_add_event_publish_target
Revises: 0015_add_event_commission_stats
Create Date: 2026-03-02 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_add_event_publish_target"
down_revision: Union[str, None] = "0015_add_event_commission_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "publish_target",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'both'"),
        ),
    )
    op.create_check_constraint(
        "ck_events_publish_target",
        "events",
        "publish_target IN ('bot', 'channel', 'both')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_events_publish_target", "events", type_="check")
    op.drop_column("events", "publish_target")
