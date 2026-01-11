"""reorder users columns

Revision ID: a1b2c3d4e5f6
Revises: f7a1b2c3d4e5
Create Date: 2026-01-01 15:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_users_sequence() -> None:
    op.execute(
        """
        DO $$
        DECLARE seq text;
        BEGIN
            SELECT pg_get_serial_sequence('users', 'id') INTO seq;
            IF seq IS NOT NULL THEN
                EXECUTE format(
                    'SELECT setval(%L, (SELECT COALESCE(MAX(id), 1) FROM users), false)',
                    seq
                );
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.users') IS NOT NULL THEN
                ALTER TABLE users RENAME TO users_old;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.users_old') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    WHERE t.relname = 'users_old'
                      AND c.conname = 'uq_users_user_id'
                ) THEN
                    EXECUTE 'ALTER TABLE users_old DROP CONSTRAINT uq_users_user_id';
                END IF;
            END IF;
        END $$;
        """
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("age_group", sa.String(length=32), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tz_region", sa.String(length=50), nullable=True),
        sa.Column("tz_offset", sa.String(length=10), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "partner",
                "user",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("is_alive", sa.Boolean(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_users_user_id"),
    )
    op.execute(
        """
        INSERT INTO users (
            id,
            user_id,
            username,
            gender,
            age_group,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        )
        SELECT
            id,
            user_id,
            username,
            gender,
            age_group,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            role,
            is_alive,
            is_blocked
        FROM users_old
        """
    )
    op.drop_table("users_old")
    _set_users_sequence()


def downgrade() -> None:
    op.rename_table("users", "users_old")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tz_region", sa.String(length=50), nullable=True),
        sa.Column("tz_offset", sa.String(length=10), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("age_group", sa.String(length=32), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "partner",
                "user",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("is_alive", sa.Boolean(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_users_user_id"),
    )
    op.execute(
        """
        INSERT INTO users (
            id,
            user_id,
            username,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            gender,
            age_group,
            role,
            is_alive,
            is_blocked
        )
        SELECT
            id,
            user_id,
            username,
            created,
            tz_region,
            tz_offset,
            longitude,
            latitude,
            language,
            gender,
            age_group,
            role,
            is_alive,
            is_blocked
        FROM users_old
        """
    )
    op.drop_table("users_old")
    _set_users_sequence()
