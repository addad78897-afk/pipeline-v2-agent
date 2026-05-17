import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import numpy as np

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ==========================================
# 1. 环境配置与中文字体修复
# ==========================================
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font='Arial Unicode MS')

BASE_PATH = _PV2 + "/" if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/"

# 适配改进后的 Step 1-10：实际输出文件名与列名
ROUND1_DATA = os.path.join(BASE_PATH, "005_data/round1_output.jsonl")
FINAL_ANALYSIS_CSV = os.path.join(BASE_PATH, "005_data/step10_multidimensional_analysis.csv")


def run_analysis():
    print("开始执行本地实证数据透视分析...\n")

    # ==========================================
    # 2. 宏观统计：法定赔偿的"统治地位" (基于 Round 1)
    # ==========================================
    if os.path.exists(ROUND1_DATA):
        r1_list = []
        try:
            with open(ROUND1_DATA, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        r1_list.append(json.loads(line))
            df_r1 = pd.DataFrame(r1_list)

            method_counts = df_r1['compensation_method'].value_counts()
            print("--- 宏观统计结果 ---")
            print(f"总处理案件数: {len(df_r1)}")

            statutory_val = method_counts.get('法定赔偿', 0)
            print(f"法定赔偿适用率: {(statutory_val / len(df_r1) * 100):.2f}%")
            print("\n赔偿方式分布:")
            for method, count in method_counts.items():
                print(f"  {method}: {count} ({count / len(df_r1) * 100:.1f}%)")

            # 绘图 1: 赔偿方式分布
            fig, ax = plt.subplots(figsize=(12, 6))
            colors = sns.color_palette("viridis", len(method_counts))
            bars = sns.barplot(x=method_counts.index, y=method_counts.values, hue=method_counts.index, palette="viridis", legend=False)
            ax.set_title("商标侵权案件：赔偿计算法定顺位适用现状", fontsize=15, pad=20)
            ax.set_ylabel("案件数量")
            ax.set_xlabel("赔偿方式")
            # 在柱状图上标注数值
            for bar, val in zip(bars.patches, method_counts.values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                        f'{val}\n({val / len(df_r1) * 100:.1f}%)',
                        ha='center', va='bottom', fontsize=9)
            plt.xticks(rotation=30, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_1_Methods.png"), dpi=300)
            plt.close()
            print("已生成图表 1：Analysis_1_Methods.png")

            # 绘图 2: 行业分布 Top 15
            plt.figure(figsize=(12, 7))
            industry_counts = df_r1['industry_category'].value_counts().head(15)
            sns.barplot(x=industry_counts.values, y=industry_counts.index, hue=industry_counts.index, palette="magma", legend=False)
            plt.title("Round 1 案件行业分布（Top 15）", fontsize=15, pad=20)
            plt.xlabel("案件数量")
            plt.ylabel("行业")
            plt.tight_layout()
            plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_1b_Industry.png"), dpi=300)
            plt.close()
            print("已生成图表 1b：Analysis_1b_Industry.png")

        except Exception as e:
            print(f"读取 Round 1 数据出错: {e}")
            import traceback; traceback.print_exc()
    else:
        print(f"未找到文件：{ROUND1_DATA}")

    # ==========================================
    # 3. 深度定性：裁判尺度透视 (基于 Step 10 多维分析)
    # ==========================================
    if os.path.exists(FINAL_ANALYSIS_CSV):
        try:
            df_final = pd.read_csv(FINAL_ANALYSIS_CSV)
            # 清理 BOM 字符
            df_final.columns = [c.replace('﻿', '') for c in df_final.columns]

            print(f"\n深度分析案件数: {len(df_final)}")

            # --- 映射：Step 10 新列名 -> 旧分类代码语义 ---
            # margin_adoption_category: A1_完全采信 / A2_行业同业参考 / A3_举证妨碍推定 / A4_证据不足驳回
            # contribution_attitude: B1_全额归因 / B2_多因素剥离 / B3_避而不谈

            # 绘图 3：利润率认定分类
            plt.figure(figsize=(12, 7))
            margin_order = ["A1_完全采信", "A2_行业同业参考", "A3_举证妨碍推定", "A4_证据不足驳回"]
            actual_margin_order = [o for o in margin_order if o in df_final['margin_adoption_category'].unique()]
            sns.countplot(data=df_final, y='margin_adoption_category', hue='margin_adoption_category',
                          order=actual_margin_order, palette="Blues_r", legend=False)
            plt.title("维度 A：法院对'利润率'证据的采信尺度", fontsize=15, pad=20)
            plt.xlabel("案件数量")
            plt.ylabel("分类代码")
            plt.tight_layout()
            plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_2_Margin_Scale.png"), dpi=300)
            plt.close()

            # 绘图 4：商标贡献率审查态度
            plt.figure(figsize=(12, 7))
            contrib_order = ["B1_全额归因", "B2_多因素剥离", "B3_避而不谈"]
            actual_contrib_order = [o for o in contrib_order if o in df_final['contribution_attitude'].unique()]
            sns.countplot(data=df_final, y='contribution_attitude', hue='contribution_attitude',
                          order=actual_contrib_order, palette="Greens_r", legend=False)
            plt.title("维度 B：法院对'商标贡献率'的审查态度", fontsize=15, pad=20)
            plt.xlabel("案件数量")
            plt.ylabel("分类代码")
            plt.tight_layout()
            plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_3_Contribution_Scale.png"), dpi=300)
            plt.close()

            print("\n--- 深度分类统计详情 ---")
            print("\n利润率采信尺度:")
            margin_stats = df_final['margin_adoption_category'].value_counts()
            for k, v in margin_stats.items():
                print(f"  {k}: {v} ({v / len(df_final) * 100:.1f}%)")
            print("\n贡献率审查态度:")
            contrib_stats = df_final['contribution_attitude'].value_counts()
            for k, v in contrib_stats.items():
                print(f"  {k}: {v} ({v / len(df_final) * 100:.1f}%)")

            # --- 新增图表：利用 Step 10 的丰富字段 ---

            # 绘图 5：判赔比例分布（判赔额/索赔额）
            if 'award_to_claim_ratio' in df_final.columns:
                ratios = pd.to_numeric(df_final['award_to_claim_ratio'], errors='coerce').dropna()
                ratios = ratios[(ratios >= 0) & (ratios <= 1)]
                if len(ratios) > 0:
                    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

                    axes[0].hist(ratios, bins=50, color='steelblue', edgecolor='white', alpha=0.85)
                    axes[0].axvline(ratios.median(), color='red', linestyle='--',
                                    label=f'中位数: {ratios.median():.2%}')
                    axes[0].axvline(ratios.mean(), color='orange', linestyle='--',
                                    label=f'均值: {ratios.mean():.2%}')
                    axes[0].set_title("判赔/索赔比例分布", fontsize=14)
                    axes[0].set_xlabel("判赔比例")
                    axes[0].set_ylabel("案件数量")
                    axes[0].legend()

                    axes[1].boxplot(ratios, vert=True, patch_artist=True,
                                    boxprops=dict(facecolor='lightblue'))
                    axes[1].set_title("判赔/索赔比例 箱线图", fontsize=14)
                    axes[1].set_ylabel("判赔比例")
                    axes[1].set_xticklabels([])

                    plt.suptitle("法院实际判赔与原告索赔额的比例分析", fontsize=15, y=1.02)
                    plt.tight_layout()
                    plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_4_Award_Ratio.png"),
                                dpi=300, bbox_inches='tight')
                    plt.close()
                    print(f"\n判赔比例统计: 均值={ratios.mean():.2%}, 中位数={ratios.median():.2%}, 标准差={ratios.std():.2%}")
                    print(f"已生成图表 4：Analysis_4_Award_Ratio.png")

            # 绘图 6：法院层级 vs 利润率采信尺度 交叉分析
            if 'court_level' in df_final.columns and 'margin_adoption_category' in df_final.columns:
                ct = pd.crosstab(df_final['court_level'], df_final['margin_adoption_category'])
                if not ct.empty:
                    ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
                    fig, ax = plt.subplots(figsize=(14, 8))
                    ct_pct.plot(kind='barh', stacked=True, colormap='Blues_r', ax=ax)
                    ax.set_title("不同层级法院的利润率证据采信尺度对比", fontsize=14, pad=20)
                    ax.set_xlabel("占比 (%)")
                    ax.set_ylabel("法院层级")
                    ax.legend(title="采信尺度", bbox_to_anchor=(1.02, 1), loc='upper left')
                    plt.tight_layout()
                    plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_5_Court_Margin.png"),
                                dpi=300, bbox_inches='tight')
                    plt.close()
                    print("已生成图表 5：Analysis_5_Court_Margin.png")

            # 绘图 7：Top 10 行业的贡献率审查态度
            if 'industry_category' in df_final.columns and 'contribution_attitude' in df_final.columns:
                top_industries = df_final['industry_category'].value_counts().head(10).index
                df_top = df_final[df_final['industry_category'].isin(top_industries)]
                ct_ind = pd.crosstab(df_top['industry_category'], df_top['contribution_attitude'])
                if not ct_ind.empty:
                    ct_ind_pct = ct_ind.div(ct_ind.sum(axis=1), axis=0) * 100
                    fig, ax = plt.subplots(figsize=(14, 8))
                    ct_ind_pct.plot(kind='barh', stacked=True, colormap='Greens_r', ax=ax)
                    ax.set_title("Top 10 行业的商标贡献率审查态度对比", fontsize=14, pad=20)
                    ax.set_xlabel("占比 (%)")
                    ax.set_ylabel("行业")
                    ax.legend(title="审查态度", bbox_to_anchor=(1.02, 1), loc='upper left')
                    plt.tight_layout()
                    plt.savefig(os.path.join(BASE_PATH, "008_charts/Analysis_6_Industry_Contribution.png"),
                                dpi=300, bbox_inches='tight')
                    plt.close()
                    print("已生成图表 6：Analysis_6_Industry_Contribution.png")

            print("\n已生成图表 2 至 6")

        except Exception as e:
            print(f"分析定性数据出错: {e}")
            import traceback; traceback.print_exc()
    else:
        print(f"未找到文件：{FINAL_ANALYSIS_CSV}")

    print(f"\n分析完毕！所有图表已保存在：{BASE_PATH}")


if __name__ == "__main__":
    run_analysis()
