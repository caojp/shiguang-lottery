"""冷热号与形态分析接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..engine.config import GAMES
from ..services import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/hot-cold")
async def hot_cold(game_code: str, periods: int = 60):
    if game_code not in GAMES:
        raise HTTPException(404, f"未知彩种: {game_code}")
    return await analysis_service.hot_cold(game_code, min(max(periods, 1), 500))


@router.get("/stats")
async def stats(game_code: str, periods: int = 60):
    """遗漏值 / 和值 / 跨度 / 012 路统计。"""
    if game_code not in GAMES:
        raise HTTPException(404, f"未知彩种: {game_code}")
    return await analysis_service.stats(game_code, min(max(periods, 1), 500))
