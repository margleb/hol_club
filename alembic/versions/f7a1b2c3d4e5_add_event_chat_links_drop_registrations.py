"""add event chat links and drop event registrations

Revision ID: f7a1b2c3d4e5
Revises: e3c4b5a6d7f8
Create Date: 2026-01-01 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a1b2c3d4e5"
down_revision: Union[str, None] = "4d87d15135bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "male_chat_url",
                sa.String(length=255),
                nullable=False,
                server_default="",
            )
        )
        batch_op.add_column(
            sa.Column(
                "female_chat_url",
                sa.String(length=255),
                nullable=False,
                server_default="",
            )
        )
        batch_op.drop_column("auto_message_text")

    op.drop_table("event_interesting")
    op.drop_table("adv_stats")


def downgrade() -> None:
    op.create_table(
        "event_interesting",
        sa.Column("id", sa.Integer(), primary_key=True),
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
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_interesting"),
    )
    op.create_index(
        "ix_event_interesting_event_id",
        "event_interesting",
        ["event_id"],
        unique=False,
    )

    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column(
            "interesting_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "register_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "paid_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "confirmed_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_stats_event_date_channel_price",
        ),
    )

    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("auto_message_text", sa.Text(), nullable=True))
        batch_op.drop_column("female_chat_url")
        batch_op.drop_column("male_chat_url")
