"""管线执行路由

职责：接收运行请求，管理作业生命周期。
"""
import uuid
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from services.pipeline_executor import execute_pipeline

router = APIRouter()

# 简单内存存储（单用户场景，无需数据库）
JOBS: Dict[str, dict] = {}


class RunRequest(BaseModel):
    session_id: str
    phase_selection: Optional[List[int]] = None


@router.post("/pipeline/run")
async def run_pipeline(req: RunRequest):
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "job_id": job_id,
        "session_id": req.session_id,
        "status": "QUEUED",
        "progress_percent": 0,
        "current_step": 0,
        "started_at": None,
    }
    # 启动后台任务
    asyncio.create_task(_run_pipeline_background(job_id, req.session_id, req.phase_selection))
    return {"job_id": job_id, "status": "QUEUED"}


async def _run_pipeline_background(job_id: str, session_id: str, phases: Optional[list] = None):
    JOBS[job_id]["status"] = "RUNNING"
    async for event in execute_pipeline(job_id, session_id, phases):
        if event["type"] == "progress":
            JOBS[job_id]["progress_percent"] = event["progress_percent"]
            JOBS[job_id]["current_step"] = event["step"]
        elif event["type"] == "pipeline_complete":
            JOBS[job_id]["status"] = "COMPLETED"
            JOBS[job_id]["progress_percent"] = 100
        elif event["type"] == "step_error":
            pass  # 记录错误但不中断
        # 保存事件用于WebSocket重连回放
        JOBS[job_id].setdefault("events", []).append(event)
    if JOBS[job_id]["status"] != "COMPLETED":
        JOBS[job_id]["status"] = "COMPLETED"


@router.get("/pipeline/status/{job_id}")
async def get_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job not found"}
    return job


@router.websocket("/ws/pipeline/{job_id}")
async def websocket_progress(ws: WebSocket, job_id: str):
    await ws.accept()
    try:
        # 重连时回放已有事件
        job = JOBS.get(job_id, {})
        for event in job.get("events", []):
            await ws.send_json(event)

        # 轮询新事件
        last_idx = len(job.get("events", []))
        while True:
            await asyncio.sleep(0.5)
            events = JOBS.get(job_id, {}).get("events", [])
            while last_idx < len(events):
                await ws.send_json(events[last_idx])
                last_idx += 1
            if JOBS.get(job_id, {}).get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                break
    except WebSocketDisconnect:
        pass
