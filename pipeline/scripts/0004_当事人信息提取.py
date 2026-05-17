#!/usr/bin/env python3
"""
诉讼主体字段深度清洗脚本。
清洗 output_judgments.xlsx 中 原告/上诉人 和 被告/被上诉人 两列。
"""

import os
import re
import pandas as pd
from collections import OrderedDict

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
XLSX_BAK = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments_backup3.xlsx")

# ---- 正则模式 ----

# 1. 角色前缀（含括号限定语）：原告：, 上诉人(原审被告)：, (原审原告)： 等
ROLE_PREFIX_RE = re.compile(
    r'^[（(]?\s*'
    r'(?:原审|一审|二审|再审|终审|本审|共同|申请|被申请)?'
    r'(?:原告|被告|上诉人|被上诉人|再审申请人|再审被申请人'
    r'|申诉人|被申诉人|第三人|申请执行人|被执行人|异议人)'
    r'(?:\([^)]*\))?'         # 可选的括号内角色限定
    r'\s*[）)]?\s*'
    r'[：:]\s*'
)

# 2. 括号内角色说明 — 删除，但保留曾用名/前企业名称/原名
#    删除：(原审被告) (反诉原告) (一审原告) (再审申请人) 等
ROLE_PAREN_RE = re.compile(
    r'[（(]\s*'
    r'(?:原审|一审|二审|再审|终审|本审|反诉|申请|被申请)?'
    r'(?:原告|被告|上诉人|被上诉人|再审申请人|再审被申请人'
    r'|申诉人|被申诉人|第三人|申请执行人|被执行人|异议人'
    r'|原审[^)]{0,10})'
    r'\s*[）)]'
)

# 3. 尾部干扰词：从此处开始全部截断
#    注意：匹配前需要逗号/句号/空格分隔，避免误伤公司名
TAIL_CUT_RE = re.compile(
    r'[，,。；;]\s*'
    r'(?:'
    r'经营场所[：:]?(?:位于|地址)?|'
    r'法定代表人[：:]?|'
    r'负责人[：:]?|'
    r'执行事务合伙人[：:]?|'
    r'统一社会信用代码[：:]?|'
    r'注册号[：:]?|'
    r'住所地[：:]?|'
    r'住址[：:]?|'
    r'主要经营场所[：:]?|'
    r'实际经营地[：:]?'
    r')'
)

# 直接跟在名称后的尾部词（无逗号分隔，通过空格或直接连接）
TAIL_CUT_LOOSE_RE = re.compile(
    r'\s*[（(]?(?:统一社会信用代码|注册号)\s*[：:].*$'
)

# "男，" "女，" 自然人性别标记
PERSON_GENDER_RE = re.compile(r'[，,]\s*(?:男|女)\s*[，,]\s*.*$')

# 4. 拆分用分隔符
SPLIT_SEP_RE = re.compile(r'\|\||[;；]\s*|\n+|、')

# 5. 逗号分隔多主体（需谨慎：公司名中也可能含逗号）
#    只在明显是分隔多主体时拆分：逗号前后是"XX公司" "XX有限公司" 或自然人姓名模式
COMMA_SPLIT = re.compile(r'[，,]\s*(?=[一-鿿A-Za-z（(]{2,}(?:有限|股份|集团|合伙|厂|店|部|行|社|所|中心|学校|医院|银行))')

# 6. 空值占位
EMPTY_PLACEHOLDERS = re.compile(r'^(?:nan|null|none|无|暂无|未知)$', re.IGNORECASE)


def clean_single_party(raw: str) -> str:
    """清洗单个当事人名称。"""
    if not raw or not isinstance(raw, str):
        return ''

    name = raw.strip()

    # 空值占位
    if EMPTY_PLACEHOLDERS.match(name):
        return ''

    # 1. 剔除角色前缀
    name = ROLE_PREFIX_RE.sub('', name).strip()

    # 2. 剔除括号内角色说明（但保留曾用名、前企业名称）
    name = ROLE_PAREN_RE.sub('', name)

    # 清理可能遗留的空括号
    name = re.sub(r'[（(]\s*[）)]', '', name)

    # 3. 剔除尾部干扰
    # 3a. 逗号/句号引导的经营场所等
    m = TAIL_CUT_RE.search(name)
    if m:
        name = name[:m.start()]

    # 3b. 直接尾随的统一社会信用代码
    m = TAIL_CUT_LOOSE_RE.search(name)
    if m:
        name = name[:m.start()]

    # 3c. "男，"/"女，" 自然人标记
    m = PERSON_GENDER_RE.search(name)
    if m:
        name = name[:m.start()]

    # 3d. "。" 句号后的内容通常不是名称的一部分
    idx = name.find('。')
    if idx >= 0:
        candidate = name[:idx].strip()
        # 仅在句号前有足够长度时截断（避免过度截断）
        if len(candidate) >= 4:
            name = candidate

    # 4. 再次清理角色前缀（可能在去掉括号后暴露出来）
    name = ROLE_PREFIX_RE.sub('', name).strip()

    # 5. 去除首尾残留标点
    name = name.strip('，,。；;、：: 　\t\n\r')

    # 6. 清理连续空格和不可见字符
    name = re.sub(r'\s{2,}', ' ', name)
    name = re.sub(r'[​‎‏   　]+', '', name)

    return name


def split_parties(raw: str) -> list:
    """将多主体的原始文本拆分为列表。"""
    if not raw or not isinstance(raw, str):
        return []

    # 先按 || 和 ; ； 和换行拆分
    parts = SPLIT_SEP_RE.split(raw)

    result = []
    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue
        # 逗号拆分（限于公司名/机构名模式）
        # 注意：含"曾用名"的括号内逗号不应拆分
        if '曾用名' in part or '前企业名称' in part or '原名' in part:
            result.append(part)
        elif COMMA_SPLIT.search(part):
            # 按逗号拆并各自清洗
            sub_parts = re.split(r'[，,]\s*', part)
            for sp in sub_parts:
                sp = sp.strip()
                if sp and len(sp) >= 2:
                    result.append(sp)
        else:
            result.append(part)

    return result


def clean_field(raw: str) -> str:
    """清洗整个当事人字段（对外接口）。"""
    if not raw or not isinstance(raw, str):
        return ''

    raw = raw.strip()
    if not raw or EMPTY_PLACEHOLDERS.match(raw):
        return ''

    # 拆分
    parts = split_parties(raw)

    # 逐个清洗
    cleaned = []
    for p in parts:
        c = clean_single_party(p)
        if c and len(c) >= 2 and not EMPTY_PLACEHOLDERS.match(c):
            cleaned.append(c)

    # 过滤已知垃圾词条和过短词条
    GARBAGE_TOKENS = {
        '经营场所', '法定代表人', '负责人', '执行事务合伙人',
        '统一社会信用代码', '住所地', '住址', '注册号', '注册地',
        '主要经营场所', '实际经营地', '男', '女',
    }
    cleaned = [c for c in cleaned
               if c not in GARBAGE_TOKENS and len(c) >= 2]

    # 去重（保留顺序）
    seen = set()
    unique = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return '; '.join(unique)


def main():
    print(f"[INFO] 读取 Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, dtype=str, keep_default_na=False)
    total = len(df)
    print(f"[INFO] 共 {total} 条记录")

    # 备份
    df.to_excel(XLSX_BAK, index=False, engine='openpyxl')
    print(f"[INFO] 备份 → {XLSX_BAK}")

    # 清洗两列
    changes = []

    for col in ['原告/上诉人', '被告/被上诉人']:
        print(f"\n[INFO] 清洗列: {col}")
        col_modified = 0
        samples = []

        for idx in range(total):
            old_val = df.at[idx, col]
            new_val = clean_field(old_val)

            if old_val.strip() != new_val:
                df.at[idx, col] = new_val
                col_modified += 1
                if len(samples) < 8 and len(old_val.strip()) > 20:
                    samples.append((old_val.strip(), new_val))

        changes.append((col, col_modified, samples))
        print(f"  → 已修改: {col_modified} 条")

    # 保存
    print(f"\n[INFO] 保存更新后的 Excel ...")
    df.to_excel(XLSX_PATH, index=False, engine='openpyxl')

    # 报告
    total_modified = sum(c[1] for c in changes)
    print()
    print("=" * 70)
    print(f"  诉讼主体清洗完成！")
    for col, n, _ in changes:
        print(f"  {col}: 修改 {n} 条 / {total} 条")
    print(f"  合计修改:  {total_modified}")
    print("=" * 70)

    # 打印对比示例
    print(f"\n{'─' * 70}")
    print("  清洗前后对比示例：")
    print(f"{'─' * 70}")

    example_num = 1
    for col, _, samples in changes:
        for old, new in samples[:5]:
            # 截断过长的文本
            old_display = old[:150] + ('...' if len(old) > 150 else '')
            new_display = new[:150] + ('...' if len(new) > 150 else '')
            print(f"\n  [{example_num}] 列: {col}")
            print(f"      修改前: {old_display}")
            print(f"      修改后: {new_display}")
            example_num += 1


if __name__ == '__main__':
    main()
