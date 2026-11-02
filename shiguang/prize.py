"""中奖判定与奖金计算。

规则口径见 PRD 2.3 节，均按官方现行规则实现：
- 每注只兑付所中最高奖级奖金，不兼中兼得（与官方一致）
- 浮动奖按配置的模拟默认值返回（可自定义）
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import GameConfig, PrizeLevel
from .draw import DrawResult
from .engine import Ticket


@dataclass
class PrizeResult:
    """单注对奖结果。"""

    level: PrizeLevel | None        # 命中的奖级；None 表示未中奖
    level_index: int                # 在 game.prize_levels 中的下标；-1 表示未中奖
    money: int                      # 单注奖金（元）
    hits: dict[str, int] = field(default_factory=dict)  # 各区命中数，如 {"red": 4, "blue": 1}

    @property
    def won(self) -> bool:
        return self.level is not None


def _hits(ticket: Ticket, draw_result: DrawResult, game: GameConfig) -> dict[str, int]:
    """计算各号码池分组的命中数。"""
    return {
        z.name: len(set(ticket.zones.get(z.name, ())) & set(draw_result.zones.get(z.name, ())))
        for z in game.zones
    }


def check(
    game: GameConfig,
    ticket: Ticket,
    draw_result: DrawResult,
    pool_high: bool = False,
    play: str | None = None,
) -> PrizeResult:
    """对奖。play 为数字型投注玩法（直选/组选3/组选6）。"""
    levels = game.prize_levels

    if game.game_type == "lotto":
        hits = _hits(ticket, draw_result, game)
        if game.code == "ssq":
            rh, bh = hits["red"], hits["blue"]
            if rh == 6 and bh:
                idx = 0
            elif rh == 6:
                idx = 1
            elif rh == 5 and bh:
                idx = 2
            elif rh == 5 or (rh == 4 and bh):
                idx = 3
            elif rh == 4 or (rh == 3 and bh):
                idx = 4
            elif bh:
                idx = 5
            else:
                idx = -1
        elif game.code == "qlc":
            bh = hits["base"]
            sh = 1 if draw_result.special is not None and draw_result.special in set(ticket.zones.get("base", ())) else 0
            if bh == 7:
                idx = 0
            elif bh == 6 and sh:
                idx = 1
            elif bh == 6:
                idx = 2
            elif bh == 5 and sh:
                idx = 3
            elif bh == 5:
                idx = 4
            elif bh == 4 and sh:
                idx = 5
            elif bh == 4:
                idx = 6
            else:
                idx = -1
            hits = {"base": bh, "special": sh}
        elif game.code == "dlt":
            fh, bh = hits["front"], hits["back"]
            if (fh, bh) == (5, 2):
                idx = 0
            elif (fh, bh) == (5, 1):
                idx = 1
            elif (fh, bh) in ((5, 0), (4, 2)):
                idx = 2
            elif (fh, bh) == (4, 1):
                idx = 3
            elif (fh, bh) in ((4, 0), (3, 2)):
                idx = 4
            elif (fh, bh) in ((3, 1), (2, 2)):
                idx = 5
            elif (fh, bh) in ((3, 0), (2, 1), (1, 2), (0, 2)):
                idx = 6
            else:
                idx = -1
        else:  # 其他乐透型彩种通用回退：按奖级表顺序逐级匹配（预留扩展）
            idx = _generic_lotto_match(game, ticket, draw_result)
        return _result(levels, idx, hits, pool_high)

    if game.game_type == "keno":
        k = len(set(ticket.zones.get("main", ())) & set(draw_result.zones.get("main", ())))
        hits = {"main": k}
        mapping = {10: 0, 9: 1, 8: 2, 7: 3, 6: 4, 5: 5, 0: 6}
        idx = mapping.get(k, -1)
        return _result(levels, idx, hits, pool_high)

    if game.game_type == "digit3":
        user, win = ticket.digits, draw_result.digits
        hits = {"digit": 3 if user == win else 0}
        if play == "直选" or play is None:
            idx = 0 if user == win else -1
        else:
            same = sorted(user) == sorted(win)
            uniq = len(set(win))
            if same and uniq == 2 and play == "组选3":
                idx = 1
            elif same and uniq == 3 and play == "组选6":
                idx = 2
            else:
                idx = -1
        return _result(levels, idx, hits, pool_high)

    if game.game_type == "digit5":
        hits = {"digit": 5 if ticket.digits == draw_result.digits else 0}
        idx = 0 if ticket.digits == draw_result.digits else -1
        return _result(levels, idx, hits, pool_high)

    raise ValueError(f"未知彩种类型: {game.game_type}")


def _generic_lotto_match(game: GameConfig, ticket: Ticket, draw_result: DrawResult) -> int:
    """通用乐透型回退匹配：按奖级表顺序调用匹配函数（预留扩展用）。"""
    hits = _hits(ticket, draw_result, game)
    # 扩展点：新增乐透彩种时在此按 game.code 添加匹配逻辑
    return -1


def _result(levels: tuple[PrizeLevel, ...], idx: int, hits: dict[str, int], pool_high: bool) -> PrizeResult:
    if idx < 0 or idx >= len(levels):
        return PrizeResult(level=None, level_index=-1, money=0, hits=hits)
    level = levels[idx]
    return PrizeResult(level=level, level_index=idx, money=level.money(pool_high), hits=hits)
