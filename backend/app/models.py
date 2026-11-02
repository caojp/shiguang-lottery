"""四张核心表（SQLAlchemy 2.0 Core，不使用 ORM relationship）。

- games            彩种静态配置（JSONB 存储规则）
- draw_history     历史开奖（UNIQUE(game_code, issue)，幂等写入）
- bets             模拟投注（session_id 匿名，支持单式/复式、ticket_count）
- backtest_reports 回测报告（策略 vs 基线对照、显著性、detail JSONB）
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

games = Table(
    "games",
    metadata,
    Column("code", String(16), primary_key=True),
    Column("name", String(32), nullable=False),
    Column("game_type", String(16), nullable=False),
    Column("config_json", JSONB, nullable=False),   # 完整规则（zones/prize_levels/price/…）
)

draw_history = Table(
    "draw_history",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("game_code", String(16), nullable=False),
    Column("issue", String(32), nullable=False),    # 期号，如 "2026100"
    Column("draw_date", Date, nullable=True),
    Column("numbers_json", JSONB, nullable=False),  # {"red":[...],"blue":[...],"special":1,"digits":"007"}
    Column("source", String(32), nullable=False, server_default="manual"),  # 数据来源（official/demo/manual）
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("game_code", "issue", name="uq_draw_history_game_issue"),
    Index("ix_draw_history_game_date", "game_code", "draw_date"),
)

bets = Table(
    "bets",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("session_id", String(64), nullable=False, index=True),   # 匿名会话，不做账户体系
    Column("game_code", String(16), nullable=False),
    Column("bet_type", String(16), nullable=False, server_default="single"),  # single=单式 multiple=复式
    Column("numbers_json", JSONB, nullable=False),  # {"zones":{...},"digits":"..."}
    Column("ticket_count", Integer, nullable=False, server_default="1"),
    Column("stake", Integer, nullable=False, server_default="2"),   # 单注金额（元）
    Column("draw_issue", String(32), nullable=True),
    Column("draw_numbers_json", JSONB, nullable=True),
    Column("prize_level", String(32), nullable=True),   # 最高命中奖级名，未中奖为 NULL
    Column("prize_money", BigInteger, nullable=False, server_default="0"),
    Column("pool_high", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Index("ix_bets_session_created", "session_id", "created_at"),
)

backtest_reports = Table(
    "backtest_reports",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("session_id", String(64), nullable=False, index=True),
    Column("game_code", String(16), nullable=False),
    Column("strategy_json", JSONB, nullable=False, server_default="{}"),
    Column("periods", Integer, nullable=False),
    Column("avg_hits", Numeric(10, 4), nullable=False),
    Column("avg_similarity", Numeric(10, 4), nullable=False),
    Column("baseline_hits", Numeric(10, 4), nullable=True),
    Column("baseline_similarity", Numeric(10, 4), nullable=True),
    Column("is_significant", Boolean, nullable=False, server_default="false"),
    Column("detail_json", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Index("ix_backtest_reports_session_created", "session_id", "created_at"),
)
