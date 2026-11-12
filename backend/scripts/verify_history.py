"""数据核对：把官方接口当前返回的数据与库内同 issue 记录逐字段比对。

用法（backend/ 目录）：
    python scripts/verify_history.py            # 每彩种核对最新 5 期
    python scripts/verify_history.py --pages 1  # 核对最新 30 期
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import db  # noqa: E402
from app.engine.config import GAMES  # noqa: E402
from app.models import draw_history  # noqa: E402
from app.services.official_fetcher import fetch_game  # noqa: E402


def _norm(numbers: dict) -> str:
    """把 numbers JSON 归一为可比较字符串。"""
    zones = numbers.get("zones") or {}
    parts = [f"{k}={'/'.join(str(n) for n in sorted(v))}" for k, v in sorted(zones.items())]
    if numbers.get("special") is not None:
        parts.append(f"special={numbers['special']}")
    if numbers.get("digits"):
        parts.append(f"digits={numbers['digits']}")
    return " ".join(parts)


async def verify(codes: list[str], pages: int) -> int:
    db.init_engine()
    mismatch_total = 0
    checked_total = 0

    for code in codes:
        g = GAMES[code]
        recs = await asyncio.to_thread(fetch_game, code, pages, 30)
        if not recs:
            print(f"[verify] {g.name}: 官方接口无数据，跳过")
            continue

        mismatches = 0
        checked = 0
        async with db.get_session_factory()() as session:
            for rec in recs:
                row = await session.execute(
                    select(draw_history.c.draw_date, draw_history.c.numbers_json, draw_history.c.source)
                    .where(
                        draw_history.c.game_code == code,
                        draw_history.c.issue == rec.issue,
                    )
                )
                m = row.mappings().first()
                if not m:
                    print(f"[verify] {g.name} {rec.issue}: 库中缺失（官方有，建议重新拉取）")
                    mismatches += 1
                    continue
                checked += 1
                local = _norm(m["numbers_json"] or {})
                remote = _norm(rec.numbers)
                date_ok = m["draw_date"] == rec.draw_date
                if local != remote or not date_ok:
                    mismatches += 1
                    print(f"[verify] {g.name} {rec.issue}: 不一致")
                    print(f"   库内: {m['draw_date']} {local}")
                    print(f"   官方: {rec.draw_date} {remote}")
                elif m["source"] != "official":
                    print(f"[verify] {g.name} {rec.issue}: 号码一致，但 source={m['source']}")

        checked_total += checked
        mismatch_total += mismatches
        if mismatches == 0:
            print(f"[verify] {g.name}: {checked} 期全部一致（最新 {recs[0].issue}）")

    print(f"\n[verify] 合计核对 {checked_total} 期，不一致 {mismatch_total} 期")
    return 1 if mismatch_total else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="库内开奖数据与官方接口逐字段核对")
    parser.add_argument("--game", default="", help="仅核对指定彩种，逗号分隔，留空全部")
    parser.add_argument("--pages", type=int, default=1, help="每彩种核对页数（每页 30 期，默认 1）")
    args = parser.parse_args()

    codes = [c for c in GAMES] if not args.game else [c.strip() for c in args.game.split(",") if c.strip() in GAMES]
    if not codes:
        print(f"未知彩种，可用：{', '.join(GAMES)}")
        sys.exit(1)
    sys.exit(asyncio.run(verify(codes, args.pages)))


if __name__ == "__main__":
    main()
