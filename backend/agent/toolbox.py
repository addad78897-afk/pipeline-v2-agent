"""工具箱模块

将16个脚本封装为Agent可自主选择调用的工具。
每个工具声明：名称、描述、前置条件、执行函数。
Agent根据文档Profile自主决定调用哪些工具、按什么顺序。
"""
import os
import subprocess
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from config import SCRIPTS_DIR


@dataclass
class Tool:
    """Agent工具箱中的一个工具"""
    id: str
    name: str
    description: str
    script: str          # 对应的Python脚本文件名
    phase: int           # 1=规则引擎 2=LLM提取 3=高级分析
    preconditions: list[str] = field(default_factory=list)  # 前置条件描述
    estimated_cost: str = "free"  # free / llm_api_call

    def can_run(self, precheck_result: dict) -> bool:
        """检查前置条件是否满足（基于感知结果）"""
        for condition in self.preconditions:
            if condition == "need_court_reasoning":
                if not precheck_result.get("has_court_reasoning"):
                    return False
            elif condition == "need_case_number":
                if not precheck_result.get("has_case_number"):
                    return False
            elif condition == "need_verdict":
                if not precheck_result.get("has_verdict"):
                    return False
            elif condition == "need_reasonable_quality":
                if precheck_result.get("quality_score", 0) < 0.3:
                    return False
        return True


# ---- 16个工具的完整定义 ----
TOOLS: list[Tool] = [
    Tool(
        id="encoding", name="编码检测与转换",
        description="检测文件编码（UTF-8/GBK/GB18030），统一转为UTF-8",
        script="0001_编码检测与转换.py", phase=1,
        preconditions=[],
    ),
    Tool(
        id="segmentation", name="段落分割",
        description="按判决书结构切分为：原告诉称、被告辩称、本院查明、本院认为、判决如下等段落",
        script="0002_段落分割.py", phase=1,
        preconditions=[],
    ),
    Tool(
        id="case_info", name="案号与法院提取",
        description="提取案号、法院全称、省份、法院层级、文书类型",
        script="0003_案号与法院提取.py", phase=1,
        preconditions=["need_case_number"],
    ),
    Tool(
        id="parties", name="当事人信息提取",
        description="提取原告、被告、上诉人、被上诉人、第三人、委托代理人",
        script="0004_当事人信息提取.py", phase=1,
        preconditions=[],
    ),
    Tool(
        id="entity_classify", name="主体分类",
        description="将当事人分类为自然人、企业、个体工商户",
        script="0005_主体分类_自然人企业个体工商户.py", phase=1,
        preconditions=[],
    ),
    Tool(
        id="name_normalize", name="名称规范化",
        description="公司全称→简称、自然人姓名去重、法院名称标准化",
        script="0006_名称规范化.py", phase=1,
        preconditions=[],
    ),
    Tool(
        id="field_extract_r1", name="Round 1 字段提取",
        description="DeepSeek-chat批量提取：原告诉请、判赔金额、法定赔偿率等核心字段",
        script="0007_第一轮_批量字段提取.py", phase=2,
        preconditions=["need_court_reasoning"],
        estimated_cost="llm_api_call",
    ),
    Tool(
        id="deep_extract_r2", name="Round 2 深度提取",
        description="对高值案件深度数值提取与交叉验算",
        script="0008_第二轮_深度数值提取与验算.py", phase=2,
        preconditions=["need_court_reasoning", "need_verdict"],
        estimated_cost="llm_api_call",
    ),
    Tool(
        id="manual_patch", name="手工分类补丁",
        description="对AI分类边界模糊的案例进行修正",
        script="0009_手工分类数据补丁.py", phase=2,
        preconditions=[],
    ),
    Tool(
        id="analysis_19d", name="19维综合分析",
        description="DeepSeek多维度分析：侵权认定、赔偿方式、行业分类等19个维度",
        script="0010_多维度AI综合分析_19维.py", phase=2,
        preconditions=["need_court_reasoning", "need_reasonable_quality"],
        estimated_cost="llm_api_call",
    ),
    Tool(
        id="vis_6charts", name="可视化（6图）",
        description="生成年度趋势、法院层级、行业判赔差异等6张统计图表",
        script="0011_可视化_6图.py", phase=3,
        preconditions=[],
    ),
    Tool(
        id="evidence_reasoning", name="证据类型与说理",
        description="分析证据类型分布和判决书说理深度",
        script="0012_证据类型与说理深度.py", phase=3,
        preconditions=["need_court_reasoning"],
    ),
    Tool(
        id="inconsistency", name="同案不同判分析",
        description="检测相似案情下的裁判冲突",
        script="0013_同案不同判冲突分析.py", phase=3,
        preconditions=["need_court_reasoning", "need_verdict"],
    ),
    Tool(
        id="evidence_standard", name="阶梯式证明标准",
        description="构建证据标准的三阶梯分类模型",
        script="0014_阶梯式证明标准模型.py", phase=3,
        preconditions=["need_court_reasoning"],
    ),
    Tool(
        id="econometrics", name="计量经济学建模",
        description="多元回归、Logistic模型等4个计量经济模型",
        script="0015_计量经济学建模_4模型.py", phase=3,
        preconditions=["need_court_reasoning", "need_verdict"],
    ),
    Tool(
        id="time_trend", name="时间趋势分析",
        description="年度-月度案件量、判赔额、法定赔偿率的时间序列分析",
        script="0016_时间趋势分析.py", phase=3,
        preconditions=[],
    ),
]


async def execute_tool(
    tool: Tool,
    workspace: str,
    input_dir: str,
    output_dir: str,
    env_extra: dict = None,
) -> dict:
    """Agent调用单个工具，返回执行结果"""
    script_path = os.path.join(SCRIPTS_DIR, tool.script)

    if not os.path.isfile(script_path):
        return {
            "tool_id": tool.id,
            "success": False,
            "error": f"脚本不存在: {tool.script}",
            "duration_seconds": 0,
            "output_lines": [],
        }

    env = {
        **os.environ,
        "PV2_WORKSPACE": workspace,
        "PV2_INPUT_DIR": input_dir,
        "PV2_OUTPUT_DIR": output_dir,
    }
    if env_extra:
        env.update(env_extra)

    step_start = time.time()
    try:
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
        duration = round(time.time() - step_start, 1)

        if proc.returncode != 0:
            return {
                "tool_id": tool.id,
                "success": False,
                "error": stderr.decode("utf-8", errors="replace")[:300],
                "duration_seconds": duration,
                "output_lines": log_lines,
            }

        return {
            "tool_id": tool.id,
            "success": True,
            "duration_seconds": duration,
            "output_lines": log_lines[-5:],
        }

    except asyncio.TimeoutError:
        return {
            "tool_id": tool.id,
            "success": False,
            "error": "执行超时（3600秒）",
            "duration_seconds": 3600,
            "output_lines": [],
        }
    except Exception as e:
        return {
            "tool_id": tool.id,
            "success": False,
            "error": str(e)[:300],
            "duration_seconds": round(time.time() - step_start, 1),
            "output_lines": [],
        }
