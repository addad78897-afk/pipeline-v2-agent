"""集中管理所有配置常量

开发环境：使用桌面绝对路径
生产环境：使用环境变量 + 项目内相对路径
"""
import os

# 项目根目录（backend/ 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 脚本路径（优先查环境变量 → 项目内 → 原始项目）
SCRIPTS_DIR = os.environ.get(
    "PV2_SCRIPTS_DIR",
    os.path.join(PROJECT_ROOT, "pipeline", "scripts")
)
# 如果项目内脚本不存在，回退到原始项目路径
if not os.path.isdir(SCRIPTS_DIR):
    SCRIPTS_DIR = os.path.join(
        os.path.expanduser("~/Desktop/管线V2.0_原始项目/管线V2.0_源码"),
        "002_脚本"
    )

# 工作区根目录（生产环境使用项目内路径）
WORKSPACE_ROOT = os.environ.get(
    "PV2_WORKSPACE_ROOT",
    os.path.join(PROJECT_ROOT, "workspaces")
)

# 上传文件保存目录
UPLOAD_DIR = os.environ.get(
    "PV2_UPLOAD_DIR",
    os.path.join(PROJECT_ROOT, "uploads")
)

# DeepSeek API配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
