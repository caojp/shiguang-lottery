"""策略回测接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import BacktestOut, BacktestRequest
from ..services import backtest_service

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestOut)
async def run_backtest(req: BacktestRequest):
    try:
        return await backtest_service.run_backtest(
            session_id=req.session_id,
            game_code=req.game_code,
            periods=req.periods,
            strategy=req.strategy,
            trials_per_period=req.trials_per_period,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/reports")
async def reports(session_id: str = "anonymous", limit: int = 20):
    return await backtest_service.list_reports(session_id, limit)
