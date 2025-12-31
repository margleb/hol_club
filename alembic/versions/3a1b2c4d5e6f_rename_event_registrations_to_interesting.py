"""rename event registrations to event interesting

Revision ID: 3a1b2c4d5e6f
Revises: 2f9c8d1a7b3e
Create Date: 2025-03-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a1b2c4d5e6f"
down_revision: Union[str, None] = "2f9c8d1a7b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("event_registrations", "event_interesting")
    op.execute(
        "ALTER INDEX ix_event_registrations_event_id "
        "RENAME TO ix_event_interesting_event_id"
    )
    op.drop_constraint(
        "uq_event_registrations",
        "event_interesting",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_event_interesting",
        "event_interesting",
        ["event_id", "user_id"],
    )
    op.add_column(
        "event_interesting",
        sa.Column(
            "is_registered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute("UPDATE event_interesting SET is_registered = true")


def downgrade() -> None:
    op.drop_column("event_interesting", "is_registered")
    op.drop_constraint(
        "uq_event_interesting",
        "event_interesting",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_event_registrations",
        "event_interesting",
        ["event_id", "user_id"],
    )
    op.execute(
        "ALTER INDEX ix_event_interesting_event_id "
        "RENAME TO ix_event_registrations_event_id"
    )
    op.rename_table("event_interesting", "event_registrations")
