#!/usr/bin/env python3
"""
审理法院名称规范化清洗脚本。
读取 output_judgments.xlsx，清洗法院名称并补齐省份前缀。
"""

import os
import re
import pandas as pd

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
XLSX_BAK = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments_backup2.xlsx")

# ---- 省份简称映射（用于模糊匹配 court 中已有的省份） ----
PROVINCE_SHORT = {
    '北京市': '北京', '天津市': '天津', '上海市': '上海', '重庆市': '重庆',
    '河北省': '河北', '山西省': '山西', '辽宁省': '辽宁', '吉林省': '吉林',
    '黑龙江省': '黑龙江', '江苏省': '江苏', '浙江省': '浙江', '安徽省': '安徽',
    '福建省': '福建', '江西省': '江西', '山东省': '山东', '河南省': '河南',
    '湖北省': '湖北', '湖南省': '湖南', '广东省': '广东', '海南省': '海南',
    '四川省': '四川', '贵州省': '贵州', '云南省': '云南', '陕西省': '陕西',
    '甘肃省': '甘肃', '青海省': '青海', '台湾省': '台湾',
    '内蒙古自治区': '内蒙古', '广西壮族自治区': '广西',
    '西藏自治区': '西藏', '宁夏回族自治区': '宁夏',
    '新疆维吾尔自治区': '新疆',
}

# ---- 专门法院关键词（不强加省份前缀） ----
SPECIAL_COURT_KW = [
    '最高人民法院',
    '知识产权法院',
    '互联网法院',
    '海事法院',
    '金融法院',
    '自由贸易',        # 覆盖 自由贸易区 / 自由贸易试验区
    '铁路运输法院',
    '军事法院',
]

# ---- 法院名前的噪声前缀 ----
NOISE_PREFIX_RE = re.compile(
    r'^('
    r'不服中华人民共和国|不服中华|不服|'
    r'(?:上诉人?|诉人|再审申请人?|申诉人?|原审[一-鿿]{0,4}|各方均?|双方均?|'
    r'当事人|[一-鿿]{1,4})?'
    r'(?:不服|认为)'
    r'(?:中华人民共和国|中华)?'
    r'|'
    r'(?:上诉人?|诉人|再审申请人?|申诉人?|原审[一-鿿]{0,4}|各方均?|各方|双方)'
    r'(?:不服|认为|上诉|主张)'
    r'(?:中华人民共和国|中华)?'
    r'|'
    r'(?:一|二|再)?审(?:法院)?(?:认定|查明|认为)[的之]?(?:事实(?:及|和))?(?:裁判?)?(?:理由见|理由|查明|认定|认为)?'
    r'(?:见|：|:)?'
    r'|'
    r'[的之]?事实(?:及|和)(?:裁判)?理由见|'
    r'[的之]?(?:裁判)?理由见|'
    r'本?院?(?:认为|查明|认定)'
    r')'
)

# 噪声后缀正则（剪切掉法院名之后的多余文字）
NOISE_SUFFIX_RE = re.compile(
    r'('
    r'(?:作出|出具|于|的|，|,).*$'
    r')'
)

# ---- 空格与不可见字符 ----
CLEAN_RE = re.compile(r'[​‎‏   　]+')


def is_special_court(name: str) -> bool:
    """判断是否为专门法院（应豁免省份拼接）。"""
    for kw in SPECIAL_COURT_KW:
        if kw in name:
            return True
    return False


def province_already_in(name: str, province: str) -> bool:
    """判断法院名称中是否已包含省份信息。"""
    if province and province in name:
        return True
    short = PROVINCE_SHORT.get(province, '')
    if short and short in name:
        return True
    return False


def clean_court_name(raw: str, province: str) -> str:
    """清洗单个审理法院名称并补齐省份前缀。

    返回 (cleaned_name, was_modified)
    """
    if not raw or not isinstance(raw, str):
        return '', False

    original = raw

    # 1. 去除不可见字符和首尾空格
    name = CLEAN_RE.sub('', raw).strip()

    # 2. 去除噪声前缀（"不服...", "的事实及裁判理由见..." 等）
    m = NOISE_PREFIX_RE.match(name)
    if m:
        name = name[m.end():].strip()

    # 2b. 去除噪声后缀（"作出...", "于...", "的...", 逗号后的多余文字）
    #    但要确保清理后法院名称仍然完整
    m2 = NOISE_SUFFIX_RE.search(name)
    if m2:
        candidate = name[:m2.start()].strip()
        # 只在仍然包含"法院"时才执行截断
        if '法院' in candidate:
            name = candidate

    # 如果清理后变空了，保留原样
    if not name:
        return original.strip(), False

    # 3. 去除多余的"中华人民共和国"前缀
    #    保留 "中华人民共和国最高人民法院" 整体
    if name.startswith('中华人民共和国') and '最高人民法院' not in name:
        name = name[len('中华人民共和国'):]

    # 4. 如果看起来不像法院名称，保留原样
    if '人民法院' not in name and '法院' not in name:
        return name, (name != original.strip())

    # 5. 专门法院豁免：不强加省份前缀
    if is_special_court(name):
        return name, (name != original.strip())

    # 6. 补齐省份前缀
    if province and province.lower() != 'nan' and not province_already_in(name, province):
        name = province + name

    modified = (name != original.strip())
    return name, modified


def main():
    print(f"[INFO] 读取 Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, dtype=str, keep_default_na=False)
    total = len(df)
    print(f"[INFO] 共 {total} 条记录")

    # 备份
    df.to_excel(XLSX_BAK, index=False, engine='openpyxl')
    print(f"[INFO] 备份 → {XLSX_BAK}")

    # 逐行清洗
    modified = 0
    before_after = []

    for idx in range(total):
        old_val = df.at[idx, '审理法院']
        province = df.at[idx, '省份']
        new_val, was_mod = clean_court_name(old_val, province)

        if was_mod:
            df.at[idx, '审理法院'] = new_val
            modified += 1
            if len(before_after) < 10:
                before_after.append((old_val.strip(), new_val))

    # 保存
    print(f"\n[INFO] 保存更新后的 Excel ...")
    df.to_excel(XLSX_PATH, index=False, engine='openpyxl')

    # 汇报
    print()
    print("=" * 70)
    print(f"  法院名称规范化完成！")
    print(f"  总记录:    {total}")
    print(f"  已修改:    {modified}")
    print(f"  未修改:    {total - modified}")
    print("=" * 70)

    # 打印对比示例
    if before_after:
        print(f"\n{'─' * 70}")
        print("  修改前后对比示例：")
        print(f"{'─' * 70}")
        for i, (old, new) in enumerate(before_after[:10], 1):
            print(f"\n  [{i}] 修改前: {old[:100]}")
            print(f"      修改后: {new[:100]}")


if __name__ == '__main__':
    main()
