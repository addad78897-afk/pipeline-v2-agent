"""工作区文件管理

职责：创建/清理每次上传会话的工作目录。
"""
import os
import uuid
import shutil
from config import UPLOAD_DIR, WORKSPACE_ROOT


def create_session() -> str:
    """创建上传会话，返回 session_id"""
    session_id = uuid.uuid4().hex[:12]
    os.makedirs(os.path.join(UPLOAD_DIR, session_id), exist_ok=True)
    return session_id


def save_upload(session_id: str, filename: str, content: bytes) -> str:
    """保存上传文件，返回文件路径"""
    dirpath = os.path.join(UPLOAD_DIR, session_id)
    filepath = os.path.join(dirpath, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath


def list_uploads(session_id: str) -> list[str]:
    """列出某会话的所有上传文件名"""
    dirpath = os.path.join(UPLOAD_DIR, session_id)
    if not os.path.isdir(dirpath):
        return []
    return sorted(os.listdir(dirpath))


def create_workspace(job_id: str) -> str:
    """为管线执行创建独立工作区"""
    ws = os.path.join(WORKSPACE_ROOT, job_id)
    for sub in ("input", "output", "charts", "reports", "logs"):
        os.makedirs(os.path.join(ws, sub), exist_ok=True)
    return ws


def cleanup_workspace(job_id: str) -> None:
    """删除工作区"""
    ws = os.path.join(WORKSPACE_ROOT, job_id)
    if os.path.isdir(ws):
        shutil.rmtree(ws, ignore_errors=True)
