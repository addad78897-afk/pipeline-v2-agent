#!/usr/bin/env python3
"""
诉讼主体类型分类脚本。
基于已清洗的 原告/上诉人 和 被告/被上诉人 字段，将主体归类为：
  企业法人 / 个体工商户及非法人组织 / 自然人 / 其他组织
"""

import os
import re
import pandas as pd
from collections import Counter

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



SCRIPT_DIR = _os.environ.get("PV2_WORKSPACE", "/Users/weiyueshao/Desktop/pipeline_v2")
XLSX_PATH = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments.xlsx")
XLSX_BAK = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments_backup4.xlsx")

# ---- 分类关键词 ----

# 其他组织（优先匹配 — 社会团体、非营利组织等）
OTHER_ORG_KW = [
    '协会', '委员会', '合作社', '学会', '研究会', '基金会',
    '联合会', '促进会', '校友会', '同学会', '商会', '联谊会',
    '总工会', '妇联', '共青团', '红十字会', '村委会', '居委会',
    '业主委员会', '业委会',
]

# 个体工商户及非法人组织（店/铺/行/部/馆/中心/超市/厂等）
SELF_EMPLOYED_KW = [
    '店', '商行', '经营部', '馆', '工作室', '中心', '超市',
    '批发部', '铺', '摊', '个体工商户', '个人独资企业',
    '合伙企业', '农家院', '小吃', '饭馆', '餐厅', '酒楼',
    '茶庄', '酒庄', '药房', '药店', '诊所', '门诊部',
    '服务部', '经销部', '供应站', '维修部',
    '商社', '贸易行', '百货', '士多', '小卖部',
]

# 后缀/子串判断：厂 只有在不带有"公司""有限""股份"时才归个体工商户
FACTORY_KW = ['厂']

# 企业法人
CORPORATION_KW = [
    '公司', '集团', '有限', '股份', '控股', '银行', '支行',
    '分社', '联社', '保险', '证券', '信托', '基金',
    '株式会社',                        # 日本公司
    'CORP', 'LTD', 'INC', 'CO.',       # 英文公司后缀
    'SRL', 'SARL', 'GMBH', 'BV',       # 多语种公司后缀
]

# 自然人判定：姓名模式
# 中文姓名：2-4个汉字
# 带某字匿名化：李某、张某、王某某 等

def is_natural_person(name: str) -> bool:
    """判断是否为自然人姓名。"""
    if not name:
        return False

    # 剔除括号内容后再判断
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', name).strip()

    # 长度检查
    if len(cleaned) < 2 or len(cleaned) > 6:
        return False

    # 纯中文或中文+某
    non_cjk = [c for c in cleaned if not ('一' <= c <= '鿿')]
    if non_cjk:
        # 允许数字序号后缀（如 陈某1）
        if len(non_cjk) == 1 and non_cjk[0].isdigit() and len(cleaned) <= 5:
            pass
        else:
            return False

    # 不含任何组织关键词
    all_org_kw = (OTHER_ORG_KW + SELF_EMPLOYED_KW + FACTORY_KW +
                  CORPORATION_KW + ['行', '部', '局', '处'])
    if any(kw in cleaned for kw in all_org_kw):
        return False

    return True


def classify_single(name: str) -> str:
    """对单个主体名称进行分类。"""
    if not name or not isinstance(name, str):
        return ''

    name = name.strip()
    if not name:
        return ''

    # 先去除括号内角色说明（如 （原审被告）），但保留曾用名/企业名信息
    bare = re.sub(r'[（(]\s*(?:原审|一审|二审|再审|反诉|本审)?(?:原告|被告|上诉人|被上诉人|第三人)\s*[）)]', '', name).strip()
    # 如果整条名称就是一对括号包起来的公司名，则去括号保留内容
    m = re.match(r'^[（(]([^）)]+)[）)]$', bare)
    if m:
        bare = m.group(1).strip()
    # 二次清理：去掉残留的空括号
    bare = re.sub(r'[（(]\s*[）)]', '', bare).strip()
    # 如果清洗后变空，退回到原始名称
    if not bare:
        bare = name.strip()
    # 再去首尾括号（全外文公司名可能被括号包裹）
    if bare.startswith('(') and bare.endswith(')'):
        bare = bare[1:-1].strip()
    if bare.startswith('（') and bare.endswith('）'):
        bare = bare[1:-1].strip()

    # 1. 其他组织
    if any(kw in bare for kw in OTHER_ORG_KW):
        return '其他组织'

    # 2. 企业法人
    if any(kw in bare.upper() for kw in CORPORATION_KW):
        return '企业法人'
    # 含"厂"且含公司特征 → 企业法人
    if any(kw in bare for kw in FACTORY_KW) and \
       any(kw in bare for kw in ['公司', '有限', '股份', '集团']):
        return '企业法人'
    # 全英文/含英文公司名 → 企业法人
    if re.match(r'^[A-Za-z0-9\s.,&()（）\-]+$', bare) and len(bare) >= 5:
        return '企业法人'
    # 韩文/日文会社（株）模式 → 企业法人
    if '株式会社' in name or re.match(r'^\(株\)', name):
        return '企业法人'

    # 3. 个体工商户及非法人组织
    if any(kw in bare for kw in SELF_EMPLOYED_KW):
        return '个体工商户及非法人组织'
    if any(kw in bare for kw in FACTORY_KW):
        return '个体工商户及非法人组织'
    # 以"行"结尾（不包含公司）
    if bare.endswith('行') and not any(kw in bare for kw in ['公司', '有限', '股份']):
        return '个体工商户及非法人组织'

    # 4. 兜底：自然人
    if is_natural_person(bare):
        return '自然人'

    # 5. 无法判定 → 企业法人兜底（绝大多数未知实体是企业）
    if bare:
        return '企业法人'
    return ''


def classify_field(raw: str) -> str:
    """对整列值进行主体分类（处理多主体拼接）。"""
    if not raw or not isinstance(raw, str):
        return ''

    raw = raw.strip()
    if not raw:
        return ''

    # 拆分为各主体
    parties = [p.strip() for p in raw.split(';') if p.strip()]
    if not parties:
        return ''

    # 逐个分类
    types = []
    for p in parties:
        t = classify_single(p)
        if t and t not in types:
            types.append(t)

    return '; '.join(types)


def main():
    print(f"[INFO] 读取 Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, dtype=str, keep_default_na=False)
    total = len(df)
    print(f"[INFO] 共 {total} 条")

    # 备份
    df.to_excel(XLSX_BAK, index=False, engine='openpyxl')
    print(f"[INFO] 备份 → {XLSX_BAK}")

    # 分类
    mapping = {
        '原告/上诉人': '被侵权主体类型',
        '被告/被上诉人': '侵权主体类型',
    }

    # 找到原告/上诉人列的位置，在其后插入新列
    plaintiff_col_idx = df.columns.get_loc('原告/上诉人')
    defendant_col_idx = df.columns.get_loc('被告/被上诉人')

    print(f"\n[INFO] 正在分类...")
    plaintiff_types = []
    defendant_types = []

    for idx in range(total):
        plaintiff_types.append(classify_field(df.at[idx, '原告/上诉人']))
        defendant_types.append(classify_field(df.at[idx, '被告/被上诉人']))

    # 更新/插入新列（紧跟在对应源列之后）
    for col_name, col_idx, data in [
        ('侵权主体类型', defendant_col_idx, defendant_types),
        ('被侵权主体类型', plaintiff_col_idx, plaintiff_types),
    ]:
        if col_name in df.columns:
            df[col_name] = data
        else:
            df.insert(col_idx + 1, col_name, data)

    # 保存（先写到临时文件再替换，避免覆盖原文件时的 I/O 锁竞争）
    print(f"[INFO] 保存更新后的 Excel ...")
    tmp_path = os.path.join(SCRIPT_DIR, '005_data/_tmp_output_judgments.xlsx')
    df.to_excel(tmp_path, index=False, engine='openpyxl')
    os.replace(tmp_path, XLSX_PATH)

    # ---- 统计报告 ----
    print()
    print("=" * 70)
    print("  主体类型分类统计报告")
    print("=" * 70)

    for col_name, type_col in [('被侵权主体类型', '原告/上诉人'),
                                ('侵权主体类型', '被告/被上诉人')]:
        print(f"\n{'─' * 50}")
        print(f"  {col_name} (基于 {type_col})")
        print(f"{'─' * 50}")

        vals = df[col_name]
        nonempty = vals[vals != '']

        # 展开所有类型标签（因为一个字段可能有多个类型用;拼接）
        type_counter = Counter()
        for v in nonempty:
            for t in str(v).split(';'):
                t = t.strip()
                if t:
                    type_counter[t] += 1

        print(f"  非空记录: {len(nonempty)} / {total}")
        print(f"  --- 按类型出现频次 ---")
        for t_name in ['企业法人', '个体工商户及非法人组织', '自然人', '其他组织']:
            count = type_counter.get(t_name, 0)
            print(f"    {t_name}: {count} 次")

        # 混合类型记录
        mixed = nonempty[nonempty.str.contains(';', na=False)]
        print(f"\n  含混合类型的记录: {len(mixed)} 条")
        if len(mixed) > 0:
            # 组合类型分布
            combo = Counter()
            for v in mixed:
                types = tuple(sorted(set(str(v).split('; '))))
                combo[types] += 1
            for types, n in combo.most_common(5):
                print(f"    组合: {' + '.join(types)} → {n} 条")

    # 示例对比
    print(f"\n{'─' * 50}")
    print("  分类示例 (前 8 条)")
    print(f"{'─' * 50}")
    for i in range(min(8, total)):
        p = str(df.at[i, '原告/上诉人'])[:80]
        pt = str(df.at[i, '被侵权主体类型'])[:60]
        d = str(df.at[i, '被告/被上诉人'])[:80]
        dt = str(df.at[i, '侵权主体类型'])[:60]
        if p or d:
            print(f"\n  [{i+1}] 原告: {p}")
            print(f"       被侵权类型: {pt}")
            print(f"       被告: {d}")
            print(f"       侵权类型: {dt}")


if __name__ == '__main__':
    main()
