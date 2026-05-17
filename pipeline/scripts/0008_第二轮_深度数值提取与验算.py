#!/usr/bin/env python3
"""
round2_deepcode_refinement.py
深度数值提取与数学校验 -- 针对 round1 中筛选出的高价值案件
调用 DeepSeek API，提取利润率/贡献率并做数学逻辑验证。
输出: round2_output.jsonl + round2_analysis_report.csv
"""

import json
import os
import re
import sys
import time
import csv
import logging
from pathlib import Path
from typing import Optional

import openai
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ── 配置 ──────────────────────────────────────────────
BASE_DIR_002 = Path(_PV2, "input") if _PV2 else Path("/Users/weiyueshao/Desktop/all/clean")  # inputs
BASE_OUT_002 = Path(_PV2, "_data") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/_data")  # outputs
ROUND1_PATH = str(BASE_DIR_002 / "round1_case_extraction_results.jsonl")
CASE_DIR    = Path(_PV2, "input") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/003_案例")
OUTPUT_JSONL = BASE_OUT_002 / "round2_deep_analysis_results.jsonl"
OUTPUT_CSV   = BASE_OUT_002 / "round2_deep_analysis_report.csv"
ERROR_LOG    = BASE_OUT_002 / "round2_error.log"

MODEL_NAME = "deepseek-chat"   # DeepSeek 推理模型
TEMPERATURE = 0.0
MAX_RETRIES = 5
BASE_DELAY = 2  # seconds base for exponential backoff
MAX_CHUNK_CHARS = 8000  # max chars extracted from case file
MAX_CONCURRENT_002 = 3   # v2.0优化: 从sequential改为3线程并发

# ── API 客户端（延迟初始化） ─────────────────────────────
_client = None  # type: Optional[openai.OpenAI]


def get_client() -> openai.OpenAI:
    """延迟初始化 DeepSeek API 客户端，优先从环境变量读取 API Key。"""
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量未设置。"
            "请运行: export DEEPSEEK_API_KEY=sk-xxx"
        )
    _client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    return _client

# ── 日志 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ERROR_LOG, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# ── 系统 Prompt ───────────────────────────────────────
SYSTEM_PROMPT = """你是一位精通财务精算与知识产权损害赔偿计算的高级法官。你的任务是提取商标侵权赔偿计算中的关键费率，并进行绝对客观的逻辑校验。
请严格从输入的裁判文书段落中提取以下信息，并**仅输出合法的 JSON 格式**（不要包含任何代码块符号 ```json 或额外的说明文字）：

{
  "case_id": "填入文书案号",
  "profit_margin_data": {
    "claimed_margin": "原告主张的利润率数值（仅保留数字和%，如 35%）。未提及填 null",
    "court_adopted_margin": "法院最终采信的利润率数值（如 20%）。如果法院未采信具体数值而是说明综合考量或酌定，必须严格填入 '酌定'。未提及填 null",
    "margin_source_quote": "提取得出上述数值的原文片段原话，不多加一个字。未提及填 null"
  },
  "contribution_rate_data": {
    "claimed_contribution": "原告主张的商标贡献率（如 50%）。未提及填 null",
    "court_adopted_contribution": "法院最终采信的商标贡献率。如果未采信具体数值而是酌定，必须严格填入 '酌定'。未提及填 null",
    "contribution_source_quote": "提取得出上述数值的原文片段原话，不多加一个字。未提及填 null"
  },
  "logic_check": {
    "found_revenue": "判决书中明确记录的涉案商品销售额或营业额（纯数字）。未提及填 null",
    "found_awarded_amount": "判决书中明确记录的最终判赔金额（纯数字）。",
    "validation_result": "如果法院采信了具体的销售额、利润率和贡献率数值，执行以下验证：计算判赔额 = 销售额 × 利润率 × 贡献率。比较计算判赔额与实际判赔额之间的偏差率 = |计算判赔额 - 实际判赔额| / 实际判赔额。如果偏差率 ≤ 15%，输出 'logic_consistent'（司法实践中，法官通常会在公式计算结果之上叠加合理维权开支（律师费/公证费/购买取证费用等）并对总额取整处理（如300542元取整为300000元），因此 ±15% 以内的偏差应视为逻辑自洽而非计算错误）；如果偏差率在 15%-20% 之间，输出 'near_match'（可能因维权开支叠加或取整导致，需在explanation中注明可能原因）；如果偏差率 > 20%，输出 'mismatch'（显著偏离，存在其他未观测的裁量因素）；如果上述三个数值有任何一个缺失或为'酌定'导致无法计算，输出 'insufficient_data'。",
    "logic_explanation": "简要解释验证结果的原因。例如：'计算判赔额=X元，实际判赔Y元，偏差Z%，在±15%容忍区间内，判定为逻辑自洽'，或 '计算判赔额=X元，实际判赔Y元，偏差Z%，可能叠加了维权合理开支及法官取整处理'，或 '利润率为酌定，无法进行数学验算'。务必标出偏差率的百分比值。"
  }
}"""


# ── 文本截取逻辑 ──────────────────────────────────────
def extract_relevant_text(full_text: str, max_chars: int = MAX_CHUNK_CHARS) -> str:
    """
    从判决书全文中截取关键段落：本院查明 + 本院认为 + 裁判结果
    策略：先定位三个段落起始标记，然后截取合并，超过 max_chars 时截断。
    """
    # 清理多余空白（保留中文段落格式）
    text = full_text.strip()

    # 定义各段落的起始关键词（按优先级排列）
    section_markers = [
        # (正则匹配模式, 段落标签)
        (r'(本院查明|经审理查明|一审查明|原审查明)', "查明事实"),
        (r'(本院认为|本院经审查认为)', "本院认为"),
        (r'(裁判结果|判决如下)', "判决结果"),
    ]

    sections = []
    for pattern, label in section_markers:
        match = re.search(pattern, text)
        if match:
            start = match.start()
            # 从该标记开始截取到下一个大段落或文末
            # 找一个合理截断点：下一个 section marker 或 "审判长|审判员|落款|书记员"
            remaining = text[start:]
            end_match = re.search(
                r'\n\s*(审判长|审判员|审 判 员|落款|书 记 员|书记员|合议庭|【法宝引证码】)',
                remaining[10:],  # 跳过标记本身避免误匹配
            )
            if end_match:
                chunk = remaining[: 10 + end_match.start()]
            else:
                chunk = remaining
            sections.append((label, chunk))

    if not sections:
        # 回退：找不到标准段落标记时，截取文本中间部分（通常包含核心事实）
        mid_start = max(0, len(text) // 5)
        return text[mid_start: mid_start + max_chars]

    # 合并三个段落
    combined = "\n\n".join(f"=== {label} ===\n{chunk}" for label, chunk in sections)

    # 如过长则截断（优先保留后面的段落）
    if len(combined) > max_chars:
        # 保留每个段落的前面部分，按比例分配
        per_section = max_chars // len(sections)
        truncated = []
        for label, chunk in sections:
            truncated.append(f"=== {label} ===\n{chunk[:per_section]}")
        combined = "\n\n".join(truncated)

    return combined


# ── API 调用 + 指数退避 ──────────────────────────────
def call_deepseek(case_id: str, case_text: str) -> Optional[dict]:
    """
    调用 DeepSeek API 进行分析。失败返回 None。
    """
    user_msg = f"案号: {case_id}\n\n裁判文书段落:\n{case_text}"

    for attempt in range(MAX_RETRIES):
        try:
            response = get_client().chat.completions.create(
                model=MODEL_NAME,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=4096,
            )

            raw_content = response.choices[0].message.content.strip()

            # 清理可能的 markdown 代码块包装
            if raw_content.startswith("```"):
                raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
                raw_content = re.sub(r"\s*```$", "", raw_content)

            result = json.loads(raw_content)
            return result

        except json.JSONDecodeError as e:
            logger.warning(
                "case_id=%s attempt=%d JSON parse error: %s, raw=%s",
                case_id, attempt + 1, e, raw_content[:200]
            )
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(BASE_DELAY * (2 ** attempt))

        except openai.RateLimitError as e:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(
                "case_id=%s attempt=%d Rate limited: %s, retry in %ds",
                case_id, attempt + 1, e, delay
            )
            time.sleep(delay)

        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(
                "case_id=%s attempt=%d API error: %s, retry in %ds",
                case_id, attempt + 1, e, delay
            )
            time.sleep(delay)

        except Exception as e:
            logger.error("case_id=%s attempt=%d Unexpected error: %s", case_id, attempt + 1, e)
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(BASE_DELAY * (2 ** attempt))

    return None


# ── JSON 扁平化 ───────────────────────────────────────
def flatten_result(result: dict) -> dict:
    """
    将嵌套的 API 返回结果扁平化为一层 dict，适合 CSV 输出。
    """
    flat = {}
    flat["case_id"] = result.get("case_id", "")

    pm = result.get("profit_margin_data", {}) or {}
    flat["claimed_margin"] = pm.get("claimed_margin")
    flat["court_adopted_margin"] = pm.get("court_adopted_margin")
    flat["margin_source_quote"] = pm.get("margin_source_quote")

    cr = result.get("contribution_rate_data", {}) or {}
    flat["claimed_contribution"] = cr.get("claimed_contribution")
    flat["court_adopted_contribution"] = cr.get("court_adopted_contribution")
    flat["contribution_source_quote"] = cr.get("contribution_source_quote")

    lc = result.get("logic_check", {}) or {}
    flat["found_revenue"] = lc.get("found_revenue")
    flat["found_awarded_amount"] = lc.get("found_awarded_amount")
    flat["validation_result"] = lc.get("validation_result")
    flat["logic_explanation"] = lc.get("logic_explanation")

    return flat


# ── CSV 列定义 ────────────────────────────────────────
CSV_COLUMNS = [
    "case_id",
    "claimed_margin",
    "court_adopted_margin",
    "margin_source_quote",
    "claimed_contribution",
    "court_adopted_contribution",
    "contribution_source_quote",
    "found_revenue",
    "found_awarded_amount",
    "validation_result",
    "logic_explanation",
]


# ── 主流程 ─────────────────────────────────────────────
def main():
    # 1. 读取 round1_output.jsonl 并过滤
    print("=" * 60)
    print("📋 步骤 1/4: 加载 round1 数据并筛选高价值案件...")
    candidates = []  # list of dicts with round1 metadata

    with open(ROUND1_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("profit_margin_mentioned") is True or rec.get("contribution_rate_mentioned") is True:
                candidates.append(rec)

    total_candidates = len(candidates)
    print(f"✅ 共发现 {total_candidates} 个需要进行二次校验的高价值案件")

    # 2. 断点续传: 加载已处理的 case_id
    print(f"\n📋 步骤 2/4: 检测断点续传状态...")
    processed_ids = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    cid = rec.get("case_id", "")
                    if cid:
                        processed_ids.add(cid)
                except json.JSONDecodeError:
                    pass
        print(f"   已处理 {len(processed_ids)} 条记录，将跳过这些 case")
    else:
        print("   首次运行，无断点数据")

    # 是否需要初始化 CSV 头部
    csv_exists = OUTPUT_CSV.exists()

    # 3. 逐条处理
    print(f"\n📋 步骤 3/4: 开始调用 DeepSeek API 进行深度分析...")
    success_count = 0
    skip_count = 0
    error_count = 0

    # 过滤掉已处理的
    pending = [c for c in candidates if c.get("case_id", "") not in processed_ids]
    print(f"   待处理: {len(pending)} / 总计: {total_candidates}")

    # 打开输出文件（追加模式）+ 线程锁
    jsonl_f = open(OUTPUT_JSONL, "a", encoding="utf-8")
    csv_f = open(OUTPUT_CSV, "a", encoding="utf-8", newline="")
    csv_writer = csv.DictWriter(csv_f, fieldnames=CSV_COLUMNS)
    write_lock = threading.Lock()

    if not csv_exists:
        csv_writer.writeheader()

    def process_one(rec):
        """单案件处理函数（线程安全）。"""
        case_id = rec.get("case_id", "unknown")
        source_file = rec.get("source_file", "")

        if case_id in processed_ids:
            return ("skip", None)

        txt_path = CASE_DIR / source_file
        if not txt_path.exists():
            logger.warning("case_id=%s source_file not found: %s", case_id, source_file)
            return ("error", None)

        try:
            full_text = txt_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("case_id=%s read error: %s", case_id, e)
            return ("error", None)

        extracted_text = extract_relevant_text(full_text)
        result = call_deepseek(case_id, extracted_text)

        if result is None:
            logger.error("case_id=%s FAILED after %d retries", case_id, MAX_RETRIES)
            return ("error", None)

        flat = flatten_result(result)
        return ("success", {"jsonl": result, "csv": flat, "case_id": case_id})

    try:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_002) as executor:
            futures = {executor.submit(process_one, rec): rec for rec in pending}

            pbar = tqdm(as_completed(futures), total=len(pending),
                       desc="DeepSeek 分析", unit="case", ncols=100)

            for future in pbar:
                status, data = future.result()

                if status == "skip":
                    skip_count += 1
                elif status == "error":
                    error_count += 1
                elif status == "success":
                    with write_lock:
                        jsonl_f.write(json.dumps(data["jsonl"], ensure_ascii=False) + "\n")
                        jsonl_f.flush()
                        csv_writer.writerow(data["csv"])
                        csv_f.flush()
                    success_count += 1
                    processed_ids.add(data["case_id"])

                pbar.set_postfix(success=success_count, errors=error_count)

    finally:
        jsonl_f.close()
        csv_f.close()

    # 4. 汇总
    print(f"\n📋 步骤 4/4: 执行完毕，汇总统计")
    print("=" * 60)
    print(f"   总候选案件:     {total_candidates}")
    print(f"   断点跳过:       {skip_count}")
    print(f"   成功处理:       {success_count}")
    print(f"   处理失败:       {error_count}")
    print(f"   累计已完成:     {len(processed_ids) + success_count - skip_count}")
    print(f"   JSONL 输出:     {OUTPUT_JSONL}")
    print(f"   CSV 输出:       {OUTPUT_CSV}")
    print(f"   错误日志:       {ERROR_LOG}")
    print("=" * 60)


if __name__ == "__main__":
    main()
