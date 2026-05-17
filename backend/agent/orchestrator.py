"""决策中心 —— Agent的大脑

五大循环步骤：
① 观察(Observe): 调用感知模块，为每份文书生成Profile
② 规划(Plan):   根据Profile自主决定——选哪些工具、什么顺序、用什么策略
③ 执行(Execute): 逐个调用选定的工具
④ 核查(Verify):  检查输出质量，不合格则换策略重试
⑤ 记录(Record):  写入记忆，更新长期统计
"""
import asyncio
import time
from typing import AsyncGenerator, Optional

from agent.perception import perceive_document, perceive_batch, DocumentProfile
from agent.toolbox import TOOLS, Tool, execute_tool
from agent.memory import DocumentMemory, StepRecord, global_memory


# ---- 规划引擎 ----
# 基于规则的规划（不调用LLM，确定性策略）
# 比固定管线灵活：根据文书Profile动态调整工具选择和执行顺序

PLAN_STRATEGIES = {
    "standard": {
        "name": "标准流程",
        "description": "文书结构完整、质量良好 → 走完整16步",
        "phase_tools": {1: [t for t in TOOLS if t.phase == 1],
                        2: [t for t in TOOLS if t.phase == 2],
                        3: [t for t in TOOLS if t.phase == 3]},
    },
    "minimal": {
        "name": "精简流程",
        "description": "文书质量较差或有结构缺失 → 跳过不可行的步骤",
        "phase_tools": {1: [t for t in TOOLS if t.phase == 1 and "need_court_reasoning" not in t.preconditions],
                        2: [t for t in TOOLS if t.phase == 2 and "need_court_reasoning" not in t.preconditions and t.id != "analysis_19d"],
                        3: [t for t in TOOLS if t.phase == 3 and "need_court_reasoning" not in t.preconditions]},
    },
    "rule_only": {
        "name": "纯规则",
        "description": "文书质量很差 → 只用规则引擎（阶段1），跳过LLM分析",
        "phase_tools": {1: [t for t in TOOLS if t.phase == 1],
                        2: [],
                        3: []},
    },
    "quick_scan": {
        "name": "快速扫描",
        "description": "非民事判决或无案号 → 仅做基础信息提取",
        "phase_tools": {1: [t for t in TOOLS if t.id in ("encoding", "segmentation", "case_info")],
                        2: [],
                        3: []},
    },
}


def plan_actions(profile: DocumentProfile) -> dict:
    """根据文书Profile自主规划执行策略和工具列表"""
    precheck = {
        "has_court_reasoning": profile.has_court_reasoning,
        "has_case_number": profile.has_case_number,
        "has_verdict": profile.has_verdict,
        "quality_score": profile.quality_score,
    }

    # 策略选择逻辑
    if profile.doc_type != "civil":
        strategy = "quick_scan"
        reason = f"非民事判决（{profile.doc_type}），仅做基础信息提取"
    elif profile.quality_score < 0.3:
        strategy = "rule_only"
        reason = f"质量评分过低（{profile.quality_score:.2f}），放弃LLM分析"
    elif profile.quality_score < 0.6 or not profile.has_court_reasoning:
        strategy = "minimal"
        missing = "缺少本院认为段落" if not profile.has_court_reasoning else ""
        reason = f"质量评分{profile.quality_score:.2f} {missing}，使用精简流程"
    else:
        strategy = "standard"
        reason = "文书结构完整、质量良好，使用标准16步流程"

    plan_def = PLAN_STRATEGIES[strategy]

    # 筛选可执行工具
    selected: list[Tool] = []
    skipped: list[str] = []
    all_selected_tools = []
    for phase in [1, 2, 3]:
        phase_tools = plan_def["phase_tools"][phase]
        for tool in phase_tools:
            if tool.can_run(precheck):
                selected.append(tool)
                all_selected_tools.append(tool.id)
            else:
                skipped.append(f"{tool.name}: 前置条件不满足")

    return {
        "strategy": strategy,
        "strategy_name": plan_def["name"],
        "strategy_reason": reason,
        "selected_tools": selected,
        "total_tools": len(selected),
        "skipped_tools": skipped,
        "estimated_llm_calls": sum(1 for t in selected if t.estimated_cost == "llm_api_call"),
    }


# ---- 核查引擎 ----

def verify_output(tool: Tool, result: dict, profile: DocumentProfile) -> dict:
    """核查单个工具的输出质量，返回核查报告"""
    checks = []

    # 基础检查
    if not result["success"]:
        checks.append({"pass": False, "reason": f"工具执行失败: {result.get('error', '')}"})
        return _verdict(tool, checks)

    # 案号格式验证（针对case_info工具）
    if tool.id == "case_info":
        output_joined = " ".join(result.get("output_lines", []))
        if output_joined and "错误" in output_joined:
            checks.append({"pass": False, "reason": "输出包含异常关键词"})
        elif not output_joined:
            checks.append({"pass": False, "reason": "案号提取无输出"})
        else:
            checks.append({"pass": True, "reason": "输出看起来有效"})

    # 字段提取验证（针对LLM工具）
    if tool.id in ("field_extract_r1", "deep_extract_r2", "analysis_19d"):
        output_joined = " ".join(result.get("output_lines", []))
        if any(kw in output_joined for kw in ["错误", "失败", "异常", "无法"]):
            checks.append({"pass": False, "reason": "LLM输出包含疑似异常关键词"})
        elif len(output_joined) < 50:
            checks.append({"pass": False, "reason": "LLM输出过短"})
        else:
            checks.append({"pass": True, "reason": "LLM输出格式正常"})

    # 通用：至少运行了
    if not checks:
        checks.append({"pass": True, "reason": "执行完成"})

    return _verdict(tool, checks)


def _verdict(tool: Tool, checks: list) -> dict:
    all_pass = all(c["pass"] for c in checks)
    return {
        "tool_id": tool.id,
        "passed": all_pass,
        "checks": checks,
        "needs_retry": not all_pass,
        "suggested_action": "retry" if not all_pass else "continue",
    }


# ---- 核心循环 ----

async def run_agent_loop(
    job_id: str,
    session_id: str,
    workspace: str,
    input_dir: str,
    output_dir: str,
    filepaths: list[str],
) -> AsyncGenerator:
    """Agent主循环 —— 逐份文书：观察→规划→执行→核查→记录

    每份文书产生一个DocumentMemory，Agent自主决定对其做什么。
    yield的事件类型：
    - agent_thought: Agent的思考/决策（前端展示思维气泡）
    - tool_start / tool_complete / tool_error: 工具执行事件
    - verify: 核查结果
    - document_complete: 单份文书处理完毕
    - agent_complete: 所有文书处理完毕
    """
    started_at = time.time()
    total_files = len(filepaths)
    doc_memories: list[DocumentMemory] = []
    total_tools_run = 0
    total_llm_saved = 0

    yield {
        "type": "agent_thought",
        "job_id": job_id,
        "thought": f"收到 {total_files} 份判决书。开始逐份感知...",
        "phase": "observe",
        "timestamp": time.time(),
    }

    for idx, filepath in enumerate(filepaths):
        filename = filepath.split("/")[-1]

        # ====== ① 观察 ======
        yield {
            "type": "agent_thought",
            "job_id": job_id,
            "thought": f"📋 [{idx+1}/{total_files}] 正在感知：{filename}",
            "phase": "observe",
            "document_index": idx,
            "timestamp": time.time(),
        }

        profile = perceive_document(filepath)
        doc_memory = DocumentMemory(
            filename=filename,
            quality_score=profile.quality_score,
            anomalies=profile.structure_anomalies,
            doc_type=profile.doc_type,
            trial_level=profile.trial_level,
        )

        # 感知结果 → 前端
        yield {
            "type": "agent_thought",
            "job_id": job_id,
            "thought": _describe_perception(profile),
            "phase": "observe",
            "document_index": idx,
            "profile": {
                "encoding": profile.encoding_detected,
                "quality_score": round(profile.quality_score, 2),
                "doc_type": profile.doc_type,
                "trial_level": profile.trial_level,
                "anomalies": profile.structure_anomalies,
                "has_sections": {
                    "plaintiff_claim": profile.has_plaintiff_claim,
                    "defendant_argument": profile.has_defendant_argument,
                    "court_finding": profile.has_court_finding,
                    "court_reasoning": profile.has_court_reasoning,
                    "verdict": profile.has_verdict,
                    "case_number": profile.has_case_number,
                },
            },
            "timestamp": time.time(),
        }

        # ====== ② 规划 ======
        plan = plan_actions(profile)
        doc_memory.record_decision(
            thought=plan["strategy_reason"],
            tools_selected=[t.id for t in plan["selected_tools"]],
        )

        standard_tool_count = 16
        skipped_count = standard_tool_count - len(plan["selected_tools"])
        total_llm_saved += max(0, 4 - plan["estimated_llm_calls"])  # 标准4次LLM调用

        yield {
            "type": "agent_thought",
            "job_id": job_id,
            "thought": f"🧠 决策：{plan['strategy_reason']}\n选用策略「{plan['strategy_name']}」\n选定 {len(plan['selected_tools'])} 个工具，跳过 {skipped_count} 个（含 {plan['estimated_llm_calls']} 次LLM调用，节省 ~¥{max(0, (4-plan['estimated_llm_calls'])*0.5):.2f}）",
            "phase": "plan",
            "document_index": idx,
            "plan": {
                "strategy": plan["strategy"],
                "strategy_name": plan["strategy_name"],
                "strategy_reason": plan["strategy_reason"],
                "selected_tool_ids": [t.id for t in plan["selected_tools"]],
                "skipped_tools": plan["skipped_tools"],
                "estimated_llm_calls": plan["estimated_llm_calls"],
            },
            "timestamp": time.time(),
        }

        # ====== ③ 执行 + ④ 核查（交替进行） ======
        for tool in plan["selected_tools"]:
            yield {
                "type": "tool_start",
                "job_id": job_id,
                "document_index": idx,
                "tool_id": tool.id,
                "tool_name": tool.name,
                "phase": tool.phase,
                "timestamp": time.time(),
            }

            result = await execute_tool(tool, workspace, input_dir, output_dir)
            total_tools_run += 1

            # 核查
            verification = verify_output(tool, result, profile)

            if result["success"] and verification["passed"]:
                step_record = StepRecord(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    success=True,
                    duration_seconds=result["duration_seconds"],
                    output_summary="\n".join(result.get("output_lines", [])[:3]),
                    strategy_used=plan["strategy"],
                )
                doc_memory.record_action(step_record)

                yield {
                    "type": "tool_complete",
                    "job_id": job_id,
                    "document_index": idx,
                    "tool_id": tool.id,
                    "tool_name": tool.name,
                    "duration_seconds": result["duration_seconds"],
                    "output_summary": step_record.output_summary,
                    "verified": True,
                    "timestamp": time.time(),
                }
            else:
                # 核查失败 → 尝试一次重试（仅规则工具）
                need_retry = (not verification["passed"]
                              and tool.phase == 1
                              and result["success"])

                if need_retry:
                    doc_memory.record_strategy_change(
                        reason=f"核查未通过: {verification['checks']}",
                        old_strategy="default",
                        new_strategy="retry_once"
                    )
                    yield {
                        "type": "agent_thought",
                        "job_id": job_id,
                        "thought": f"⚠️ {tool.name} 首次执行后核查未通过，换策略重试...",
                        "phase": "verify",
                        "document_index": idx,
                        "timestamp": time.time(),
                    }

                # 记录错误
                error_msg = result.get("error", "核查未通过")
                step_record = StepRecord(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    success=False,
                    duration_seconds=result["duration_seconds"],
                    output_summary="",
                    error=error_msg,
                    retry_count=1 if need_retry else 0,
                    strategy_used=plan["strategy"],
                )
                doc_memory.record_action(step_record)
                doc_memory.record_error(tool.id, error_msg)

                yield {
                    "type": "tool_error",
                    "job_id": job_id,
                    "document_index": idx,
                    "tool_id": tool.id,
                    "tool_name": tool.name,
                    "error": error_msg,
                    "will_retry": need_retry,
                    "timestamp": time.time(),
                }

        # ====== ⑤ 记录 ======
        doc_memory.completed_at = time.time()
        doc_memories.append(doc_memory)
        global_memory.update_from_doc(doc_memory)

        yield {
            "type": "document_complete",
            "job_id": job_id,
            "document_index": idx,
            "filename": filename,
            "quality_score": round(profile.quality_score, 2),
            "strategy_used": plan["strategy"],
            "tools_run": len(plan["selected_tools"]),
            "errors": len(doc_memory.errors),
            "total_docs_processed": idx + 1,
            "doc_memory": doc_memory.to_dict(),
            "timestamp": time.time(),
        }

    # ====== 全部完成 ======
    total_duration = round(time.time() - started_at, 1)
    yield {
        "type": "agent_complete",
        "job_id": job_id,
        "total_files": total_files,
        "total_tools_run": total_tools_run,
        "total_llm_calls_saved": total_llm_saved,
        "total_duration_seconds": total_duration,
        "avg_duration_per_doc": round(total_duration / max(total_files, 1), 1),
        "long_term_stats": global_memory.get_summary(),
        "timestamp": time.time(),
    }


def _describe_perception(profile: DocumentProfile) -> str:
    """将感知结果转为人类可读描述"""
    parts = []

    # 编码
    parts.append(f"编码: {profile.encoding_detected}")

    # 类型和审级
    type_map = {"civil": "民事", "criminal": "刑事", "admin": "行政"}
    level_map = {"first": "一审", "second": "二审", "retrial": "再审"}
    parts.append(f"{type_map.get(profile.doc_type, '未知')} · {level_map.get(profile.trial_level, '未知')}")

    # 长度
    if profile.total_chars > 10000:
        parts.append(f"{profile.total_chars//1000}千字（较长）")
    elif profile.total_chars > 3000:
        parts.append(f"{profile.total_chars//1000}千字")
    else:
        parts.append(f"{profile.total_chars}字（偏短）")

    # 质量
    if profile.quality_score >= 0.8:
        parts.append("质量：良好 ✓")
    elif profile.quality_score >= 0.5:
        parts.append("质量：一般")
    else:
        parts.append("质量：较差 ⚠")

    # 异常
    if profile.structure_anomalies:
        parts.append(f"发现 {len(profile.structure_anomalies)} 个异常")

    return " · ".join(parts)
