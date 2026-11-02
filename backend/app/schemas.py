"""Pydantic 请求 / 响应模型与 engine 配置序列化助手。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .engine.config import GameConfig, PrizeLevel, Zone


# ---------------------------------------------------------------- 序列化

def zone_out(z: Zone) -> dict[str, Any]:
    return {"name": z.name, "pool_size": z.pool_size, "pick": z.pick, "label": z.label}


def level_out(l: PrizeLevel) -> dict[str, Any]:
    return {
        "name": l.name,
        "condition": l.condition,
        "amount": l.amount,
        "float_default": l.float_default,
        "amount_high": l.amount_high,
        "is_float": l.is_float,
    }


def game_out(g: GameConfig) -> dict[str, Any]:
    return {
        "code": g.code,
        "name": g.name,
        "game_type": g.game_type,
        "price": g.price,
        "digits": g.digits,
        "special": g.special,
        "pool_high": g.pool_high,
        "play_names": list(g.play_names),
        "draw_days": list(g.draw_days),
        "zones": [zone_out(z) for z in g.zones],
        "prize_levels": [level_out(l) for l in g.prize_levels],
    }


# ---------------------------------------------------------------- 请求

class PickRequest(BaseModel):
    game_code: str
    mode: str = "random"                       # random | strategy | history | manual
    count: int = Field(default=1, ge=1, le=100)
    strategy: dict[str, Any] = Field(default_factory=dict)   # 策略参数（冷热权重/区间/奇偶…）
    zone_inputs: dict[str, str] = Field(default_factory=dict)  # 自选：各分组号码文本
    digits: str = ""                                          # 自选：数字型号码
    play: str = ""                                            # 数字型玩法：直选/组选3/组选6
    compound: bool = False                                    # 自选复式（乐透型多选号码）
    history_periods: int = Field(default=60, ge=10, le=200)    # 历史推演参考期数


class TicketIn(BaseModel):
    zones: dict[str, list[int]] = Field(default_factory=dict)
    digits: str = ""


class DrawRequest(BaseModel):
    game_code: str
    session_id: str = "anonymous"
    tickets: list[TicketIn] = Field(min_length=1, max_length=200)
    pool_high: bool = True
    play: Optional[str] = None


class BacktestRequest(BaseModel):
    game_code: str
    session_id: str = "anonymous"
    periods: int = Field(default=100, ge=10, le=300)
    strategy: dict[str, Any] = Field(default_factory=dict)
    trials_per_period: int = Field(default=10, ge=1, le=100)   # 每期生成注数


class AgentChatRequest(BaseModel):
    session_id: str = "anonymous"
    message: str = Field(min_length=1)


# ---------------------------------------------------------------- 响应

class PickOut(BaseModel):
    game_code: str
    mode: str
    count: int
    price: int
    cost: int
    play: str = ""
    tickets: list[dict[str, Any]]              # [{zones, digits, display}]
    basis: Optional[dict[str, Any]] = None     # 历史推演依据（期数/热号/遗漏号）


class DrawOut(BaseModel):
    game_code: str
    draw: dict[str, Any]                       # 开奖号码（zones/special/digits/display）
    cost: int
    win: int
    profit: int
    hit_count: int
    results: list[dict[str, Any]]              # 逐注对奖
    bet_id: Optional[int] = None


class BacktestOut(BaseModel):
    id: Optional[int] = None
    game_code: str
    periods: int
    avg_hits: float
    avg_similarity: float
    baseline_hits: Optional[float] = None
    baseline_similarity: Optional[float] = None
    is_significant: bool
    cost: int = 0
    total_win: int = 0
    roi: float = 0.0
    baseline_total_win: int = 0
    baseline_roi: float = 0.0
    win_rate: float = 0.0
    baseline_win_rate: float = 0.0
    detail: list[dict[str, Any]]               # 每期 {issue, hits, similarity, baseline_hits, baseline_similarity, rolling_mean}
