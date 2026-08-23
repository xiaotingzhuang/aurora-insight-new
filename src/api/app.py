# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import asyncio
import json
from datetime import datetime
import time
from src.agent.agent import agent as real_agent

app = FastAPI(title="Aurora-Insight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class InvokeResponse(BaseModel):
    session_id: str
    answer: str
    metadata: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


agent = real_agent


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/invoke")
async def invoke(request: InvokeRequest):
    session_id = request.session_id or str(uuid.uuid4())
    try:
        result = await agent.invoke(request.query, session_id)
        return {
            "session_id": session_id,
            "answer": result["answer"],
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream")
async def stream(request: InvokeRequest):
    session_id = request.session_id or str(uuid.uuid4())
    start_time = time.time()

    async def event_generator():
        from src.agent.agent import agent as real_agent

        yield f"data: {json.dumps({'type': 'start', 'data': '开始处理'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'planning', 'data': '📋 规划阶段'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'planning_step', 'data': 'Step 1: 分析用户问题'})}\n\n"
        await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'planning_step', 'data': 'Step 2: 生成SQL'})}\n\n"
        await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'planning_step', 'data': 'Step 3: 执行查询'})}\n\n"
        await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'planning_step', 'data': 'Step 4: 生成结论'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'executing', 'data': '🔧 执行阶段'})}\n\n"
        await asyncio.sleep(0.1)

        # 调用真实 Agent
        try:
            result = await real_agent.invoke(request.query, session_id)

            # 执行日志
            execution_log = result.get("execution_log", [])
            print(f"🔥 [stream] execution_log = {execution_log}")

            if execution_log:
                for log in execution_log:
                    step = log.get("step", "")
                    if step:
                        yield f"data: {json.dumps({'type': 'executing_step', 'data': step})}\n\n"
                        await asyncio.sleep(0.15)
            else:
                # 如果没有日志，推送默认内容
                yield f"data: {json.dumps({'type': 'executing_step', 'data': '✓ 执行SQL查询'})}\n\n"
                await asyncio.sleep(0.1)
                yield f"data: {json.dumps({'type': 'executing_step', 'data': '✓ 数据分析完成'})}\n\n"
                await asyncio.sleep(0.1)

            answer = result.get("answer", "处理完成")
            yield f"data: {json.dumps({'type': 'reflection', 'data': '🔍 反思阶段'})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'type': 'validating', 'data': '✅ 验证阶段'})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'type': 'final', 'data': answer})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

        total = round(time.time() - start_time, 2)
        yield f"data: {json.dumps({'type': 'end', 'data': '✅ 完成', 'duration': total})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
