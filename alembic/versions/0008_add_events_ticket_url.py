"""add events ticket url

Revision ID: 0008_add_events_ticket_url
Revises: 0007_private_chat_invite_link
Create Date: 2026-02-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_add_events_ticket_url"
down_revision: Union[str, None] = "0007_private_chat_invite_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("ticket_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "ticket_url")
