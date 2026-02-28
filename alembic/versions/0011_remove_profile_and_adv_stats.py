"""remove profile and advertising stats schema

Revision ID: 0011_remove_profile_adv_stats
Revises: 0010_event_reg_payment_proof
Create Date: 2026-02-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_remove_profile_adv_stats"
down_revision: Union[str, None] = "0010_event_reg_payment_proof"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("profile_nudges")
    op.drop_table("adv_registrations")
    op.drop_table("adv_stats")

    op.drop_column("users", "temperature")
    op.drop_column("users", "age_group")
    op.drop_column("users", "gender")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("gender", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("age_group", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "temperature",
            sa.String(length=16),
            nullable=False,
            server_default="cold",
        ),
    )

    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column("register_count", sa.Integer(), nullable=False, server_default="0"),
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
        "profile_nudges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
