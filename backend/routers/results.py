"""结果查询路由

职责：返回已完成作业的分析结果数据。
"""
import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from config import WORKSPACE_ROOT

router = APIRouter()


@router.get("/results/{job_id}/summary")
async def get_summary(job_id: str):
    """返回概览指标，暂时返回mock数据"""
    return {
        "job_id": job_id,
        "total_cases": 10435,
        "key_metrics": {
            "statutory_rate": "83.2%",
            "avg_awarded": "¥18,520",
            "avg_claim_ratio": "34.7%",
            "industry_distribution": [
                {"industry": "服装", "count": 2134},
                {"industry": "电子产品", "count": 1856},
                {"industry": "食品", "count": 1432},
            ],
        },
    }


@router.get("/results/{job_id}/dimensions")
async def get_dimensions(job_id: str, page: int = 1, per_page: int = 50):
    """返回19维分析数据（分页），暂时mock"""
    return {
        "job_id": job_id,
        "total": 10435,
        "page": page,
        "per_page": per_page,
        "columns": [
            "案件ID", "原告诉请金额", "判赔金额", "法定赔偿率",
            "侵权认定", "赔偿方式", "行业分类", "法院层级",
        ],
        "rows": [],
    }


@router.get("/results/{job_id}/charts")
async def get_charts(job_id: str):
    """返回图表列表"""
    charts_dir = os.path.join(WORKSPACE_ROOT, job_id, "charts")
    charts = []
    if os.path.isdir(charts_dir):
        for f in sorted(os.listdir(charts_dir)):
            if f.endswith(".png"):
                charts.append({
                    "name": f.replace(".png", ""),
                    "url": f"/api/results/{job_id}/charts/{f}",
                })
    return {"charts": charts}


@router.get("/results/{job_id}/charts/{name}")
async def get_chart_file(job_id: str, name: str):
    path = os.path.join(WORKSPACE_ROOT, job_id, "charts", name)
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "not found"}, status_code=404)


@router.get("/results/{job_id}/reports")
async def get_reports(job_id: str):
    """返回报告列表"""
    reports_dir = os.path.join(WORKSPACE_ROOT, job_id, "reports")
    reports = []
    if os.path.isdir(reports_dir):
        for f in sorted(os.listdir(reports_dir)):
            if f.endswith(".md") or f.endswith(".txt"):
                reports.append({
                    "name": f,
                    "url": f"/api/results/{job_id}/reports/{f}",
                })
    return {"reports": reports}


@router.get("/results/{job_id}/reports/{name}")
async def get_report_file(job_id: str, name: str):
    path = os.path.join(WORKSPACE_ROOT, job_id, "reports", name)
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "not found"}, status_code=404)
