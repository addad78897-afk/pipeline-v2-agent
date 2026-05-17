"""Agent路由

职责：接收Agent运行请求，通过WebSocket推送Agent思考过程。
Agent模式 vs 管线模式：
- 管线模式：固定16步流程，不管文书长什么样都走一遍
- Agent模式：每份文书独立感知→规划→执行→核查，Agent自主决定做什么
"""
import uuid
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from services.file_manager import create_workspace, list_uploads
from agent.orchestrator import run_agent_loop

router = APIRouter()

# Agent作业存储
AGENT_JOBS: dict = {}

UPLOAD_DIR = os.path.expanduser("~/Desktop/管线V2.0_网页/uploads")


class AgentRunRequest(BaseModel):
    session_id: str


@router.post("/agent/run")
async def run_agent(req: AgentRunRequest):
    """启动Agent分析"""
    job_id = uuid.uuid4().hex[:12]

    # 查找该session的上传文件
    session_dir = os.path.join(UPLOAD_DIR, req.session_id)
    filepaths = []
    if os.path.isdir(session_dir):
        filepaths = [
            os.path.join(session_dir, f)
            for f in sorted(os.listdir(session_dir))
            if f.endswith(".txt")
        ]

    if not filepaths:
        return {"error": "该会话没有找到上传文件，请先上传判决书"}

    AGENT_JOBS[job_id] = {
        "job_id": job_id,
        "session_id": req.session_id,
        "status": "QUEUED",
        "file_count": len(filepaths),
        "filepaths": filepaths,
        "documents_processed": 0,
        "events": [],
        "doc_memories": [],
    }

    # 后台启动Agent
    asyncio.create_task(_run_agent_background(job_id, req.session_id, filepaths))

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "file_count": len(filepaths),
        "mode": "agent",
    }


async def _run_agent_background(job_id: str, session_id: str, filepaths: list):
    """后台运行Agent循环"""
    job = AGENT_JOBS[job_id]
    job["status"] = "RUNNING"

    workspace = create_workspace(job_id)
    input_dir = os.path.join(workspace, "input")
    output_dir = os.path.join(workspace, "output")

    # 把上传的文件复制到input_dir供工具使用
    for fp in filepaths:
        dest = os.path.join(input_dir, os.path.basename(fp))
        if not os.path.exists(dest):
            try:
                os.link(fp, dest)
            except OSError:
                import shutil
                shutil.copy2(fp, dest)

    try:
        async for event in run_agent_loop(
            job_id=job_id,
            session_id=session_id,
            workspace=workspace,
            input_dir=input_dir,
            output_dir=output_dir,
            filepaths=filepaths,
        ):
            # 追踪进度
            if event["type"] == "document_complete":
                job["documents_processed"] += 1
                # 收集文档记忆
                if "doc_memory" in event:
                    job.setdefault("doc_memories", []).append(event["doc_memory"])
            elif event["type"] == "agent_complete":
                job["status"] = "COMPLETED"

            job.setdefault("events", []).append(event)
    except Exception as e:
        job["status"] = "FAILED"
        job.setdefault("events", []).append({
            "type": "agent_complete",
            "job_id": job_id,
            "error": str(e),
            "timestamp": __import__("time").time(),
        })


@router.get("/agent/status/{job_id}")
async def get_agent_status(job_id: str):
    """查询Agent作业状态"""
    job = AGENT_JOBS.get(job_id)
    if not job:
        return {"error": "agent job not found"}
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "file_count": job["file_count"],
        "documents_processed": job["documents_processed"],
        "event_count": len(job.get("events", [])),
    }


@router.get("/agent/memory")
async def get_agent_memory():
    """获取Agent长期记忆（跨文档统计）"""
    from agent.memory import global_memory
    return global_memory.get_summary()


@router.get("/agent/job/{job_id}/documents")
async def get_agent_documents(job_id: str):
    """获取某次Agent作业的文档处理记录"""
    job = AGENT_JOBS.get(job_id)
    if not job:
        return {"error": "agent job not found"}
    return {
        "job_id": job_id,
        "documents": job.get("doc_memories", []),
    }


@router.websocket("/ws/agent/{job_id}")
async def ws_agent(ws: WebSocket, job_id: str):
    """Agent WebSocket —— 实时推送Agent思考过程"""
    await ws.accept()
    try:
        # 重连回放
        job = AGENT_JOBS.get(job_id, {})
        for event in job.get("events", []):
            await ws.send_json(event)

        last_idx = len(job.get("events", []))
        while True:
            await asyncio.sleep(0.3)
            events = AGENT_JOBS.get(job_id, {}).get("events", [])
            while last_idx < len(events):
                await ws.send_json(events[last_idx])
                last_idx += 1
            status = AGENT_JOBS.get(job_id, {}).get("status")
            if status in ("COMPLETED", "FAILED", "CANCELLED"):
                break
    except WebSocketDisconnect:
        pass
