"""Agent 对话接口（SSE 流式）。"""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agent.orchestrator import stream_chat
from ..schemas import AgentChatRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat")
async def chat(req: AgentChatRequest):
    async def event_gen():
        async for ev in stream_chat(req.session_id, req.message):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/chat-sync")
async def chat_sync(req: AgentChatRequest):
    """非流式版本：收集编排结果，返回最终回复文本（便于小程序端消费）。"""
    text = ""
    async for ev in stream_chat(req.session_id, req.message):
        if ev.get("type") == "message":
            text = ev.get("text", "")
    return {"text": text, "session_id": req.session_id}
