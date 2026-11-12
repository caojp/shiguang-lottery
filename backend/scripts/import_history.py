"""从 CSV 导入历史开奖（幂等 upsert，source 保留文件内标注）。

场景：部署服务器无法直连中国福彩网/中国体彩网（机房出口被 WAF 拦截），
先在可直连的机器执行 fetch_history.py + export_history.py，再把 CSV 传上来导入。

用法（在 backend/ 目录执行，路径为容器内或宿主机上的 CSV 绝对路径）：

    python scripts/import_history.py --csv /tmp/history_official.csv
    python scripts/import_history.py --csv /tmp/h.csv --game ssq,dlt

CSV 列：game_code,issue,draw_date,numbers_json,source（export_history.py 产出）
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.config import GAMES  # noqa: E402
from app.services.history_service import import_rows  # noqa: E402


def load_rows(path: Path, games: list[str]) -> list[dict]:
    rows: list[dict] = []
    skipped = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for rec in csv.DictReader(f):
            code = (rec.get("game_code") or "").strip()
            issue = (rec.get("issue") or "").strip()
            if code not in games or not issue:
                skipped += 1
                continue
            rows.append(
                {
                    "game_code": code,
                    "issue": issue,
                    "draw_date": date.fromisoformat((rec.get("draw_date") or "").strip()),
                    "numbers_json": json.loads(rec["numbers_json"]),
                    "source": (rec.get("source") or "official").strip() or "official",
                }
            )
    print(f"[import] 读取 {len(rows)} 行（跳过 {skipped} 行不匹配记录）")
    return rows


async def run(path: Path, games: list[str]) -> int:
    rows = load_rows(path, games)
    if not rows:
        print("[import] 没有可导入的数据")
        return 1
    summary = await import_rows(rows)
    for code, item in summary.items():
        print(f"[import] {item['name']}: 写入 {item['added']} 期（{item['first_issue']} ~ {item['last_issue']}）")
    print(f"[import] 完成：{len(summary)} 个彩种")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="从 CSV 导入历史开奖")
    parser.add_argument("--csv", required=True, help="CSV 文件路径")
    parser.add_argument("--game", default="", help="仅导入指定彩种，逗号分隔")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.is_file():
        print(f"文件不存在：{path}")
        sys.exit(1)
    games = [c for c in GAMES] if not args.game else [c.strip() for c in args.game.split(",") if c.strip() in GAMES]
    if not games:
        print(f"未知彩种，可用：{', '.join(GAMES)}")
        sys.exit(1)

    sys.exit(asyncio.run(run(path, games)))


if __name__ == "__main__":
    main()
