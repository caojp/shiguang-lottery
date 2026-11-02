"""彩种列表与规则查询。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..engine.config import GAMES
from ..schemas import game_out

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
async def list_games():
    return [game_out(g) for g in GAMES.values()]


@router.get("/{code}")
async def get_game(code: str):
    g = GAMES.get(code)
    if g is None:
        raise HTTPException(404, f"未知彩种: {code}")
    return game_out(g)
