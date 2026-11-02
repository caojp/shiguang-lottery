"""回测服务：策略 vs 随机基线，逐期命中 / 相似度，结果写入 backtest_reports。

口径说明：
- 相似度 = 单注命中数 / 该彩种总抽取数（数字型按是否中奖计 0/1）
- 每期生成 trials_per_period 注，取平均作为该期指标
- 滚动均值（窗口 10）写入 detail，体现"窗口聚合"；期号缺口检测见 data 路由（窗口函数 LAG + generate_series）
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select

from ..db import get_session_factory
from ..engine.config import GAMES
from ..engine.draw import DrawResult, draw
from ..engine.engine import Ticket, generate_tickets, quick_pick
from ..engine.prize import check
from ..settings import get_settings
from ..models import backtest_reports, draw_history

_ROLLING = 10


def _numbers_to_draw(game_code: str, numbers: dict[str, Any]) -> DrawResult:
    return DrawResult(
        game_code=game_code,
        zones={k: tuple(v) for k, v in (numbers.get("zones") or {}).items()},
        special=numbers.get("special"),
        digits=numbers.get("digits", ""),
    )


def _ticket_metrics(game_code: str, ticket: Ticket, draw_result: DrawResult, pool_high: bool) -> tuple[float, float, int]:
    """返回 (hits, similarity, 单注奖金)。"""
    r = check(GAMES[game_code], ticket, draw_result, pool_high=pool_high)
    g = GAMES[game_code]
    if g.is_digit:
        return (1.0, 1.0, r.money) if r.won else (0.0, 0.0, 0)
    total_pick = sum(z.pick for z in g.zones)
    hits = sum(r.hits.values())
    return float(hits), hits / total_pick, r.money


def _rolling(values: list[float], window: int = _ROLLING) -> list[float]:
    out: list[float] = []
    for i in range(len(values)):
        seg = values[max(0, i - window + 1): i + 1]
        out.append(round(sum(seg) / len(seg), 4))
    return out


async def run_backtest(
    session_id: str,
    game_code: str,
    periods: int,
    strategy: dict[str, Any],
    trials_per_period: int,
) -> dict[str, Any]:
    settings = get_settings()
    game = GAMES[game_code]
    periods = min(periods, settings.backtest_max_periods)

    async with get_session_factory()() as session:
        rows = await session.execute(
            select(draw_history.c.issue, draw_history.c.numbers_json)
            .where(draw_history.c.game_code == game_code)
            .order_by(draw_history.c.issue.desc())
            .limit(periods)
        )
        hist = [dict(r._mapping) for r in rows][::-1]
    if not hist:
        raise ValueError("暂无该彩种历史数据，请先在「数据」页执行拉取或运行 scripts/fetch_history.py --seed-demo")

    pool_high = settings.default_pool_high
    detail: list[dict[str, Any]] = []
    hits_all: list[float] = []
    sim_all: list[float] = []
    base_hits_all: list[float] = []
    base_sim_all: list[float] = []
    win_total = 0
    base_win_total = 0
    win_tickets = 0
    base_win_tickets = 0
    bet_tickets = 0

    for h in hist:
        dr = _numbers_to_draw(game_code, h["numbers_json"])
        hh, ss, bh, bs = [], [], [], []
        for _ in range(trials_per_period):
            t = generate_tickets(game, 1, strategy)[0]
            m = _ticket_metrics(game_code, t, dr, pool_high)
            hh.append(m[0]); ss.append(m[1])
            win_total += m[2]
            bet_tickets += 1
            if m[2] > 0:
                win_tickets += 1
            t2 = quick_pick(game)
            m2 = _ticket_metrics(game_code, t2, dr, pool_high)
            bh.append(m2[0]); bs.append(m2[1])
            base_win_total += m2[2]
            if m2[2] > 0:
                base_win_tickets += 1
        h_, s_, b_, bs_ = sum(hh) / len(hh), sum(ss) / len(ss), sum(bh) / len(bh), sum(bs) / len(bs)
        hits_all.append(h_); sim_all.append(s_); base_hits_all.append(b_); base_sim_all.append(bs_)
        detail.append({
            "issue": h["issue"],
            "hits": round(h_, 4),
            "similarity": round(s_, 4),
            "baseline_hits": round(b_, 4),
            "baseline_similarity": round(bs_, 4),
        })

    # 窗口聚合：滚动均值
    for i, rm in enumerate(_rolling(sim_all)):
        detail[i]["rolling_mean"] = rm

    avg_hits = round(sum(hits_all) / len(hits_all), 4)
    avg_sim = round(sum(sim_all) / len(sim_all), 4)
    base_hits = round(sum(base_hits_all) / len(base_hits_all), 4)
    base_sim = round(sum(base_sim_all) / len(base_sim_all), 4)
    significant = avg_sim > base_sim and avg_hits >= base_hits
    cost = bet_tickets * game.price
    roi = round((win_total - cost) / cost, 4) if cost else 0.0
    base_roi = round((base_win_total - cost) / cost, 4) if cost else 0.0
    win_rate = round(win_tickets / bet_tickets, 4) if bet_tickets else 0.0
    base_win_rate = round(base_win_tickets / bet_tickets, 4) if bet_tickets else 0.0

    async with get_session_factory()() as session:
        res = await session.execute(
            insert(backtest_reports)
            .values(
                session_id=session_id,
                game_code=game_code,
                strategy_json=strategy,
                periods=len(hist),
                avg_hits=avg_hits,
                avg_similarity=avg_sim,
                baseline_hits=base_hits,
                baseline_similarity=base_sim,
                is_significant=significant,
                detail_json=detail,
            )
            .returning(backtest_reports.c.id)
        )
        await session.commit()
        report_id = res.scalar()

    return {
        "id": report_id,
        "game_code": game_code,
        "periods": len(hist),
        "avg_hits": avg_hits,
        "avg_similarity": avg_sim,
        "baseline_hits": base_hits,
        "baseline_similarity": base_sim,
        "is_significant": significant,
        "cost": cost,
        "total_win": win_total,
        "roi": roi,
        "baseline_total_win": base_win_total,
        "baseline_roi": base_roi,
        "win_rate": win_rate,
        "baseline_win_rate": base_win_rate,
        "detail": detail,
    }


async def list_reports(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    async with get_session_factory()() as session:
        rows = await session.execute(
            select(
                backtest_reports.c.id,
                backtest_reports.c.game_code,
                backtest_reports.c.periods,
                backtest_reports.c.avg_hits,
                backtest_reports.c.avg_similarity,
                backtest_reports.c.baseline_hits,
                backtest_reports.c.baseline_similarity,
                backtest_reports.c.is_significant,
                backtest_reports.c.created_at,
            )
            .where(backtest_reports.c.session_id == session_id)
            .order_by(backtest_reports.c.created_at.desc())
            .limit(limit)
        )
        return [dict(r._mapping) for r in rows]
