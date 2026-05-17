#!/usr/bin/env python3
"""
Step 12 — 证据类型与裁判说理深度提取
从 round2 + gemini 数据中提取法官认定利润率所依据的证据类型、以及商标贡献率的说理基础。
调用 DeepSeek API 进行二次文本分类与结构化提取。
输出: step006_evidence_reasoning_results.jsonl

改进点（v2.1）:
- API key 硬编码兜底，不再强依赖环境变量
- 重试退避加入随机抖动，避免惊群效应
- JSON 抽取更鲁棒，覆盖更多边界格式
- 响应结构校验，防止畸形 JSON 静默写入
- 降低 MAX_REASONING 到 6000 字符，防止上下文溢出
- 用 asyncio.as_completed + 手动 tqdm 替代脆弱的 tqdm.asyncio API
- 失败日志记录更多诊断信息
"""

import os
import sys
import json
import re
import time
import random
import asyncio
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from tqdm import tqdm

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ── 路径配置 ────────────────────────────────────────────────────────────────
DATA_DIR = Path(_PV2, "input") if _PV2 else Path("/Users/weiyueshao/Desktop/all/clean")
BASE_DIR = Path(_PV2, "_data") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/_data")
ROUND2_PATH = Path(_PV2, "005_data/round2_deep_analysis_results.jsonl") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/005_data/round2_deep_analysis_results.jsonl")
GEMINI_PATH = DATA_DIR / "gemini_upload_case_batch.json"
OUTPUT_PATH = BASE_DIR / "step006_evidence_reasoning_results.jsonl"
ERROR_LOG = BASE_DIR / "step006_error.log"

# ── API 配置 ────────────────────────────────────────────────────────────────
API_KEY = "sk-1e6deae9e49740099c6d2185e7524f97"
API_BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"
TEMPERATURE = 0.0
MAX_TOKENS = 2048
MAX_RETRIES = 5
MAX_CONCURRENT = 8
REQUEST_TIMEOUT = 90
MAX_REASONING_CHARS = 6000  # 从 8000 降到 6000，留足 prompt 空间

SYSTEM_PROMPT = """你是一位拥有15年经验的中国知识产权审判专家，现在需要对中国商标侵权案件的裁判文书说理段落进行精细化的证据类型与说理分析。

请仔细阅读以下裁判文书中的"本院认为"说理段落，并提取以下信息，**严格且仅输出合法的 JSON 格式**（不要有任何 Markdown 标记或额外说明）：

{
  "case_id": "案号字符串",
  "profit_margin_evidence": {
    "evidence_type": "法院认定利润率所依据的具体证据类型（选填以下之一）: 第三方审计/司法会计鉴定 | 上市公司年报/公告 | 税务申报/纳税证明 | 行业统计数据/行业协会数据 | 招股说明书/IPO文件 | 原告单方财务数据 | 举证妨碍推定(被告拒不提供账簿) | 电商平台销售数据 | 综合酌定/未明确具体证据 | 其他",
    "evidence_detail": "对证据的简要描述（1-2句话概括），例如'法院采信了原告提交的审计报告中的12.6%营业利润率'或'法院认为原告举证不足因此综合酌定'",
    "court_adopted_specific_value": true 或 false（法院是否采信了具体的百分比数值）"
  },
  "contribution_rate_reasoning": {
    "reasoning_basis": "法院论证商标贡献率的说理基础（选填以下之一）: 商标知名度/市场声誉 | 侵权人主观过错程度 | 产品自身固有价值/技术贡献分离 | 侵权规模/持续时间 | 消费者认知/市场调查 | 多因素综合酌定但未量化 | 完全未提及商标贡献率 | 其他",
    "reasoning_detail": "对说理逻辑的简要描述（1-2句话概括），例如'法院指出购买工业设备时消费者更看重技术参数而非品牌，故对商标贡献率进行了大幅限制'",
    "court_adopted_specific_contribution": true 或 false（法院是否采信了具体的贡献率百分比数值）"
  },
  "judicial_discretion_level": "高度依赖法定赔偿/酌定 | 部分参考经济数据 | 完全基于精确经济数据"
}

如果原文中没有相关信息，对应字段填 null。
如果原文中没有提供足够的'本院认为'文本或说理内容太少无法判断，evidence_type 填 '信息不足无法判断'。
"""

# ── 必需字段校验 ────────────────────────────────────────────────────────────
REQUIRED_TOP_KEYS = ["profit_margin_evidence", "contribution_rate_reasoning", "judicial_discretion_level"]


# ── 数据加载 ────────────────────────────────────────────────────────────────
def load_round2_data(path: Path) -> dict:
    """加载 round2 深度分析结果，返回 {case_id: record} 字典。"""
    data = {}
    if not path.exists():
        print(f"警告: 找不到 {path}")
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                cid = rec.get("case_id", "")
                if cid:
                    data[cid] = rec
            except json.JSONDecodeError:
                continue
    return data


def load_gemini_data(path: Path) -> dict:
    """加载 gemini 上传批次数据，返回 {case_id: record} 字典。"""
    data = {}
    if not path.exists():
        print(f"警告: 找不到 {path}")
        return data
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for rec in raw:
        cid = rec.get("case_id", "")
        if cid:
            data[cid] = rec
    return data


def load_processed_ids(path: Path) -> set:
    """加载已处理的 case_id 用于断点续传。"""
    processed = set()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    cid = rec.get("case_id", "")
                    if cid:
                        processed.add(cid)
                except json.JSONDecodeError:
                    continue
    return processed


# ── JSON 抽取（改进版）───────────────────────────────────────────────────────
def extract_json(text: str) -> Optional[dict]:
    """从 API 响应中鲁棒提取 JSON，覆盖多种边界格式。"""
    if not text:
        return None
    text = text.strip()

    # 1) 清理 markdown 代码块（支持无语言标记、带 json 标记、多余空白）
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    # 2) 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3) 尝试修复常见问题：尾部多余逗号
    text_fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(text_fixed)
    except json.JSONDecodeError:
        pass

    # 4) 提取最外层大括号块（贪婪）
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidate = brace.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            candidate_fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(candidate_fixed)
            except json.JSONDecodeError:
                pass

    # 5) 尝试提取多个可能的 JSON 块中第一个合法的
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

    return None


def validate_result(data: dict) -> bool:
    """校验 API 返回的 JSON 是否包含必需字段。"""
    if not isinstance(data, dict):
        return False
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            return False
    return True


# ── API 调用（改进版）────────────────────────────────────────────────────────
async def call_api(
    client: AsyncOpenAI,
    sem: asyncio.Semaphore,
    case_id: str,
    reasoning_text: str,
    round2_data: Optional[dict],
) -> Optional[dict]:
    """调用 DeepSeek API 进行证据类型与说理分析。"""
    context_parts = [f"案号: {case_id}"]
    if round2_data:
        pm = round2_data.get("profit_margin_data", {}) or {}
        cr = round2_data.get("contribution_rate_data", {}) or {}
        if pm.get("court_adopted_margin"):
            context_parts.append(f"系统已提取的法院采信利润率: {pm['court_adopted_margin']}")
        if pm.get("margin_source_quote"):
            context_parts.append(f"利润率相关原文引用: {pm['margin_source_quote'][:500]}")
        if cr.get("court_adopted_contribution"):
            context_parts.append(f"系统已提取的法院采信贡献率: {cr['court_adopted_contribution']}")
        if cr.get("contribution_source_quote"):
            context_parts.append(f"贡献率相关原文引用: {cr['contribution_source_quote'][:500]}")

    reasoning_section = (
        reasoning_text[:MAX_REASONING_CHARS] if reasoning_text else "（无'本院认为'说理文本）"
    )

    user_message = (
        f"{chr(10).join(context_parts)}\n\n"
        f"=== 裁判文书'本院认为'说理段落 ===\n{reasoning_section}"
    )

    async with sem:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    timeout=REQUEST_TIMEOUT,
                )
                raw = response.choices[0].message.content
                data = extract_json(raw)
                if data is None:
                    tqdm.write(
                        f"  [{case_id}] JSON parse failed (attempt {attempt+1}), "
                        f"raw preview: {raw[:300].replace(chr(10), ' ')}"
                    )
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 * (2 ** attempt) + random.uniform(0, 1))
                        continue
                    return None

                if not validate_result(data):
                    tqdm.write(
                        f"  [{case_id}] Response missing required keys (attempt {attempt+1}): "
                        f"got keys={list(data.keys())[:10]}"
                    )
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 * (2 ** attempt) + random.uniform(0, 1))
                        continue
                    return None

                return data

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                wait = 2 * (2 ** attempt) + random.uniform(0, 2)
                tqdm.write(
                    f"  [{case_id}] {type(e).__name__}, "
                    f"retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s"
                )
                await asyncio.sleep(wait)

            except APIError as e:
                if e.status_code in (429, 503) or e.status_code >= 500:
                    wait = 2 * (2 ** attempt) + random.uniform(0, 2)
                    tqdm.write(
                        f"  [{case_id}] HTTP {e.status_code}, "
                        f"retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    tqdm.write(f"  [{case_id}] API error {e.status_code}: {e}")
                    return None

            except Exception as e:
                wait = 2 * (2 ** attempt) + random.uniform(0, 2)
                tqdm.write(
                    f"  [{case_id}] Error (attempt {attempt+1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

    return None


# ── 主流程 ──────────────────────────────────────────────────────────────────
async def main_async():
    api_key = os.environ.get("DEEPSEEK_API_KEY") or API_KEY

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=API_BASE_URL,
        timeout=REQUEST_TIMEOUT,
    )

    print("=" * 60)
    print("Step 12: 证据类型与裁判说理深度提取 (v2.1)")
    print("=" * 60)

    # 加载数据
    print("\n[1/4] 加载数据...")
    round2_data = load_round2_data(ROUND2_PATH)
    gemini_data = load_gemini_data(GEMINI_PATH)
    processed_ids = load_processed_ids(OUTPUT_PATH)

    all_case_ids = set(round2_data.keys()) | set(gemini_data.keys())
    print(f"  round2 案件数: {len(round2_data)}")
    print(f"  gemini 案件数: {len(gemini_data)}")
    print(f"  合并后唯一 case_id: {len(all_case_ids)}")
    print(f"  已处理: {len(processed_ids)}")

    # 构建待处理列表
    pending = []
    skip_no_text = 0
    for cid in sorted(all_case_ids):
        if cid in processed_ids:
            continue
        gemini_rec = gemini_data.get(cid, {})
        reasoning_text = (
            gemini_rec.get("reasoning_text", "") if isinstance(gemini_rec, dict) else ""
        )
        round2_rec = round2_data.get(cid)

        has_reasoning = bool(reasoning_text and len(reasoning_text.strip()) > 20)
        has_margin_data = False
        if round2_rec:
            pm = round2_rec.get("profit_margin_data", {}) or {}
            cr = round2_rec.get("contribution_rate_data", {}) or {}
            has_margin_data = bool(
                pm.get("court_adopted_margin")
                or pm.get("margin_source_quote")
                or cr.get("court_adopted_contribution")
                or cr.get("contribution_source_quote")
            )

        if has_reasoning or has_margin_data:
            pending.append((cid, reasoning_text, round2_rec))
        else:
            skip_no_text += 1

    print(f"  待处理: {len(pending)}")
    print(f"  跳过(无有效文本): {skip_no_text}")

    if not pending:
        print("所有案件已处理完毕。")
        return

    # 处理
    print(f"\n[2/4] 开始调用 DeepSeek API (并发={MAX_CONCURRENT})...")
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    out_lock = asyncio.Lock()
    success_count = 0
    error_count = 0
    start_time = time.time()

    out_f = open(OUTPUT_PATH, "a", encoding="utf-8")
    err_f = open(ERROR_LOG, "a", encoding="utf-8")

    async def process_one(case_id: str, reasoning_text: str, round2_rec: Optional[dict]):
        nonlocal success_count, error_count

        result = await call_api(client, sem, case_id, reasoning_text, round2_rec)

        if result is None:
            async with out_lock:
                err_f.write(
                    json.dumps(
                        {
                            "case_id": case_id,
                            "error": "API_FAILED",
                            "reasoning_len": len(reasoning_text) if reasoning_text else 0,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                err_f.flush()
            error_count += 1
            return

        result["case_id"] = case_id
        if round2_rec:
            result["_round2_profit_margin"] = round2_rec.get("profit_margin_data")
            result["_round2_contribution"] = round2_rec.get("contribution_rate_data")

        async with out_lock:
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()
        success_count += 1

    # 使用 asyncio.as_completed + 手动 tqdm，避免 tqdm.asyncio API 兼容问题
    pbar = tqdm(total=len(pending), desc="Analyzing", unit="case")
    tasks = [
        asyncio.ensure_future(process_one(cid, rt, r2r)) for cid, rt, r2r in pending
    ]

    for coro in asyncio.as_completed(tasks):
        await coro
        pbar.update(1)

    pbar.close()
    out_f.close()
    err_f.close()

    elapsed = time.time() - start_time
    print(f"\n[3/4] 处理完成: 成功 {success_count}, 失败 {error_count}")
    print(f"  耗时: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    if len(pending) > 0:
        print(f"  平均每案件: {elapsed/len(pending):.1f}s")
    print(f"  输出文件: {OUTPUT_PATH}")

    # 统计摘要
    print(f"\n[4/4] 证据类型分布摘要:")
    evidence_counts = {}
    reasoning_counts = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pm = rec.get("profit_margin_evidence", {}) or {}
                et = pm.get("evidence_type", "unknown")
                evidence_counts[et] = evidence_counts.get(et, 0) + 1

                cr = rec.get("contribution_rate_reasoning", {}) or {}
                rb = cr.get("reasoning_basis", "unknown")
                reasoning_counts[rb] = reasoning_counts.get(rb, 0) + 1

    print("\n  利润率证据类型:")
    for k, v in sorted(evidence_counts.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")
    print("\n  贡献率说理基础:")
    for k, v in sorted(reasoning_counts.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")

    print("\n" + "=" * 60)
    print("Step 12 完成。")
    print("=" * 60)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
