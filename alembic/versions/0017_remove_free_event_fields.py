"""remove free event fields

Revision ID: 0017_remove_free_event_fields
Revises: 0016_add_event_publish_target
Create Date: 2026-03-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_remove_free_event_fields"
down_revision: Union[str, None] = "0016_add_event_publish_target"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE events
            SET price = CASE
                WHEN price IS NOT NULL AND btrim(price) <> '' THEN btrim(price)
                WHEN prepay_fixed_free IS NOT NULL THEN prepay_fixed_free::text
                WHEN is_paid = FALSE THEN '0'
                ELSE price
            END
            WHERE price IS NULL OR btrim(price) = ''
            """
        )
    )

    unresolved_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM events
            WHERE price IS NULL OR btrim(price) = ''
            """
        )
    ).scalar_one()
    if unresolved_count:
        raise RuntimeError(
            "Cannot remove free event fields: some events still have no price after normalization."
        )

    op.alter_column("events", "price", existing_type=sa.String(length=32), nullable=False)
    op.drop_column("events", "prepay_fixed_free")
    op.drop_column("events", "prepay_percent")
    op.drop_column("events", "is_paid")


def downgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "events",
        sa.Column("prepay_percent", sa.Integer(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("prepay_fixed_free", sa.Integer(), nullable=True),
    )
    op.alter_column("events", "price", existing_type=sa.String(length=32), nullable=True)
