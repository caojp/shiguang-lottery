"""导出库内历史开奖为 CSV（跨环境搬运官方数据用）。

场景：服务器出口 IP 被官网 WAF 拦截、无法直接调用官方接口时，
在能直连官网的机器上拉取后导出 CSV，再到服务器用 import_history.py 导入。

用法（在 backend/ 目录执行）：

    python scripts/export_history.py                        # 全部彩种，默认路径 data/history_official.csv
    python scripts/export_history.py --game ssq,dlt --out /tmp/h.csv
    python scripts/export_history.py --source all           # 含 demo/manual（默认仅 official）
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import db  # noqa: E402
from app.engine.config import GAMES  # noqa: E402
from app.models import draw_history  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "history_official.csv"

FIELDS = ["game_code", "issue", "draw_date", "numbers_json", "source"]


async def export(path: Path, games: list[str], source: str) -> int:
    db.init_engine()
    async with db.get_session_factory()() as session:
        stmt = select(
            draw_history.c.game_code,
            draw_history.c.issue,
            draw_history.c.draw_date,
            draw_history.c.numbers_json,
            draw_history.c.source,
        ).where(draw_history.c.game_code.in_(games))
        if source != "all":
            stmt = stmt.where(draw_history.c.source == source)
        stmt = stmt.order_by(draw_history.c.game_code, draw_history.c.issue)
        rows = [dict(r._mapping) for r in (await session.execute(stmt)).all()]

    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig：Excel 直接双击打开不乱码；import_history.py 读取时自动兼容
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "game_code": row["game_code"],
                    "issue": row["issue"],
                    "draw_date": row["draw_date"].isoformat(),
                    "numbers_json": json.dumps(row["numbers_json"], ensure_ascii=False),
                    "source": row["source"],
                }
            )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="导出历史开奖 CSV")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"输出路径（默认 {DEFAULT_OUT}）")
    parser.add_argument("--game", default="", help="仅导出指定彩种，逗号分隔")
    parser.add_argument("--source", default="official", help="来源过滤：official / demo / manual / all")
    args = parser.parse_args()

    games = [c for c in GAMES] if not args.game else [c.strip() for c in args.game.split(",") if c.strip() in GAMES]
    if not games:
        print(f"未知彩种，可用：{', '.join(GAMES)}")
        sys.exit(1)

    path = Path(args.out)
    count = asyncio.run(export(path, games, args.source))
    print(f"[export] 已导出 {count} 行 -> {path}")


if __name__ == "__main__":
    main()
