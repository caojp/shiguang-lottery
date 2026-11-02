"""历史数据与冷热号分析。

支持：
- load_draws_csv：读取历史开奖 CSV（期号 + 各列号码，乐透型最后 1~2 列为蓝球/后区/特别号）
- analyze：统计各号码出现频率与遗漏期数
- hot_cold：输出热号 / 冷号列表

CSV 格式约定（以双色球为例）：
    期号,号码1,号码2,号码3,号码4,号码5,号码6,蓝号
    2026001,01,05,12,18,22,30,07
"""
from __future__ import annotations

import csv
from pathlib import Path

from .config import GameConfig
from .draw import DrawResult


def load_draws_csv(path: str | Path, game: GameConfig) -> list[DrawResult]:
    """读取历史开奖 CSV，返回 DrawResult 列表（按行序）。

    列结构：第一列期号（忽略），其后按 game.zones 顺序为各区号码；
    乐透型多区时列数 = 各区 pick 之和（如双色球 6 红 + 1 蓝 = 7 列）。
    """
    rows: list[DrawResult] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return rows
        for line in reader:
            if not line or not line[0].strip():
                continue
            cells = [c.strip() for c in line]
            if game.is_digit:
                continue  # 数字型历史数据不参与冷热号分析
            zones: dict[str, tuple[int, ...]] = {}
            offset = 1  # 跳过期号
            ok = True
            for z in game.zones:
                nums: list[int] = []
                for _ in range(z.pick):
                    if offset >= len(cells):
                        ok = False
                        break
                    try:
                        nums.append(int(cells[offset]))
                    except ValueError:
                        ok = False
                        break
                    offset += 1
                if not ok:
                    break
                zones[z.name] = tuple(sorted(nums))
            if not ok or any(len(v) != z.pick for z, v in zip(game.zones, zones.values())):
                continue
            special: int | None = None
            if game.special and offset < len(cells):
                try:
                    special = int(cells[offset])
                except ValueError:
                    special = None
            rows.append(DrawResult(game.code, zones=zones, special=special))
    return rows


def frequencies(draws: list[DrawResult], game: GameConfig) -> dict[str, dict[int, int]]:
    """各号码池分组的出现频次：zone -> 号码 -> 次数。"""
    result: dict[str, dict[int, int]] = {}
    for z in game.zones:
        counter: dict[int, int] = {n: 0 for n in range(1, z.pool_size + 1)}
        for d in draws:
            for n in d.zones.get(z.name, ()):
                counter[n] = counter.get(n, 0) + 1
        result[z.name] = counter
    if game.special:
        special_counter: dict[int, int] = {n: 0 for n in range(1, game.zones[0].pool_size + 1)}
        for d in draws:
            if d.special is not None:
                special_counter[d.special] = special_counter.get(d.special, 0) + 1
        result["special"] = special_counter
    return result


def missing_periods(draws: list[DrawResult], game: GameConfig) -> dict[str, dict[int, int]]:
    """遗漏期数：从最后一期往前找最近一次出现，期间隔的期数（0 表示上一期出现过）。"""
    total = len(draws)
    result: dict[str, dict[int, int]] = {}
    for z in game.zones:
        miss: dict[int, int] = {n: total for n in range(1, z.pool_size + 1)}
        for idx, d in enumerate(draws):
            for n in d.zones.get(z.name, ()):
                # 越晚出现，遗漏越小；取最后一次出现位置
                miss[n] = total - 1 - idx
        result[z.name] = miss
    if game.special:
        s_miss: dict[int, int] = {n: total for n in range(1, game.zones[0].pool_size + 1)}
        for idx, d in enumerate(draws):
            if d.special is not None:
                s_miss[d.special] = total - 1 - idx
        result["special"] = s_miss
    return result


def hot_cold(
    draws: list[DrawResult],
    game: GameConfig,
    top_n: int = 8,
    min_periods: int = 20,
) -> dict[str, dict[str, list[int]]]:
    """输出热号 / 冷号。

    - 热号：出现频率最高的 top_n 个
    - 冷号：出现频率最低且遗漏期数最长的 top_n 个（数据期数不足 min_periods 时按频率排序）

    返回：zone -> {"hot": [...], "cold": [...]}
    """
    freq = frequencies(draws, game)
    miss = missing_periods(draws, game)
    result: dict[str, dict[str, list[int]]] = {}
    for z in game.zones:
        counter = freq[z.name]
        miss_map = miss[z.name]
        # 热号：按频率降序、遗漏升序
        hot = sorted(counter, key=lambda n: (-counter[n], miss_map[n]))[:top_n]
        # 冷号：按频率升序、遗漏降序（长期不出更冷）
        cold = sorted(counter, key=lambda n: (counter[n], -miss_map[n]))[:top_n]
        result[z.name] = {"hot": hot, "cold": cold}
    if game.special and "special" in freq:
        counter = freq["special"]
        miss_map = miss["special"]
        hot = sorted(counter, key=lambda n: (-counter[n], miss_map[n]))[:top_n]
        cold = sorted(counter, key=lambda n: (counter[n], -miss_map[n]))[:top_n]
        result["special"] = {"hot": hot, "cold": cold}
    return result


def demo_csv_for(game: GameConfig, periods: int = 60, seed: int = 2026) -> list[str]:
    """生成一组可复现的模拟历史开奖 CSV 行（演示数据，仅用于功能演示）。"""
    import random

    rng = random.Random(seed)
    lines = ["期号" + "".join(f",号码{i}" for i in range(1, sum(z.pick for z in game.zones) + 1))]
    if game.special:
        lines[0] += ",特别号"
    for p in range(1, periods + 1):
        cells: list[str] = [str(2026000 + p)]
        for z in game.zones:
            nums = sorted(rng.sample(range(1, z.pool_size + 1), z.pick))
            cells.extend(f"{n:02d}" for n in nums)
        if game.special:
            base = game.zones[0]
            rest = [n for n in range(1, base.pool_size + 1) if n not in nums]
            cells.append(f"{rng.choice(rest):02d}")
        lines.append(",".join(cells))
    return lines
