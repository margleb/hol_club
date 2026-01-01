"""merge event interesting sources into event interesting

Revision ID: d1e2f3a4b5c6
Revises: 8f9a0b1c2d3e
Create Date: 2026-01-01 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "8f9a0b1c2d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_interesting",
        sa.Column("adv_placement_date", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "event_interesting",
        sa.Column("adv_channel_username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_interesting",
        sa.Column("adv_placement_price", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "event_interesting",
        sa.Column("adv_created", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE event_interesting ei
        SET
            adv_placement_date = eis.placement_date,
            adv_channel_username = eis.channel_username,
            adv_placement_price = eis.placement_price,
            adv_created = eis.created
        FROM event_interesting_sources eis
        WHERE ei.event_id = eis.event_id
          AND ei.user_id = eis.user_id
        """
    )

    op.drop_table("event_interesting_sources")


def downgrade() -> None:
    op.create_table(
        "event_interesting_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("placement_date", sa.String(length=32), nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("placement_price", sa.String(length=32), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "user_id",
            name="uq_event_interesting_sources",
        ),
    )

    op.execute(
        """
        INSERT INTO event_interesting_sources (
            event_id,
            user_id,
            placement_date,
            channel_username,
            placement_price,
            created
        )
        SELECT
            event_id,
            user_id,
            adv_placement_date,
            adv_channel_username,
            adv_placement_price,
            adv_created
        FROM event_interesting
        WHERE adv_placement_date IS NOT NULL
          AND adv_channel_username IS NOT NULL
          AND adv_placement_price IS NOT NULL
        """
    )

    op.drop_column("event_interesting", "adv_created")
    op.drop_column("event_interesting", "adv_placement_price")
    op.drop_column("event_interesting", "adv_channel_username")
    op.drop_column("event_interesting", "adv_placement_date")
