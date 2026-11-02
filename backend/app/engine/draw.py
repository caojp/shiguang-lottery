"""模拟开奖引擎：按各彩种规则随机产生中奖号码。"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import GameConfig

_rng = random.SystemRandom()


@dataclass
class DrawResult:
    """一期模拟开奖结果。"""

    game_code: str
    zones: dict[str, tuple[int, ...]] = field(default_factory=dict)  # 乐透/基诺开奖号码
    special: int | None = None                                        # 七乐彩特别号
    digits: str = ""                                                  # 数字型开奖号码

    def display(self, game: GameConfig | None = None) -> str:
        """格式化展示开奖号码。"""
        if game is None:
            from .config import GAMES

            game = GAMES[self.game_code]
        if game.is_digit:
            return self.digits
        parts: list[str] = []
        for z in game.zones:
            nums = self.zones.get(z.name, ())
            parts.append(" ".join(f"{n:02d}" for n in nums))
        text = " + ".join(parts)
        if self.special is not None:
            text += f"  特别号 {self.special:02d}"
        return text


def draw(game: GameConfig) -> DrawResult:
    """按彩种规则随机摇出一期开奖号码。

    - 乐透型：各号码池无放回抽取（双色球蓝球、大乐透后区为独立池）
    - 基诺型（快乐8）：从 1~80 摇出 20 个号码
    - 七乐彩：额外从基本号池剩余号码中摇出 1 个特别号
    - 数字型：随机一个 n 位数
    """
    if game.is_digit:
        num = _rng.randint(0, 10**game.digits - 1)
        return DrawResult(game.code, digits=f"{num:0{game.digits}d}")

    zones: dict[str, tuple[int, ...]] = {}
    for z in game.zones:
        keno_count = 20 if game.game_type == "keno" else z.pick
        zones[z.name] = tuple(sorted(_rng.sample(range(1, z.pool_size + 1), keno_count)))

    special: int | None = None
    if game.special:
        base = zones.get("base", ())
        pool = game.zone("base").pool_size
        rest = [n for n in range(1, pool + 1) if n not in set(base)]
        special = _rng.choice(rest)

    return DrawResult(game.code, zones=zones, special=special)
