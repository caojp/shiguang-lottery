"""时光选彩后端（FastAPI + SQLAlchemy Core + asyncpg + PostgreSQL）。"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import db, models
from .engine.config import GAMES
from .routers import agent, analysis, backtests, data, draws, games, picks
from .schemas import game_out
from .services.scheduler import daily_fetch_loop
from .settings import get_settings


async def seed_games() -> None:
    """首次启动时把 7 彩种配置写入 games 表（幂等）。"""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with db.get_session_factory()() as session:
        for g in GAMES.values():
            stmt = pg_insert(models.games).values(
                code=g.code, name=g.name, game_type=g.game_type, config_json=game_out(g)
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.games.c.code],
                set_={"config_json": stmt.excluded.config_json},
            )
            await session.execute(stmt)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_engine()
    await seed_games()
    # 每日开奖后自动入库（首次无数据时先引导补数）
    fetch_task = asyncio.create_task(daily_fetch_loop())
    yield
    fetch_task.cancel()
    try:
        await fetch_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="时光选彩 API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router)
app.include_router(picks.router)
app.include_router(draws.router)
app.include_router(backtests.router)
app.include_router(analysis.router)
app.include_router(data.router)
app.include_router(agent.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "games": len(GAMES)}
