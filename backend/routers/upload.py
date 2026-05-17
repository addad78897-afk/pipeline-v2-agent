"""文件上传路由

职责：接收.txt文件上传，保存到会话目录。
"""
from fastapi import APIRouter, UploadFile, File
from services.file_manager import create_session, save_upload, list_uploads

router = APIRouter()


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    session_id = create_session()
    saved = []
    for f in files:
        if not f.filename or not f.filename.endswith(".txt"):
            continue
        content = await f.read()
        filepath = save_upload(session_id, f.filename, content)
        saved.append({"filename": f.filename, "size": len(content)})

    return {
        "session_id": session_id,
        "file_count": len(saved),
        "files": saved,
    }
