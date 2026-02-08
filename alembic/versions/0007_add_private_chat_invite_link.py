"""add events.private_chat_invite_link

Revision ID: 0007_private_chat_invite_link
Revises: 0006_drop_events_attendance_code
Create Date: 2026-02-08 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_private_chat_invite_link"
down_revision: Union[str, None] = "0006_drop_events_attendance_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("private_chat_invite_link", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "private_chat_invite_link")
