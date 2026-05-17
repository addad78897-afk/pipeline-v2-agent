#!/usr/bin/env python3
"""
Step 14 — 阶梯式证明标准模型构建
基于 Step 006 提取的证据类型，统计各证据类型的频率与法院采信率，
映射为三层阶梯式证明标准（Tier 1-3），输出结构化 JSON + Markdown 报告。
输出: step014_tiered_evidence_standard.json + step014_tiered_evidence_standard.md

改进点（v2.1）:
- 输入路径改为从 pipeline_v2 读取（step006 / round2 均在本目录），不再依赖 clean/
- 输入文件缺失时明确报错退出，不再静默产出空报告
- 输出文件加 step014_ 前缀，便于追溯
- 增加整体执行耗时与关键统计的 console 摘要
- 证据类型统计增加 explicit True/False/None 三态计数，更精确反映采信情况
- round2 索引构建防御空值
"""

import json
import sys
import time
from pathlib import Path
from collections import defaultdict

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ── 路径配置 ────────────────────────────────────────────────────────────────
BASE_DIR = Path(_PV2) if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2")
STEP006_PATH = Path(_PV2, "005_data/step006_evidence_reasoning_results.jsonl") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/005_data/step006_evidence_reasoning_results.jsonl")
ROUND2_PATH = Path(_PV2, "005_data/round2_deep_analysis_results.jsonl") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/005_data/round2_deep_analysis_results.jsonl")
OUTPUT_JSON = BASE_DIR / "005_data/step014_tiered_evidence_standard.json"
OUTPUT_MD = BASE_DIR / "007_reports/step014_tiered_evidence_standard.md"


# ── 三阶梯证据标准定义 ─────────────────────────────────────────────────────
TIER_MAPPING = {
    "第三方审计/司法会计鉴定": 1,
    "税务申报/纳税证明": 2,
    "上市公司年报/公告": 2,
    "招股说明书/IPO文件": 2,
    "行业统计数据/行业协会数据": 3,
    "电商平台销售数据": 3,
    "原告单方财务数据": 3,
    "举证妨碍推定(被告拒不提供账簿)": 3,
    "综合酌定/未明确具体证据": 0,
    "信息不足无法判断": 0,
    "其他": 3,
}

TIER_LABELS = {
    1: "Tier 1 — 最优证据（第三方独立验证）",
    2: "Tier 2 — 次优证据（公开法定文件，可推定真实性）",
    3: "Tier 3 — 参考性证据（间接/单方，作综合参考）",
    0: "无具体经济证据（综合酌定/法定赔偿）",
}

TIER_SHORT = {1: "最优证据", 2: "次优证据", 3: "参考性证据", 0: "无具体证据"}

TIER_DESCRIPTIONS = {
    1: "经第三方独立审计或司法会计鉴定的财务数据，具有最高证明力，法院倾向于采信具体利润率数值。",
    2: "具有法律效力的公开法定文件（年报、税务申报、招股书），虽非专门为诉讼准备但真实性有制度保障。",
    3: "间接或单方来源的数据（行业统计、电商平台、原告单方陈述），法院通常仅作综合参考，不单独作为定案依据。",
    0: "法院无法或未依据具体经济证据认定利润率，转而适用法定赔偿或综合酌定。",
}

EVIDENCE_TIER_RATIONALE = {
    "第三方审计/司法会计鉴定": "审计报告/司法会计鉴定由独立第三方出具，具有法律规定的证明效力，可直接作为定案依据。",
    "税务申报/纳税证明": "税务申报数据虽由当事人自行填报，但经税务机关备案，具有公法上的约束力和可信度。",
    "上市公司年报/公告": "上市公司年报经审计并公开披露，受证券法规约束，但其中的行业细分数据可能不够精确。",
    "招股说明书/IPO文件": "招股书经保荐机构核查及监管审核，数据详实度高，但反映的是特定时期的历史数据。",
    "行业统计数据/行业协会数据": "行业协会或统计机构的数据可反映行业整体水平，但无法证明个案中涉案产品的具体利润率。",
    "电商平台销售数据": "平台销售数据可反映实际交易价格与销量，但难以直接对应到净利润率。",
    "原告单方财务数据": "原告单方提供的数据未经第三方验证，证明力有限，一般需要结合其他证据。",
    "举证妨碍推定(被告拒不提供账簿)": "被告无正当理由拒不提供账簿时，法院可参照原告主张及证据推定，但仍需综合考量。",
    "综合酌定/未明确具体证据": "法院未采信具体经济证据，依据案件综合因素（侵权性质、规模、主观过错等）酌情确定赔偿额。",
    "信息不足无法判断": "裁判文书中说理过于简略，无法判断法院依据何种证据认定事实。",
    "其他": "其他非常规证据类型，需个案分析其证明力。",
}


# ── 工具函数 ────────────────────────────────────────────────────────────────
def load_jsonl(path: Path) -> list[dict]:
    """加载 JSONL 文件，文件缺失则抛出 FileNotFoundError。"""
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在: {path}")
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def load_round2_index(path: Path) -> dict:
    """返回 {case_id: {court_adopted_margin, is_discretionary, has_specific_value}}。"""
    index = {}
    if not path.exists():
        return index
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("case_id", "")
            if not cid:
                continue
            pm = rec.get("profit_margin_data") or {}
            margin_raw = pm.get("court_adopted_margin")
            margin_str = str(margin_raw).strip() if margin_raw else ""
            index[cid] = {
                "court_adopted_margin": margin_raw,
                "is_discretionary": margin_str == "酌定",
                "has_specific_value": bool(
                    margin_str
                    and margin_str not in ("酌定", "", "None", "null")
                ),
            }
    return index


# ── 主流程 ──────────────────────────────────────────────────────────────────
def main():
    start_time = time.time()
    print("=" * 60)
    print("Step 14: 阶梯式证明标准模型构建 (v2.1)")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/3] 加载 step006 与 round2 数据...")
    try:
        s6_records = load_jsonl(STEP006_PATH)
    except FileNotFoundError as e:
        print(f"\n  FATAL: {e}")
        sys.exit(1)

    if not s6_records:
        print("  FATAL: step006 数据为空，请先运行 Step 12 (0012.py)。")
        sys.exit(1)

    r2_index = load_round2_index(ROUND2_PATH)
    print(f"  step006 记录数: {len(s6_records)}")
    print(f"  round2 索引数: {len(r2_index)}")

    # 2. 按证据类型分组统计
    print("\n[2/3] 计算各证据类型频率与采信率...")

    evidence_cases: dict[str, list[dict]] = defaultdict(list)
    for rec in s6_records:
        pm_ev = rec.get("profit_margin_evidence") or {}
        etype = pm_ev.get("evidence_type") or "信息不足无法判断"
        evidence_cases[etype].append(rec)

    tier_model = {
        "meta": {
            "title": "商标侵权赔偿利润率认定 — 阶梯式证明标准模型",
            "total_cases_analyzed": len(s6_records),
            "description": (
                "基于实证数据，将法院认定利润率所依据的证据类型按证明力分为三层阶梯，"
                "为统一裁判尺度提供证据标准参考。"
            ),
        },
        "tiers": {},
    }

    for tier_num in [1, 2, 3, 0]:
        tier_label = TIER_LABELS[tier_num]
        tier_evidence_types = [et for et, tn in TIER_MAPPING.items() if tn == tier_num]

        tier_summary = {
            "tier_level": tier_num,
            "label": tier_label,
            "description": TIER_DESCRIPTIONS[tier_num],
            "total_cases_in_tier": 0,
            "total_with_specific_value": 0,
            "adoption_rate_pct": 0.0,
            "evidence_types": [],
        }

        for etype in tier_evidence_types:
            cases = evidence_cases.get(etype, [])
            if not cases:
                tier_summary["evidence_types"].append({
                    "evidence_type": etype,
                    "case_count": 0,
                    "pct_of_tier": 0.0,
                    "adopted_specific_value_count": 0,
                    "explicit_false_count": 0,
                    "unknown_count": 0,
                    "adoption_rate_pct": 0.0,
                    "rationale": EVIDENCE_TIER_RATIONALE.get(etype, ""),
                })
                continue

            adopted_specific = 0
            explicit_false = 0
            unknown = 0
            for rec in cases:
                cid = rec.get("case_id", "")
                pm_ev = rec.get("profit_margin_evidence") or {}
                s6_specific = pm_ev.get("court_adopted_specific_value")

                if s6_specific is True:
                    adopted_specific += 1
                elif s6_specific is False:
                    explicit_false += 1
                else:
                    # step006 未明确标记，回退到 round2 判断
                    r2 = r2_index.get(cid, {})
                    if r2.get("has_specific_value"):
                        adopted_specific += 1
                    else:
                        unknown += 1

            count = len(cases)
            adoption_rate = round(adopted_specific / count * 100, 1) if count > 0 else 0.0

            tier_summary["evidence_types"].append({
                "evidence_type": etype,
                "case_count": count,
                "pct_of_tier": 0.0,
                "adopted_specific_value_count": adopted_specific,
                "explicit_false_count": explicit_false,
                "unknown_count": unknown,
                "adoption_rate_pct": adoption_rate,
                "rationale": EVIDENCE_TIER_RATIONALE.get(etype, ""),
            })

        tier_total = sum(et["case_count"] for et in tier_summary["evidence_types"])
        tier_adopted = sum(et["adopted_specific_value_count"] for et in tier_summary["evidence_types"])
        tier_summary["total_cases_in_tier"] = tier_total
        tier_summary["total_with_specific_value"] = tier_adopted
        tier_summary["adoption_rate_pct"] = (
            round(tier_adopted / tier_total * 100, 1) if tier_total > 0 else 0.0
        )

        for et in tier_summary["evidence_types"]:
            et["pct_of_tier"] = (
                round(et["case_count"] / tier_total * 100, 1) if tier_total > 0 else 0.0
            )

        tier_model["tiers"][str(tier_num)] = tier_summary

    # 写入 JSON
    OUTPUT_JSON.write_text(
        json.dumps(tier_model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  JSON: {OUTPUT_JSON}")

    # 3. 生成 Markdown 报告
    print("\n[3/3] 生成 Markdown 报告...")

    lines = []
    lines.append("# 商标侵权赔偿利润率认定 — 阶梯式证明标准模型")
    lines.append("")
    lines.append(f"> 基于 {len(s6_records)} 件商标侵权案件的裁判文书实证分析")
    lines.append("> 数据来源：Step 006 证据类型与说理深度提取结果")
    lines.append("")

    # 总览
    lines.append("## 一、三阶梯证明标准总览\n")
    lines.append("| 阶梯 | 案件数 | 占比 | 采信具体数值数 | 采信率 |")
    lines.append("|------|--------|------|---------------|--------|")

    total_cases_with_data = sum(
        ts["total_cases_in_tier"] for ts in tier_model["tiers"].values()
    )
    for tier_num in [1, 2, 3, 0]:
        ts = tier_model["tiers"][str(tier_num)]
        pct = (
            round(ts["total_cases_in_tier"] / total_cases_with_data * 100, 1)
            if total_cases_with_data > 0
            else 0.0
        )
        label_short = TIER_SHORT[tier_num]
        lines.append(
            f"| **Tier {tier_num}** — {label_short} "
            f"| {ts['total_cases_in_tier']} | {pct}% "
            f"| {ts['total_with_specific_value']} | {ts['adoption_rate_pct']}% |"
        )
    lines.append("")

    # 各 Tier 详解
    for tier_num in [1, 2, 3, 0]:
        ts = tier_model["tiers"][str(tier_num)]
        label_short = TIER_SHORT[tier_num]
        lines.append(f"## 二.{tier_num} {TIER_LABELS[tier_num]}\n")
        lines.append(f"**定义**：{TIER_DESCRIPTIONS[tier_num]}\n")
        lines.append(
            f"**本 Tier 总计**：{ts['total_cases_in_tier']} 件，"
            f"其中法院采信具体数值 {ts['total_with_specific_value']} 件，"
            f"**采信率 {ts['adoption_rate_pct']}%**。\n"
        )

        if ts["evidence_types"]:
            lines.append(
                "| 证据类型 | 案件数 | 占本Tier比例 | 采信具体数值 | 采信率 |"
            )
            lines.append(
                "|---------|--------|-------------|-------------|--------|"
            )
            for et in sorted(ts["evidence_types"], key=lambda x: -x["case_count"]):
                lines.append(
                    f"| {et['evidence_type']} | {et['case_count']} "
                    f"| {et['pct_of_tier']}% "
                    f"| {et['adopted_specific_value_count']} "
                    f"| {et['adoption_rate_pct']}% |"
                )
            lines.append("")

            for et in ts["evidence_types"]:
                if et["case_count"] > 0:
                    lines.append(
                        f"  - **{et['evidence_type']}**：{et['rationale']}\n"
                    )
        else:
            lines.append("（本 Tier 暂无案件）\n")

    # 结论与建议
    lines.append("---\n")
    lines.append("## 三、研究结论与裁判建议\n")

    t1_rate = tier_model["tiers"]["1"]["adoption_rate_pct"]
    t2_rate = tier_model["tiers"]["2"]["adoption_rate_pct"]
    t3_rate = tier_model["tiers"]["3"]["adoption_rate_pct"]
    t0_count = tier_model["tiers"]["0"]["total_cases_in_tier"]
    t0_pct = (
        round(t0_count / total_cases_with_data * 100, 1)
        if total_cases_with_data > 0
        else 0.0
    )

    lines.append(
        f"1. **证据质量与采信率正相关**：Tier 1（最优证据）的采信率为 {t1_rate}%，"
        f"Tier 2 为 {t2_rate}%，Tier 3 为 {t3_rate}%，"
        f"表明证据类型与法院采信具体数值的概率密切相关。"
    )
    lines.append(
        f"2. **法定赔偿兜底效应显著**：共 {t0_count} 件案件未依赖具体经济证据，"
        f"占全样本的 {t0_pct}%，说明当前商标侵权赔偿仍高度依赖法官自由裁量。"
    )
    lines.append(
        "3. **统一裁判尺度建议**：建议最高人民法院在司法解释中明确，"
        "当原告提交 Tier 1 级证据时，法院原则上应采信其利润率数值并说明理由；"
        "提交 Tier 2 级证据时，在被告未提出有效反驳的情况下可推定采信；"
        "仅提交 Tier 3 级证据时，应结合其他因素综合考量。"
    )
    lines.append(
        "4. **举证妨碍规则的激活**：在被告拒不提供账簿的情形下，"
        "应积极适用举证妨碍推定规则，参照原告证据及行业数据合理确定利润率，"
        "避免简单转入法定赔偿。"
    )
    lines.append("")

    lines.append(f"\n*模型构建于 {len(s6_records)} 件商标侵权案件实证数据。*")
    lines.append(f"\n*详细结构化数据见 `{OUTPUT_JSON.name}`*。")

    report = "\n".join(lines)
    OUTPUT_MD.write_text(report, encoding="utf-8")
    print(f"  Markdown: {OUTPUT_MD}")

    # 4. 控制台摘要
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("阶梯式证明标准模型 — 摘要")
    print("=" * 60)
    for tier_num in [1, 2, 3, 0]:
        ts = tier_model["tiers"][str(tier_num)]
        print(f"\n  Tier {tier_num} | {ts['label']}")
        print(f"    案件数: {ts['total_cases_in_tier']} | 采信率: {ts['adoption_rate_pct']}%")
        for et in ts["evidence_types"]:
            if et["case_count"] > 0:
                detail_parts = [f"{et['case_count']}件 ({et['adoption_rate_pct']}%)"]
                if et.get("explicit_false_count"):
                    detail_parts.append(f"明确未采信: {et['explicit_false_count']}")
                if et.get("unknown_count"):
                    detail_parts.append(f"未知: {et['unknown_count']}")
                print(f"      - {et['evidence_type']}: {', '.join(detail_parts)}")

    print(f"\n{'=' * 60}")
    print(f"Step 14 完成。耗时: {elapsed:.1f}s")
    print(f"输出: {OUTPUT_JSON.name}, {OUTPUT_MD.name}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
