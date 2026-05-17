"""管线V2.0 网页分析工具 — FastAPI 后端入口

开发模式：前后端分离（Vite dev server proxy到后端）
生产模式：FastAPI托管前端静态文件（单URL部署）
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import upload, pipeline, results, history, agent

app = FastAPI(title="管线V2.0 API", version="0.2.0")

# CORS：开发时Vite dev server需要，生产同源部署时无影响
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API路由
app.include_router(upload.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- 生产模式：托管前端静态文件 ----
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    # SPA fallback：所有非API路径返回index.html
    from starlette.responses import FileResponse

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = os.path.join(FRONTEND_DIST, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
