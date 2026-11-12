"""历史数据定时任务：每日开奖后从官方接口自动入库。

- 首次部署且库中无数据时，先引导拉取官方数据（每彩种 3 页 × 30 期）。
- 此后每天在设定时间（默认北京时间 21:35）拉取各彩种最新 1 期。
- 时间与开关可通过环境变量调整：AUTO_FETCH_ENABLED / AUTO_FETCH_HOUR / AUTO_FETCH_MINUTE。

重要：拉取失败时只记录告警，绝不写入随机演示数据。
部署环境（机房出口）若被官方 WAF 拦截，请改用
`scripts/export_history.py`（可直连的机器导出）+ `scripts/import_history.py`（服务器导入）。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..engine.config import GAMES
from ..settings import get_settings
from .history_service import has_history, import_official

logger = logging.getLogger("shiguang.scheduler")
_TZ = ZoneInfo("Asia/Shanghai")


def _log_summary(stage: str, summary: dict) -> None:
    ok = [f"{v['name']} {v.get('added', 0)} 期" for v in summary.values() if not v.get("error")]
    bad = [f"{v['name']}: {v['error']}" for v in summary.values() if v.get("error")]
    logger.info("%s完成：%s", stage, "、".join(ok) if ok else "无成功彩种")
    for item in bad:
        logger.warning("%s失败：%s", stage, item)


async def _bootstrap_if_empty() -> None:
    """库中没有任何历史数据时，从官方接口引导拉取（不写入演示数据）。"""
    if await has_history():
        return
    summary = await import_official(list(GAMES), pages=3, page_size=30)
    _log_summary("引导拉取", summary)


async def daily_fetch_loop() -> None:
    """常驻协程：每天固定时间从官方接口续写当日开奖数据。"""
    settings = get_settings()
    if not settings.auto_fetch_enabled:
        logger.info("自动拉取已关闭（AUTO_FETCH_ENABLED=false）")
        return

    try:
        await _bootstrap_if_empty()
    except Exception:
        logger.exception("引导拉取失败，等待下一次定时任务")

    while True:
        now = datetime.now(_TZ)
        target = datetime.combine(
            now.date(), time(settings.auto_fetch_hour, settings.auto_fetch_minute), tzinfo=_TZ
        )
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep(max(1.0, (target - now).total_seconds()))
        try:
            summary = await import_official(list(GAMES), pages=1, page_size=1)
            _log_summary("定时拉取", summary)
        except Exception:
            logger.exception("定时拉取异常，将在次日重试")
