"""add events fingerprint

Revision ID: 4a6f1c2b7f9a
Revises: 8c3a2f1d0c5a
Create Date: 2025-03-10 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a6f1c2b7f9a"
down_revision: Union[str, None] = "8c3a2f1d0c5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("fingerprint", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint(
            "uq_events_fingerprint",
            ["fingerprint"],
        )

    op.execute("UPDATE events SET fingerprint = md5(id::text)")

    with op.batch_alter_table("events") as batch_op:
        batch_op.alter_column("fingerprint", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_constraint("uq_events_fingerprint", type_="unique")
        batch_op.drop_column("fingerprint")
