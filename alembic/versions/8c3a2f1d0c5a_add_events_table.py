"""add events table

Revision ID: 8c3a2f1d0c5a
Revises: 6b9c7f4f8bda
Create Date: 2025-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c3a2f1d0c5a"
down_revision: Union[str, None] = "6b9c7f4f8bda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
        sa.Column("notify_users", sa.Boolean(), nullable=False),
        sa.Column("photo_file_id", sa.String(length=255), nullable=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_events_partner_user_id",
        "events",
        ["partner_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_partner_user_id", table_name="events")
    op.drop_table("events")
