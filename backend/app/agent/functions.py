"""Agent 编排层：LLM function calling 工具定义与执行分派。

tools 均路由到确定性规则引擎与数据访问层，LLM 只负责意图理解与参数抽取。
"""
from __future__ import annotations

import json
from typing import Any

from ..engine.config import GAMES
from ..schemas import game_out

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "generate_picks",
            "description": "生成模拟彩票号码（机选/策略/自选）。策略只改变分布形态，不改变中奖概率。",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_code": {"type": "string", "enum": list(GAMES.keys()), "description": "彩种代码"},
                    "mode": {"type": "string", "enum": ["random", "strategy", "manual"], "default": "random"},
                    "count": {"type": "integer", "default": 1, "minimum": 1, "maximum": 20},
                    "strategy": {"type": "object", "description": "策略参数，如 {'hot_cold': {'weights': {号码:权重}}}"},
                },
                "required": ["game_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_draw",
            "description": "对一组号码执行模拟开奖并对奖，返回逐注奖级与奖金。",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_code": {"type": "string", "enum": list(GAMES.keys())},
                    "tickets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "zones": {"type": "object", "description": "如 {'red': [1,5,12], 'blue': [7]}"},
                                "digits": {"type": "string", "description": "数字型号码，如 '007'"},
                            },
                        },
                    },
                    "session_id": {"type": "string", "default": "anonymous"},
                },
                "required": ["game_code", "tickets"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_hot_cold",
            "description": "查询某彩种最近 N 期的冷热号统计（出现次数 Top / 低频）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_code": {"type": "string", "enum": list(GAMES.keys())},
                    "periods": {"type": "integer", "default": 60},
                },
                "required": ["game_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_rule",
            "description": "查询某彩种的完整规则（号码池、抽取个数、奖级与奖金）。",
            "parameters": {
                "type": "object",
                "properties": {"game_code": {"type": "string", "enum": list(GAMES.keys())}},
                "required": ["game_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "用历史开奖对指定策略做回测，返回平均命中、相似度与基线对照。",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_code": {"type": "string", "enum": list(GAMES.keys())},
                    "periods": {"type": "integer", "default": 100, "minimum": 10, "maximum": 300},
                    "strategy": {"type": "object", "default": {}},
                    "session_id": {"type": "string", "default": "anonymous"},
                },
                "required": ["game_code"],
            },
        },
    },
]


async def dispatch(session_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """执行工具并返回可 JSON 序列化的结果。"""
    from ..routers.picks import _ticket_out  # 复用展示序列化
    from ..engine.engine import Ticket, generate_tickets, quick_pick, validate_ticket
    from ..engine.draw import draw
    from ..engine.prize import check
    from ..services import analysis_service, backtest_service

    if name == "generate_picks":
        game = GAMES[args["game_code"]]
        mode = args.get("mode", "random")
        count = int(args.get("count", 1))
        if mode == "manual":
            ok, err = validate_ticket(game, args.get("zone_inputs") or {}, args.get("digits") or "")
            if not ok:
                return {"error": err}
        if mode == "strategy":
            tickets = generate_tickets(game, count, strategy=args.get("strategy") or None)
        else:
            tickets = [quick_pick(game) for _ in range(count)]
        return {"tickets": [_ticket_out(t, game) for t in tickets]}

    if name == "simulate_draw":
        game = GAMES[args["game_code"]]
        dr = draw(game)
        tickets = [
            Ticket(game.code, zones={k: tuple(v) for k, v in t.get("zones", {}).items()}, digits=t.get("digits", ""))
            for t in args.get("tickets", [])
        ]
        results = []
        for i, t in enumerate(tickets):
            r = check(game, t, dr)
            results.append({
                "index": i,
                "display": t.display(game),
                "won": r.won,
                "level": r.level.name if r.level else None,
                "money": r.money,
            })
        return {"draw": dr.display(game), "results": results}

    if name == "query_hot_cold":
        return await analysis_service.hot_cold(args["game_code"], int(args.get("periods", 60)))

    if name == "get_game_rule":
        return game_out(GAMES[args["game_code"]])

    if name == "run_backtest":
        try:
            return await backtest_service.run_backtest(
                session_id=args.get("session_id") or session_id,
                game_code=args["game_code"],
                periods=int(args.get("periods", 100)),
                strategy=args.get("strategy") or {},
                trials_per_period=10,
            )
        except ValueError as exc:
            return {"error": str(exc)}

    return {"error": f"未知工具: {name}"}
