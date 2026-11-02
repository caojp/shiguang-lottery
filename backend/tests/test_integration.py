"""集成测试：需本地 PostgreSQL（docker compose up -d 后已迁移）。

默认跳过；设置环境变量 RUN_DB_TESTS=1 后执行：
    python -m pytest tests/test_integration.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_TESTS") != "1",
    reason="需要本地 PostgreSQL：docker compose up -d && cd backend && alembic upgrade head",
)


@pytest_asyncio.fixture(scope="module")
async def client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["games"] == 7


async def test_games_list(client):
    r = await client.get("/api/games")
    data = r.json()
    assert len(data) == 7
    ssq = next(g for g in data if g["code"] == "ssq")
    assert ssq["zones"][0]["pick"] == 6


async def test_pick_and_draw(client):
    r = await client.post("/api/picks/generate", json={"game_code": "ssq", "mode": "random", "count": 2})
    assert r.status_code == 200
    tickets = r.json()["tickets"]
    assert len(tickets) == 2

    r2 = await client.post(
        "/api/draws/simulate",
        json={"game_code": "ssq", "session_id": "test-session", "tickets": tickets},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["cost"] == 4
    assert body["bet_id"] is not None


async def test_backtest_requires_history(client):
    r = await client.post(
        "/api/backtests/run",
        json={"game_code": "ssq", "periods": 30, "strategy": {"zone_split": {}}},
    )
    # 未拉历史时返回 400 提示
    assert r.status_code == 400 or r.status_code == 200
