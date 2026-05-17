#!/usr/bin/env python3
"""
文件重命名脚本：根据 output_judgments.xlsx 中提取的法宝引证码 + 标题，
将乱码文件名的 txt 文件重命名为清晰的中文文件名。
"""

import os
import re
import pandas as pd
from pathlib import Path

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ---- 配置 ----
SCRIPT_DIR = _os.environ.get("PV2_WORKSPACE", "/Users/weiyueshao/Desktop/pipeline_v2")
XLSX_PATH = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments.xlsx")
XLSX_BACKUP = os.path.join(SCRIPT_DIR, "006_outputs/output_judgments_backup.xlsx")

# macOS / Windows 文件名非法字符
ILLEGAL_CHARS_PATTERN = re.compile(r'[/:\\*?"<>|]')
# 全角非法字符（中文系统里部分也被禁止）
ILLEGAL_FULLWIDTH = str.maketrans({
    '/': '／', '\\': '＼', ':': '：', '*': '＊',
    '?': '？', '"': '＂', '<': '＜', '>': '＞', '|': '｜',
})
# 连续空白
MULTISPACE = re.compile(r'\s{2,}')

MAX_FILENAME_BYTES = 240  # macOS 文件名最大 255 UTF-8 字节，留余量


def sanitize_filename(raw: str) -> str:
    """清理文件名中的非法字符和多余空白。

    - 替换 macOS 非法字符为全角替代
    - 合并连续空白
    - 去除首尾空白
    """
    # 先替换非法字符
    cleaned = raw.translate(ILLEGAL_FULLWIDTH)
    # 去掉未替换干净的残留（如果有的话）
    cleaned = ILLEGAL_CHARS_PATTERN.sub('', cleaned)
    # 合并空格/制表符
    cleaned = MULTISPACE.sub(' ', cleaned)
    # 去除首尾空白和点号（避免隐藏文件）
    cleaned = cleaned.strip().strip('.')
    return cleaned


def truncate_to_bytes(s: str, max_bytes: int) -> str:
    """按 UTF-8 字节数截断字符串，保留完整字符。"""
    encoded = s.encode('utf-8')[:max_bytes]
    return encoded.decode('utf-8', errors='ignore')


def build_new_name(row) -> str:
    """根据行数据生成新文件名（不含路径，不含扩展名）。"""
    pkulaw = str(row.get('法宝引证码', '')).strip()
    case_no = str(row.get('案件字号', '')).strip()
    seq = str(row.get('序号', '')).strip()
    title = str(row.get('标题', '')).strip()

    # 核心标识符：法宝引证码 > 案件字号 > 序号
    if pkulaw and pkulaw.lower() != 'nan':
        identifier = pkulaw
    elif case_no and case_no.lower() != 'nan':
        identifier = case_no
    elif seq and seq.lower() != 'nan':
        identifier = f"SEQ{int(float(seq)):05d}" if seq.replace('.','',1).isdigit() else seq
    else:
        identifier = "UNKNOWN"

    # 清理标识符中的非法字符
    identifier = sanitize_filename(identifier)

    # 标题部分
    if title and title.lower() != 'nan':
        title_clean = sanitize_filename(title)
    else:
        title_clean = ""

    # 拼接：【标识符】_标题 (保留扩展名在外部加)
    if title_clean:
        basename = f"{identifier}_{title_clean}"
    else:
        basename = identifier

    # UTF-8 字节截断
    basename = truncate_to_bytes(basename, MAX_FILENAME_BYTES)

    return basename


def main():
    # 1. 读取 Excel
    print(f"[INFO] 读取 Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, dtype=str, keep_default_na=False)
    total = len(df)
    print(f"[INFO] 共 {total} 条记录")

    # 备份原 Excel
    print(f"[INFO] 备份原 Excel → {XLSX_BACKUP}")
    df.to_excel(XLSX_BACKUP, index=False, engine='openpyxl')

    # 2. 逐行处理
    success_count = 0
    skip_count = 0
    error_count = 0

    for idx in range(total):
        old_path = str(df.at[idx, '源文件']).strip()
        if not old_path or old_path.lower() == 'nan':
            skip_count += 1
            continue

        # 检查旧文件是否存在
        if not os.path.exists(old_path):
            print(f"  [SKIP] 文件不存在: {os.path.basename(old_path)[:60]}")
            skip_count += 1
            continue

        # 生成新文件名
        new_basename = build_new_name(df.iloc[idx])
        new_filename = new_basename + ".txt"
        new_dir = os.path.dirname(old_path)
        new_path = os.path.join(new_dir, new_filename)

        # 如果新旧路径完全相同，跳过
        if old_path == new_path:
            skip_count += 1
            continue

        # 如果目标文件名已被其他文件占用，追加序号区分
        if os.path.exists(new_path) and old_path != new_path:
            collision_idx = 2
            while True:
                new_filename = f"{new_basename}_{collision_idx}.txt"
                new_path = os.path.join(new_dir, new_filename)
                if not os.path.exists(new_path) or new_path == old_path:
                    break
                collision_idx += 1

        # 执行重命名
        try:
            os.rename(old_path, new_path)
            df.at[idx, '源文件'] = new_path
            success_count += 1
            if success_count <= 5 or success_count % 2000 == 0:
                print(f"  [OK] 重命名 → {new_filename[:100]}")
        except OSError as e:
            print(f"  [ERROR] 重命名失败: {os.path.basename(old_path)[:60]} → {e}")
            error_count += 1
            continue

    # 3. 保存 Excel
    print(f"\n[INFO] 保存更新后的 Excel → {XLSX_PATH}")
    df.to_excel(XLSX_PATH, index=False, engine='openpyxl')

    # 4. 汇报
    print()
    print("=" * 60)
    print(f"  重命名完成！")
    print(f"  总记录:   {total}")
    print(f"  成功重命名: {success_count}")
    print(f"  跳过:      {skip_count}")
    print(f"  失败:      {error_count}")
    print(f"  备份文件:  {XLSX_BACKUP}")
    print("=" * 60)


if __name__ == '__main__':
    main()
