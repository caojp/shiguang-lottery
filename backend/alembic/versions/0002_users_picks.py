"""users / user_picks：登录账户与登录用户选号记录

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_table(
        "user_picks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_code", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="random"),
        sa.Column("play", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("numbers_json", postgresql.JSONB(), nullable=False),
        sa.Column("draw_json", postgresql.JSONB(), nullable=True),
        sa.Column("win", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_picks_user_created", "user_picks", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_picks_user_created", table_name="user_picks")
    op.drop_table("user_picks")
    op.drop_table("users")
