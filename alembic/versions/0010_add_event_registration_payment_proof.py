"""add payment proof fields to event registrations

Revision ID: 0010_event_reg_payment_proof
Revises: 0009_add_profile_nudges
Create Date: 2026-02-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_event_reg_payment_proof"
down_revision: Union[str, None] = "0009_add_profile_nudges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column("payment_proof_file_id", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "event_registrations",
        sa.Column("payment_proof_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "event_registrations",
        sa.Column("payment_proof_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "payment_proof_uploaded_at")
    op.drop_column("event_registrations", "payment_proof_type")
    op.drop_column("event_registrations", "payment_proof_file_id")
