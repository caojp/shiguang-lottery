"""冷热号与形态分析服务：基于 draw_history 统计频率、遗漏与和值/跨度/012 路。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..db import get_session_factory
from ..engine.config import GAMES
from ..models import draw_history


def _buckets(values: list[int], parts: int = 8) -> list[dict[str, Any]]:
    """把数值序列分桶，返回 [{label, count}]；无数据时返回空列表。"""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"label": str(lo), "count": len(values)}]
    parts = min(parts, hi - lo + 1)
    width = (hi - lo + 1) / parts
    counts = [0] * parts
    for v in values:
        idx = min(parts - 1, int((v - lo) / width))
        counts[idx] += 1
    return [
        {"label": f"{int(lo + i * width)}-{int(lo + (i + 1) * width) - 1}", "count": c}
        for i, c in enumerate(counts)
    ]


def _omission_top(omission: dict[Any, int], limit: int = 8) -> list[dict[str, Any]]:
    """遗漏值从大到小取前 limit 个号码。"""
    items = sorted(omission.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"number": k, "omission": v} for k, v in items]


def _form(numbers_list: list[list[int]]) -> dict[str, Any]:
    """和值 / 跨度 / 奇偶 / 012 路统计。"""
    sums = [sum(nums) for nums in numbers_list if nums]
    spans = [max(nums) - min(nums) for nums in numbers_list if nums]
    odd = sum(1 for nums in numbers_list for n in nums if n % 2 == 1)
    even = sum(1 for nums in numbers_list for n in nums if n % 2 == 0)
    roads = {0: 0, 1: 0, 2: 0}
    for nums in numbers_list:
        for n in nums:
            roads[n % 3] += 1
    return {
        "sum": {
            "avg": round(sum(sums) / len(sums), 1) if sums else 0,
            "min": min(sums) if sums else 0,
            "max": max(sums) if sums else 0,
            "buckets": _buckets(sums),
        },
        "span": {
            "avg": round(sum(spans) / len(spans), 1) if spans else 0,
            "min": min(spans) if spans else 0,
            "max": max(spans) if spans else 0,
            "buckets": _buckets(spans, 6),
        },
        "odd_even": {"odd": odd, "even": even},
        "road_012": {str(k): v for k, v in roads.items()},
    }


async def stats(game_code: str, periods: int = 60) -> dict[str, Any]:
    """返回各号码池的遗漏与形态统计；数字型按位统计遗漏与形态。"""
    game = GAMES[game_code]
    async with get_session_factory()() as session:
        rows = await session.execute(
            select(draw_history.c.numbers_json)
            .where(draw_history.c.game_code == game_code)
            .order_by(draw_history.c.issue.desc())
            .limit(periods)
        )
        records = [dict(r._mapping)["numbers_json"] for r in rows]
    if not records:
        return {
            "game_code": game_code,
            "periods": 0,
            "zones": {},
            "digit_positions": [],
            "digit_form": None,
            "message": "暂无历史数据",
        }

    if game.is_digit:
        positions: list[dict[str, Any]] = []
        for pos in range(game.digits):
            freq = {str(d): 0 for d in range(10)}
            omission = {str(d): len(records) for d in range(10)}
            for i, rec in enumerate(records):
                ch = (rec.get("digits") or "")[pos:pos + 1]
                if not ch:
                    continue
                freq[ch] += 1
                if omission[ch] == len(records):
                    omission[ch] = i
            positions.append({
                "label": f"第 {pos + 1} 位",
                "frequency": freq,
                "omission": omission,
                "omission_top": _omission_top(omission),
            })
        digit_rows = [[int(ch) for ch in (rec.get("digits") or "")] for rec in records]
        return {
            "game_code": game_code,
            "periods": len(records),
            "zones": {},
            "digit_positions": positions,
            "digit_form": _form(digit_rows),
        }

    zones_out: dict[str, Any] = {}
    for z in game.zones:
        freq = {n: 0 for n in range(1, z.pool_size + 1)}
        omission = {n: len(records) for n in range(1, z.pool_size + 1)}
        rows: list[list[int]] = []
        for i, rec in enumerate(records):
            nums = [int(n) for n in rec.get("zones", {}).get(z.name, [])]
            rows.append(nums)
            for n in nums:
                if 1 <= n <= z.pool_size:
                    freq[n] += 1
                    if omission[n] == len(records):
                        omission[n] = i
        zones_out[z.name] = {
            "label": z.label,
            "pool_size": z.pool_size,
            "frequency": freq,
            "omission": omission,
            "avg_omission": round(sum(omission.values()) / len(omission), 2),
            "omission_top": _omission_top(omission),
            "form": _form(rows),
        }
    return {
        "game_code": game_code,
        "periods": len(records),
        "zones": zones_out,
        "digit_positions": [],
        "digit_form": None,
    }


async def hot_cold(game_code: str, periods: int = 60) -> dict[str, Any]:
    """返回各号码池的频次字典与热/冷 Top。

    - 乐透 / 基诺：按号码池统计（如双色球 red/blue）
    - 数字型：按位统计 0-9 出现频率
    """
    game = GAMES[game_code]
    async with get_session_factory()() as session:
        rows = await session.execute(
            select(draw_history.c.numbers_json)
            .where(draw_history.c.game_code == game_code)
            .order_by(draw_history.c.issue.desc())
            .limit(periods)
        )
        records = [dict(r._mapping)["numbers_json"] for r in rows]
    if not records:
        return {"game_code": game_code, "periods": 0, "zones": {}, "digit_positions": {}, "message": "暂无历史数据"}

    if game.is_digit:
        positions: list[dict[str, int]] = [{} for _ in range(game.digits)]
        for rec in records:
            digits = rec.get("digits", "")
            for pos, ch in enumerate(digits):
                positions[pos][ch] = positions[pos].get(ch, 0) + 1
        out: dict[str, Any] = {"game_code": game_code, "periods": len(records), "zones": {}, "digit_positions": positions}
        return out

    freq: dict[str, dict[int, int]] = {}
    for z in game.zones:
        freq[z.name] = {n: 0 for n in range(1, z.pool_size + 1)}
    for rec in records:
        zones = rec.get("zones", {})
        for z in game.zones:
            for n in zones.get(z.name, ()):
                freq[z.name][int(n)] = freq[z.name].get(int(n), 0) + 1

    zones_out: dict[str, dict[str, Any]] = {}
    for z in game.zones:
        items = sorted(freq[z.name].items(), key=lambda kv: kv[1])
        cold = [{"number": n, "count": c} for n, c in items[:8]]
        hot = [{"number": n, "count": c} for n, c in items[-8:]][::-1]
        zones_out[z.name] = {
            "pool_size": z.pool_size,
            "label": z.label,
            "hot": hot,
            "cold": cold,
            "frequency": freq[z.name],
        }
    return {"game_code": game_code, "periods": len(records), "zones": zones_out, "digit_positions": {}}
