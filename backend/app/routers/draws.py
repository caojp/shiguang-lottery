"""模拟开奖与对奖接口：开奖 + 逐注判定 + 写入 bets。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import insert

from ..db import get_session_factory
from ..engine.config import GAMES
from ..engine.draw import draw
from ..engine.engine import Ticket
from ..engine.prize import check
from ..models import bets
from ..schemas import DrawOut, DrawRequest

router = APIRouter(prefix="/api/draws", tags=["draws"])


@router.post("/simulate", response_model=DrawOut)
async def simulate_draw(req: DrawRequest):
    game = GAMES.get(req.game_code)
    if game is None:
        raise HTTPException(404, f"未知彩种: {req.game_code}")

    dr = draw(game)
    tickets = [
        Ticket(game.code, zones={k: tuple(v) for k, v in t.zones.items()}, digits=t.digits)
        for t in req.tickets
    ]

    results = []
    hit_count, win = 0, 0
    best_level = None
    for i, t in enumerate(tickets):
        r = check(game, t, dr, pool_high=req.pool_high, play=req.play)
        hit_numbers = {
            z.name: sorted(
                set(t.zones.get(z.name, ())) & set(dr.zones.get(z.name, ()))
            )
            for z in game.zones
        }
        results.append({
            "index": i,
            "display": t.display(game),
            "won": r.won,
            "level": r.level.name if r.level else None,
            "level_index": r.level_index,
            "money": r.money,
            "hits": r.hits,
            "hit_numbers": hit_numbers,
            "digits": t.digits,
            "digit_hits": [a == b for a, b in zip(t.digits, dr.digits)] if game.is_digit else [],
        })
        if r.won:
            hit_count += 1
            win += r.money
            if best_level is None or (r.level_index < best_level[1]):
                best_level = (r.level.name, r.level_index)

    cost = len(tickets) * game.price
    draw_payload = {
        "zones": {k: list(v) for k, v in dr.zones.items()},
        "special": dr.special,
        "digits": dr.digits,
        "display": dr.display(game),
    }

    bet_id = None
    async with get_session_factory()() as session:
        res = await session.execute(
            insert(bets).values(
                session_id=req.session_id,
                game_code=game.code,
                bet_type="single",
                numbers_json={"zones": {k: list(v) for k, v in t.zones.items()}, "digits": t.digits}
                if len(tickets) == 1 else {"zones": {}, "digits": ""},
                ticket_count=len(tickets),
                stake=game.price,
                draw_issue=None,
                draw_numbers_json=draw_payload,
                prize_level=best_level[0] if best_level else None,
                prize_money=win,
                pool_high=req.pool_high,
            )
            .returning(bets.c.id)
        )
        await session.commit()
        bet_id = res.scalar()

    return DrawOut(
        game_code=game.code,
        draw=draw_payload,
        cost=cost,
        win=win,
        profit=win - cost,
        hit_count=hit_count,
        results=results,
        bet_id=bet_id,
    )
