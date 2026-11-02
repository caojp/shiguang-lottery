"""时光选彩核心逻辑包。

模块划分：
- config   彩种规则配置（号码池、抽取个数、奖级表、浮动奖默认值）
- engine   号码生成引擎（机选 / 策略选号 / 自选校验）
- draw     模拟开奖引擎
- prize    中奖判定与奖金计算
- stats    批量模拟与统计
- history  历史数据导入与冷热号分析
"""
from .config import GameConfig, PrizeLevel, Zone, GAMES
from .engine import Ticket, quick_pick, generate_tickets, validate_ticket, validate_digits, parse_numbers
from .draw import DrawResult, draw
from .prize import PrizeResult, check
from .stats import BatchReport, simulate

__all__ = [
    "GameConfig", "PrizeLevel", "Zone", "GAMES",
    "Ticket", "quick_pick", "generate_tickets", "validate_ticket", "validate_digits", "parse_numbers",
    "DrawResult", "draw",
    "PrizeResult", "check",
    "BatchReport", "simulate",
]
