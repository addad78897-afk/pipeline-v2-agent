#!/usr/bin/env python3
"""Batch extract structured data from court judgment documents using DeepSeek API (OpenAI SDK)."""

import os
import json
import re
import asyncio
import sys
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from tqdm.asyncio import tqdm

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ── Configuration ────────────────────────────────────────────────────────
CASE_DIR = _os.path.join(_PV2, "input") if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/003_案例"
OUTPUT_FILE = _os.path.join(_PV2, "005_data/round1_output.jsonl") if _PV2 else _os.path.join("/Users/weiyueshao/Desktop/pipeline_v2", "005_data/round1_output.jsonl")
ERROR_LOG = _os.path.join(_PV2, "005_data/error_log.txt") if _PV2 else _os.path.join("/Users/weiyueshao/Desktop/pipeline_v2", "005_data/error_log.txt")

MODEL = "deepseek-chat"                  # 修正：官方模型名
TEMPERATURE = 0.0
MAX_TOKENS = 1500
MAX_RETRIES = 6
MAX_CONCURRENT = 8                       # 并发请求数（v2.0优化: 5→8, ~120RPM）
REQUEST_TIMEOUT = 90                     # 秒
MAX_INPUT_CHARS = 40000                  # 截断长文书，保留上下文窗口余量

SYSTEM_PROMPT = """你是一位拥有10年经验的中国知识产权高级法官兼司法大数据分析专家。你的任务是绝对客观地从裁判文书中提取事实，严禁任何推理、联想或编造。
请仔细阅读判决书，提取以下信息，并**严格且仅输出合法的 JSON 格式**（不要有任何 Markdown 标记或额外说明）：
{
  "case_id": "案号字符串，未提及则为 null",
  "industry_category": "涉案商品或服务所属的具体行业，未提及则为 null",
  "plaintiff_claimed_amount": 原告主张的经济损失赔偿金额（纯数字，精确到元），未提及则为 null,
  "court_awarded_amount": 法院最终支持的经济损失赔偿金额（纯数字，精确到元，不含合理开支），未提及则为 null,
  "compensation_method": "法院采用的赔偿计算法定顺位（选填：实际损失 / 侵权获利 / 许可费倍数 / 法定赔偿 / 惩罚性赔偿）。关键区分：侵权获利=法院沿用了'销售额×利润率'公式框架（即使部分参数酌定）；法定赔偿=法院未使用任何计算公式，直接依据商标法第63条第3款在500万元以下酌定。未提及则为 null",
  "profit_margin_mentioned": true 或 false (判决书中是否明确提及了"利润率"、"毛利率"或"净利率"),
  "contribution_rate_mentioned": true 或 false (判决书中是否明确提及了"商标贡献率"、"品牌价值占比"或类似概念)
}
如果原文没有明确数据，对应字段必须严格填 null。"""

# ── Helpers ───────────────────────────────────────────────────────────────
def load_processed_files(output_path):
    processed = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    fname = record.get("source_file")
                    if fname:
                        processed.add(fname)
                except json.JSONDecodeError:
                    continue
    return processed

def collect_txt_files(case_dir):
    txt_files = []
    for root, dirs, files in os.walk(case_dir):
        for fname in files:
            if fname.endswith(".txt"):
                txt_files.append(os.path.join(root, fname))
    return sorted(txt_files)

def extract_json(text):
    text = text.strip()
    fence_pattern = r"```(?:json)?\s*(.*?)```"
    m = re.search(fence_pattern, text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None

# ── Async API call (OpenAI style) ────────────────────────────────────────
async def call_api(client, sem, file_content, file_name):
    """使用 OpenAI SDK 调用 DeepSeek API，带信号量和重试"""
    truncated = file_content[:MAX_INPUT_CHARS]
    user_message = f"请提取以下裁判文书的数据：\n\n{truncated}"
    for attempt in range(MAX_RETRIES):
        async with sem:
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    timeout=REQUEST_TIMEOUT,
                )
                raw_text = response.choices[0].message.content
                data = extract_json(raw_text)
                if data is None:
                    raise ValueError(f"JSON parse failed, raw: {raw_text[:200]}")
                return data

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                wait = 2 * (2 ** attempt)
                tqdm.write(f"  [{file_name}] {type(e).__name__}, retry {attempt+1}/{MAX_RETRIES} in {wait}s")

            except APIError as e:
                if e.status_code in (503,) or e.status_code >= 500:
                    wait = 2 * (2 ** attempt)
                    tqdm.write(f"  [{file_name}] HTTP {e.status_code}, retry {attempt+1}/{MAX_RETRIES} in {wait}s")
                else:
                    tqdm.write(f"  [{file_name}] API error {e.status_code}: {e}")
                    return None

            except Exception as e:
                wait = 2 * (2 ** attempt)
                tqdm.write(f"  [{file_name}] Unexpected error, retry {attempt+1}/{MAX_RETRIES} in {wait}s: {e}")

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(wait)

    return None

# ── Main async logic ─────────────────────────────────────────────────────
async def main_async():
    # 从环境变量读取 DeepSeek API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY environment variable not set.")
        print("Please run: export DEEPSEEK_API_KEY='sk-...'")
        sys.exit(1)

    # 使用 OpenAI SDK，base_url 指向 DeepSeek 官方端点
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",   # DeepSeek 官方端点
        timeout=REQUEST_TIMEOUT,
    )

    processed = load_processed_files(OUTPUT_FILE)
    print(f"Already processed files: {len(processed)}")

    all_files = collect_txt_files(CASE_DIR)
    print(f"Total .txt files found: {len(all_files)}")

    pending = [f for f in all_files if os.path.basename(f) not in processed]
    print(f"Pending files: {len(pending)}")

    if not pending:
        print("All files already processed. Exiting.")
        return

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    out_lock = asyncio.Lock()
    success_count = 0
    error_count = 0

    out_file = open(OUTPUT_FILE, "a", encoding="utf-8")

    try:
        async def process_one(file_path):
            nonlocal success_count, error_count
            file_name = os.path.basename(file_path)

            # 异步读取文件内容
            try:
                loop = asyncio.get_running_loop()
                content = await loop.run_in_executor(
                    None, lambda: open(file_path, "r", encoding="utf-8").read()
                )
            except Exception as e:
                tqdm.write(f"  [{file_name}] READ ERROR: {e}")
                async with out_lock:
                    with open(ERROR_LOG, "a", encoding="utf-8") as ef:
                        ef.write(f"{file_name}\tREAD_ERROR\t{str(e)}\n")
                error_count += 1
                return

            if not content.strip():
                return

            data = await call_api(client, sem, content, file_name)

            if data is None:
                tqdm.write(f"  [{file_name}] FAILED after {MAX_RETRIES} retries")
                async with out_lock:
                    with open(ERROR_LOG, "a", encoding="utf-8") as ef:
                        ef.write(f"{file_name}\tAPI_FAILED\tafter {MAX_RETRIES} retries\n")
                error_count += 1
                return

            data["source_file"] = file_name
            async with out_lock:
                out_file.write(json.dumps(data, ensure_ascii=False) + "\n")
                out_file.flush()
            success_count += 1

            # 可选的小延迟，降低 API 压力
            await asyncio.sleep(0.5)

        # 并发执行所有任务
        tasks = [asyncio.create_task(process_one(fp)) for fp in pending]
        for coro in tqdm.as_completed(tasks, total=len(pending), desc="Processing", unit="file"):
            await coro

        print(f"\nDone. Success: {success_count}, Errors: {error_count}")
        if error_count > 0:
            print(f"See {ERROR_LOG} for details on failed files.")
    finally:
        out_file.close()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
