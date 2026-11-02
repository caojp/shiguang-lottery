"""历史开奖入库服务：演示数据生成与幂等写入，供脚本和在线接口共用。

- 命令行：backend/scripts/fetch_history.py --seed-demo
- 移动端：POST /api/data/fetch（由数据页“立即拉取”按钮触发）
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import db
from ..engine.config import GAMES
from ..models import draw_history


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
