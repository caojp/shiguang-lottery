"""initial schema: games / draw_history / bets / backtest_reports

Revision ID: 0001
Revises:
Create Date: 2026-10-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("code", sa.String(length=16), primary_key=True),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("game_type", sa.String(length=16), nullable=False),
        sa.Column("config_json", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "draw_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_code", sa.String(length=16), nullable=False),
        sa.Column("issue", sa.String(length=32), nullable=False),
        sa.Column("draw_date", sa.Date(), nullable=True),
        sa.Column("numbers_json", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_code", "issue", name="uq_draw_history_game_issue"),
    )
    op.create_index("ix_draw_history_game_date", "draw_history", ["game_code", "draw_date"])
    op.create_table(
        "bets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("game_code", sa.String(length=16), nullable=False),
        sa.Column("bet_type", sa.String(length=16), nullable=False, server_default="single"),
        sa.Column("numbers_json", postgresql.JSONB(), nullable=False),
        sa.Column("ticket_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stake", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("draw_issue", sa.String(length=32), nullable=True),
        sa.Column("draw_numbers_json", postgresql.JSONB(), nullable=True),
        sa.Column("prize_level", sa.String(length=32), nullable=True),
        sa.Column("prize_money", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("pool_high", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bets_session_id", "bets", ["session_id"])
    op.create_index("ix_bets_session_created", "bets", ["session_id", "created_at"])
    op.create_table(
        "backtest_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("game_code", sa.String(length=16), nullable=False),
        sa.Column("strategy_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("periods", sa.Integer(), nullable=False),
        sa.Column("avg_hits", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("avg_similarity", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("baseline_hits", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("baseline_similarity", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("is_significant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("detail_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_reports_session_id", "backtest_reports", ["session_id"])
    op.create_index("ix_backtest_reports_session_created", "backtest_reports", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_table("backtest_reports")
    op.drop_table("bets")
    op.drop_table("draw_history")
    op.drop_table("games")
