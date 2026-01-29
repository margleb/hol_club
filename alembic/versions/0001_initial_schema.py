"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-29 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("age_group", sa.String(length=32), nullable=True),
        sa.Column("intent", sa.String(length=16), nullable=True),
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

    op.create_table(
        "partner_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="partnerrequeststatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column(
            "register_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_stats_date_channel_price",
        ),
    )

    op.create_table(
        "adv_registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_registrations_user_date_channel_price",
        ),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("partner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_datetime", sa.String(length=32), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column("price", sa.String(length=32), nullable=True),
        sa.Column("age_group", sa.String(length=32), nullable=True),
        sa.Column("photo_file_id", sa.String(length=255), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("male_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("male_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("male_message_id", sa.BigInteger(), nullable=True),
        sa.Column("male_chat_username", sa.String(length=255), nullable=True),
        sa.Column("female_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("female_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("female_message_id", sa.BigInteger(), nullable=True),
        sa.Column("female_chat_username", sa.String(length=255), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("adv_registrations")
    op.drop_table("adv_stats")
    op.drop_table("partner_requests")
    op.drop_table("users")
