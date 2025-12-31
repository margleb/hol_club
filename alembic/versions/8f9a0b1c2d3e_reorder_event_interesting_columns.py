"""reorder event interesting columns

Revision ID: 8f9a0b1c2d3e
Revises: 7e8f9a0b1c2d
Create Date: 2025-03-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f9a0b1c2d3e"
down_revision: Union[str, None] = "7e8f9a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_event_interesting_sequence() -> None:
    op.execute(
        """
        DO $$
        DECLARE seq text;
        BEGIN
            SELECT pg_get_serial_sequence('event_interesting', 'id') INTO seq;
            IF seq IS NOT NULL THEN
                EXECUTE format(
                    'SELECT setval(%L, (SELECT COALESCE(MAX(id), 0) FROM event_interesting), true)',
                    seq
                );
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.rename_table("event_interesting", "event_interesting_old")
    op.drop_constraint(
        "uq_event_interesting",
        "event_interesting_old",
        type_="unique",
    )
    op.drop_index(
        "ix_event_interesting_event_id",
        table_name="event_interesting_old",
    )
    op.create_table(
        "event_interesting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "is_registered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("receipt", sa.String(length=255), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_interesting"),
    )
    op.create_index(
        "ix_event_interesting_event_id",
        "event_interesting",
        ["event_id"],
    )
    op.execute(
        """
        INSERT INTO event_interesting (
            id,
            event_id,
            user_id,
            source,
            is_registered,
            is_paid,
            receipt,
            created
        )
        SELECT
            id,
            event_id,
            user_id,
            source,
            is_registered,
            is_paid,
            receipt,
            created
        FROM event_interesting_old
        """
    )
    op.drop_table("event_interesting_old")
    _set_event_interesting_sequence()


def downgrade() -> None:
    op.rename_table("event_interesting", "event_interesting_old")
    op.drop_constraint(
        "uq_event_interesting",
        "event_interesting_old",
        type_="unique",
    )
    op.drop_index(
        "ix_event_interesting_event_id",
        table_name="event_interesting_old",
    )
    op.create_table(
        "event_interesting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("receipt", sa.String(length=255), nullable=True),
        sa.Column(
            "is_registered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_interesting"),
    )
    op.create_index(
        "ix_event_interesting_event_id",
        "event_interesting",
        ["event_id"],
    )
    op.execute(
        """
        INSERT INTO event_interesting (
            id,
            event_id,
            user_id,
            source,
            created,
            is_paid,
            receipt,
            is_registered
        )
        SELECT
            id,
            event_id,
            user_id,
            source,
            created,
            is_paid,
            receipt,
            is_registered
        FROM event_interesting_old
        """
    )
    op.drop_table("event_interesting_old")
    _set_event_interesting_sequence()
