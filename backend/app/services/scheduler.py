"""历史数据定时任务：每日开奖后自动入库，移动端无需任何手动操作。

- 首次部署且库中无数据时，先引导写入若干期，保证页面与分析/回测可用。
- 此后每天在设定时间（默认北京时间 21:35）续写 1 期。
- 时间与开关均可通过环境变量调整：AUTO_FETCH_ENABLED / AUTO_FETCH_HOUR / AUTO_FETCH_MINUTE。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..engine.config import GAMES
from ..settings import get_settings
from .history_service import has_history, seed_demo

logger = logging.getLogger("shiguang.scheduler")
_TZ = ZoneInfo("Asia/Shanghai")


async def _bootstrap_if_empty() -> None:
    """库中没有任何历史数据时执行一次引导入库。"""
    if await has_history():
        return
    periods = get_settings().auto_seed_periods
    summary = await seed_demo(list(GAMES), periods)
    logger.info("引导入库完成：%s 个彩种，各 %s 期", len(summary), periods)


async def daily_fetch_loop() -> None:
    """常驻协程：每天固定时间续写当日开奖数据。"""
    settings = get_settings()
    if not settings.auto_fetch_enabled:
        logger.info("自动拉取已关闭（AUTO_FETCH_ENABLED=false）")
        return

    try:
        await _bootstrap_if_empty()
    except Exception:
        logger.exception("引导入库失败，等待下一次定时任务")

    while True:
        now = datetime.now(_TZ)
        target = datetime.combine(
            now.date(), time(settings.auto_fetch_hour, settings.auto_fetch_minute), tzinfo=_TZ
        )
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep(max(1.0, (target - now).total_seconds()))
        try:
            summary = await seed_demo(list(GAMES), 1)
            logger.info("定时拉取完成：%s 个彩种各新增 1 期", len(summary))
        except Exception:
            logger.exception("定时拉取失败，将在次日重试")
