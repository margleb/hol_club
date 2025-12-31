"""reorder adv stats columns

Revision ID: 7e8f9a0b1c2d
Revises: 6d7e8f9a0c1d
Create Date: 2025-03-20 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e8f9a0b1c2d"
down_revision: Union[str, None] = "6d7e8f9a0c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_adv_stats_sequence() -> None:
    op.execute(
        """
        DO $$
        DECLARE seq text;
        BEGIN
            SELECT pg_get_serial_sequence('adv_stats', 'id') INTO seq;
            IF seq IS NOT NULL THEN
                EXECUTE format(
                    'SELECT setval(%L, (SELECT COALESCE(MAX(id), 0) FROM adv_stats), true)',
                    seq
                );
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.rename_table("adv_stats", "adv_stats_old")
    op.drop_constraint(
        "uq_adv_stats_event_date_channel_price",
        "adv_stats_old",
        type_="unique",
    )
    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), nullable=False),
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
    op.execute(
        """
        INSERT INTO adv_stats (
            id,
            event_id,
            placement_date,
            channel_username,
            placement_price,
            interesting_count,
            register_count,
            paid_count,
            confirmed_count,
            created
        )
        SELECT
            id,
            event_id,
            placement_date,
            channel_username,
            placement_price,
            interesting_count,
            register_count,
            paid_count,
            confirmed_count,
            created
        FROM adv_stats_old
        """
    )
    op.drop_table("adv_stats_old")
    _set_adv_stats_sequence()


def downgrade() -> None:
    op.rename_table("adv_stats", "adv_stats_old")
    op.drop_constraint(
        "uq_adv_stats_event_date_channel_price",
        "adv_stats_old",
        type_="unique",
    )
    op.create_table(
        "adv_stats",
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.Column(
            "register_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
    op.execute(
        """
        INSERT INTO adv_stats (
            id,
            event_id,
            placement_date,
            channel_username,
            placement_price,
            interesting_count,
            paid_count,
            confirmed_count,
            created,
            register_count
        )
        SELECT
            id,
            event_id,
            placement_date,
            channel_username,
            placement_price,
            interesting_count,
            paid_count,
            confirmed_count,
            created,
            register_count
        FROM adv_stats_old
        """
    )
    op.drop_table("adv_stats_old")
    _set_adv_stats_sequence()
