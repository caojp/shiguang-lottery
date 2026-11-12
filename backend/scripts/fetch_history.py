"""官方历史数据拉取脚本（幂等 ON CONFLICT DO UPDATE）。

用法（在 backend/ 目录执行，需 PostgreSQL 已启动并完成迁移）：

    # 1. 拉取官方真实开奖数据（默认，每彩种 3 页 × 30 期 ≈ 90 期）
    python scripts/fetch_history.py
    python scripts/fetch_history.py --game ssq --pages 5
    python scripts/fetch_history.py --purge-demo      # 顺带清掉历史演示数据

    # 2. 仅清理演示数据（source='demo'）
    python scripts/fetch_history.py --purge-demo --only-purge

    # 3. 检查期号缺口
    python scripts/fetch_history.py --check-gaps

    # 4. 无网络环境下的界面演示数据（随机生成，仅供 UI 展示，不可用于核对）
    python scripts/fetch_history.py --seed-demo

数据源：
- 福彩：中国福彩网 findDrawNotice（双色球/福彩3D/快乐8/七乐彩）
- 体彩：中国体彩网 getHistoryPageListV1（超级大乐透 85 / 排列3 35 / 排列5 350133）
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
from app.services.history_service import import_official, purge_demo, seed_demo  # noqa: E402

# 期号缺口：兼容福彩 7 位（2026129）与体彩 5 位（26129）
GAP_SQL = text(
    """
    WITH normalized AS (
        SELECT issue,
               CASE WHEN length(issue) = 7 THEN substring(issue from 5)::bigint
                    ELSE substring(issue from 3)::bigint END AS seq,
               CASE WHEN length(issue) = 7 THEN substring(issue from 1 for 4)
                    ELSE substring(issue from 1 for 2) END AS yr
        FROM draw_history
        WHERE game_code = :code AND issue ~ '^[0-9]+$'
    ),
    ranked AS (
        SELECT issue, seq, yr, LAG(seq) OVER (PARTITION BY yr ORDER BY seq) AS prev_seq
        FROM normalized
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


async def run(args, games: list[str]) -> int:
    """在同一个事件循环内完成全部步骤（多次 asyncio.run 会让引擎绑定的 loop 失效）。"""
    if args.check_gaps:
        await check_gaps(games)
        return 0

    if args.purge_demo or args.only_purge:
        removed = await purge_demo(games)
        print(f"[purge] 已删除演示数据 {removed} 行")
        if args.only_purge:
            return 0

    if args.seed_demo:
        summary = await seed_demo(games, args.demo_periods)
        for item in summary.values():
            print(f"[demo] {item['name']}: 写入 {item['added']} 期（{item['first_issue']} ~ {item['last_issue']}）")
        print("[demo] 注意：演示数据为随机生成，仅用于界面展示，不能用于与实体彩票核对")
        return 0

    summary = await import_official(games, args.pages, args.page_size)
    failed = 0
    for item in summary.values():
        if item.get("error"):
            failed += 1
            print(f"[official] {item['name']}: 失败 -> {item['error']}")
        else:
            print(
                f"[official] {item['name']}: 写入 {item['added']} 期"
                f"（{item['first_issue']} ~ {item['last_issue']}）"
            )
    print(f"[official] 完成：{len(summary) - failed}/{len(summary)} 个彩种成功")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="时光选彩历史数据拉取（官方源，幂等）")
    parser.add_argument("--game", default="", help="仅处理指定彩种代码，逗号分隔，留空处理全部")
    parser.add_argument("--pages", type=int, default=3, help="官方接口拉取页数（每页 30 期，默认 3）")
    parser.add_argument("--page-size", type=int, default=30, help="每页期数（默认 30）")
    parser.add_argument("--purge-demo", action="store_true", help="先删除 source='demo' 的演示数据")
    parser.add_argument("--only-purge", action="store_true", help="仅清理演示数据，不拉取")
    parser.add_argument("--seed-demo", action="store_true", help="生成演示数据（仅供无网络环境展示）")
    parser.add_argument("--demo-periods", type=int, default=60, help="演示数据每彩种期数（默认 60）")
    parser.add_argument("--check-gaps", action="store_true", help="检查期号连续性缺口")
    args = parser.parse_args()

    games = [c for c in GAMES] if not args.game else [c.strip() for c in args.game.split(",") if c.strip() in GAMES]
    if not games:
        print(f"未知彩种，可用：{', '.join(GAMES)}")
        sys.exit(1)

    sys.exit(asyncio.run(run(args, games)))


if __name__ == "__main__":
    main()
