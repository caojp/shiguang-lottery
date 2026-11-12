"""历史开奖入库服务：官方数据拉取与演示数据生成，供脚本和在线接口共用。

- 官方数据：fetch_history.py --source official / POST /api/data/fetch
- 演示数据：fetch_history.py --seed-demo（仅用于无网络环境的界面演示，source='demo'）
- 清理演示数据：fetch_history.py --purge-demo / purge_demo()
"""
from __future__ import annotations

import asyncio
import random
from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import db
from ..engine.config import GAMES
from ..models import draw_history
from .official_fetcher import fetch_game


def demo_numbers(game_code: str, rng: random.Random) -> dict[str, Any]:
    """按彩种规则生成一期演示开奖号码 JSON（数字型写 digits，其余写 zones）。"""
    g = GAMES[game_code]
    if g.is_digit:
        return {
            "zones": {},
            "special": None,
            "digits": f"{rng.randint(0, 10**g.digits - 1):0{g.digits}d}",
        }

    zones: dict[str, list[int]] = {}
    for z in g.zones:
        k = 20 if g.game_type == "keno" else z.pick
        zones[z.name] = sorted(rng.sample(range(1, z.pool_size + 1), k))

    special = None
    if g.special:
        rest = [n for n in range(1, 31) if n not in zones["base"]]
        special = rng.choice(rest)

    return {"zones": zones, "special": special, "digits": ""}


async def has_history() -> bool:
    """是否已有任意历史开奖（用于首次部署时决定是否引导入库）。"""
    db.init_engine()
    async with db.get_session_factory()() as session:
        row = await session.execute(select(draw_history.c.id).limit(1))
        return row.first() is not None


async def seed_demo(games: list[str], periods: int) -> dict[str, dict[str, Any]]:
    """从各彩种已有最大期号续写 N 期演示数据；幂等写入，返回本期新增摘要。"""
    db.init_engine()
    summary: dict[str, dict[str, Any]] = {}

    async with db.get_session_factory()() as session:
        for code in games:
            g = GAMES[code]
            rng = random.Random(f"shiguang-demo-{code}-2026")

            row = await session.execute(
                select(func.max(draw_history.c.issue)).where(draw_history.c.game_code == code)
            )
            latest = row.scalar()
            # 期号格式为「年份 + 年内期序」；跨年时从 001 重新开始
            year = str(date.today().year)
            start_seq = int(latest[4:]) + 1 if latest and latest[:4] == year else 1

            rows = [
                {
                    "game_code": code,
                    "issue": f"{year}{start_seq + i:03d}",
                    # 演示数据按每天 1 期倒推日期，便于“最近开奖”展示时间轴
                    "draw_date": date.today() - timedelta(days=periods - 1 - i),
                    "numbers_json": demo_numbers(code, rng),
                    "source": "demo",
                }
                for i in range(periods)
            ]

            stmt = pg_insert(draw_history).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_draw_history_game_issue",
                set_={"numbers_json": stmt.excluded.numbers_json, "source": stmt.excluded.source},
            )
            await session.execute(stmt)
            await session.commit()

            summary[code] = {
                "name": g.name,
                "added": len(rows),
                "first_issue": rows[0]["issue"],
                "last_issue": rows[-1]["issue"],
            }

    return summary


async def import_official(
    games: list[str], pages: int = 1, page_size: int = 30
) -> dict[str, dict[str, Any]]:
    """从官方接口拉取真实历史开奖并幂等入库（source='official'）。

    抓取为同步 HTTP，用 to_thread 包裹避免阻塞事件循环。
    每个彩种先在线程内完成抓取，再用独立的短会话写入，避免长阻塞期间持有
    asyncpg 连接（Windows 事件循环下易触发连接失效）。
    期号保持官网原样：福彩 7 位（2026129），体彩 5 位（26129）。
    """
    db.init_engine()
    summary: dict[str, dict[str, Any]] = {}

    for code in games:
        g = GAMES[code]
        try:
            recs = await asyncio.to_thread(fetch_game, code, pages, page_size)
        except Exception as e:  # noqa: BLE001 - 单彩种失败不影响其他彩种
            summary[code] = {"name": g.name, "added": 0, "error": f"{type(e).__name__}: {e}"}
            continue
        if not recs:
            summary[code] = {"name": g.name, "added": 0, "error": "官方接口未返回数据"}
            continue

        rows = [
            {
                "game_code": code,
                "issue": r.issue,
                "draw_date": r.draw_date,
                "numbers_json": r.numbers,
                "source": r.source,
            }
            for r in recs
        ]
        stmt = pg_insert(draw_history).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_draw_history_game_issue",
            set_={
                "draw_date": stmt.excluded.draw_date,
                "numbers_json": stmt.excluded.numbers_json,
                "source": stmt.excluded.source,
            },
        )
        async with db.get_session_factory()() as session:
            await session.execute(stmt)
            await session.commit()

        issues = sorted(r.issue for r in recs)
        summary[code] = {
            "name": g.name,
            "added": len(rows),
            "first_issue": issues[0],
            "last_issue": issues[-1],
        }

    return summary


async def purge_demo(games: list[str]) -> int:
    """删除演示数据（source='demo'），返回删除行数。"""
    db.init_engine()
    async with db.get_session_factory()() as session:
        res = await session.execute(
            delete(draw_history).where(
                draw_history.c.game_code.in_(games),
                draw_history.c.source == "demo",
            )
        )
        await session.commit()
        return res.rowcount or 0


async def import_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """把外部来源（CSV 导出）的开奖记录按彩种幂等写入，返回各彩种汇总。

    rows 每项字段：game_code / issue / draw_date / numbers_json / source。
    用于部署环境无法直连官方接口时（机房出口被官网 WAF 拦截），
    在可直连的机器上 `scripts/export_history.py` 导出后在服务器 `scripts/import_history.py` 导入。
    """
    db.init_engine()
    by_game: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_game.setdefault(row["game_code"], []).append(row)

    summary: dict[str, dict[str, Any]] = {}
    for code, items in by_game.items():
        stmt = pg_insert(draw_history).values(items)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_draw_history_game_issue",
            set_={
                "draw_date": stmt.excluded.draw_date,
                "numbers_json": stmt.excluded.numbers_json,
                "source": stmt.excluded.source,
            },
        )
        async with db.get_session_factory()() as session:
            await session.execute(stmt)
            await session.commit()

        issues = sorted(str(i["issue"]) for i in items)
        g = GAMES.get(code)
        summary[code] = {
            "name": g.name if g else code,
            "added": len(items),
            "first_issue": issues[0],
            "last_issue": issues[-1],
        }
    return summary
