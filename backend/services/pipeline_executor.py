"""管线执行器

职责：通过subprocess调用现有16个Python脚本，推送进度事件。
不修改、不复制原始脚本——只通过环境变量注入路径参数。
"""
import os
import subprocess
import asyncio
import json
import time
from typing import AsyncGenerator, Optional

from config import SCRIPTS_DIR
from services.file_manager import create_workspace

STEPS = [
    (1, "编码检测与转换", "0001_编码检测与转换.py", 1),
    (2, "段落分割", "0002_段落分割.py", 1),
    (3, "案号与法院提取", "0003_案号与法院提取.py", 1),
    (4, "当事人信息提取", "0004_当事人信息提取.py", 1),
    (5, "主体分类", "0005_主体分类_自然人企业个体工商户.py", 1),
    (6, "名称规范化", "0006_名称规范化.py", 1),
    (7, "Round 1 字段提取", "0007_第一轮_批量字段提取.py", 2),
    (8, "Round 2 深度提取", "0008_第二轮_深度数值提取与验算.py", 2),
    (9, "手工分类补丁", "0009_手工分类数据补丁.py", 2),
    (10, "19维综合分析", "0010_多维度AI综合分析_19维.py", 2),
    (11, "可视化（6图）", "0011_可视化_6图.py", 3),
    (12, "证据类型与说理", "0012_证据类型与说理深度.py", 3),
    (13, "同案不同判分析", "0013_同案不同判冲突分析.py", 3),
    (14, "阶梯式证明标准", "0014_阶梯式证明标准模型.py", 3),
    (15, "计量经济学建模", "0015_计量经济学建模_4模型.py", 3),
    (16, "时间趋势分析", "0016_时间趋势分析.py", 3),
]


async def execute_pipeline(
    job_id: str, session_id: str, phase_selection: Optional[list] = None
) -> AsyncGenerator:
    """异步执行管线，yield进度事件。

    每个事件dict格式：
    {"type": "progress|step_complete|step_error|pipeline_complete", ...}
    """
    workspace = create_workspace(job_id)

    # 将要执行的步骤过滤出来
    todo = STEPS
    if phase_selection:
        todo = [s for s in STEPS if s[3] in phase_selection]

    total = len(todo)
    started_at = time.time()

    for idx, (step_num, step_name, script_name, phase) in enumerate(todo):
        script_path = os.path.join(SCRIPTS_DIR, script_name)

        # 1) 发出 step_start 事件
        yield {
            "type": "progress",
            "job_id": job_id,
            "progress_percent": round(idx / total * 100, 1),
            "phase": phase,
            "step": step_num,
            "step_name": step_name,
            "status": "RUNNING",
            "detail": f"开始执行 {script_name}...",
            "timestamp": time.time(),
        }

        step_start = time.time()
        try:
            # 2) 通过subprocess执行脚本
            env = {
                **os.environ,
                "PV2_WORKSPACE": workspace,
                "PV2_INPUT_DIR": os.path.join(workspace, "input"),
                "PV2_OUTPUT_DIR": os.path.join(workspace, "output"),
            }

            proc = await asyncio.create_subprocess_exec(
                "python3", script_path,
                cwd=SCRIPTS_DIR,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=3600
            )

            log_lines = stdout.decode("utf-8", errors="replace").strip().split("\n")[:20]

            if proc.returncode != 0:
                raise RuntimeError(stderr.decode("utf-8", errors="replace")[:500])

            # 3) 发出 step_complete 事件
            yield {
                "type": "step_complete",
                "step": step_num,
                "step_name": step_name,
                "duration_seconds": round(time.time() - step_start, 1),
                "output_summary": log_lines[-3:] if log_lines else "",
            }

        except Exception as e:
            yield {
                "type": "step_error",
                "step": step_num,
                "step_name": step_name,
                "error_message": str(e),
            }
            # 不中断管线，继续下一步

    # 发出 pipeline_complete 事件
    yield {
        "type": "pipeline_complete",
        "job_id": job_id,
        "total_duration_seconds": round(time.time() - started_at, 1),
    }
