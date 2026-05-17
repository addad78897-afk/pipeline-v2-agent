#!/usr/bin/env python3
"""
Step 0016 — 审判日期趋势分析
从 output_judgments.xlsx 提取审结日期，按年/月统计案件数、判赔金额、法定赔偿率趋势。
输出: temporal_trend_analysis.csv + 4张趋势图表 + temporal_trend_report.md
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── 路径配置 ────────────────────────────────────────────────────────────────
BASE_PV2 = Path("/Users/weiyueshao/Desktop/pipeline_v2")
XLSX_PATH = Path("/Users/weiyueshao/Desktop/pipeline_v2/006_outputs/output_judgments.xlsx")
ROUND1_PATH = Path("/Users/weiyueshao/Desktop/all/clean/round1_case_extraction_results.jsonl")

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font='Arial Unicode MS')


def parse_date(val) -> str:
    """解析日期为 YYYY-MM-DD。"""
    if not val or not isinstance(val, str):
        return ''
    val = val.strip()
    if re.match(r'\d{4}-\d{2}-\d{2}', val):
        return val
    return ''


def normalize_case_id(raw: str) -> str:
    """规范化案号：统一括号格式，去除首尾噪声。
    '(2024)粤0111民初687号'  ←→  '2024）粤0111民初687号' → '(2024)粤0111民初687号'
    """
    if not raw or not isinstance(raw, str):
        return ''
    s = raw.strip()
    # 统一中文括号为英文括号
    s = s.replace('（', '(').replace('）', ')')
    # 补齐可能缺失的左括号
    if not s.startswith('(') and ')' in s and s[0].isdigit():
        s = '(' + s
    return s


def load_round1() -> dict:
    """返回 {case_id: {compensation_method, court_awarded_amount}}。"""
    idx = {}
    if not ROUND1_PATH.exists():
        print(f"警告: 找不到 {ROUND1_PATH}")
        return idx
    with open(ROUND1_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = normalize_case_id(rec.get('case_id', ''))
            if cid:
                idx[cid] = {
                    'compensation_method': rec.get('compensation_method', ''),
                    'awarded_amount': rec.get('court_awarded_amount'),
                }
    return idx


def main():
    print("=" * 60)
    print("Step 0016: 审判日期趋势分析")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/4] 加载数据...")
    df = pd.read_excel(XLSX_PATH, dtype=str, keep_default_na=False)
    r1 = load_round1()
    print(f"  Excel: {len(df)} 行")
    print(f"  round1: {len(r1)} 条")

    # 2. 合并
    print("\n[2/4] 合并日期与赔偿数据...")
    rows = []
    matched = 0
    unmatched_date = 0
    unmatched_r1 = 0
    out_of_range = 0

    for _, row in df.iterrows():
        case_no = str(row.get('案件字号', '')).strip()
        date_str = parse_date(str(row.get('审结日期', '')))
        if not case_no or not date_str:
            if not date_str:
                unmatched_date += 1
            continue

        # 日期范围校验：仅接受 2024-03-01 至 2026-05-01
        if not ('2024-03-01' <= date_str <= '2026-05-01'):
            out_of_range += 1
            continue

        norm_case = normalize_case_id(case_no)
        r1r = r1.get(norm_case)
        if not r1r:
            unmatched_r1 += 1
            continue

        matched += 1
        year = int(date_str[:4])
        month = int(date_str[5:7])
        rows.append({
            'case_id': case_no,
            'trial_date': date_str,
            'trial_year': year,
            'trial_month': month,
            'year_month': f"{year}-{month:02d}",
            'compensation_method': r1r['compensation_method'],
            'awarded_amount': r1r['awarded_amount'] if r1r['awarded_amount'] else 0,
            'is_statutory': 1 if '法定赔偿' in str(r1r.get('compensation_method', '')) else 0,
        })

    merged = pd.DataFrame(rows)
    print(f"  匹配成功: {matched}")
    print(f"  日期缺失: {unmatched_date}")
    print(f"  日期超出范围(非2024-03~2026-05): {out_of_range}")
    print(f"  round1无匹配: {unmatched_r1}")

    # 3. 统计分析
    print("\n[3/4] 计算年/月趋势...")

    # ── 年度统计 ──
    yearly = merged.groupby('trial_year').agg(
        case_count=('case_id', 'count'),
        total_damages=('awarded_amount', 'sum'),
        avg_damages=('awarded_amount', 'mean'),
        median_damages=('awarded_amount', 'median'),
        statutory_count=('is_statutory', 'sum'),
    ).reset_index()
    yearly['statutory_rate'] = (yearly['statutory_count'] / yearly['case_count'] * 100).round(1)
    yearly['avg_damages'] = yearly['avg_damages'].round(0)
    yearly['median_damages'] = yearly['median_damages'].round(0)

    # ── 月度统计 ──
    monthly = merged.groupby('year_month').agg(
        case_count=('case_id', 'count'),
        avg_damages=('awarded_amount', 'mean'),
        statutory_rate=('is_statutory', 'mean'),
    ).reset_index()
    monthly['avg_damages'] = monthly['avg_damages'].round(0)
    monthly['statutory_rate'] = (monthly['statutory_rate'] * 100).round(1)
    monthly = monthly.sort_values('year_month')

    # ── 年度-月份矩阵 ──
    pivot = merged.pivot_table(
        index='trial_year', columns='trial_month',
        values='case_id', aggfunc='count', fill_value=0
    )

    # 合并输出
    merged.to_csv(BASE_PV2 / '005_data/temporal_trend_data.csv', index=False, encoding='utf-8-sig')
    yearly.to_csv(BASE_PV2 / '005_data/temporal_trend_yearly.csv', index=False, encoding='utf-8-sig')
    monthly.to_csv(BASE_PV2 / '005_data/temporal_trend_monthly.csv', index=False, encoding='utf-8-sig')
    print(f"  yearly: {len(yearly)} 年")
    print(f"  monthly: {len(monthly)} 月")

    # 4. 图表
    print("\n[4/4] 生成趋势图表...")

    # Chart 1: 年度案件数 + 平均判赔
    fig, ax1 = plt.subplots(figsize=(14, 6))
    bars = ax1.bar(yearly['trial_year'], yearly['case_count'], color='steelblue', alpha=0.7, label='案件数')
    for bar, val in zip(bars, yearly['case_count']):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, str(val), ha='center', fontsize=8)
    ax1.set_ylabel('案件数', fontsize=12)
    ax1.set_xlabel('审判年份', fontsize=12)
    ax2 = ax1.twinx()
    ax2.plot(yearly['trial_year'], yearly['avg_damages'], 'o-', color='darkorange', linewidth=2, markersize=6, label='平均判赔(元)')
    ax2.set_ylabel('平均判赔金额（元）', fontsize=12)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'¥{x:,.0f}'))
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    plt.title('商标侵权案件：年度案件数与平均判赔金额趋势', fontsize=15, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(BASE_PV2 / '008_charts/chart_yearly_cases_and_damages.png', dpi=300)
    plt.close()
    print("  图表1: chart_yearly_cases_and_damages.png")

    # Chart 2: 法定赔偿率年度趋势
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(yearly['trial_year'], yearly['statutory_rate'], 's-', color='crimson', linewidth=2, markersize=8)
    ax.fill_between(yearly['trial_year'], yearly['statutory_rate'], alpha=0.15, color='crimson')
    for _, r in yearly.iterrows():
        ax.annotate(f"{r['statutory_rate']:.1f}%", (r['trial_year'], r['statutory_rate']),
                    textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, color='crimson')
    ax.set_ylabel('法定赔偿适用率 (%)', fontsize=12)
    ax.set_xlabel('审判年份', fontsize=12)
    ax.set_ylim(bottom=max(0, yearly['statutory_rate'].min() - 5))
    plt.title('商标侵权案件：法定赔偿适用率年度趋势', fontsize=15, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(BASE_PV2 / '008_charts/chart_yearly_statutory_rate.png', dpi=300)
    plt.close()
    print("  图表2: chart_yearly_statutory_rate.png")

    # Chart 3: 月度案件数趋势
    fig, ax = plt.subplots(figsize=(18, 6))
    recent = monthly.tail(36)  # 最近36个月
    ax.fill_between(range(len(recent)), recent['case_count'], alpha=0.3, color='steelblue')
    ax.plot(range(len(recent)), recent['case_count'], 'o-', color='steelblue', linewidth=1.5, markersize=4)
    # 每6个月标一个标签
    tick_positions = list(range(0, len(recent), 6))
    tick_labels = [recent.iloc[i]['year_month'] for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax.set_ylabel('案件数', fontsize=12)
    ax.set_xlabel('年月', fontsize=12)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.title('商标侵权案件：月度案件数趋势（近36个月）', fontsize=15, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(BASE_PV2 / '008_charts/chart_monthly_cases.png', dpi=300)
    plt.close()
    print("  图表3: chart_monthly_cases.png")

    # Chart 4: 年度-月份热力图
    fig, ax = plt.subplots(figsize=(16, max(6, len(pivot) * 0.8)))
    sns.heatmap(pivot, annot=True, fmt='d', cmap='YlOrRd', linewidths=0.5,
                cbar_kws={'label': '案件数'}, ax=ax)
    ax.set_title('商标侵权案件：年度-月份分布热力图', fontsize=15, fontweight='bold', pad=20)
    ax.set_ylabel('审判年份', fontsize=12)
    ax.set_xlabel('审判月份', fontsize=12)
    month_labels = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
    ax.set_xticklabels([month_labels[int(t.get_text())-1] if t.get_text().isdigit() else t.get_text() for t in ax.get_xticklabels()])
    plt.tight_layout()
    plt.savefig(BASE_PV2 / '008_charts/chart_year_month_heatmap.png', dpi=300)
    plt.close()
    print("  图表4: chart_year_month_heatmap.png")

    # 5. Markdown 报告
    lines = []
    lines.append("# 商标侵权案件审判日期趋势分析报告\n")
    lines.append(f"> Step 0016 自动生成 | 匹配案件: {matched}/{len(df)} | 日期范围: 2024-03-01 ~ 2026-05-01\n")

    lines.append("## 一、年度趋势\n")
    lines.append("| 年份 | 案件数 | 法定赔偿率 | 平均判赔(¥) | 中位判赔(¥) |")
    lines.append("|------|--------|-----------|------------|------------|")
    for _, r in yearly.iterrows():
        lines.append(f"| {int(r['trial_year'])} | {int(r['case_count'])} | {r['statutory_rate']:.1f}% | {r['avg_damages']:,.0f} | {r['median_damages']:,.0f} |")

    lines.append(f"\n## 二、月度趋势（最近12个月）\n")
    lines.append("| 年月 | 案件数 | 平均判赔(¥) | 法定赔偿率 |")
    lines.append("|------|--------|------------|-----------|")
    for _, r in monthly.tail(12).iterrows():
        lines.append(f"| {r['year_month']} | {int(r['case_count'])} | {r['avg_damages']:,.0f} | {r['statutory_rate']:.1f}% |")

    lines.append(f"\n## 三、关键发现\n")
    # Find peak year
    peak_year = yearly.loc[yearly['case_count'].idxmax()]
    lines.append(f"- **案件高峰年份**：{int(peak_year['trial_year'])}年（{int(peak_year['case_count'])}件）")
    # Trend direction
    if len(yearly) >= 3:
        recent_years = yearly.tail(3)
        trend = "上升" if recent_years['avg_damages'].is_monotonic_increasing else "下降" if recent_years['avg_damages'].is_monotonic_decreasing else "波动"
        lines.append(f"- **近3年平均判赔趋势**：{trend}（{recent_years.iloc[0]['trial_year']:.0f}年¥{recent_years.iloc[0]['avg_damages']:,.0f} → {recent_years.iloc[-1]['trial_year']:.0f}年¥{recent_years.iloc[-1]['avg_damages']:,.0f}）")
    lines.append(f"- **法定赔偿率波动范围**：{yearly['statutory_rate'].min():.1f}% ~ {yearly['statutory_rate'].max():.1f}%")

    lines.append(f"\n*报告结束。图表和CSV保存在 {BASE_PV2}/*。")

    report = "\n".join(lines)
    (BASE_PV2 / '007_reports/temporal_trend_report.md').write_text(report, encoding='utf-8')
    print(f"  报告: temporal_trend_report.md")

    print("\n" + "=" * 60)
    print("Step 0016 完成。")
    print("=" * 60)


if __name__ == "__main__":
    main()
