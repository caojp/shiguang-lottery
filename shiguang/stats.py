"""批量模拟与统计：生成 N 注 → 一次模拟开奖 → 逐注对奖 → 汇总。

统计指标：总投入、总奖金、各奖级注数、盈亏、回报率。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import GameConfig
from .draw import draw
from .engine import Ticket, generate_tickets
from .prize import check


@dataclass
class BatchReport:
    """一次批量模拟的汇总结果。"""

    game_code: str
    count: int
    cost: int                          # 总投入（元）
    win: int                           # 总中奖金额（元）
    profit: int                        # 盈亏 = 总奖金 - 总投入
    roi: float                         # 回报率 = 总奖金 / 总投入
    hit_count: int                     # 中奖注数
    level_counts: dict[str, int] = field(default_factory=dict)   # 奖级名 -> 中奖注数
    win_money_by_level: dict[str, int] = field(default_factory=dict)
    draw_display: str = ""             # 本期开奖号码（格式化）
    tickets: list[Ticket] = field(default_factory=list)          # 生成的号码


def simulate(
    game: GameConfig,
    count: int = 1000,
    strategy: dict | None = None,
    pool_high: bool = False,
    play: str | None = None,
    seed: int | None = None,
) -> BatchReport:
    """批量模拟。count 为投注注数，每注 game.price 元。"""
    count = max(1, int(count))
    tickets = generate_tickets(game, count=count, strategy=strategy)
    draw_result = draw(game)

    level_counts: dict[str, int] = {}
    win_money: dict[str, int] = {}
    total_win = 0
    hit_count = 0
    for t in tickets:
        r = check(game, t, draw_result, pool_high=pool_high, play=play)
        if r.won:
            hit_count += 1
            total_win += r.money
            assert r.level is not None
            level_counts[r.level.name] = level_counts.get(r.level.name, 0) + 1
            win_money[r.level.name] = win_money.get(r.level.name, 0) + r.money

    cost = count * game.price
    roi = round(total_win / cost, 6) if cost else 0.0
    return BatchReport(
        game_code=game.code,
        count=count,
        cost=cost,
        win=total_win,
        profit=total_win - cost,
        roi=roi,
        hit_count=hit_count,
        level_counts=level_counts,
        win_money_by_level=win_money,
        draw_display=draw_result.display(game),
        tickets=tickets,
    )
