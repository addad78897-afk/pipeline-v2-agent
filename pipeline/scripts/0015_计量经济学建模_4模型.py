#!/usr/bin/env python3
"""
Step 15 — 计量经济学建模：利润率/贡献率对判赔金额的因果效应
======================================================================
四个计量模型，Stata 风格学术输出，写入 step015_econometric_results.md

Model 1: Logit 回归 — 证据层级对法院采信利润率概率的影响
Model 2: One-Way ANOVA — 行业间利润率认定差异的统计显著性
Model 3: OLS (HC1稳健标准误) — 利润率/贡献率对判赔金额的边际效应
        [含控制变量: 法院层级、审判年份、沿海地区、律师代理]
Model C: Tobit 截断回归 — 法定赔偿上限导致的数据截断偏误修正
        [替代 Heckman 两步法：因排他性工具变量在司法场景中不可获得]

改进点（v2.1）:
- 输入路径：round2/step006 从 pipeline_v2 读取，round1 从 clean/ 读取
- 输入文件缺失时明确报错退出，不再静默产出空报告
- 输出文件加 step015_ 前缀，便于追溯
- 修复 Tobit 模型 ols_result.params.values 崩溃
- trial_year 中心化处理（基准年 2019），消除多重共线性，系数可解释
- 控制变量零方差/常量检测，自动排除无变异变量（如 has_lawyer 全空）
- Spec 2 最小样本量阈值从 5 提升至 20
- Tier 3 100% 采信率时给出有意义的法学解读而非静默排除
- 增加整体执行耗时与关键统计的 console 摘要
- 移除未使用的 PATH_STEP007/PATH_STEP008 死代码
- 模型结果同时输出纯文本系数表（便于阅读，替代仅 LaTeX）
"""

import json
import re
import sys
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ── 路径配置 ────────────────────────────────────────────────────────────────
DATA = Path("/Users/weiyueshao/Desktop/pipeline_v2/003_案例")          # round1（仅此文件在 clean/）
BASE = Path("/Users/weiyueshao/Desktop/pipeline_v2")        # round2, step006 输入 + 所有输出
PATH_ROUND1 = DATA / "round1_case_extraction_results.jsonl"
PATH_ROUND2 = BASE / "005_data/round2_deep_analysis_results.jsonl"
PATH_STEP006 = BASE / "005_data/step006_evidence_reasoning_results.jsonl"
OUTPUT_MD = BASE / "007_reports/step015_econometric_results.md"

# ── 证据类型 → Tier 映射（与 Step 008/014 一致）───────────────────────────
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

# ── 控制变量构造工具 ──────────────────────────────────────────────────────
COASTAL_PROVINCES = {
    "北京市", "天津市", "上海市", "河北省", "辽宁省", "江苏省", "浙江省",
    "福建省", "山东省", "广东省", "广西壮族自治区", "海南省",
}

TRIAL_YEAR_BASE = 2019  # 旧商标法最后一次修正年份，中心化基准


def extract_year_from_caseid(case_id: str) -> Optional[int]:
    """从案号提取结案年份，如 '(2024)粤0111民初687号' → 2024。"""
    if not case_id:
        return None
    m = re.search(r'[（(](\d{4})[）)]', str(case_id))
    return int(m.group(1)) if m else None


def extract_province_from_caseid(case_id: str) -> str:
    """从案号提取省份简称，如 '(2024)粤0111民初687号' → 广东。"""
    if not case_id:
        return "未知"
    PROVINCE_CODE_MAP = {
        "京": "北京市", "津": "天津市", "沪": "上海市", "渝": "重庆市",
        "冀": "河北省", "晋": "山西省", "辽": "辽宁省", "吉": "吉林省",
        "黑": "黑龙江省", "苏": "江苏省", "浙": "浙江省", "皖": "安徽省",
        "闽": "福建省", "赣": "江西省", "鲁": "山东省", "豫": "河南省",
        "鄂": "湖北省", "湘": "湖南省", "粤": "广东省", "桂": "广西壮族自治区",
        "琼": "海南省", "川": "四川省", "蜀": "四川省", "黔": "贵州省", "贵": "贵州省",
        "滇": "云南省", "云": "云南省", "藏": "西藏自治区", "陕": "陕西省",
        "秦": "陕西省", "甘": "甘肃省", "陇": "甘肃省", "青": "青海省",
        "宁": "宁夏回族自治区", "新": "新疆维吾尔自治区",
        "蒙": "内蒙古自治区", "台": "台湾省",
    }
    m = re.search(r'[（(]\d{4}[）)]([一-鿿])', str(case_id))
    if m:
        code = m.group(1)
        return PROVINCE_CODE_MAP.get(code, code)
    return "未知"


def extract_court_level_from_caseid(case_id: str) -> str:
    """从案号推断法院级别。"""
    if not case_id:
        return "未知"
    s = str(case_id)
    if any(kw in s for kw in ["知民", "知行"]):
        return "知识产权法院"
    if "最高法" in s or "最高" in s:
        return "最高人民法院"
    if "民终" in s:
        return "中级/高级人民法院(二审)"
    if "民再" in s:
        return "中级/高级人民法院(再审)"
    if "民初" in s:
        return "基层人民法院(一审)"
    return "未知"


def court_level_ordinal(level: str) -> int:
    """法院级别 → 序数变量。"""
    if "基层" in str(level):
        return 1
    if "中级" in str(level) or "知识产权" in str(level):
        return 2
    if "高级" in str(level) or "最高" in str(level):
        return 3
    return 0


def is_coastal_province(province: str) -> int:
    """沿海省份 dummy。"""
    return 1 if province in COASTAL_PROVINCES else 0


# ── 数据加载 ──────────────────────────────────────────────────────────────
def parse_pct(val) -> Optional[float]:
    """从字符串提取百分比数值。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s in ("酌定", "", "None", "null", "nan"):
        return None
    m = re.search(r"(\d+\.?\d*)\s*%?", s)
    return float(m.group(1)) if m else None


def load_round1() -> dict:
    """返回 {case_id: {industry_category, compensation_method, court_awarded_amount, ...}}"""
    idx = {}
    if not PATH_ROUND1.exists():
        print(f"  FATAL: round1 文件不存在: {PATH_ROUND1}")
        sys.exit(1)
    with open(PATH_ROUND1, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("case_id", "")
            if cid:
                idx[cid] = rec
    return idx


def load_round2() -> dict:
    """返回 {case_id: round2 record}"""
    idx = {}
    if not PATH_ROUND2.exists():
        print(f"  FATAL: round2 文件不存在: {PATH_ROUND2}")
        sys.exit(1)
    with open(PATH_ROUND2, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("case_id", "")
            if cid:
                idx[cid] = rec
    return idx


def load_step006() -> dict:
    """返回 {case_id: {evidence_type, court_adopted_specific_value, ...}}"""
    idx = {}
    if not PATH_STEP006.exists():
        return idx  # step006 可选，缺失时回退
    with open(PATH_STEP006, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("case_id", "")
            if cid:
                pm_ev = rec.get("profit_margin_evidence", {}) or {}
                idx[cid] = {
                    "evidence_type": pm_ev.get("evidence_type"),
                    "court_adopted_specific_value": pm_ev.get("court_adopted_specific_value"),
                }
    return idx


def infer_evidence_tier_from_quote(quote: str) -> int:
    """从 margin_source_quote 文本推断证据层级（step006 未运行时的回退策略）。"""
    if not quote or not isinstance(quote, str):
        return 0
    q = quote
    if any(kw in q for kw in ["审计", "司法会计", "鉴定", "财务账册", "财务数据"]):
        return 1
    if any(kw in q for kw in ["上市公司", "年报", "公告", "招股", "IPO", "税务", "纳税"]):
        return 2
    if any(kw in q for kw in ["行业", "协会", "统计", "电商", "平台销售", "天猫", "淘宝", "京东"]):
        return 3
    if any(kw in q for kw in ["酌定", "综合考量", "综合考虑", "综合因素"]):
        return 0
    return 0


# ── 主分析函数 ────────────────────────────────────────────────────────────
def build_dataset() -> pd.DataFrame:
    """合并 round1 + round2 + step006，构造回归就绪的 DataFrame。"""
    r1 = load_round1()
    r2 = load_round2()
    s6 = load_step006()

    print(f"  round1 索引: {len(r1)}")
    print(f"  round2 索引: {len(r2)}")
    print(f"  step006 索引: {len(s6)}")
    data_source = "step006 证据类型" if s6 else "round2 margin_source_quote 推断（step006 未运行，Tier 为推断值）"

    rows = []
    for cid, r2r in r2.items():
        r1r = r1.get(cid, {})
        s6r = s6.get(cid, {})

        pm = r2r.get("profit_margin_data", {}) or {}
        cr = r2r.get("contribution_rate_data", {}) or {}
        lc = r2r.get("logic_check", {}) or {}

        margin_raw = pm.get("court_adopted_margin")
        margin_pct = parse_pct(margin_raw)
        margin_quote = pm.get("margin_source_quote", "")
        contrib_raw = cr.get("court_adopted_contribution")
        contrib_pct = parse_pct(contrib_raw)
        contrib_quote = cr.get("contribution_source_quote", "")
        awarded = lc.get("found_awarded_amount")
        revenue = lc.get("found_revenue")

        # 利润率是否被采信（Binary）
        if s6r:
            is_accepted = 1 if s6r.get("court_adopted_specific_value") is True else 0
        else:
            is_accepted = 1 if margin_pct is not None else 0

        # 证据层级
        if s6r:
            et = s6r.get("evidence_type") or "信息不足无法判断"
            tier = TIER_MAP.get(et, 0)
        else:
            tier = infer_evidence_tier_from_quote(margin_quote)

        industry = r1r.get("industry_category") or "未知行业"
        comp_method = r1r.get("compensation_method") or "未知"
        plaintiff_claim = r1r.get("plaintiff_claimed_amount")
        r1_awarded = r1r.get("court_awarded_amount")

        # ── 构造控制变量 ──────────────────────────────────────────────
        trial_year_raw = extract_year_from_caseid(cid)
        trial_year_centered = (trial_year_raw - TRIAL_YEAR_BASE) if trial_year_raw else None
        province = extract_province_from_caseid(cid)
        court_lvl_str = extract_court_level_from_caseid(cid)
        court_lvl_ord = court_level_ordinal(court_lvl_str)
        coastal = is_coastal_province(province)

        # has_lawyer：round1 中该字段几乎全为空，作为可选控制变量纳入
        lawyer_raw = r1r.get("代理律师")
        has_lawyer = 1 if (
            lawyer_raw and str(lawyer_raw).strip()
            and str(lawyer_raw).strip() not in ("nan", "None", "")
        ) else 0

        rows.append({
            "case_id": cid,
            "industry": industry,
            "compensation_method": comp_method,
            "court_adopted_margin_pct": margin_pct,
            "court_adopted_contribution_pct": contrib_pct,
            "margin_raw": str(margin_raw) if margin_raw else None,
            "contrib_raw": str(contrib_raw) if contrib_raw else None,
            "margin_source_quote": margin_quote,
            "contrib_source_quote": contrib_quote,
            "awarded_amount": (
                awarded if (awarded and awarded > 0)
                else (r1_awarded if (r1_awarded and r1_awarded > 0) else None)
            ),
            "revenue": revenue if (revenue and revenue > 0) else None,
            "plaintiff_claimed_amount": (
                plaintiff_claim if (plaintiff_claim and plaintiff_claim > 0) else None
            ),
            "is_margin_accepted": is_accepted,
            "evidence_tier": tier,
            "tier_1": 1 if tier == 1 else 0,
            "tier_2": 1 if tier == 2 else 0,
            "tier_3": 1 if tier == 3 else 0,
            "tier_0": 1 if tier == 0 else 0,
            "is_statutory": 1 if "法定赔偿" in str(comp_method) else 0,
            # 控制变量
            "trial_year_raw": trial_year_raw,
            "trial_year": trial_year_centered,  # 中心化：2019=0
            "province": province,
            "court_level_str": court_lvl_str,
            "court_level_ordinal": court_lvl_ord,
            "is_coastal": coastal,
            "has_lawyer": has_lawyer,
        })

    df = pd.DataFrame(rows)
    print(f"  合并后总行数: {len(df)}")
    print(f"  利润率被采信(1): {df['is_margin_accepted'].sum()}")
    print(f"  利润率被采信(0): {(df['is_margin_accepted'] == 0).sum()}")
    print(f"  Tier 分布: 1={df['tier_1'].sum()}, 2={df['tier_2'].sum()}, 3={df['tier_3'].sum()}, 0={df['tier_0'].sum()}")
    print(f"  数据来源说明: {data_source}")
    # 控制变量诊断
    for cv in ["trial_year", "court_level_ordinal", "is_coastal", "has_lawyer"]:
        n_valid = df[cv].notna().sum()
        n_unique = df[cv].nunique()
        flag = " **常量!" if n_unique < 2 else ""
        print(f"  {cv}: {n_valid} 有效值, {n_unique} 唯一值{flag}")
    return df


def _check_var_variation(series: pd.Series, var_name: str) -> bool:
    """检查变量是否有足够变异用于回归（至少 2 个唯一值，非全 NaN）。"""
    clean = series.dropna()
    if len(clean) < 2:
        return False
    if clean.nunique() < 2:
        return False
    return True


# ── Model 1: Logit ────────────────────────────────────────────────────────
def run_logit_model(df: pd.DataFrame, lines: list):
    """Logit 回归：证据层级 → 法院采信利润率概率"""
    lines.append("## Model 1: Logit 回归 — 证据层级对法院采信利润率的影响\n")
    lines.append("**研究问题**：证据层级（Tier 1/2/3）是否显著影响法院采信原告利润率的概率？\n")
    lines.append("**模型设定**：")
    lines.append("```")
    lines.append("Y = is_margin_accepted (Binary: 1=法院采信具体利润率数值, 0=酌定/不采信)")
    lines.append("X = tier_1 (dummy), tier_2 (dummy), tier_3 (dummy)  [参照组: tier_0 无具体证据]")
    lines.append("```\n")

    # 各证据层级采信率描述统计
    tier_counts = df.groupby("evidence_tier")["is_margin_accepted"].agg(["count", "sum", "mean"])
    lines.append("### 各证据层级采信率描述统计\n")
    lines.append("| 证据层级 | 案件数 | 采信数 | 采信率 | 备注 |")
    lines.append("|---------|--------|--------|--------|------|")
    for t in [1, 2, 3, 0]:
        if t in tier_counts.index:
            r = tier_counts.loc[t]
            note = ""
            if r["mean"] == 1.0 and r["count"] > 0:
                note = "（该层级所有案件均被采信，无变异）"
            elif r["mean"] == 0.0 and r["count"] > 0:
                note = "（该层级无案件被采信）"
            lines.append(
                f"| Tier {t} | {int(r['count'])} | {int(r['sum'])} "
                f"| {r['mean']*100:.1f}% | {note} |"
            )
        else:
            lines.append(f"| Tier {t} | 0 | 0 | — | 无该层级案件 |")
    lines.append("")

    # 检查每个 tier 是否有足够变异
    valid_tiers = []
    for t in [1, 2, 3]:
        grp = df[df[f"tier_{t}"] == 1]
        n = len(grp)
        if n >= 5 and grp["is_margin_accepted"].nunique() >= 2:
            valid_tiers.append(f"tier_{t}")
        elif n > 0 and grp["is_margin_accepted"].nunique() < 2:
            rate = grp["is_margin_accepted"].mean()
            lines.append(
                f"> 注：Tier {t} 有 {n} 件案件，采信率 {rate*100:.0f}%（无变异），已从 Logit 模型中排除。"
                f"{'该层级证据被法院 100% 采信，是极强的正向信号。' if rate == 1.0 else ''}\n"
            )
        else:
            lines.append(f"> 注：Tier {t} 样本量不足（n={n}），已从模型中排除。\n")

    if len(valid_tiers) < 1:
        lines.append(
            "> **警告**：证据层级变量均无足够变异，无法估计 Logit 模型。"
            "请先运行 Step 006 获取完整证据分类数据。\n"
        )
        lines.append("")
        return

    X_vars = valid_tiers
    X = sm.add_constant(df[X_vars].astype(float))
    y = df["is_margin_accepted"].astype(float)
    # 对齐索引（drop NaN in y）
    mask = y.notna()
    X = X.loc[mask]
    y = y.loc[mask]

    try:
        model = sm.Logit(y, X)
        result = model.fit(disp=False)
    except Exception as e:
        lines.append(f"> **模型估计失败**：{e}\n")
        lines.append("")
        return

    lines.append("### Stata 风格回归表\n")
    lines.append("```")
    lines.append(result.summary2().as_latex() if hasattr(result.summary2(), 'as_latex') else str(result.summary()))
    lines.append("```\n")

    # 纯文本系数表
    lines.append("#### 系数解读\n")
    lines.append("| 变量 | 系数 | 标准误 | z值 | p值 | Odds Ratio |")
    lines.append("|------|------|--------|-----|-----|-----------|")
    for var in result.params.index:
        coef = result.params[var]
        se = result.bse[var]
        zval = result.tvalues[var]
        pval = result.pvalues[var]
        or_ = np.exp(coef) if var != "const" else float("nan")
        or_str = f"{or_:.4f}" if var != "const" else "—"
        sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
        lines.append(
            f"| {var}{sig} | {coef:.4f} | {se:.4f} | {zval:.4f} | {pval:.4f} | {or_str} |"
        )
    lines.append("")
    lines.append(f"*Pseudo R² = {result.prsquared:.4f}*  |  *N = {int(result.nobs)}*\n")

    # 法学解读
    lines.append("### 法学解读\n")
    lines.append(f"- **Pseudo R² = {result.prsquared:.4f}**：模型整体解释力。\n")

    for var in valid_tiers:
        coef = result.params[var]
        pval = result.pvalues[var]
        or_ = np.exp(coef)
        tier_label = var.replace("tier_", "Tier ")
        if pval < 0.01:
            sig = "（在 1% 水平上显著）"
            sig_note = "***"
        elif pval < 0.05:
            sig = "（在 5% 水平上显著）"
            sig_note = "**"
        elif pval < 0.10:
            sig = "（在 10% 水平上显著）"
            sig_note = "*"
        else:
            sig = "（不显著）"
            sig_note = ""

        lines.append(
            f"- **{tier_label}{sig_note}**：系数 = {coef:.4f}，p = {pval:.4f} {sig}。"
            f"相对于 Tier 0（无具体经济证据），{tier_label} 证据使法院采信具体利润率的"
            f"对数几率增加 {coef:.4f}（Odds Ratio = {or_:.4f}）。"
        )
        if pval < 0.10:
            lines.append(
                f"  **法学含义**：{tier_label} 级证据的提交显著提高法院采信精确经济数据的可能性，"
                f"验证了「证据质量越高 → 法院越可能依据精确数据裁判」的假设。"
            )
        else:
            lines.append(
                f"  在统计上不显著，可能因该层级样本量不足或法院裁量权过大导致。"
            )
    lines.append("")


# ── Model 2: ANOVA ────────────────────────────────────────────────────────
def run_anova(df: pd.DataFrame, lines: list):
    """One-Way ANOVA：行业间利润率认定差异"""
    lines.append("## Model 2: One-Way ANOVA — 行业间利润率认定的系统性差异\n")
    lines.append("**研究问题**：不同行业的法院认定利润率是否存在统计上显著的系统性差异？\n")
    lines.append("**模型设定**：")
    lines.append("```")
    lines.append("H0: μ_industry_1 = μ_industry_2 = ... = μ_industry_k")
    lines.append("H1: 至少有一个行业的平均利润率与其他行业不同")
    lines.append("因变量: court_adopted_margin_pct (连续变量, 法院采信的具体利润率数值)")
    lines.append("```\n")

    anova_df = df[df["court_adopted_margin_pct"].notna()].copy()
    industry_sizes = anova_df.groupby("industry").size()
    valid_industries = industry_sizes[industry_sizes >= 3].index
    anova_df = anova_df[anova_df["industry"].isin(valid_industries)]

    lines.append("### 描述统计\n")
    lines.append(f"- 有效观测值（含数值利润率的案件）：{len(anova_df)}")
    lines.append(f"- 行业数（每组 ≥3 观测）：{len(valid_industries)}")
    lines.append(f"- 全样本利润率均值：{anova_df['court_adopted_margin_pct'].mean():.2f}%")
    lines.append(f"- 全样本利润率标准差：{anova_df['court_adopted_margin_pct'].std():.2f}%\n")

    if len(valid_industries) < 2:
        lines.append("> **警告**：有效行业组数不足 2，无法执行 ANOVA。\n")
        lines.append("")
        return

    # 按行业列出基础统计
    lines.append("### 分行业利润率统计\n")
    lines.append("| 行业 | 案件数 | 均值(%) | 标准差(%) | 最小值(%) | 最大值(%) |")
    lines.append("|------|--------|---------|----------|----------|----------|")
    for ind, grp in anova_df.groupby("industry"):
        lines.append(
            f"| {ind} | {len(grp)} "
            f"| {grp['court_adopted_margin_pct'].mean():.2f} "
            f"| {grp['court_adopted_margin_pct'].std():.2f} "
            f"| {grp['court_adopted_margin_pct'].min():.2f} "
            f"| {grp['court_adopted_margin_pct'].max():.2f} |"
        )
    lines.append("")

    # 执行 ANOVA
    groups = [
        grp["court_adopted_margin_pct"].dropna().values
        for _, grp in anova_df.groupby("industry")
    ]
    try:
        f_stat, p_val = scipy_stats.f_oneway(*groups)
    except Exception as e:
        lines.append(f"> **ANOVA 执行失败**：{e}\n")
        lines.append("")
        return

    sig_label = (
        "*** p<0.01" if p_val < 0.01
        else "** p<0.05" if p_val < 0.05
        else "* p<0.10" if p_val < 0.10
        else "Not significant"
    )
    lines.append("### ANOVA 结果\n")
    lines.append("```")
    lines.append(f"F-statistic: {f_stat:.4f}")
    lines.append(f"p-value:     {p_val:.4f}")
    lines.append(f"Significance: {sig_label}")
    lines.append("```\n")

    lines.append("### 法学解读\n")
    if p_val < 0.05:
        lines.append(
            f"- **行业间利润率存在显著差异**（F = {f_stat:.4f}，p = {p_val:.4f} < 0.05）。"
            f"拒绝原假设，说明不同行业的法院认定利润率在统计上存在系统性差异。\n"
            f"- **法学含义**：支持「同案不同判」的实证存在——"
            f"不同行业的类似侵权行为可能因行业利润率证据的可获得性差异而面临不同判赔结果。"
            f"为统一裁判尺度、建立行业利润率参考基准数据库提供了统计学依据。\n"
        )
    else:
        lines.append(
            f"- 行业间利润率差异不显著（F = {f_stat:.4f}，p = {p_val:.4f} > 0.05）。"
            f"不能拒绝原假设，行业间利润率认定的差异在统计上不显著。\n"
            f"- **法学含义**：现有样本量有限（n = {len(anova_df)}），"
            f"可能不足以检测行业间的真实差异。建议在后续研究中扩大高价值案件样本。\n"
        )

    # Effect size (η²)
    grand_mean = anova_df["court_adopted_margin_pct"].mean()
    ss_between = sum(
        len(grp) * (grp["court_adopted_margin_pct"].mean() - grand_mean) ** 2
        for _, grp in anova_df.groupby("industry")
    )
    ss_total = sum(
        (val - grand_mean) ** 2 for val in anova_df["court_adopted_margin_pct"]
    )
    eta_sq = ss_between / ss_total if ss_total > 0 else 0
    lines.append(f"- **效应量 η² = {eta_sq:.4f}**：行业因素解释了利润率差异的 {eta_sq*100:.1f}%。\n")

    lines.append("")


# ── Model 3: OLS with Controls ─────────────────────────────────────────────
def run_ols_model(df: pd.DataFrame, lines: list):
    """OLS 回归（HC1 稳健标准误）含完整控制变量。"""
    lines.append("## Model 3: OLS 回归 — 利润率/贡献率对判赔金额的边际效应\n")
    lines.append(
        "**研究问题**：在控制法院层级、年份、地区经济水平和律师代理后，"
        "法院认定的利润率和贡献率对判赔金额的边际影响？\n"
    )
    lines.append("**模型设定**：")
    lines.append("```")
    lines.append("ln(Awarded_i) = β0 + β1·ProfitMargin_i + β2·ContributionRate_i")
    lines.append("               + β3·CourtLevel_i + β4·TrialYear_i(centered) + β5·IsCoastal_i")
    lines.append("               + β6·HasLawyer_i(if varied) + ε_i")
    lines.append(f"注: TrialYear_i = 实际年份 - {TRIAL_YEAR_BASE}（中心化处理，消除多重共线性）")
    lines.append("使用 HC1 稳健标准误（异方差一致估计）")
    lines.append("```\n")

    ols_df = df.copy()
    ols_df["ln_awarded"] = np.log(ols_df["awarded_amount"].clip(lower=1))

    # 动态控制变量列表（自动排除常量/零方差变量）
    CONTROL_CANDIDATES = {
        "court_level_ordinal": "法院层级",
        "trial_year": f"审判年份（-{TRIAL_YEAR_BASE}）",
        "is_coastal": "沿海地区",
        "has_lawyer": "律师代理",
    }
    # 诊断各控制变量
    control_diag = []
    for cv, cv_label in CONTROL_CANDIDATES.items():
        n_valid = ols_df[cv].notna().sum()
        n_unique = ols_df[cv].dropna().nunique() if n_valid > 0 else 0
        usable = n_valid > 0 and n_unique >= 2
        control_diag.append(f"{cv_label}: {n_valid}有效, {n_unique}唯一值{' ✓' if usable else ' ✗（排除）'}")

    lines.append("### 控制变量诊断\n")
    for d in control_diag:
        lines.append(f"- {d}")
    lines.append("")

    # 选出可用的控制变量（非 all-NaN 且有 >=2 个唯一值）
    available_controls = [
        cv for cv, cv_label in CONTROL_CANDIDATES.items()
        if (ols_df[cv].notna().sum() > 0 and ols_df[cv].dropna().nunique() >= 2)
    ]
    # 构建变量标签
    var_labels_full = {
        "court_adopted_margin_pct": "利润率 (%)",
        "court_adopted_contribution_pct": "贡献率 (%)",
        "court_level_ordinal": "法院层级",
        "trial_year": f"审判年份（-{TRIAL_YEAR_BASE}）",
        "is_coastal": "沿海地区",
        "has_lawyer": "律师代理",
    }

    lines.append(
        f"**实际纳入控制变量**：{', '.join(CONTROL_CANDIDATES[cv] for cv in available_controls)}"
        if available_controls else "**无可用控制变量**"
    )
    lines.append("")

    # ---- Specification 1: Profit Margin + Controls ----
    spec1 = ols_df[
        ols_df["court_adopted_margin_pct"].notna()
        & ols_df["ln_awarded"].notna()
        & np.isfinite(ols_df["ln_awarded"])
    ].copy()
    n1 = len(spec1)

    lines.append(f"### Specification 1: ln(Awarded) ~ Profit_Margin + Controls (n = {n1})\n")
    if n1 >= 15:
        _ols_with_controls(
            spec1,
            x_vars=["court_adopted_margin_pct"] + available_controls,
            y_col="ln_awarded",
            var_labels=var_labels_full,
            lines=lines,
        )
    else:
        lines.append(f"> **样本量不足**（n = {n1}，需 ≥15），跳过。\n")

    # ---- Specification 2: Profit Margin + Contribution Rate + Controls ----
    MIN_N_SPEC2 = 20  # 从 5 提升至 20，避免 n=6 时的严重过拟合
    spec2 = ols_df[
        ols_df["court_adopted_margin_pct"].notna()
        & ols_df["court_adopted_contribution_pct"].notna()
        & ols_df["ln_awarded"].notna()
        & np.isfinite(ols_df["ln_awarded"])
    ].copy()
    n2 = len(spec2)

    lines.append(
        f"### Specification 2: ln(Awarded) ~ Profit_Margin + Contribution_Rate + Controls (n = {n2})\n"
    )
    if n2 >= MIN_N_SPEC2:
        _ols_with_controls(
            spec2,
            x_vars=["court_adopted_margin_pct", "court_adopted_contribution_pct"] + available_controls,
            y_col="ln_awarded",
            var_labels=var_labels_full,
            lines=lines,
        )
    elif n2 > 0:
        lines.append(
            f"> **样本量不足**（n = {n2}，需 ≥{MIN_N_SPEC2}），跳过。"
            f"贡献率数据极为稀疏（全样本仅 {ols_df['court_adopted_contribution_pct'].notna().sum()} 件），"
            f"强行估计将导致严重过拟合。建议在后续研究中扩大含贡献率认定的案件样本。\n"
        )
    else:
        lines.append(f"> 无同时含利润率和贡献率的案件，跳过。\n")

    lines.append("")


def _ols_with_controls(data, x_vars, y_col, var_labels, lines):
    """OLS + HC1 含控制变量，输出回归表 + 纯文本系数表。"""
    # Drop rows with NaN in any model variable
    model_vars = [v for v in x_vars if v != "has_lawyer" or _check_var_variation(data.get(v), v)]
    # 二次过滤：确保每个变量在 clean data 中仍有 >=2 唯一值
    model_vars_filtered = []
    for v in x_vars:
        if v not in data.columns:
            continue
        clean_vals = data[v].dropna()
        if len(clean_vals) > 0 and clean_vals.nunique() >= 2:
            model_vars_filtered.append(v)
        else:
            lines.append(f"> 注：变量 `{v}` 为零方差或常量，已从该 Specification 中自动排除。\n")

    model_vars = model_vars_filtered
    all_vars = model_vars + [y_col]
    data_clean = data[all_vars].dropna()
    n_used = len(data_clean)

    if n_used < 10:
        lines.append(f"> **有效样本量不足**（n = {n_used}），跳过回归。\n")
        return

    X = sm.add_constant(data_clean[model_vars].astype(float))
    y = data_clean[y_col].astype(float)

    try:
        model = sm.OLS(y, X)
        result = model.fit(cov_type="HC1")
    except Exception as e:
        lines.append(f"> OLS 估计失败：{e}\n")
        return

    lines.append("#### 回归结果\n")
    lines.append("```")
    lines.append(result.summary2().as_latex() if hasattr(result.summary2(), 'as_latex') else str(result.summary()))
    lines.append("```\n")

    lines.append(f"**N = {n_used}** | **R² = {result.rsquared:.4f}** | **Adj. R² = {result.rsquared_adj:.4f}**\n")

    # 纯文本系数表
    lines.append("#### 系数解读\n")
    lines.append("| 变量 | 系数 | 稳健标准误 | t值 | p值 | 显著性 |")
    lines.append("|------|------|-----------|-----|-----|--------|")
    for var in result.params.index:
        coef = result.params[var]
        se = result.bse[var] if var in result.bse.index else float("nan")
        tval = result.tvalues[var] if var in result.tvalues.index else float("nan")
        pval = result.pvalues[var] if var in result.pvalues.index else float("nan")
        sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
        label = var if var == "const" else var_labels.get(var, var)
        lines.append(f"| {label}{sig} | {coef:.4f} | {se:.4f} | {tval:.4f} | {pval:.4f} | {sig} |")
    lines.append("")

    lines.append("#### 法学解读\n")
    for var in model_vars:
        if var not in result.params:
            continue
        coef = result.params[var]
        pval = result.pvalues[var]
        sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
        label = var_labels.get(var, var)

        if var == "court_adopted_margin_pct":
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"在控制其他变量后，法院认定的利润率每提高1个百分点，"
                f"判赔金额约增加 {coef*100:.2f}%。"
            )
        elif var == "court_adopted_contribution_pct":
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"在控制其他变量后，贡献率每提高1个百分点，判赔金额约变动 {coef*100:.2f}%。"
            )
        elif var == "court_level_ordinal":
            direction = "更高" if coef > 0 and pval < 0.10 else "无显著方向性"
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"法院层级每提高一级，判赔金额约变化 {coef*100:.2f}%。"
                f"{'高层级法院倾向于判定更高赔偿额。' if coef > 0 and pval < 0.10 else ''}"
            )
        elif var == "trial_year":
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"以 {TRIAL_YEAR_BASE} 年为基准，每推进一年，判赔金额约变化 {coef*100:.2f}%。"
                f"{'赔偿标准呈逐年上升趋势。' if coef > 0 and pval < 0.10 else ''}"
            )
        elif var == "is_coastal":
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"沿海地区（经济发达省份）与其他地区之间的判赔金额差异。"
                f"{'沿海地区判赔显著更高。' if coef > 0 and pval < 0.10 else ''}"
            )
        elif var == "has_lawyer":
            lines.append(
                f"- **{label} 系数 = {coef:.4f} {sig}（p = {pval:.4f}）**："
                f"原告委托律师对判赔金额的边际效应。"
                f"{'律师代理显著提高判赔金额。' if coef > 0 and pval < 0.10 else ''}"
            )
    lines.append("")


# ── Model C: Tobit (Censored Regression) ───────────────────────────────────
def run_tobit_model(df: pd.DataFrame, lines: list):
    """Tobit 截断回归 — 修正法定赔偿上限导致的截断偏误。

    使用 ln(Awarded) 作为因变量以与 OLS Model 3 保持一致。
    截断上限为 ln(¥5,000,000) ≈ 15.42。
    """
    lines.append("## Model C: Tobit 截断回归 — 法定赔偿上限下的偏误修正\n")
    lines.append("### 方法选择：Why Tobit instead of Heckman\n")
    lines.append(
        "Heckman 两阶段模型要求一个有效的工具变量（排他性约束）：该变量须影响"
        "「是否选择法定赔偿」但**不直接影响**最终判赔金额。在司法数据中，几乎不存在"
        "这样的变量——影响法院选择法定赔偿的因素（证据质量、侵权规模、原告举证能力）"
        "本身就是判赔金额的核心决定因素。强行使用 Heckman 会导致模型识别失败和误导性结论。\n"
    )
    lines.append(
        "相比之下，**Tobit 截断回归**更适合本研究的法律场景："
        "法定赔偿制度设置了上下限（例如旧法 ¥3,000,000、新法 ¥5,000,000），"
        "导致实际判赔金额被截断（censored）——法院可能认定更高或更低的金额，"
        "但受限于法定赔偿的边界而无法在判决中体现。Tobit 模型通过最大似然估计（MLE）"
        "同时利用截断观测值和非截断观测值的信息，因此能更准确估计各因素的真实边际效应。\n"
    )
    lines.append("**模型设定**：")
    lines.append("```")
    lines.append("ln(Damages_i*) = X_i·β + ε_i,  ε_i ~ N(0, σ²)    [latent variable]")
    lines.append(
        "ln(Damages_i) = max(ln(1), min(ln(5,000,000), ln(Damages_i*)))  [censored]"
    )
    lines.append("```")
    lines.append(
        "其中 X_i 包含：ProfitMargin_i, CourtLevel_i, "
        f"TrialYear_i(centered), IsCoastal_i, HasLawyer_i(if varied). "
        "因变量与 Model 3 一致使用 ln(Awarded)，确保系数可比。\n"
    )

    tobit_df = df.copy()
    tobit_df = tobit_df[
        tobit_df["awarded_amount"].notna() & (tobit_df["awarded_amount"] > 0)
    ]
    # 使用 log 尺度，与 OLS 一致
    tobit_df["ln_awarded"] = np.log(tobit_df["awarded_amount"].clip(lower=1))

    if len(tobit_df) < 20:
        lines.append(f"> **Tobit 模型样本量不足**（n = {len(tobit_df)}），跳过。\n")
        lines.append("")
        return

    # 截断点（log 尺度）
    LN_UPPER = np.log(5_000_000)   # ≈ 15.42
    LN_LOWER = np.log(1)           # = 0.0

    # 构建自变量列表（排除零方差变量）
    x_candidates = [
        ("court_adopted_margin_pct", "利润率"),
        ("court_level_ordinal", "法院层级"),
        ("trial_year", f"审判年份（-{TRIAL_YEAR_BASE}）"),
        ("is_coastal", "沿海地区"),
        ("has_lawyer", "律师代理"),
    ]
    x_vars = []
    for xv, xlabel in x_candidates:
        if xv not in tobit_df.columns:
            continue
        clean_vals = tobit_df[xv].dropna()
        if len(clean_vals) > 0 and clean_vals.nunique() >= 2:
            x_vars.append(xv)
        else:
            lines.append(f"> 注：`{xv}`（{xlabel}）为零方差/常量，已从 Tobit 中排除。\n")

    if not x_vars:
        lines.append("> **无可用自变量**，跳过 Tobit 估计。\n")
        lines.append("")
        return

    data_clean = tobit_df[x_vars + ["ln_awarded", "awarded_amount"]].dropna()
    data_clean = data_clean[np.isfinite(data_clean[x_vars]).all(axis=1)]
    n_tobit = len(data_clean)

    at_cap = (data_clean["awarded_amount"] >= 5_000_000).sum()
    lines.append(f"### 结果（n = {n_tobit}，截断上限 = ln(¥5,000,000) ≈ {LN_UPPER:.2f}）\n")
    lines.append(f"- 截断于上限的案件：{at_cap}（{at_cap/n_tobit*100:.1f}%）\n")
    lines.append(f"- 因变量：ln(Awarded)，与 Model 3 OLS 保持一致\n")

    if n_tobit < 20:
        lines.append(f"> **有效样本量不足**，跳过 Tobit 估计。\n")
        lines.append("")
        return

    X_arr = sm.add_constant(data_clean[x_vars].astype(float)).values
    y_arr = data_clean["ln_awarded"].astype(float).values

    try:
        # OLS 基准（log 尺度，与 Model 3 可比）
        ols_model = sm.OLS(y_arr, X_arr)
        ols_result = ols_model.fit(cov_type="HC1")

        lines.append("#### Tobit MLE 参数估计\n")

        from scipy.optimize import minimize
        from scipy.stats import norm as scipy_norm

        def tobit_loglik(params, X, y, lower, upper):
            beta = params[:-1]
            sigma = np.exp(params[-1])
            xb = X @ beta
            ll = 0.0
            # Uncensored
            mask_uncensored = (y > lower) & (y < upper)
            if mask_uncensored.sum() > 0:
                resid = y[mask_uncensored] - xb[mask_uncensored]
                ll += np.sum(
                    -0.5 * np.log(2 * np.pi) - np.log(sigma)
                    - 0.5 * (resid / sigma) ** 2
                )
            # Left censored
            mask_left = y <= lower
            if mask_left.sum() > 0:
                ll += np.sum(scipy_norm.logcdf((lower - xb[mask_left]) / sigma))
            # Right censored
            mask_right = y >= upper
            if mask_right.sum() > 0:
                ll += np.sum(scipy_norm.logsf((upper - xb[mask_right]) / sigma))
            return -ll

        init_params = np.append(np.asarray(ols_result.params), np.log(y_arr.std()))
        result = minimize(
            tobit_loglik, init_params,
            args=(X_arr, y_arr, LN_LOWER, LN_UPPER),
            method="L-BFGS-B",
        )

        if result.success:
            beta_tobit = result.x[:-1]
            sigma_tobit = np.exp(result.x[-1])

            lines.append("| 变量 | OLS (Naive) | Tobit (Corrected) | 偏差方向 |")
            lines.append("|------|------------|-------------------|---------|")
            var_names = ["const"] + x_vars
            var_labels_display = {
                "const": "截距",
                "court_adopted_margin_pct": "利润率",
                "court_level_ordinal": "法院层级",
                "trial_year": f"审判年份（-{TRIAL_YEAR_BASE}）",
                "is_coastal": "沿海地区",
                "has_lawyer": "律师代理",
            }
            max_abs_bias_substantive = 0.0  # 排除截距，只看实质性变量
            for i, vn in enumerate(var_names):
                ols_coef = ols_result.params[i]
                tobit_coef = beta_tobit[i]
                bias = tobit_coef - ols_coef
                if vn != "const":
                    max_abs_bias_substantive = max(max_abs_bias_substantive, abs(bias))
                bias_dir = "↑" if bias > 0.001 else "↓" if bias < -0.001 else "="
                lines.append(
                    f"| {var_labels_display.get(vn, vn)} "
                    f"| {ols_coef:.4f} | {tobit_coef:.4f} "
                    f"| {bias_dir} ({bias:+.4f}) |"
                )

            lines.append(f"\n**σ (残差标准差) = {sigma_tobit:.4f}**（log 尺度）\n")

            # 数据驱动的法学解读
            lines.append("#### 法学解读\n")
            if max_abs_bias_substantive < 0.02:
                lines.append(
                    f"- **Tobit 与 OLS 实质性系数近乎一致**"
                    f"（最大偏差 {max_abs_bias_substantive:.4f}），"
                    f"因仅 {at_cap} 件案件（{at_cap/n_tobit*100:.1f}%）触及法定赔偿上限，"
                    f"截断偏误在本样本中对核心参数估计影响极小。\n"
                    f"- **方法论含义**：Tobit 框架已正确建立并正常运行，"
                    f"当未来样本中截断比例提高时（如更多高判赔案件），"
                    f"Tobit 修正将发挥更大作用。"
                    f"当前低截断率下 OLS 与 Tobit 结论一致，增强了 OLS 发现的可靠性。\n"
                    f"- **政策含义**：法定赔偿上限（¥5M）对绝大多数案件不构成紧约束，"
                    f"判赔金额的差异主要由证据质量、侵权行为特征等实质因素驱动，"
                    f"而非制度性上限压制。\n"
                )
            else:
                lines.append(
                    f"- **Tobit 修正后实质性系数出现系统性偏移**"
                    f"（最大偏差 {max_abs_bias_substantive:.4f}），"
                    f"表明法定赔偿上限对观测判赔金额产生了显著截断偏误，"
                    f"OLS 估计存在不可忽略的偏误。\n"
                    f"- **政策含义**：如果法定赔偿上限进一步提升，"
                    f"Tobit 模型预测的实际判赔金额将相应释放，为立法评估提供量化依据。\n"
                )
        else:
            lines.append(f"> Tobit MLE 优化未收敛：{result.message}\n")

    except Exception as e:
        lines.append(f"> Tobit 估计异常：{e}\n")

    lines.append("")


# ── 附录：探索性数据统计 ──────────────────────────────────────────────────
def appendix_stats(df: pd.DataFrame, lines: list):
    """附加统计：判赔金额分布、法定赔偿率、诉请支持率。"""
    lines.append("## 附录：探索性数据统计\n")

    valid_awarded = df["awarded_amount"].dropna()
    valid_claim = df["plaintiff_claimed_amount"].dropna()

    if len(valid_awarded) > 0:
        lines.append("### 判赔金额分布\n")
        lines.append("| 统计量 | 值 |")
        lines.append("|--------|-----|")
        for label, val in [
            ("案件数", f"{len(valid_awarded)}"),
            ("均值", f"¥{valid_awarded.mean():,.0f}"),
            ("中位数", f"¥{valid_awarded.median():,.0f}"),
            ("标准差", f"¥{valid_awarded.std():,.0f}"),
            ("最小值", f"¥{valid_awarded.min():,.0f}"),
            ("P25", f"¥{valid_awarded.quantile(0.25):,.0f}"),
            ("P75", f"¥{valid_awarded.quantile(0.75):,.0f}"),
            ("最大值", f"¥{valid_awarded.max():,.0f}"),
        ]:
            lines.append(f"| {label} | {val} |")
        lines.append("")

    lines.append("### 法定赔偿适用率\n")
    stat_rate = df["is_statutory"].mean() * 100
    lines.append(
        f"- {stat_rate:.1f}% 的高价值案件中法院适用了法定赔偿"
        f"（{int(df['is_statutory'].sum())}/{len(df)}）。\n"
    )

    # 诉请支持率
    common = df[
        df["plaintiff_claimed_amount"].notna()
        & df["awarded_amount"].notna()
        & (df["plaintiff_claimed_amount"] > 0)
    ]
    if len(common) > 0:
        common = common.copy()
        common["support_rate"] = common["awarded_amount"] / common["plaintiff_claimed_amount"]
        lines.append("### 原告诉请支持率\n")
        lines.append(f"- 有效案件数：{len(common)}")
        lines.append(f"- 均值：{common['support_rate'].mean()*100:.1f}%")
        lines.append(f"- 中位数：{common['support_rate'].median()*100:.1f}%")
        lines.append(
            f"- 诉请支持率 > 50% 的案件："
            f"{(common['support_rate'] > 0.5).sum()} 件"
            f"（{(common['support_rate'] > 0.5).mean()*100:.1f}%）\n"
        )

    # 利润率 vs. 法定赔偿
    lines.append("### 利润率采信 × 法定赔偿交叉表\n")
    ct = pd.crosstab(
        df["is_margin_accepted"], df["is_statutory"], margins=True
    )
    ct.index = ["酌定/不采信", "采信具体利润率", "合计"]
    ct.columns = ["非 法定赔偿", "法定赔偿", "合计"]
    lines.append(ct.to_markdown())
    lines.append("\n")


# ── 主入口 ────────────────────────────────────────────────────────────────
def main():
    start_time = time.time()
    print("=" * 60)
    print("Step 15: 计量经济学建模分析 (v2.1)")
    print("=" * 60)

    # 检查关键输入文件
    print("\n[0/3] 检查输入文件...")
    missing = []
    for path, label in [
        (PATH_ROUND1, "round1 (clean/)"),
        (PATH_ROUND2, "round2 (pipeline_v2/)"),
    ]:
        if path.exists():
            print(f"  ✓ {label}: {path.name}")
        else:
            print(f"  ✗ FATAL: {label} 不存在: {path}")
            missing.append(str(path))
    if PATH_STEP006.exists():
        print(f"  ✓ step006 (pipeline_v2/): {PATH_STEP006.name}")
    else:
        print(f"  ! step006 缺失，将回退到 round2 margin_source_quote 推断 Tier")

    if missing:
        print(f"\nFATAL: {len(missing)} 个关键输入文件缺失，无法继续。")
        sys.exit(1)

    print("\n[1/3] 构建数据集...")
    df = build_dataset()

    lines = []
    lines.append("# 商标侵权赔偿计量经济学分析报告")
    lines.append("")
    lines.append(f"> Step 15 (v2.1) 自动生成 | 数据来源：round1 (clean/) + round2 + step006 (pipeline_v2/)")
    lines.append(f"> 分析样本：{len(df)} 件高价值商标侵权案件")
    lines.append(f"> 模型时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    print("\n[2/3] 执行计量模型...")

    # 数据完整性提示
    n_margin = df["court_adopted_margin_pct"].notna().sum()
    n_contrib = df["court_adopted_contribution_pct"].notna().sum()
    n_both = (
        df["court_adopted_margin_pct"].notna()
        & df["court_adopted_contribution_pct"].notna()
    ).sum()

    lines.append("## 数据概览\n")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 总案件数 | {len(df)} |")
    lines.append(f"| 含具体利润率数值 | {n_margin}（{n_margin/len(df)*100:.1f}%） |")
    lines.append(f"| 含具体贡献率数值 | {n_contrib}（{n_contrib/len(df)*100:.1f}%） |")
    lines.append(f"| 两者均有 | {n_both}（{n_both/len(df)*100:.1f}%） |")
    lines.append(f"| 证据层级可映射 | {df['evidence_tier'].notna().sum()} |")
    lines.append(f"| 法定赔偿适用率 | {df['is_statutory'].mean()*100:.1f}% |")
    lines.append("")

    if n_margin < 10:
        lines.append(
            f"> **重要提示**：仅有 {n_margin} 件案件含有具体利润率数值，定量分析的统计功效有限。"
            f"以下结论应作为探索性发现而非确证性结论来解读。"
            f"建议在后续研究中扩大样本或采用贝叶斯方法。\n"
        )

    run_logit_model(df, lines)
    run_anova(df, lines)
    run_ols_model(df, lines)
    run_tobit_model(df, lines)
    appendix_stats(df, lines)

    lines.append("---\n")
    lines.append(
        f"*分析完成。原始数据与脚本位于 `/Users/weiyueshao/Desktop/pipeline_v2/`*。\n"
        f"*改进版 (v2.1)：trial_year 中心化、控制变量自动诊断、Tobit 修复、输出前缀规范。*\n"
    )

    report = "\n".join(lines)
    OUTPUT_MD.write_text(report, encoding="utf-8")
    print(f"\n[3/3] 报告已写入: {OUTPUT_MD}")

    # Console 摘要
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Step 15 计量分析 — 摘要")
    print("=" * 60)
    print(f"  总案件数:           {len(df)}")
    print(f"  含利润率数值:        {n_margin} ({n_margin/len(df)*100:.1f}%)")
    print(f"  含贡献率数值:        {n_contrib} ({n_contrib/len(df)*100:.1f}%)")
    print(f"  两者均有:            {n_both}")
    print(f"  法定赔偿率:          {df['is_statutory'].mean()*100:.1f}%")
    print(f"  采信利润率案件:      {df['is_margin_accepted'].sum()}/{len(df)}")
    print(f"  Tier 分布: 0={df['tier_0'].sum()}, 1={df['tier_1'].sum()}, 2={df['tier_2'].sum()}, 3={df['tier_3'].sum()}")
    print(f"  判赔中位数:          ¥{df['awarded_amount'].dropna().median():,.0f}")
    print(f"  判赔均值:            ¥{df['awarded_amount'].dropna().mean():,.0f}")
    print(f"  耗时:                {elapsed:.1f}s")
    print(f"  输出:                {OUTPUT_MD.name}")
    print("=" * 60)
    print("Step 15 完成。")


if __name__ == "__main__":
    main()
