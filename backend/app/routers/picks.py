"""选号接口：机选 / 策略选号 / 自选校验（支持数字型玩法与乐透型复式）。

复式说明：乐透型自选时每区可多选号码，按组合展开为多注单式票，
展开后的注数上限与单次机选一致（100 注）。
"""
from __future__ import annotations

from itertools import combinations, product
from math import comb

from fastapi import APIRouter, HTTPException

from ..engine.config import GAMES
from ..engine.engine import (
    Ticket,
    generate_history_tickets,
    generate_tickets,
    parse_numbers,
    quick_pick,
    validate_play,
    validate_ticket,
)
from ..schemas import PickOut, PickRequest
from ..services.analysis_service import stats as analysis_stats

router = APIRouter(prefix="/api/picks", tags=["picks"])

MAX_COMPOUND_TICKETS = 100


def _ticket_out(t: Ticket, game) -> dict:
    return {
        "zones": {k: list(v) for k, v in t.zones.items()},
        "digits": t.digits,
        "display": t.display(game),
    }


def _parse_compound(game, zone_inputs: dict[str, str]) -> list[Ticket]:
    """解析复式选号并按组合展开为单式票。

    先按组合数公式校验注数上限，再展开，避免多选号码时生成大量组合对象。
    """
    parsed: list[list[int]] = []
    total = 1
    for z in game.zones:
        nums = sorted(set(parse_numbers(zone_inputs.get(z.name, ""), z.pool_size)))
        if len(nums) < z.pick:
            raise HTTPException(400, f"{z.label}至少选 {z.pick} 个号码")
        total *= comb(len(nums), z.pick)
        parsed.append(nums)
    if total > MAX_COMPOUND_TICKETS:
        raise HTTPException(400, f"复式展开后共 {total} 注，超过单次上限 {MAX_COMPOUND_TICKETS} 注")

    per_zone = [list(combinations(nums, z.pick)) for nums, z in zip(parsed, game.zones)]
    tickets: list[Ticket] = []
    for picked in product(*per_zone):
        tickets.append(
            Ticket(
                game.code,
                zones={z.name: tuple(sorted(nums)) for z, nums in zip(game.zones, picked)},
            )
        )
    return tickets


def _basis_out(stats_data: dict) -> dict:
    """把统计结果压缩成前端可展示的推演依据。"""
    periods = stats_data.get("periods", 0)
    zones = stats_data.get("zones") or {}
    first = next(iter(zones.values()), None)
    if not first:
        return {"periods": periods, "label": "", "hot": [], "overdue": []}
    freq = first.get("frequency") or {}
    hot = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return {
        "periods": periods,
        "label": first.get("label", ""),
        "hot": [int(n) for n, _ in hot],
        "overdue": [int(x["number"]) for x in (first.get("omission_top") or [])[:6]],
    }


@router.post("/generate", response_model=PickOut)
async def generate_picks(req: PickRequest):
    game = GAMES.get(req.game_code)
    if game is None:
        raise HTTPException(404, f"未知彩种: {req.game_code}")

    play = (req.play or "").strip()
    if play and play not in game.play_names:
        raise HTTPException(400, f"{game.name}不支持「{play}」玩法")

    basis = None
    if req.mode == "manual":
        if game.is_digit:
            ok, err = validate_ticket(game, req.zone_inputs, req.digits)
            if not ok:
                raise HTTPException(400, err)
            ok, err = validate_play(game, req.digits.strip(), play)
            if not ok:
                raise HTTPException(400, err)
            tickets = [Ticket(game.code, digits=req.digits.strip())]
        elif req.compound:
            tickets = _parse_compound(game, req.zone_inputs)
        else:
            ok, err = validate_ticket(game, req.zone_inputs, req.digits)
            if not ok:
                raise HTTPException(400, err)
            zones = {
                z.name: tuple(sorted(parse_numbers(req.zone_inputs.get(z.name, ""), z.pool_size)))
                for z in game.zones
            }
            tickets = [Ticket(game.code, zones=zones)]
    elif req.mode == "strategy":
        tickets = generate_tickets(game, req.count, strategy=req.strategy or None, play=play or None)
    elif req.mode == "history":
        stats_data = await analysis_stats(game.code, req.history_periods)
        tickets = generate_history_tickets(game, stats_data, req.count, play or None)
        basis = _basis_out(stats_data)
    else:  # random
        tickets = [quick_pick(game, play or None) for _ in range(max(1, req.count))]

    return PickOut(
        game_code=game.code,
        mode=req.mode,
        count=len(tickets),
        price=game.price,
        cost=len(tickets) * game.price,
        play=play,
        tickets=[_ticket_out(t, game) for t in tickets],
        basis=basis,
    )
