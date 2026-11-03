"""选号接口：机选 / 策略选号 / 自选校验（支持数字型玩法与乐透型复式）。

复式说明：乐透型自选时每区可多选号码，按组合展开为多注单式票，
展开后的注数上限与单次机选一致（100 注）。

登录用户还可将模拟选号记录保存到服务端（user_picks）并在「我的」页查看。
"""
from __future__ import annotations

from itertools import combinations, product
from math import comb

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .. import db, models
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
from ..schemas import PickOut, PickRecordOut, PickRequest, PickSaveRequest, TicketIn
from ..security import get_current_user
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


def _stored_ticket(game, t: TicketIn) -> dict:
    """保存记录时由后端基于彩种规则重新生成 display，不信任前端传入文本。"""
    zones = {k: [int(x) for x in v] for k, v in t.zones.items()}
    display = ""
    try:
        tk = Ticket(
            game.code,
            zones={k: tuple(sorted(v)) for k, v in t.zones.items()},
            digits=(t.digits or "").strip(),
        )
        display = tk.display(game)
    except Exception:
        display = ""
    return {"zones": zones, "digits": t.digits, "display": display}


def _record_out(row) -> PickRecordOut:
    created = row.created_at.isoformat() if row.created_at is not None else None
    return PickRecordOut(
        id=row.id,
        game_code=row.game_code,
        mode=row.mode,
        play=row.play or "",
        count=row.count,
        cost=row.cost,
        win=row.win or 0,
        tickets=row.numbers_json or [],
        draw=row.draw_json,
        created_at=created,
    )


@router.post("/save", response_model=PickRecordOut)
async def save_pick(req: PickSaveRequest, user: models.users = Depends(get_current_user)):
    """登录用户保存一条模拟选号记录（可仅选号，或含开奖结果）。"""
    game = GAMES.get(req.game_code)
    if game is None:
        raise HTTPException(404, f"未知彩种: {req.game_code}")
    stored = [_stored_ticket(game, t) for t in req.tickets]
    async with db.get_session_factory()() as session:
        result = await session.execute(
            models.user_picks.insert()
            .values(
                user_id=user.id,
                game_code=req.game_code,
                mode=req.mode,
                play=req.play,
                count=req.count,
                cost=req.cost,
                numbers_json=stored,
                draw_json=req.draw,
                win=req.win,
            )
            .returning(
                models.user_picks.c.id,
                models.user_picks.c.game_code,
                models.user_picks.c.mode,
                models.user_picks.c.play,
                models.user_picks.c.count,
                models.user_picks.c.cost,
                models.user_picks.c.numbers_json,
                models.user_picks.c.draw_json,
                models.user_picks.c.win,
                models.user_picks.c.created_at,
            )
        )
        await session.commit()
        row = result.one()
    return _record_out(row)


@router.get("/mine", response_model=list[PickRecordOut])
async def my_picks(
    limit: int = 20,
    user: models.users = Depends(get_current_user),
):
    """登录用户查看自己的选号记录（倒序）。"""
    async with db.get_session_factory()() as session:
        rows = (
            await session.execute(
                select(models.user_picks)
                .where(models.user_picks.c.user_id == user.id)
                .order_by(models.user_picks.c.created_at.desc(), models.user_picks.c.id.desc())
                .limit(max(1, min(limit, 100)))
            )
        ).all()
    return [_record_out(r) for r in rows]
