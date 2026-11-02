"""幂等历史数据拉取脚本。

用法（在 backend/ 目录执行，需 PostgreSQL 已启动并完成迁移）：

    # 1. 生成演示历史数据（确定性伪随机，幂等 ON CONFLICT DO UPDATE）
    python scripts/fetch_history.py --seed-demo
    python scripts/fetch_history.py --seed-demo --game ssq --demo-periods 120

    # 2. 检查期号缺口
    python scripts/fetch_history.py --check-gaps

    # 3. 真实官方接口（扩展点）：官方页面/接口可能改版，请在 fetchers 中按需实现，
    #    当前版本未内置真实抓取，避免提供会失效的假接口。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app import db  # noqa: E402
from app.engine.config import GAMES  # noqa: E402
from app.services.history_service import seed_demo  # noqa: E402

GAP_SQL = text(
    """
    WITH ranked AS (
        SELECT issue,
               substring(issue from 5)::bigint AS seq,
               substring(issue from 1 for 4) AS yr,
               LAG(substring(issue from 5)::bigint)
                   OVER (PARTITION BY substring(issue from 1 for 4) ORDER BY issue) AS prev_seq
        FROM draw_history
        WHERE game_code = :code AND issue ~ '^[0-9]+$'
    )
    SELECT yr, seq, prev_seq
    FROM ranked
    WHERE prev_seq IS NOT NULL AND seq - prev_seq > 1
    ORDER BY yr DESC, seq DESC
    """
)


async def check_gaps(games: list[str]) -> None:
    db.init_engine()
    async with db.get_session_factory()() as session:
        for code in games:
            g = GAMES[code]
            res = await session.execute(GAP_SQL, {"code": code})
            gaps = [dict(r._mapping) for r in res]
            if not gaps:
                print(f"[gap] {g.name}: 无缺口")
                continue
            for gap in gaps[:5]:
                missing = list(range(int(gap["prev_seq"]) + 1, int(gap["seq"])))
                print(f"[gap] {g.name}: {gap['yr']} 年缺失 {len(missing)} 期（第 {missing[0]} 期起）")


def main() -> None:
    parser = argparse.ArgumentParser(description="时光选彩历史数据拉取（幂等）")
    parser.add_argument("--seed-demo", action="store_true", help="生成演示历史数据入库")
    parser.add_argument("--check-gaps", action="store_true", help="检查期号连续性缺口")
    parser.add_argument("--game", default="", help="仅处理指定彩种代码，留空处理全部")
    parser.add_argument("--demo-periods", type=int, default=60, help="每个彩种生成期数（默认 60）")
    args = parser.parse_args()

    games = [c for c in GAMES] if not args.game else [c.strip() for c in args.game.split(",") if c.strip() in GAMES]
    if not games:
        print(f"未知彩种，可用：{', '.join(GAMES)}")
        sys.exit(1)

    if args.seed_demo:
        summary = asyncio.run(seed_demo(games, args.demo_periods))
        for item in summary.values():
            print(
                f"[demo] {item['name']}: 写入 {item['added']} 期"
                f"（{item['first_issue']} ~ {item['last_issue']}）"
            )
    elif args.check_gaps:
        asyncio.run(check_gaps(games))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
