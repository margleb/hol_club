"""make event datetime timezone aware

Revision ID: 0018_event_datetime_tz
Revises: 0017_remove_free_event_fields
Create Date: 2026-03-09 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_event_datetime_tz"
down_revision: Union[str, None] = "0017_remove_free_event_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "events",
        sa.Column("event_datetime_tmp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("private_chat_delete_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("private_chat_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind.execute(
        sa.text(
            """
            UPDATE events
            SET event_datetime_tmp = CASE
                WHEN event_datetime IS NULL OR btrim(event_datetime) = '' THEN NULL
                WHEN btrim(event_datetime) ~ '^\\d{4}\\.\\d{2}\\.\\d{2} \\d{2}:\\d{2}$'
                    THEN to_timestamp(
                        btrim(event_datetime),
                        'YYYY.MM.DD HH24:MI'
                    )::timestamp AT TIME ZONE 'Europe/Moscow'
                WHEN btrim(event_datetime) ~ '(Z|[+-]\\d{2}:\\d{2})$'
                    THEN btrim(event_datetime)::timestamptz
                ELSE btrim(event_datetime)::timestamp AT TIME ZONE 'Europe/Moscow'
            END
            """
        )
    )

    unresolved_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM events
            WHERE event_datetime_tmp IS NULL
            """
        )
    ).scalar_one()
    if unresolved_count:
        raise RuntimeError(
            "Cannot convert event datetimes to timezone-aware values."
        )

    bind.execute(
        sa.text(
            """
            UPDATE events
            SET private_chat_delete_at = (
                (
                    date_trunc(
                        'day',
                        event_datetime_tmp AT TIME ZONE 'Europe/Moscow'
                    )
                    + interval '1 day'
                    + interval '3 hour'
                ) AT TIME ZONE 'Europe/Moscow'
            )
            WHERE event_datetime_tmp IS NOT NULL
            """
        )
    )

    op.drop_column("events", "event_datetime")
    op.alter_column(
        "events",
        "event_datetime_tmp",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        new_column_name="event_datetime",
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "events",
        sa.Column("event_datetime_old", sa.String(length=32), nullable=True),
    )

    bind.execute(
        sa.text(
            """
            UPDATE events
            SET event_datetime_old = to_char(
                event_datetime AT TIME ZONE 'Europe/Moscow',
                'YYYY.MM.DD HH24:MI'
            )
            WHERE event_datetime IS NOT NULL
            """
        )
    )

    op.drop_column("events", "event_datetime")
    op.alter_column(
        "events",
        "event_datetime_old",
        existing_type=sa.String(length=32),
        nullable=False,
        new_column_name="event_datetime",
    )
    op.drop_column("events", "private_chat_deleted_at")
    op.drop_column("events", "private_chat_delete_at")
