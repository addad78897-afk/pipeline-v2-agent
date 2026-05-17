"""历史记录路由

职责：管理历史作业列表。
"""
from fastapi import APIRouter
from routers.pipeline import JOBS

router = APIRouter()


@router.get("/history")
async def get_history(page: int = 1, per_page: int = 20):
    jobs = list(JOBS.values())
    jobs.sort(key=lambda j: j.get("started_at") or "", reverse=True)
    total = len(jobs)
    start = (page - 1) * per_page
    return {
        "total": total,
        "page": page,
        "jobs": jobs[start : start + per_page],
    }


@router.delete("/history/{job_id}")
async def delete_job(job_id: str):
    if job_id in JOBS:
        del JOBS[job_id]
        return {"deleted": True}
    return {"deleted": False, "error": "not found"}
