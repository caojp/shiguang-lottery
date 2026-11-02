"""号码生成引擎：随机机选、策略化选号、自选录入校验。

策略说明（界面须标注）：策略只改变号码分布形态，不改变理论中奖概率。
"""
from __future__ import annotations

import re
import random
from dataclasses import dataclass, field

from .config import DIGIT_CODES, GameConfig, Zone

# 加密级伪随机源（娱乐模拟足够，且避免可预测的 Mersenne Twister 序列）
_rng = random.SystemRandom()

MAX_TRY = 300          # 策略约束拒绝采样的最大尝试次数
_GUARD = 2000          # 加权抽样去重的最大循环保护次数


@dataclass
class Ticket:
    """一注号码。

    - 乐透型 / 基诺型：zones 形如 {"red": (1,5,12,18,22,30), "blue": (7)}
    - 数字型：digits 形如 "007" / "12345"
    """

    game_code: str
    zones: dict[str, tuple[int, ...]] = field(default_factory=dict)
    digits: str = ""

    def display(self, game: GameConfig | None = None) -> str:
        """格式化展示：乐透型升序 + ' + ' 分隔各区；数字型保留前导零。"""
        if self.game_code in DIGIT_CODES:
            return self.digits
        if game is None:
            from .config import GAMES

            game = GAMES[self.game_code]
        parts: list[str] = []
        for z in game.zones:
            nums = self.zones.get(z.name, ())
            parts.append(" ".join(f"{n:02d}" for n in nums))
        return " + ".join(parts)


# ------------------------------------------------------------------ 机选

def quick_pick(game: GameConfig) -> Ticket:
    """纯随机机选一注。"""
    if game.is_digit:
        num = _rng.randint(0, 10**game.digits - 1)
        return Ticket(game.code, digits=f"{num:0{game.digits}d}")
    zones: dict[str, tuple[int, ...]] = {}
    for z in game.zones:
        zones[z.name] = tuple(sorted(_rng.sample(range(1, z.pool_size + 1), z.pick)))
    return Ticket(game.code, zones=zones)


# ------------------------------------------------------------------ 策略选号

def _split_counts(pick: int, parts: int = 3) -> list[int]:
    """把 pick 个名额尽量均匀地分到 parts 个区间。"""
    base, rem = divmod(pick, parts)
    counts = [base + 1] * rem + [base] * (parts - rem)
    return counts


def _weighted_sample(z: Zone, weights: dict[int, float]) -> list[int]:
    """按权重抽样（冷热号加权），返回 pick 个不重复号码并升序。"""
    population = list(range(1, z.pool_size + 1))
    w = [max(weights.get(n, 1.0), 0.0) for n in population]
    if sum(w) <= 0:
        w = [1.0] * len(population)
    chosen: list[int] = []
    used: set[int] = set()
    guard = 0
    while len(chosen) < z.pick and guard < _GUARD:
        guard += 1
        for x in _rng.choices(population, weights=w, k=z.pick):
            if x not in used:
                used.add(x)
                chosen.append(x)
            if len(chosen) >= z.pick:
                break
    if len(chosen) < z.pick:
        rest = [n for n in population if n not in used]
        chosen.extend(_rng.sample(rest, z.pick - len(chosen)))
    return sorted(chosen[: z.pick])


def _split_sample(z: Zone, counts: list[int]) -> list[int]:
    """区间均衡：把号码池均分为 len(counts) 段，每段抽取 counts[i] 个。"""
    pool = z.pool_size
    parts = len(counts)
    seg = (pool + parts - 1) // parts  # 每段大小（向上取整）
    nums: list[int] = []
    for i, cnt in enumerate(counts):
        lo = i * seg + 1
        hi = min((i + 1) * seg, pool)
        if hi < lo:
            continue
        nums.extend(_rng.sample(range(lo, hi + 1), min(cnt, hi - lo + 1)))
    # 个别段容量不足时补抽，保证个数正确
    while len(nums) < z.pick:
        rest = [n for n in range(1, pool + 1) if n not in set(nums)]
        nums.append(_rng.choice(rest))
    return sorted(nums[: z.pick])


def _odd_even_sample(z: Zone, odd: int) -> list[int]:
    """奇偶约束：指定奇数个数，其余为偶数。"""
    even = z.pick - odd
    odds = [n for n in range(1, z.pool_size + 1) if n % 2 == 1]
    evens = [n for n in range(1, z.pool_size + 1) if n % 2 == 0]
    odd = max(0, min(odd, len(odds)))
    even = max(0, min(even, len(evens)))
    nums = _rng.sample(odds, odd) + _rng.sample(evens, even)
    return sorted(nums)


def _gen_zone(z: Zone, strategy: dict) -> list[int]:
    """按策略约束生成一个号码池分组的号码。"""
    hot_cold = strategy.get("hot_cold")
    if hot_cold and hot_cold.get("weights"):
        return _weighted_sample(z, hot_cold["weights"])

    split = (strategy.get("zone_split") or {}).get(z.name)
    if split:
        return _split_sample(z, list(split))

    odd_even = (strategy.get("odd_even") or {}).get(z.name)
    if odd_even is not None:
        return _odd_even_sample(z, int(odd_even))

    return list(quick_pick_zones(z))


def quick_pick_zones(z: Zone) -> tuple[int, ...]:
    return tuple(sorted(_rng.sample(range(1, z.pool_size + 1), z.pick)))


def _has_consecutive(nums: tuple[int, ...]) -> bool:
    return any(b - a == 1 for a, b in zip(nums, nums[1:]))


def _satisfies(ticket: Ticket, game: GameConfig, strategy: dict) -> bool:
    """检查一注号码是否满足所有策略约束（和值、连号）。"""
    sum_range = strategy.get("sum_range")
    if sum_range and not game.is_digit:
        zone_name = sum_range.get("zone") or game.zones[0].name
        nums = ticket.zones.get(zone_name, ())
        if nums:
            total = sum(nums)
            if total < sum_range["min"] or total > sum_range["max"]:
                return False

    if strategy.get("consecutive") == "forbid":
        for nums in ticket.zones.values():
            if _has_consecutive(nums):
                return False
    return True


def generate_tickets(
    game: GameConfig,
    count: int = 1,
    strategy: dict | None = None,
    max_try: int = MAX_TRY,
) -> list[Ticket]:
    """生成 count 注号码。

    传入 strategy 时采用策略选号（拒绝采样）；约束无法满足时回退为普通机选。
    """
    strategy = strategy or {}
    tickets: list[Ticket] = []
    for _ in range(max(1, count)):
        picked: Ticket | None = None
        if strategy:
            for _ in range(max_try):
                zones: dict[str, tuple[int, ...]] = {}
                for z in game.zones:
                    zones[z.name] = tuple(_gen_zone(z, strategy))
                cand = Ticket(game.code, zones=zones)
                if _satisfies(cand, game, strategy):
                    picked = cand
                    break
        if picked is None:
            picked = quick_pick(game)
        tickets.append(picked)
    return tickets


# ------------------------------------------------------------------ 自选校验

_NUM_SPLIT = re.compile(r"[,\s，、]+")


def parse_numbers(text: str, pool_size: int) -> list[int]:
    """解析用户输入的号码字符串，如 "01, 05, 12" 或 "1 5 12"。"""
    parts = [p for p in _NUM_SPLIT.split(text.strip()) if p]
    nums: list[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError as exc:
            raise ValueError(f"「{p}」不是有效数字") from exc
        if n < 1 or n > pool_size:
            raise ValueError(f"号码 {n} 超出 1~{pool_size} 范围")
        nums.append(n)
    return nums


def validate_zones(game: GameConfig, zone_inputs: dict[str, str]) -> tuple[bool, str]:
    """校验乐透型 / 基诺型自选号码。返回 (是否合法, 错误信息)。"""
    for z in game.zones:
        raw = (zone_inputs.get(z.name) or "").strip()
        if not raw:
            return False, f"请填写{z.label}号码"
        try:
            nums = parse_numbers(raw, z.pool_size)
        except ValueError as exc:
            return False, str(exc)
        if len(nums) != z.pick:
            return False, f"{z.label}需选 {z.pick} 个号码，当前输入了 {len(nums)} 个"
        if len(set(nums)) != len(nums):
            return False, f"{z.label}号码不能重复"
    return True, ""


def validate_digits(game: GameConfig, text: str) -> tuple[bool, str]:
    """校验数字型自选号码（3 位 / 5 位）。"""
    raw = text.strip()
    if not re.fullmatch(r"\d{%d}" % game.digits, raw):
        return False, f"请输入 {game.digits} 位数字（可含前导零，如 {'007' if game.digits == 3 else '00001'}）"
    return True, ""


def validate_ticket(
    game: GameConfig,
    zone_inputs: dict[str, str] | None = None,
    digits_text: str = "",
) -> tuple[bool, str]:
    """自选录入统一入口。"""
    if game.is_digit:
        return validate_digits(game, digits_text)
    return validate_zones(game, zone_inputs or {})
