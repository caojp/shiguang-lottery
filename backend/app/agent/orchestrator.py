"""Agent 编排：LLM function calling 主路径 + 无密钥时的关键词降级路由。

SSE 事件协议（每行 JSON）：
- {"type":"tool_start","name":...,"args":...}
- {"type":"tool_result","name":...,"data":...}
- {"type":"message","text":...}
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from ..settings import get_settings
from .functions import TOOLS, dispatch

SYSTEM_PROMPT = (
    "你是「时光选彩」模拟彩票助手。职责：帮用户生成模拟号码、解释玩法规则、查询冷热号统计、"
    "运行策略回测。重要约束：本工具为娱乐/学习用途，不涉及真实投注；任何选号策略都不改变中奖概率；"
    "回复简洁口语化，涉及金额用千分位；涉及概率必须附带免责提醒。"
)


async def stream_chat(session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
    settings = get_settings()
    if settings.llm_api_key and settings.agent_enabled:
        async for ev in _llm_loop(session_id, message, settings):
            yield ev
    else:
        async for ev in _keyword_loop(session_id, message):
            yield ev


async def _llm_loop(session_id: str, message: str, settings) -> AsyncIterator[dict[str, Any]]:
    url = settings.llm_api_base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    async with httpx.AsyncClient(timeout=60) as client:
        for _ in range(6):
            payload: dict[str, Any] = {"model": settings.llm_model, "messages": messages, "tools": TOOLS}
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                yield {"type": "message", "text": f"模型调用失败（HTTP {resp.status_code}），请检查 LLM 配置或稍后重试。"}
                return
            msg = resp.json()["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content"),
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    fn = tc["function"]
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    yield {"type": "tool_start", "name": fn["name"], "args": args}
                    result = await dispatch(session_id, fn["name"], args)
                    yield {"type": "tool_result", "name": fn["name"], "data": result}
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                continue
            text = msg.get("content") or "已完成。"
            yield {"type": "message", "text": text}
            return
    yield {"type": "message", "text": "处理轮次过多，请把问题拆简单一点。"}


async def _keyword_loop(session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
    """未配置 LLM key 时的内置路由，覆盖常见意图。"""
    m = message.strip()
    if any(k in m for k in ("冷热", "热号", "分析", "频率")):
        args = {"game_code": _pick_game(m), "periods": 60}
        yield {"type": "tool_start", "name": "query_hot_cold", "args": args}
        data = await dispatch(session_id, "query_hot_cold", args)
        yield {"type": "tool_result", "name": "query_hot_cold", "data": data}
        zones = data.get("zones") or {}
        if not zones:
            yield {"type": "message", "text": "该彩种暂无历史数据，请先在「数据」页拉取。"}
            return
        z0 = next(iter(zones.values()))
        hot = "、".join(f"{h['number']:02d}" for h in z0["hot"][:6])
        cold = "、".join(f"{c['number']:02d}" for c in z0["cold"][:6])
        yield {"type": "message", "text": f"近 {data['periods']} 期热号：{hot}；冷号：{cold}。仅供娱乐，不预示未来开奖。"}
        return
    if any(k in m for k in ("规则", "奖金", "奖级", "怎么中", "怎么玩")):
        args = {"game_code": _pick_game(m)}
        yield {"type": "tool_start", "name": "get_game_rule", "args": args}
        data = await dispatch(session_id, "get_game_rule", args)
        yield {"type": "tool_result", "name": "get_game_rule", "data": data}
        tops = "；".join(f"{l['name']}（{l['condition']}）" for l in data["prize_levels"][:3])
        zones_desc = " + ".join(f"{z['label']} 1-{z['pool_size']} 选 {z['pick']}" for z in data["zones"])
        yield {"type": "message", "text": f"{data['name']}：{zones_desc}。主要奖级：{tops}。"}
        return
    if any(k in m for k in ("回测", "策略")):
        args = {"game_code": _pick_game(m), "periods": 100, "strategy": {}, "session_id": session_id}
        yield {"type": "tool_start", "name": "run_backtest", "args": args}
        data = await dispatch(session_id, "run_backtest", args)
        yield {"type": "tool_result", "name": "run_backtest", "data": data}
        if data.get("error"):
            yield {"type": "message", "text": data["error"]}
            return
        sig = "显著优于基线" if data["is_significant"] else "与基线无显著差异"
        yield {"type": "message", "text": f"回测 {data['periods']} 期完成：平均命中 {data['avg_hits']}、相似度 {data['avg_similarity']}，基线相似度 {data['baseline_similarity']}，{sig}。提醒：样本内结论不代表未来。"}
        return
    if any(k in m for k in ("选", "机选", "号码", "来一注", "帮我")):
        args = {"game_code": _pick_game(m), "mode": "random", "count": 1}
        yield {"type": "tool_start", "name": "generate_picks", "args": args}
        data = await dispatch(session_id, "generate_picks", args)
        yield {"type": "tool_result", "name": "generate_picks", "data": data}
        nums = data["tickets"][0]["display"]
        yield {"type": "message", "text": f"为你机选一注：{nums}。仅作模拟演示，不涉及真实投注。"}
        return
    if any(k in m for k in ("开奖", "中奖", "兑")):
        yield {"type": "message", "text": "模拟开奖需要先选号：让我先帮你机选一注，再模拟开奖对奖？回复「帮我选一注」即可。"}
        return
    yield {"type": "message", "text": "我可以帮你：机选号码、查询冷热号、解释玩法规则、运行策略回测。试试「帮我选一注双色球」或「双色球冷热号」。"}


def _pick_game(m: str) -> str:
    name_map = {"双色球": "ssq", "大乐透": "dlt", "快乐8": "kl8", "七乐彩": "qlc", "福彩3d": "fc3d", "3d": "fc3d", "排列5": "pl5", "排列3": "pl3"}
    for k, code in name_map.items():
        if k in m.lower():
            return code
    return "ssq"
