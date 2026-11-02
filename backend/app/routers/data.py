"""数据源状态接口：各彩种入库统计 + 期号缺口检测（窗口函数 LAG + generate_series 口径）。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from ..db import get_session_factory
from ..engine.config import GAMES
from ..models import draw_history
from ..services.history_service import seed_demo

router = APIRouter(prefix="/api/data", tags=["data"])

# 期号缺口检测：按年份分组，用 LAG 窗口函数找相邻期号序号不连续的位置
_GAP_SQL = text(
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
    LIMIT 8
    """
)


@router.get("/status")
async def data_status():
    out: list[dict[str, Any]] = []
    async with get_session_factory()() as session:
        for code, g in GAMES.items():
            row = await session.execute(
                select(
                    func.count().label("total"),
                    func.max(draw_history.c.issue).label("latest"),
                    func.max(draw_history.c.source).label("source"),
                ).where(draw_history.c.game_code == code)
            )
            m = row.mappings().first()
            total = m["total"] or 0
            latest = m["latest"]
            source = m["source"]

            gaps: list[str] = []
            if total:
                gres = await session.execute(_GAP_SQL, {"code": code})
                for gr in gres.mappings():
                    # 缺失区间 (prev_seq+1 .. seq-1)，至多展示前 3 个具体期号
                    missing = list(range(int(gr["prev_seq"]) + 1, int(gr["seq"])))
                    shown = missing[:3]
                    gaps.append(
                        f"{gr['yr']} 年第 {shown[0]} 期" + (f" 等 {len(missing)} 期" if len(missing) > 1 else "")
                    )

            state = "ok" if total else "no"
            if gaps:
                state = "warn"
            out.append({
                "game_code": code,
                "name": g.name,
                "total": total,
                "latest_issue": latest,
                "source": source,
                "gaps": gaps,
                "state": state,
            })
    return out


class FetchRequest(BaseModel):
    game_code: str | None = Field(default=None, description="仅拉取指定彩种，留空表示全部")
    periods: int = Field(default=30, ge=1, le=200, description="每个彩种新增期数")


@router.post("/fetch")
async def fetch_draw_history(req: FetchRequest):
    """在线触发历史数据入库：从已有最大期号续写，幂等写入。

    当前数据源为演示生成；后续接入官方抓取时在此处替换 fetcher 即可，
    前端“立即拉取”按钮无需改动。
    """
    if req.game_code and req.game_code not in GAMES:
        raise HTTPException(status_code=404, detail="未知彩种")
    codes = [req.game_code] if req.game_code else list(GAMES)
    summary = await seed_demo(codes, req.periods)
    return {
        "updated": sum(item["added"] for item in summary.values()),
        "games": summary,
    }


@router.get("/history")
async def draw_history_list(
    game_code: str = Query(..., description="彩种代码"),
    limit: int = Query(10, ge=1, le=50, description="返回最近 N 期"),
):
    """最近开奖浏览：按期号倒序返回最近 N 期（前端数据页展示用）。"""
    if game_code not in GAMES:
        raise HTTPException(status_code=404, detail="未知彩种")
    async with get_session_factory()() as session:
        rows = await session.execute(
            select(
                draw_history.c.issue,
                draw_history.c.draw_date,
                draw_history.c.numbers_json,
                draw_history.c.source,
            )
            .where(draw_history.c.game_code == game_code)
            .order_by(draw_history.c.issue.desc())
            .limit(limit)
        )
        return [
            {
                "issue": r.issue,
                "draw_date": r.draw_date.isoformat() if r.draw_date else None,
                "numbers": r.numbers_json,
                "source": r.source,
            }
            for r in rows
        ]
