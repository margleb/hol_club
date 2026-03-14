"""add event registration reminder sent at

Revision ID: 0020_event_reg_reminder
Revises: 0019_update_private_chat_delete_at_24h
Create Date: 2026-03-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0020_event_reg_reminder"
down_revision: Union[str, None] = "0019_private_chat_delete_24h"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "reminder_sent_at")
