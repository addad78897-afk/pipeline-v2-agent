#!/usr/bin/env python3
"""
Step 13 — 同案不同判冲突分析与行业利润率差异统计
按行业分组，计算同行业内不同法院对利润率认定的差异（极差/中位数），
并标记"贡献率适用"与"忽略贡献率"之间的裁判冲突。
输出: step013_conflict_analysis_report.md + step013_conflict_data.csv

改进点（v2.1）:
- 输入文件缺失时明确报错退出，不再静默产出空报告
- 冲突案例去重，避免同一 case_id 重复录入
- CV 计算防御除零（mean=0 或 std=0 时安全处理）
- itertools.groupby 移到文件顶部
- 输出文件名加 step013_ 前缀，便于追溯
- 增加整体执行耗时与关键统计的 console 摘要
"""

import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict
from itertools import groupby
from statistics import median, stdev
from typing import Optional

import pandas as pd

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
BASE_DIR = Path(_PV2) if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2")
ROUND1_PATH = DATA_DIR / "round1_case_extraction_results.jsonl"
ROUND2_PATH = Path(_PV2, "005_data/round2_deep_analysis_results.jsonl") if _PV2 else Path("/Users/weiyueshao/Desktop/pipeline_v2/005_data/round2_deep_analysis_results.jsonl")
STEP006_PATH = BASE_DIR / "step006_evidence_reasoning_results.jsonl"
OUTPUT_MD = BASE_DIR / "step013_conflict_analysis_report.md"
OUTPUT_CSV = BASE_DIR / "step013_conflict_data.csv"


# ── 工具函数 ────────────────────────────────────────────────────────────────
def parse_numeric_pct(value) -> Optional[float]:
    """从字符串中提取百分比数值，如 '12.616%' -> 12.616。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    if value.strip() in ("酌定", "", "null", "None"):
        return None
    m = re.search(r"(\d+\.?\d*)\s*%?", str(value))
    if m:
        return float(m.group(1))
    return None


def is_statutory_compensation(method: str) -> bool:
    """判断是否适用法定赔偿。"""
    if not method:
        return False
    return "法定赔偿" in str(method)


# ── 证据类型 → Tier 映射（与 Step 12 / 0012.py 一致）───────────────────────
TIER_MAP = {
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


def get_evidence_tier(evidence_type: str) -> int:
    """将 step006 的证据类型映射为层级编号。"""
    if not evidence_type or not isinstance(evidence_type, str):
        return -1
    return TIER_MAP.get(evidence_type, -1)


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


def safe_cv(values: pd.Series) -> Optional[float]:
    """安全计算变异系数 CV(%)，防御除零与空序列。"""
    if len(values) < 2:
        return None
    mean_val = values.mean()
    if mean_val == 0 or pd.isna(mean_val):
        return None
    std_val = values.std()
    if std_val == 0 or pd.isna(std_val):
        return 0.0
    return round(float(std_val / mean_val * 100), 1)


# ── 主分析逻辑 ──────────────────────────────────────────────────────────────
def main():
    start_time = time.time()
    print("=" * 60)
    print("Step 13: 同案不同判冲突分析与行业利润率差异统计 (v2.1)")
    print("=" * 60)

    # 1. 加载数据（文件缺失直接报错退出）
    print("\n[1/4] 加载数据源...")
    try:
        round1_records = load_jsonl(ROUND1_PATH)
        round2_records = load_jsonl(ROUND2_PATH)
        step006_records = load_jsonl(STEP006_PATH)
    except FileNotFoundError as e:
        print(f"\n  FATAL: {e}")
        sys.exit(1)

    print(f"  round1 (全量): {len(round1_records)}")
    print(f"  round2 (深度): {len(round2_records)}")
    print(f"  step006 (证据说理): {len(step006_records)}")

    if len(round2_records) == 0:
        print("  FATAL: round2 数据为空，无法继续分析。")
        sys.exit(1)

    # 2. 以 round2 为基础构建合并数据集
    print("\n[2/4] 合并数据并按行业分组...")

    # 构建 round1 索引
    r1_index: dict[str, dict] = {}
    for rec in round1_records:
        cid = rec.get("case_id", "")
        if cid:
            r1_index[cid] = rec

    # 构建 step006 索引
    s6_index: dict[str, dict] = {}
    for rec in step006_records:
        cid = rec.get("case_id", "")
        if cid:
            s6_index[cid] = rec

    # 合并行
    rows = []
    skip_no_r1 = 0
    for rec in round2_records:
        cid = rec.get("case_id", "")
        r1 = r1_index.get(cid, {})
        s6 = s6_index.get(cid, {})

        if not r1:
            skip_no_r1 += 1

        pm = rec.get("profit_margin_data", {}) or {}
        cr = rec.get("contribution_rate_data", {}) or {}
        lc = rec.get("logic_check", {}) or {}
        pm_ev = s6.get("profit_margin_evidence", {}) or {}
        cr_rb = s6.get("contribution_rate_reasoning", {}) or {}

        margin_raw = pm.get("court_adopted_margin")
        margin_val = parse_numeric_pct(margin_raw)

        contrib_raw = cr.get("court_adopted_contribution")
        contrib_val = parse_numeric_pct(contrib_raw)

        industry = r1.get("industry_category", "未知行业")

        evidence_type_str = pm_ev.get("evidence_type")
        evidence_tier_val = get_evidence_tier(evidence_type_str)

        row = {
            "case_id": cid,
            "industry_category": industry,
            "compensation_method": r1.get("compensation_method"),
            "court_adopted_margin_raw": str(margin_raw) if margin_raw else None,
            "court_adopted_margin_pct": margin_val,
            "margin_evidence_type": evidence_type_str,
            "margin_evidence_tier": evidence_tier_val,
            "margin_evidence_detail": pm_ev.get("evidence_detail"),
            "court_adopted_contribution_raw": str(contrib_raw) if contrib_raw else None,
            "court_adopted_contribution_pct": contrib_val,
            "contribution_reasoning_basis": cr_rb.get("reasoning_basis"),
            "contribution_reasoning_detail": cr_rb.get("reasoning_detail"),
            "judicial_discretion_level": s6.get("judicial_discretion_level"),
            "found_revenue": lc.get("found_revenue"),
            "found_awarded_amount": lc.get("found_awarded_amount"),
            "validation_result": lc.get("validation_result"),
            "has_numeric_margin": margin_val is not None,
            "has_numeric_contribution": contrib_val is not None,
            "is_statutory_compensation": is_statutory_compensation(r1.get("compensation_method", "")),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"  合并后数据行数: {len(df)}")
    print(f"  行业数: {df['industry_category'].nunique()}")
    print(f"  含数值利润率案件: {df['has_numeric_margin'].sum()}")
    print(f"  含数值贡献率案件: {df['has_numeric_contribution'].sum()}")
    if skip_no_r1 > 0:
        print(f"  警告: {skip_no_r1} 条 round2 记录在 round1 中无匹配（行业标记为'未知行业'）")

    # 3. 行业分组分析
    print("\n[3/4] 执行行业分组分析...")

    industry_stats = []
    conflict_cases = []
    # 用 set 追踪已记录的冲突 (case_id, conflict_type, evidence_tier) 防重复
    seen_conflicts: set[tuple] = set()

    for industry, group in df.groupby("industry_category"):
        count = len(group)
        numeric_margins = group[group["has_numeric_margin"]]["court_adopted_margin_pct"].dropna()

        stat = {
            "industry": industry,
            "case_count": count,
            "cases_with_numeric_margin": len(numeric_margins),
            "margin_min": round(float(numeric_margins.min()), 2) if len(numeric_margins) > 0 else None,
            "margin_max": round(float(numeric_margins.max()), 2) if len(numeric_margins) > 0 else None,
            "margin_median": round(float(numeric_margins.median()), 2) if len(numeric_margins) > 0 else None,
            "margin_mean": round(float(numeric_margins.mean()), 2) if len(numeric_margins) > 0 else None,
            "margin_range": round(float(numeric_margins.max() - numeric_margins.min()), 2)
            if len(numeric_margins) >= 2
            else None,
            "margin_std": round(float(numeric_margins.std()), 2) if len(numeric_margins) >= 2 else None,
            "statutory_rate": round(group["is_statutory_compensation"].mean() * 100, 1),
            "evidence_types": group["margin_evidence_type"].dropna().value_counts().to_dict(),
        }

        # ── 检测 1：贡献率「适用 vs 忽略」的粗粒度标记 ─────────────────
        contrib_mentioned = group[group["contribution_reasoning_basis"].notna()]
        contrib_not_mentioned = group[
            group["contribution_reasoning_basis"].isna()
            | (group["contribution_reasoning_basis"] == "完全未提及商标贡献率")
        ]

        stat["contribution_mentioned_count"] = len(contrib_mentioned)
        stat["contribution_ignored_count"] = len(contrib_not_mentioned)
        stat["contribution_mention_disparity"] = (
            len(contrib_mentioned) > 0 and len(contrib_not_mentioned) > 0
        )

        # ── 检测 2：Tier-Aware 冲突分析（核心修正）────────────────────
        tier_conflicts = []
        for tier_val in [1, 2, 3]:
            tier_group = group[group["margin_evidence_tier"] == tier_val]
            tier_margins = tier_group[tier_group["has_numeric_margin"]]["court_adopted_margin_pct"].dropna()
            if len(tier_margins) >= 3:
                tier_cv = safe_cv(tier_margins)
                cv_exceeds = tier_cv is not None and tier_cv > 50
                tier_conflicts.append({
                    "evidence_tier": tier_val,
                    "tier_case_count": len(tier_group),
                    "tier_margin_count": len(tier_margins),
                    "tier_cv_pct": tier_cv,
                    "cv_exceeds_threshold": cv_exceeds,
                })
                if cv_exceeds:
                    for _, case_row in tier_group.iterrows():
                        key = (case_row["case_id"], "tier_aware_conflict", tier_val)
                        if key not in seen_conflicts:
                            seen_conflicts.add(key)
                            conflict_cases.append({
                                "industry": industry,
                                "case_id": case_row["case_id"],
                                "evidence_tier": tier_val,
                                "evidence_type": case_row["margin_evidence_type"],
                                "court_adopted_margin_pct": case_row["court_adopted_margin_pct"],
                                "court_adopted_contribution_raw": case_row["court_adopted_contribution_raw"],
                                "contribution_reasoning": case_row["contribution_reasoning_basis"],
                                "compensation_method": case_row["compensation_method"],
                                "conflict_type": "tier_aware_conflict",
                            })

        stat["tier_aware_conflicts"] = tier_conflicts
        stat["has_tier_aware_conflict"] = any(tc["cv_exceeds_threshold"] for tc in tier_conflicts)

        # ── 检测 3：贡献率分歧（仅在同一证据层级下比较）────────────────
        for tier_val in [1, 2, 3]:
            tier_group = group[group["margin_evidence_tier"] == tier_val]
            if len(tier_group) >= 3:
                tier_contrib_mentioned = tier_group[
                    tier_group["contribution_reasoning_basis"].notna()
                    & (tier_group["contribution_reasoning_basis"] != "完全未提及商标贡献率")
                ]
                tier_contrib_ignored = tier_group[
                    ~tier_group["contribution_reasoning_basis"].notna()
                    | (tier_group["contribution_reasoning_basis"] == "完全未提及商标贡献率")
                ]
                if len(tier_contrib_mentioned) > 0 and len(tier_contrib_ignored) > 0:
                    for _, case_row in tier_group.iterrows():
                        key = (case_row["case_id"], "contribution_disparity_within_tier", tier_val)
                        if key not in seen_conflicts:
                            seen_conflicts.add(key)
                            conflict_cases.append({
                                "industry": industry,
                                "case_id": case_row["case_id"],
                                "evidence_tier": tier_val,
                                "evidence_type": case_row["margin_evidence_type"],
                                "court_adopted_margin_pct": case_row["court_adopted_margin_pct"],
                                "court_adopted_contribution_raw": case_row["court_adopted_contribution_raw"],
                                "contribution_reasoning": case_row["contribution_reasoning_basis"],
                                "compensation_method": case_row["compensation_method"],
                                "conflict_type": "contribution_disparity_within_tier",
                            })

        # ── 利润率跨法院差异 ──────────────────────────────────────────
        if len(numeric_margins) >= 3:
            stat["margin_cv"] = safe_cv(numeric_margins)
            stat["high_dispersion_suspected"] = (
                stat["margin_cv"] is not None and stat["margin_cv"] > 50
            )
        else:
            stat["margin_cv"] = None
            stat["high_dispersion_suspected"] = False

        industry_stats.append(stat)

    # 按案件数排序
    industry_stats.sort(key=lambda x: -x["case_count"])

    print(f"  行业统计: {len(industry_stats)} 个行业")
    print(f"  冲突案例(去重后): {len(conflict_cases)} 条")
    tier_aware_count = sum(1 for c in conflict_cases if c["conflict_type"] == "tier_aware_conflict")
    contrib_disparity_count = sum(1 for c in conflict_cases if c["conflict_type"] == "contribution_disparity_within_tier")
    print(f"    - Tier-Aware 高离散: {tier_aware_count} 条")
    print(f"    - Tier内贡献率分歧: {contrib_disparity_count} 条")

    # 4. 输出
    print("\n[4/4] 生成输出文件...")

    # ---- CSV ----
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  CSV: {OUTPUT_CSV} ({len(df)} 行)")

    # ---- Markdown Report ----
    lines = []
    lines.append("# 商标侵权案件同案不同判冲突分析报告")
    lines.append(f"\n> 自动生成于 Step 13 | 数据来源：round1 + round2 + step006")
    lines.append(f"\n> 分析案件总数：{len(df)} | 涉及行业数：{len(industry_stats)}")
    lines.append("")

    # 总体摘要
    lines.append("## 一、总体数据摘要\n")
    lines.append(f"- 含**数值利润率**的案件：{df['has_numeric_margin'].sum()} / {len(df)}（{df['has_numeric_margin'].mean()*100:.1f}%）")
    lines.append(f"- 含**数值贡献率**的案件：{df['has_numeric_contribution'].sum()} / {len(df)}（{df['has_numeric_contribution'].mean()*100:.1f}%）")
    lines.append(f"- 适用**法定赔偿**的案件：{df['is_statutory_compensation'].sum()} / {len(df)}（{df['is_statutory_compensation'].mean()*100:.1f}%）")

    # 利润率数值分布
    numeric_all = df[df["has_numeric_margin"]]["court_adopted_margin_pct"].dropna()
    if len(numeric_all) >= 2:
        lines.append(f"- 全行业利润率范围：{numeric_all.min():.2f}% ~ {numeric_all.max():.2f}% | 中位数：{numeric_all.median():.2f}% | 均值：{numeric_all.mean():.2f}%")

    # 法官裁量水平
    discretion_dist = df["judicial_discretion_level"].dropna().value_counts()
    if len(discretion_dist) > 0:
        lines.append("\n### 法官裁量水平分布\n")
        for level, cnt in discretion_dist.items():
            lines.append(f"- {level}：{cnt} 件（{cnt/len(df)*100:.1f}%）")

    lines.append("")

    # 行业利润率差异
    lines.append("## 二、行业利润率跨法院差异分析\n")
    lines.append("> 仅统计含数值利润率的行业，按案件数降序排列。\n")
    lines.append("| 行业 | 案件数 | 有数值利润率 | 利润率最小值 | 利润率最大值 | 利润率中位数 | 利润率均值 | 极差(百分点) | 标准差 | 变异系数(CV%) |")
    lines.append("|------|--------|-------------|-------------|-------------|-------------|-------------|-------------|--------|--------------|")

    for s in industry_stats:
        if s["margin_min"] is not None:
            lines.append(
                f"| {s['industry']} | {s['case_count']} | {s['cases_with_numeric_margin']} "
                f"| {s['margin_min']}% | {s['margin_max']}% | {s['margin_median']}% "
                f"| {s['margin_mean']}% | {s.get('margin_range', 'N/A')} | {s.get('margin_std', 'N/A')} "
                f"| {s.get('margin_cv', 'N/A')} |"
            )

    lines.append("")
    lines.append("### 疑似高离散区间（CV > 50%）\n")
    lines.append("> 注意：高 CV 仅标记为「疑似高离散区间（Suspected High-Dispersion Interval）」，\n")
    lines.append("> 不直接等同于裁判冲突。同一行业内部的利润率差异可能源于证据层级不同\n")
    lines.append("> （如Tier 1审计报告 vs Tier 3单方陈述），这属于证据质量差异而非真正裁判冲突。\n")
    lines.append("> 真正裁判冲突需结合下方 Tier-Aware 冲突分析综合判断。\n")
    high_cv = [s for s in industry_stats if s.get("margin_cv") and s["margin_cv"] > 50]
    if high_cv:
        for s in high_cv:
            lines.append(
                f"- **{s['industry']}**：CV={s['margin_cv']}%，"
                f"利润率范围 {s['margin_min']}% ~ {s['margin_max']}%，极差 {s.get('margin_range', 'N/A')} 个百分点"
            )
    else:
        lines.append("（无满足标准差计算条件的行业）")

    lines.append("")

    # 同案不同判冲突（Tier-Aware）
    lines.append("## 三、商标贡献率适用分歧与 Tier-Aware 裁判冲突分析\n")
    lines.append("### 3.1 贡献率「适用 vs 忽略」的行业分布（粗粒度标记）\n")
    lines.append("> 同一行业内部分案件考虑了贡献率、部分未提及，标记为「疑似模式（Suspected Pattern）」。\n")
    lines.append("| 行业 | 案件总数 | 提及贡献率 | 忽略贡献率 | 疑似模式 |")
    lines.append("|------|---------|-----------|-----------|---------|")

    disparity_industries = [s for s in industry_stats if s["contribution_mention_disparity"]]
    for s in sorted(disparity_industries, key=lambda x: -x["case_count"]):
        severity = (
            "严重" if s["contribution_ignored_count"] / s["case_count"] > 0.7
            else "中等" if s["contribution_ignored_count"] / s["case_count"] > 0.4
            else "轻微"
        )
        lines.append(
            f"| {s['industry']} | {s['case_count']} "
            f"| {s['contribution_mentioned_count']} | {s['contribution_ignored_count']} "
            f"| {severity} |"
        )
    if not disparity_industries:
        lines.append("| （无贡献率分歧的行业） | - | - | - | - |")
    lines.append("")

    # Tier-Aware 冲突分析
    lines.append("### 3.2 Tier-Aware 裁判冲突（同一证据层级下的高离散度）\n")
    lines.append("> **核心逻辑**：仅当同一行业 + 同一证据层级(Tier)下，利润率认定的 CV 仍 > 50%，")
    lines.append("> 才能认定为真正的「同案不同判」裁判冲突。\n")
    lines.append("| 行业 | 证据层级 | 该层案件数 | 含数值利润率 | CV(%) | 是否真正冲突 |")
    lines.append("|------|---------|-----------|-------------|-------|-------------|")

    tier_conflict_found = False
    for s in industry_stats:
        for tc in s.get("tier_aware_conflicts", []):
            tier_conflict_found = True
            verdict = "**是**" if tc["cv_exceeds_threshold"] else "否"
            cv_display = f"{tc['tier_cv_pct']}%" if tc["tier_cv_pct"] is not None else "N/A"
            lines.append(
                f"| {s['industry']} | Tier {tc['evidence_tier']} | {tc['tier_case_count']} "
                f"| {tc['tier_margin_count']} | {cv_display} | {verdict} |"
            )
    if not tier_conflict_found:
        lines.append("| （无 Tier-Aware 冲突数据，需先运行 Step 12） | - | - | - | - | - |")
    lines.append("")

    # 典型冲突案例
    lines.append("### 3.3 典型 Tier-Aware 冲突案例摘录\n")
    lines.append("> 仅展示同一证据层级下仍存在显著差异的案例（去重后）。\n")
    conflict_cases_sorted = sorted(conflict_cases, key=lambda x: (x["industry"], x["evidence_tier"] or 0))
    shown = 0
    for industry_name, cases in groupby(conflict_cases_sorted, key=lambda x: x["industry"]):
        cases_list = list(cases)
        if shown >= 30:
            break
        lines.append(f"#### {industry_name}\n")
        for c in cases_list[:4]:
            conflict_type_label = (
                "Tier-Aware高离散" if c["conflict_type"] == "tier_aware_conflict"
                else "Tier内贡献率分歧"
            )
            lines.append(
                f"- [{conflict_type_label}] **{c['case_id']}** | Tier {c['evidence_tier']} | "
                f"利润率 = {c['court_adopted_margin_pct']}% | "
                f"证据类型 = {c['evidence_type'] or '未知'} | "
                f"贡献率 = {c['court_adopted_contribution_raw'] or '未提及'} | "
                f"赔偿方法 = {c['compensation_method'] or '未知'}"
            )
        shown += 1
        lines.append("")

    # 证据类型分布
    lines.append("## 四、利润率证据类型分布\n")
    lines.append("| 证据类型 | 案件数 | 占比 |")
    lines.append("|---------|--------|------|")
    evidence_dist = df["margin_evidence_type"].dropna().value_counts()
    for etype, cnt in evidence_dist.items():
        lines.append(f"| {etype} | {cnt} | {cnt/len(df)*100:.1f}% |")

    lines.append("")
    lines.append("---")
    lines.append(f"\n*报告结束。详细数据见 `{OUTPUT_CSV.name}`*。")

    report = "\n".join(lines)
    OUTPUT_MD.write_text(report, encoding="utf-8")
    print(f"  Markdown: {OUTPUT_MD}")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Step 13 完成。耗时: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"输出: {OUTPUT_MD.name}, {OUTPUT_CSV.name}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
