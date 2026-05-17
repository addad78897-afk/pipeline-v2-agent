"""
Step 10: 多维度 AI 分析
从 round2 标注结果 + round1 基础数据 + 判决书原文出发，产出 19 个维度综合分析 CSV。
程序化维度（12个）+ AI 分类维度（7个）= 19 个维度。
"""

import csv
import json
import os
import re
import time
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ============================================================================
# 配置
# ============================================================================
API_KEY = "sk-1e6deae9e49740099c6d2185e7524f97"
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

ROUND2_INPUT = _os.path.join(_PV2, "005_data/round2_deep_analysis_results.jsonl") if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/005_data/round2_deep_analysis_results.jsonl"
ROUND1_INPUT = _os.path.join(_PV2, "005_data/round1_output.jsonl") if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/005_data/round1_output.jsonl"
TXT_DIR = _os.path.join(_PV2, "input") if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/003_案例"
OUTPUT_CSV = "/Users/weiyueshao/Desktop/pipeline_v2/005_data/step10_multidimensional_analysis.csv"
ERROR_LOG = "/Users/weiyueshao/Desktop/pipeline_v2/005_data/step10_analysis_errors.jsonl"
CHECKPOINT_FILE = "/Users/weiyueshao/Desktop/pipeline_v2/005_data/step10_checkpoint.jsonl"
CHECKPOINT_INTERVAL = 10  # 每 N 条保存一次断点

MAX_REASONING_CHARS = 1500
MAX_FILE_SIZE = 5 * 1024 * 1024
API_CONCURRENCY = 5
API_DELAY = 0.5
MAX_RETRIES = 3

RE_CORE_REASONING = re.compile(r'(本院认为.*?)(?:依照|判决如下|$)', re.DOTALL)

# ============================================================================
# 断点续跑
# ============================================================================

def load_checkpoint() -> tuple[list[dict], list[dict]]:
    """加载已处理的结果和已记录的错误"""
    results = []
    errors = []
    if os.path.isfile(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'result':
                        results.append(entry['data'])
                    elif entry.get('type') == 'error':
                        errors.append(entry['data'])
                except json.JSONDecodeError:
                    continue
        print(f"读取断点: {len(results)} 条已处理结果, {len(errors)} 条错误")
    return results, errors


def save_checkpoint(results: list[dict], errors: list[dict]):
    """保存当前结果到断点文件"""
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps({'type': 'result', 'data': r}, ensure_ascii=False) + '\n')
        for e in errors:
            f.write(json.dumps({'type': 'error', 'data': e}, ensure_ascii=False) + '\n')


# ============================================================================
# 程序化维度提取
# ============================================================================

def extract_court_level(case_id: str) -> str:
    """从 case_id 提取法院层级"""
    if not case_id:
        return ""
    if '最高法' in case_id:
        return '最高法院'
    if '民终' in case_id or '知民终' in case_id:
        return '二审法院'
    if '民初' in case_id or '知民初' in case_id:
        return '一审法院'
    return '其他'


def extract_region(case_id: str) -> str:
    """从 case_id 提取省份/直辖市"""
    if not case_id:
        return ""
    m = re.search(r'\((\d{4})\)\s*([一-龥]{1,3})', case_id)
    if m:
        region = m.group(2)
        # 规范化
        region_map = {
            '浙': '浙江', '粤': '广东', '沪': '上海', '京': '北京',
            '苏': '江苏', '鲁': '山东', '鄂': '湖北', '陕': '陕西',
            '赣': '江西', '皖': '安徽', '豫': '河南', '辽': '辽宁',
            '渝': '重庆', '闽': '福建', '湘': '湖南', '川': '四川',
            '津': '天津', '冀': '河北', '吉': '吉林', '黑': '黑龙江',
            '贵': '贵州', '云': '云南', '甘': '甘肃', '琼': '海南',
            '晋': '山西', '桂': '广西', '蒙': '内蒙古', '宁': '宁夏',
            '青': '青海', '新': '新疆', '藏': '西藏', '最高法': '最高法院',
        }
        return region_map.get(region, region)
    if '最高法' in case_id:
        return '最高法院'
    return ""


def extract_year(case_id: str) -> str:
    """从 case_id 提取年份"""
    if not case_id:
        return ""
    m = re.search(r'\((\d{4})\)', case_id)
    return m.group(1) if m else ""


def safe_join(base: str, name: str) -> str:
    """安全拼接文件路径"""
    if not name:
        return ""
    safe_name = os.path.basename(name)
    candidate = os.path.join(base, safe_name)
    real = os.path.realpath(candidate)
    if not real.startswith(os.path.realpath(base) + os.sep) and real != os.path.realpath(base):
        return ""
    return real


def extract_reasoning(filepath: str) -> str:
    """从判决书提取'本院认为'段落"""
    try:
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            return ""
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        m = RE_CORE_REASONING.search(text)
        if m:
            return m.group(1).strip()[:MAX_REASONING_CHARS]
        return text[len(text)//2:][:MAX_REASONING_CHARS]
    except Exception:
        return ""


def has_numeric(value) -> int:
    """判断是否包含 % 数值"""
    s = str(value) if value else ""
    return 1 if '%' in s else 0


def safe_float(value) -> float:
    """安全提取浮点数"""
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(',', '').replace('，', ''))
    except (ValueError, TypeError):
        return 0.0


def extract_amount(text: str) -> float:
    """从文本中提取金额（元）"""
    if not text:
        return 0.0
    # 匹配"X元"或"X万元"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:万)?元', text)
    if m:
        val = float(m.group(1))
        if '万' in text[m.start():m.end()]:
            val *= 10000
        return val
    return 0.0


# ============================================================================
# 加载数据
# ============================================================================

def load_round1_mapping(path: str) -> dict:
    """round1: case_id -> {industry, compensation_method, claimed, awarded, source_file}"""
    mapping = {}
    if not os.path.isfile(path):
        print(f"警告：找不到 round1 文件 {path}")
        return mapping
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = d.get('case_id')
            if cid:
                mapping[cid] = {
                    'industry': d.get('industry_category', ''),
                    'compensation_method': d.get('compensation_method', ''),
                    'claimed': safe_float(d.get('plaintiff_claimed_amount')),
                    'awarded': safe_float(d.get('court_awarded_amount')),
                    'source_file': d.get('source_file', ''),
                }
    print(f"加载 round1 映射: {len(mapping)} 条")
    return mapping


def load_round2_records(path: str) -> list[dict]:
    """加载 round2 JSONL"""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    print(f"加载 round2 记录: {len(records)} 条")
    return records


# ============================================================================
# AI API 调用
# ============================================================================

SYSTEM_PROMPT = """你是一位资深知识产权法官助理，专门分析商标侵权判决书的赔偿说理逻辑。

你的任务是：阅读法院说理文本，结合已提取的利润率/贡献率结构化数据，对赔偿裁量过程进行多维度分类。

分类标准：

## 利润率采信态度 (margin_adoption_category)
- A1_完全采信：法院明确采纳了原告主张或证据显示的具体利润率数值
- A2_行业同业参考：法院参考了行业平均利润率或同类企业数据
- A3_举证妨碍推定：被告拒绝提供财务数据，法院依据原告主张推定
- A4_证据不足驳回：法院认为利润率证据不充分，转而酌定或适用法定赔偿

## 商标贡献率态度 (contribution_attitude)
- B1_全额归因：法院**在侵权获利/实际损失计算框架下明确论述**商标贡献了侵权获利的全部或绝大部分。**注意：若法院适用法定赔偿，仅在列举酌定因素时提及"贡献度100%"等表述，不属于B1。B1必须是在计算公式中做出归因论断，且赔偿方式非"法定赔偿"。**
- B2_多因素剥离：法院剥离了非商标因素（技术、渠道、包装等）的贡献，或明确论述了商标贡献率的具体比例并据此扣减
- B3_避而不谈：法院未讨论商标贡献率，包括直接使用全部利润计算但未论述商标贡献的情况

## 说理深度 (reasoning_depth)
- 详细论证：法院详细分析了各赔偿因素，引用证据并论述采信理由
- 简要说明：法院列举了考量因素但未展开论述
- 一句话带过：法院仅以一句套话说明，如"综合考量全案因素酌情确定"
- 未涉及：说理段落未涉及赔偿计算

## 证据类型 (evidence_types, 多选题)
可选: 财务账册 / 审计报告 / 行业数据 / 电商平台数据 / 单方陈述 / 未提供利润率相关财务证据

## 酌定考量因素 (discretionary_factors, 多选题)
可选: 商标知名度 / 侵权情节 / 主观过错 / 经营规模 / 维权支出 / 被告偿付能力 / 未提及酌定因素

## 计算路径 (court_calculation_path)
- 精确计算：法院基于具体数据进行了数学计算，最终判赔额直接来源于公式结果
- 参考估算：法院参考了部分数据进行了估算，最终判赔额与公式计算结果有明确对应关系
- 综合酌定：法院综合多种因素确定最终金额，不以公式计算结果为准（**关键：以最终判赔额的确定方式为准，而非过程中是否出现过数值**）

输出严格的 JSON 格式，不要有任何额外文字。"""


def build_user_prompt(record: dict) -> str:
    """构建单条记录的 user prompt"""
    pm = record.get('profit_margin_data', {})
    cr = record.get('contribution_rate_data', {})
    reasoning = record.get('reasoning_text', '') or ''

    return f"""请分析以下案件：

【说理文本】（截取1500字）
{reasoning[:MAX_REASONING_CHARS]}

【利润率结构化数据】
原告主张利润率: {pm.get('claimed_margin') or '未提及'}
法院采纳利润率: {pm.get('court_adopted_margin') or '未提及'}
利润率引用原文: {pm.get('margin_source_quote') or '无'}

【贡献率结构化数据】
原告主张贡献率: {cr.get('claimed_contribution') or '未提及'}
法院采纳贡献率: {cr.get('court_adopted_contribution') or '未提及'}
贡献率引用原文: {cr.get('contribution_source_quote') or '无'}

请输出以下 JSON 格式（每个字段都必须有值）：
{{
  "margin_adoption_category": "A1_完全采信 / A2_行业同业参考 / A3_举证妨碍推定 / A4_证据不足驳回",
  "margin_reason": "一句话理由",
  "contribution_attitude": "B1_全额归因 / B2_多因素剥离 / B3_避而不谈",
  "contribution_reason": "一句话理由",
  "reasoning_depth": "详细论证 / 简要说明 / 一句话带过 / 未涉及",
  "evidence_types": ["财务账册 / 审计报告 / 行业数据 / 电商平台数据 / 单方陈述 / 无证据"],
  "discretionary_factors": ["商标知名度 / 侵权情节 / 主观过错 / 经营规模 / 维权支出 / 被告偿付能力 / 未提及酌定因素"],
  "court_calculation_path": "精确计算 / 参考估算 / 综合酌定",
  "analysis_notes": "一句话综合评注"
}}"""


def call_deepseek(record: dict, retries: int = MAX_RETRIES) -> dict:
    """调用 DeepSeek API 进行分析"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(record)},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                body = resp.json()
                content = body['choices'][0]['message']['content']
                result = json.loads(content)
                return result
            elif resp.status_code == 429:
                wait = (attempt + 1) * 5
                time.sleep(wait)
            else:
                time.sleep((attempt + 1) * 2)
        except Exception:
            time.sleep((attempt + 1) * 2)

    return {}


# ============================================================================
# 组装单条完整记录
# ============================================================================

def safe_list_str(val) -> str:
    """将列表或值转为 CSV 友好的字符串"""
    if isinstance(val, list):
        return '; '.join(str(v) for v in val)
    return str(val) if val else ''


def clean_industry(name: str) -> str:
    """剥离行业名称中括号内的过度具象化内容，保持行业分类的抽象层级。
    '食品（食用油/芝麻油）' -> '食品'
    '体育用品（跳绳）' -> '体育用品'
    """
    if not name:
        return name
    return re.sub(r'[（(][^）)]*[）)]', '', name).strip()


def has_contrib_numeric(contrib_raw) -> int:
    """判断贡献率是否包含数值百分比（与 has_numeric 一致）。"""
    s = str(contrib_raw) if contrib_raw else ''
    return 1 if '%' in s else 0


def process_single_record(record: dict, r1_map: dict, file_map: dict) -> dict:
    """处理单条记录：程序化维度 + AI 分析"""
    case_id = record.get('case_id', '')
    r1 = r1_map.get(case_id, {})
    pm = record.get('profit_margin_data', {})
    cr = record.get('contribution_rate_data', {})
    lc = record.get('logic_check', {})

    # --- 程序化维度 ---
    court_level = extract_court_level(case_id)
    region = extract_region(case_id)
    year = extract_year(case_id)
    industry = r1.get('industry', '')
    comp_method = r1.get('compensation_method', '')
    claimed = r1.get('claimed', 0.0)
    awarded = r1.get('awarded', 0.0)

    # 优先从 logic_check 取判赔金额
    lc_awarded = safe_float(lc.get('found_awarded_amount'))
    if lc_awarded > 0:
        awarded = lc_awarded

    # 判赔/诉求比
    ratio = round(awarded / claimed, 4) if claimed > 0 else 0.0

    has_margin_num = has_numeric(pm.get('court_adopted_margin'))
    has_contrib_num = has_numeric(cr.get('court_adopted_contribution'))
    found_revenue = lc.get('found_revenue')
    validation = lc.get('validation_result', '')
    logic_explanation = lc.get('logic_explanation', '')

    # --- 获取说理文本 ---
    source_file = r1.get('source_file', '')
    txt_path = safe_join(TXT_DIR, source_file) if source_file else ''
    reasoning_text = ''
    if txt_path and os.path.isfile(txt_path):
        reasoning_text = extract_reasoning(txt_path)

    # 将 reasoning 附加到 record 供 AI 使用
    record['reasoning_text'] = reasoning_text

    # --- AI 维度 ---
    ai = call_deepseek(record)

    # --- 后处理修正：B1→B3 降级 ---
    # 规则1: 如果AI判为B1但贡献率为酌定（无数值百分数），降级为B3。
    # 规则2: 如果赔偿方式为"法定赔偿"，法院不可能在做计算公式归因，
    #         此时即使提及"贡献度100%"也是酌定因素之一，非真实B1。
    contrib_attitude = ai.get('contribution_attitude', '')
    contrib_reason = ai.get('contribution_reason', '')
    should_downgrade = False
    downgrade_reason = ''
    if contrib_attitude.startswith('B1'):
        if has_contrib_numeric(cr.get('court_adopted_contribution')) == 0:
            should_downgrade = True
            downgrade_reason = '无数值贡献率'
        elif comp_method == '法定赔偿':
            should_downgrade = True
            downgrade_reason = '法定赔偿框架下不存在B1'
    if should_downgrade:
        contrib_attitude = 'B3_避而不谈'
        contrib_reason = f"[修正:原B1因{downgrade_reason}自动降级] {contrib_reason}"

    # --- 行业名称清洗：剥离括号内具象化补充 ---
    industry_clean = clean_industry(industry)

    return {
        'case_id': case_id,
        'court_level': court_level,
        'region_province': region,
        'case_year': year,
        'industry_category': industry_clean,
        'compensation_method': comp_method,
        'plaintiff_claimed_amount': claimed,
        'court_awarded_amount': awarded,
        'award_to_claim_ratio': ratio,
        'court_adopted_margin_raw': pm.get('court_adopted_margin', ''),
        'has_numeric_margin': has_margin_num,
        'court_adopted_contribution_raw': cr.get('court_adopted_contribution', ''),
        'has_numeric_contribution': has_contrib_num,
        'found_revenue': found_revenue or '',
        'validation_result': validation,
        'logic_explanation': logic_explanation,
        'margin_adoption_category': ai.get('margin_adoption_category', ''),
        'margin_reason': ai.get('margin_reason', ''),
        'contribution_attitude': contrib_attitude,
        'contribution_reason': contrib_reason,
        'reasoning_depth': ai.get('reasoning_depth', ''),
        'evidence_types_used': safe_list_str(ai.get('evidence_types', [])),
        'discretionary_factors': safe_list_str(ai.get('discretionary_factors', [])),
        'court_calculation_path': ai.get('court_calculation_path', ''),
        'analysis_notes': ai.get('analysis_notes', ''),
    }


# ============================================================================
# CSV 输出
# ============================================================================

CSV_COLUMNS = [
    'case_id', 'court_level', 'region_province', 'case_year',
    'industry_category', 'compensation_method',
    'plaintiff_claimed_amount', 'court_awarded_amount', 'award_to_claim_ratio',
    'court_adopted_margin_raw', 'has_numeric_margin',
    'court_adopted_contribution_raw', 'has_numeric_contribution',
    'found_revenue', 'validation_result', 'logic_explanation',
    'margin_adoption_category', 'margin_reason',
    'contribution_attitude', 'contribution_reason',
    'reasoning_depth', 'evidence_types_used', 'discretionary_factors',
    'court_calculation_path', 'analysis_notes',
]


def write_csv(rows: list[dict], path: str):
    """写入 CSV（全量覆盖）"""
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ============================================================================
# 主流程
# ============================================================================

def main():
    start_time = time.time()

    print("=" * 60)
    print("Step 10: 多维度 AI 分析 (支持 Ctrl+C 断点续跑)")
    print("=" * 60)

    # 1. 加载数据
    r1_map = load_round1_mapping(ROUND1_INPUT)
    records = load_round2_records(ROUND2_INPUT)
    total = len(records)

    # 2. 加载断点
    results, errors = load_checkpoint()
    processed_case_ids = {r['case_id'] for r in results}

    if results:
        already_done = len(results)
        print(f"断点续跑: 已完成 {already_done}/{total}, 剩余 {total - already_done}")
        print(f"按 Ctrl+C 可随时暂停, 下次运行自动从第 {already_done + 1} 条继续。\n")
    else:
        print(f"\n开始处理 {total} 条记录 ...")
        print("按 Ctrl+C 可随时暂停, 下次运行自动续跑。\n")

    # 3. 逐条处理 (跳过已完成的)
    try:
        for idx in range(total):
            if idx < len(results):
                continue  # 跳过已处理

            record = records[idx]
            case_id = record.get('case_id', f'index_{idx}')

            try:
                row = process_single_record(record, r1_map, {})
                results.append(row)

                ai_ok = bool(row['margin_adoption_category'])
                status = 'Y' if ai_ok else '?'
                sys.stdout.write(
                    f"\r  [{idx+1}/{total}] {case_id} {status} "
                    f"margin={row['margin_adoption_category'] or '?'} "
                    f"contrib={row['contribution_attitude'] or '?'}      "
                )
                sys.stdout.flush()

            except Exception as e:
                error_data = {
                    'index': idx + 1,
                    'case_id': case_id,
                    'error': str(e),
                }
                errors.append(error_data)
                sys.stdout.write(f"\r  [{idx+1}/{total}] {case_id} ERR: {e}\n")
                sys.stdout.flush()

            # 每隔 N 条保存断点 + 写临时 CSV
            if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(results, errors)
                write_csv(results, OUTPUT_CSV)
                elapsed = time.time() - start_time
                eta = (elapsed / (idx + 1 - len(results) + len(results))) * (total - idx - 1)
                sys.stdout.write(
                    f"\n--- checkpoint @ {idx+1}/{total} "
                    f"({100*(idx+1)/total:.1f}%) "
                    f"已耗时 {elapsed:.0f}s ETA {eta:.0f}s ---\n"
                )
                sys.stdout.flush()

            time.sleep(API_DELAY)

    except KeyboardInterrupt:
        print("\n\n⚠ Ctrl+C 收到, 正在保存断点...")
        save_checkpoint(results, errors)
        write_csv(results, OUTPUT_CSV)
        if errors:
            with open(ERROR_LOG, 'w', encoding='utf-8') as f:
                for e in errors:
                    f.write(json.dumps(e, ensure_ascii=False) + '\n')
        print(f"已保存 {len(results)}/{total} 条结果到断点文件。")
        print(f"下次运行 python3 0010.py 自动续跑。")
        print(f"当前 CSV: {OUTPUT_CSV}")
        return

    # 4. 完成 - 写入最终输出
    save_checkpoint(results, errors)
    write_csv(results, OUTPUT_CSV)

    if errors:
        with open(ERROR_LOG, 'w', encoding='utf-8') as f:
            for e in errors:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
        print(f"错误日志: {ERROR_LOG} ({len(errors)} 条)")

    # 5. 清除断点文件（全部完成）
    if os.path.isfile(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("断点文件已清除 (全部完成)。")

    # 6. 统计摘要
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"完成! 总耗时 {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"成功: {len(results)}/{total}")
    print(f"失败: {len(errors)}/{total}")
    print(f"输出: {OUTPUT_CSV}")
    print("=" * 60)

    for col, label in [
        ('margin_adoption_category', '利润率采信态度'),
        ('contribution_attitude', '商标贡献率态度'),
        ('reasoning_depth', '说理深度'),
        ('court_calculation_path', '赔偿计算路径'),
    ]:
        dist = Counter(r[col] for r in results if r.get(col))
        print(f"\n{label}:")
        for k, v in dist.most_common():
            print(f"  {k}: {v} ({100*v/len(results):.1f}%)")


if __name__ == '__main__':
    main()
