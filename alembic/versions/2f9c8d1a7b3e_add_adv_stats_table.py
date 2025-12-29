"""add adv stats table

Revision ID: 2f9c8d1a7b3e
Revises: b7f2c3d4e5f6
Create Date: 2025-03-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f9c8d1a7b3e"
down_revision: Union[str, None] = "b7f2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column("adv_placement_date", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "event_registrations",
        sa.Column("adv_channel_username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_registrations",
        sa.Column("adv_placement_price", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column(
            "registrations_count",
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
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_stats_event_date_channel_price",
        ),
    )


def downgrade() -> None:
    op.drop_table("adv_stats")
    op.drop_column("event_registrations", "adv_placement_price")
    op.drop_column("event_registrations", "adv_channel_username")
    op.drop_column("event_registrations", "adv_placement_date")
