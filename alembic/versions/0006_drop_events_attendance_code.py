"""drop events.attendance_code

Revision ID: 0006_drop_events_attendance_code
Revises: 0005_partner_commission
Create Date: 2026-02-08 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_drop_events_attendance_code"
down_revision: Union[str, None] = "0005_partner_commission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("events", "attendance_code")


def downgrade() -> None:
    op.add_column(
        "events",
        sa.Column("attendance_code", sa.String(length=32), nullable=True),
    )
