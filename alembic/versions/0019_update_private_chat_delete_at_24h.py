"""update private chat deletion timing to 24h after event

Revision ID: 0019_private_chat_delete_24h
Revises: 0018_event_datetime_tz
Create Date: 2026-03-14 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019_private_chat_delete_24h"
down_revision: Union[str, None] = "0018_event_datetime_tz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE events
            SET private_chat_delete_at = event_datetime + interval '24 hours'
            WHERE event_datetime IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE events
            SET private_chat_delete_at = (
                (
                    date_trunc(
                        'day',
                        event_datetime AT TIME ZONE 'Europe/Moscow'
                    )
                    + interval '1 day'
                    + interval '3 hour'
                ) AT TIME ZONE 'Europe/Moscow'
            )
            WHERE event_datetime IS NOT NULL
            """
        )
    )