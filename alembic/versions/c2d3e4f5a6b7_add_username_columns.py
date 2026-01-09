"""add username columns to users and event_interesting

Revision ID: c2d3e4f5a6b7
Revises: d1e2f3a4b5c6
Create Date: 2026-01-01 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_users_sequence() -> None:
    op.execute(
        """
        DO $$
        DECLARE seq text;
        BEGIN
            SELECT pg_get_serial_sequence('users', 'id') INTO seq;
            IF seq IS NOT NULL THEN
                EXECUTE format(
                    'SELECT setval(%L, (SELECT COALESCE(MAX(id), 1) FROM users), false)',
                    seq
                );
            END IF;
        END $$;
        """
    )


def _set_event_interesting_sequence() -> None:
    op.execute(
        """
        DO $$
        DECLARE seq text;
        BEGIN
            SELECT pg_get_serial_sequence('event_interesting', 'id') INTO seq;
            IF seq IS NOT NULL THEN
                EXECUTE format(
                    'SELECT setval(%L, (SELECT COALESCE(MAX(id), 1) FROM event_interesting), false)',
                    seq
                );
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.rename_table("users", "users_old")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tz_region", sa.String(length=50), nullable=True),
        sa.Column("tz_offset", sa.String(length=10), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "partner",
                "user",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("is_alive", sa.Boolean(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_users_user_id"),
    )
    op.execute(
        """
        INSERT INTO users (
            id,
            user_id,
            username,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        )
        SELECT
            id,
            user_id,
            NULL AS username,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        FROM users_old
        """
    )
    op.drop_table("users_old")
    _set_users_sequence()

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
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("adv_placement_date", sa.String(length=32), nullable=True),
        sa.Column("adv_channel_username", sa.String(length=64), nullable=True),
        sa.Column("adv_placement_price", sa.String(length=32), nullable=True),
        sa.Column("adv_created", sa.DateTime(timezone=True), nullable=True),
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
            username,
            source,
            adv_placement_date,
            adv_channel_username,
            adv_placement_price,
            adv_created,
            is_registered,
            is_paid,
            receipt,
            created
        )
        SELECT
            id,
            event_id,
            user_id,
            NULL AS username,
            source,
            adv_placement_date,
            adv_channel_username,
            adv_placement_price,
            adv_created,
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
        sa.Column("adv_placement_date", sa.String(length=32), nullable=True),
        sa.Column("adv_channel_username", sa.String(length=64), nullable=True),
        sa.Column("adv_placement_price", sa.String(length=32), nullable=True),
        sa.Column("adv_created", sa.DateTime(timezone=True), nullable=True),
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
            created,
            adv_placement_date,
            adv_channel_username,
            adv_placement_price,
            adv_created
        )
        SELECT
            id,
            event_id,
            user_id,
            source,
            is_registered,
            is_paid,
            receipt,
            created,
            adv_placement_date,
            adv_channel_username,
            adv_placement_price,
            adv_created
        FROM event_interesting_old
        """
    )
    op.drop_table("event_interesting_old")
    _set_event_interesting_sequence()

    op.rename_table("users", "users_old")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tz_region", sa.String(length=50), nullable=True),
        sa.Column("tz_offset", sa.String(length=10), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "partner",
                "user",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("is_alive", sa.Boolean(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.execute(
        """
        INSERT INTO users (
            id,
            user_id,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        )
        SELECT
            id,
            user_id,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        FROM users_old
        """
    )
    op.drop_table("users_old")
    _set_users_sequence()
