#!/usr/bin/env python3
"""
=============================================================================
中国裁判文书（侵害商标权纠纷）批量结构化解析脚本
=============================================================================

功能：批量解析指定文件夹内的裁判文书(.txt/.docx/.pdf)，提取结构化字段并导出为Excel。

运行前安装依赖：
    pip install pandas openpyxl tqdm chardet
    可选（如需解析 .docx / .pdf）：
    pip install python-docx pdfplumber

使用方法：
    cd /Users/weiyueshao/Downloads/用所选项目新建的文件夹
    python3 parse_judgments.py

输出文件：
    output_judgments.xlsx          —— 最终合并的Excel
    005_data/output_judgments_batch_*.csv   —— 中间临时CSV（完成后自动清理）
    error_log.txt                  —— 解析失败的文件及错误原因
=============================================================================
"""

import os
import re
import sys
import csv
import glob
import time
import shutil
import logging
import traceback
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import OrderedDict

import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------------
# 可选依赖：仅在需要解析 .docx / .pdf 时导入
# ---------------------------------------------------------------------------
try:
    import chardet as _chardet_mod
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

try:
    import docx as _docx_mod
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pdfplumber as _pdf_mod
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# ===========================================================================
# 全局常量 & 正则模式
# ===========================================================================

# 支持的文件扩展名
SUPPORTED_EXTS = ('.txt', '.docx', '.pdf')

# 编码检测优先顺序
ENCODING_CANDIDATES = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'utf-16', 'utf-16-le', 'utf-16-be']

# 中国省份/直辖市/自治区关键词（用于匹配审理法院所在省份）
PROVINCE_PATTERNS = OrderedDict([
    ('北京市',    ['北京']),
    ('天津市',    ['天津']),
    ('上海市',    ['上海']),
    ('重庆市',    ['重庆']),
    ('河北省',    ['河北', '石家庄', '唐山', '秦皇岛', '邯郸', '邢台', '保定', '张家口', '承德', '沧州', '廊坊', '衡水']),
    ('山西省',    ['山西', '太原', '大同', '阳泉', '长治', '晋城', '朔州', '晋中', '运城', '忻州', '临汾', '吕梁']),
    ('内蒙古自治区', ['内蒙古', '呼和浩特', '包头', '乌海', '赤峰', '通辽', '鄂尔多斯', '呼伦贝尔', '巴彦淖尔', '乌兰察布']),
    ('辽宁省',    ['辽宁', '沈阳', '大连', '鞍山', '抚顺', '本溪', '丹东', '锦州', '营口', '阜新', '辽阳', '盘锦', '铁岭', '朝阳', '葫芦岛']),
    ('吉林省',    ['吉林', '长春', '四平', '辽源', '通化', '白山', '松原', '白城', '延边']),
    ('黑龙江省',  ['黑龙江', '哈尔滨', '齐齐哈尔', '鸡西', '鹤岗', '双鸭山', '大庆', '伊春', '佳木斯', '七台河', '牡丹江', '黑河', '绥化']),
    ('江苏省',    ['江苏', '南京', '无锡', '徐州', '常州', '苏州', '南通', '连云港', '淮安', '盐城', '扬州', '镇江', '泰州', '宿迁']),
    ('浙江省',    ['浙江', '杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '舟山', '台州', '丽水']),
    ('安徽省',    ['安徽', '合肥', '芜湖', '蚌埠', '淮南', '马鞍山', '淮北', '铜陵', '安庆', '黄山', '滁州', '阜阳', '宿州', '六安', '亳州', '池州', '宣城']),
    ('福建省',    ['福建', '福州', '厦门', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', '宁德']),
    ('江西省',    ['江西', '南昌', '景德镇', '萍乡', '九江', '新余', '鹰潭', '赣州', '吉安', '宜春', '抚州', '上饶']),
    ('山东省',    ['山东', '济南', '青岛', '淄博', '枣庄', '东营', '烟台', '潍坊', '济宁', '泰安', '威海', '日照', '临沂', '德州', '聊城', '滨州', '菏泽']),
    ('河南省',    ['河南', '郑州', '开封', '洛阳', '平顶山', '安阳', '鹤壁', '新乡', '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳', '商丘', '信阳', '周口', '驻马店']),
    ('湖北省',    ['湖北', '武汉', '黄石', '十堰', '宜昌', '襄阳', '鄂州', '荆门', '孝感', '荆州', '黄冈', '咸宁', '随州', '恩施']),
    ('湖南省',    ['湖南', '长沙', '株洲', '湘潭', '衡阳', '邵阳', '岳阳', '常德', '张家界', '益阳', '郴州', '永州', '怀化', '娄底', '湘西']),
    ('广东省',    ['广东', '广州', '韶关', '深圳', '珠海', '汕头', '佛山', '江门', '湛江', '茂名', '肇庆', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮']),
    ('广西壮族自治区', ['广西', '南宁', '柳州', '桂林', '梧州', '北海', '防城港', '钦州', '贵港', '玉林', '百色', '贺州', '河池', '来宾', '崇左']),
    ('海南省',    ['海南', '海口', '三亚', '三沙', '儋州']),
    ('四川省',    ['四川', '成都', '自贡', '攀枝花', '泸州', '德阳', '绵阳', '广元', '遂宁', '内江', '乐山', '南充', '眉山', '宜宾', '广安', '达州', '雅安', '巴中', '资阳']),
    ('贵州省',    ['贵州', '贵阳', '六盘水', '遵义', '安顺', '毕节', '铜仁', '黔西南', '黔东南', '黔南']),
    ('云南省',    ['云南', '昆明', '曲靖', '玉溪', '保山', '昭通', '丽江', '普洱', '临沧', '楚雄', '红河', '文山', '西双版纳', '大理', '德宏', '怒江', '迪庆']),
    ('西藏自治区',  ['西藏', '拉萨', '日喀则', '昌都', '林芝', '山南', '那曲', '阿里']),
    ('陕西省',    ['陕西', '西安', '铜川', '宝鸡', '咸阳', '渭南', '延安', '汉中', '榆林', '安康', '商洛']),
    ('甘肃省',    ['甘肃', '兰州', '嘉峪关', '金昌', '白银', '天水', '武威', '张掖', '平凉', '酒泉', '庆阳', '定西', '陇南', '临夏', '甘南']),
    ('青海省',    ['青海', '西宁', '海东', '海北', '黄南', '海南', '果洛', '玉树', '海西']),
    ('宁夏回族自治区', ['宁夏', '银川', '石嘴山', '吴忠', '固原', '中卫']),
    ('新疆维吾尔自治区', ['新疆', '乌鲁木齐', '克拉玛依', '吐鲁番', '哈密', '昌吉', '博尔塔拉', '巴音郭楞', '阿克苏', '克孜勒苏', '喀什', '和田', '伊犁', '塔城', '阿勒泰']),
    # 专门法院（跨省管辖）
    ('最高人民法院', ['最高人民法院']),
    ('北京知识产权法院', ['北京知识产权法院']),
    ('上海知识产权法院', ['上海知识产权法院']),
    ('广州知识产权法院', ['广州知识产权法院']),
    ('海南自由贸易港知识产权法院', ['海南自由贸易港知识产权法院']),
])


def detect_province(court_name):
    """根据法院名称识别省份。"""
    if not court_name:
        return ''
    for province, keywords in PROVINCE_PATTERNS.items():
        for kw in keywords:
            if kw in court_name:
                return province
    # 尝试匹配 "XX省" 或 "XX自治区" 或 "XX市"
    m = re.search(r'[一-鿿]{2,4}(?:省|自治区|特别行政区|市)', court_name)
    if m:
        return m.group(0)
    # 直辖市的 "XX市" 法院
    for city in ['北京', '上海', '天津', '重庆']:
        if city in court_name:
            return city + '市'
    return ''


def detect_court_level(court_name):
    """根据法院名称识别法院级别。"""
    if not court_name:
        return ''
    if '最高人民法院' in court_name:
        return '最高人民法院'
    if '高级人民法院' in court_name:
        return '高级人民法院'
    if any(kw in court_name for kw in ['中级人民法院', '知识产权法院', '互联网法院',
                                        '金融法院', '海事法院', '铁路运输中级法院',
                                        '第一中级人民法院', '第二中级人民法院', '第三中级人民法院']):
        return '中级人民法院'
    if '人民法院' in court_name:
        return '基层人民法院'
    return ''


def detect_procedure(content, title='', court_opinion=''):
    """根据标题或文书中关键词识别审理程序。"""
    text = (title or '') + ' ' + (court_opinion or '')[:2000] + ' ' + content[:3000]
    if '再审' in text or '再审' in text:
        return '再审'
    if '重审' in text or '重审' in text:
        return '重审'
    if '二审' in text or '二审' in text or '终审' in text or '终审' in text:
        # check if also mentions 一审 as original
        if '一审' in text or '一审' in text:
            return '二审'
        return '二审'
    if '一审' in text or '一审' in text:
        return '一审'
    # Heuristic: 文书标题中的判断
    if any(word in content[:1000] for word in ['二审', '上诉人', '被上诉人']):
        return '二审'
    if any(word in content[:1000] for word in ['再审', '再审申请人']):
        return '再审'
    return ''


def detect_doc_type(content):
    """识别文书类型。"""
    if '判决书' in content[:2000]:
        return '判决书'
    if '裁定书' in content[:2000]:
        return '裁定书'
    if '调解书' in content[:2000]:
        return '调解书'
    if '判决' in content[:2000]:
        return '判决书'
    if '裁定' in content[:2000]:
        return '裁定书'
    return ''


def detect_case_cause(title, content):
    """从标题或正文中提取案由。"""
    text = (title or '') + ' ' + content[:2000]
    # "侵害商标权纠纷" 是最常见的精确表达
    patterns = [
        r'(侵害[^，。\n]{0,10}商标[^，。\n]{0,10}纠纷)',
        r'(商标[^，。\n]{0,10}侵权[^，。\n]{0,10}纠纷)',
        r'(商标[^，。\n]{0,10}纠纷)',
        r'(不正当竞争[^，。\n]{0,10}纠纷)',
        r'((?:知识产权|商标)[^，。\n]{0,20}纠纷)',
        r'(著作权[^，。\n]{0,10}纠纷)',
        r'(专利权[^，。\n]{0,10}纠纷)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    # fallback: look for case cause in title line
    title_m = re.search(r'[一-鿿]{2,20}纠纷', text)
    if title_m:
        return title_m.group(0)
    return ''


# ---------------------------------------------------------------------------
# 日期解析（中文大写 & 阿拉伯数字）
# ---------------------------------------------------------------------------

# 中文数字 → 阿拉伯数字 映射
CN_NUM_MAP = {
    '〇': 0, '○': 0, '零': 0,
    '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10,
}

def _cn_num_to_int(s: str) -> int:
    """将中文数字字符串转为整数。

    支持两种模式：
    - 位置制：二〇二四 → 2024（年、电话号等）
    - 数位制：二十八 → 28（月、日等）
    """
    s = s.strip()
    if not s:
        return 0
    # 先尝试直接是阿拉伯数字
    try:
        return int(s)
    except ValueError:
        pass

    # 检查是否全部是简单数字（不含'十'、'百'、'千'等数位词）
    # 若是，按位置制解析（适合年份：二〇二四 = 2024）
    has_place_marker = any(ch in ('十', '百', '千', '万', '亿') for ch in s)
    if not has_place_marker:
        result = 0
        for ch in s:
            if ch in CN_NUM_MAP:
                result = result * 10 + CN_NUM_MAP[ch]
        if result > 0:
            return result

    # 数位制转换（包含'十'、'百'等数位词）
    total = 0
    section = 0
    for ch in s:
        if ch in CN_NUM_MAP:
            val = CN_NUM_MAP[ch]
            if val == 10:
                section = section * 10 if section > 0 else 10
            else:
                section += val
    total += section
    return total


def parse_chinese_date(text: str):
    """从文本中解析中文日期，返回 'YYYY-MM-DD' 字符串。

    支持格式：
    - 二〇二四年五月二十八日
    - 2024年5月28日
    - 二○二四年五月二十八日

    优先中文数字日期（真实审判日期几乎总是用中文书写在落款区），
    次选阿拉伯数字日期（需通过年份范围校验，排除附录中的商标注册日/到期日）。
    """
    # 优先：中文数字日期（落款区几乎全部用中文书写）
    m = re.search(
        r'([二○〇一二三四五六七八九]{4,6})\s*年\s*'
        r'([一二三四五六七八九十]+)\s*月\s*'
        r'([一二三四五六七八九十]+)\s*日',
        text
    )
    if m:
        year = _cn_num_to_int(m.group(1))
        month = _cn_num_to_int(m.group(2))
        day = _cn_num_to_int(m.group(3))
        if 2020 <= year <= 2026 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 阿拉伯数字日期（需年份校验，排除附录表中商标注册日/到期日等噪声）
    m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        if 2020 <= year <= 2026 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    return ''


# ===========================================================================
# 文书正文读取
# ===========================================================================

def read_file_content(filepath: str) -> str:
    """读取文件正文内容，自动检测编码。

    支持 .txt / .docx / .pdf 格式。
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.txt':
        return _read_txt(filepath)
    elif ext == '.docx':
        return _read_docx(filepath)
    elif ext == '.pdf':
        return _read_pdf(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _read_txt(filepath: str) -> str:
    """读取 TXT 文件，自动检测编码。"""
    # 先按序尝试常见中文编码
    for enc in ENCODING_CANDIDATES:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            if content and len(content) > 50:
                # 简单启发性检查：如果包含常见中文字符，则认为解码正确
                if any('一' <= c <= '鿿' or '　' <= c <= '〿'
                       for c in content[:500]):
                    return content
        except (UnicodeDecodeError, UnicodeError):
            continue

    # 回退：用 chardet 检测
    if HAS_CHARDET:
        with open(filepath, 'rb') as f:
            raw = f.read()
        result = _chardet_mod.detect(raw)
        enc = result.get('encoding') or 'utf-8'
        confidence = result.get('confidence', 0)
        try:
            content = raw.decode(enc, errors='replace')
            if content:
                return content
        except Exception:
            pass

    # 最后回退：用 errors='replace' 强制解码
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _read_docx(filepath: str) -> str:
    """读取 DOCX 文件正文。"""
    if not HAS_DOCX:
        raise ImportError("请先 pip install python-docx")
    doc = _docx_mod.Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n'.join(paragraphs)


def _read_pdf(filepath: str) -> str:
    """读取 PDF 文件正文。"""
    if not HAS_PDFPLUMBER:
        raise ImportError("请先 pip install pdfplumber")
    pages_text = []
    with _pdf_mod.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return '\n'.join(pages_text)


# ===========================================================================
# 文档分段（核心解析逻辑）
# ===========================================================================

# 段落定位关键词（按文书结构顺序）
SECTION_MARKERS = [
    # (内部标识, [匹配关键词列表])
    ('当事人',    ['当事人']),
    ('审理经过',  ['审理经过', '审理经过']),
    ('原告诉称',  ['原告诉称', '上诉人称', '再审申请人称', '申诉人称', '申请再审人称']),
    ('被告辩称',  ['被告辩称', '被上诉人辩称', '被申诉人辩称', '再审被申请人辩称',
                  '被申请人辩称', '一审被告辩称', '原审被告辩称']),
    ('法院查明',  ['本院查明', '经审理查明', '再审查明', '经审理查明',
                  '一审法院查明', '一审法院认定', '原审查明',
                  '本院经审理查明', '二审查明']),
    ('法院认为',  ['本院认为', '再审认为', '本院再审认为',
                  '一审法院认为', '二审法院认为', '原审法院认为',
                  '本院认为', '再审认为',
                  '本案二审的争议焦点', '本案的争议焦点']),
    ('判决主文',  ['判决如下', '裁定如下', '调解如下']),
    ('裁判结果',  ['裁判结果']),
    ('落款',      ['落款', '审判长', '审判员', '代理审判员']),
]

# 编译为 (section_name, compiled_regex)
SECTION_RE_LIST = []
for sec_name, kw_list in SECTION_MARKERS:
    pattern = r'(?:^|\n)\s*(' + '|'.join(re.escape(kw) for kw in kw_list) + r')\s*'
    SECTION_RE_LIST.append((sec_name, re.compile(pattern)))


def _find_section_spans(content: str):
    """在正文中找到每个段落的 (起始位置, 起始标记, 下一段起始位置)。

    返回列表 [(section_name, start_pos, marker_text, end_pos), ...]
    按在文档中出现的位置排序。
    """
    spans = []
    for sec_name, regex in SECTION_RE_LIST:
        for m in regex.finditer(content):
            spans.append((sec_name, m.start(), m.group(0).strip(), None))
    spans.sort(key=lambda x: x[1])

    # 计算每段的结束位置
    for i in range(len(spans)):
        end_pos = spans[i + 1][1] if i + 1 < len(spans) else len(content)
        spans[i] = (spans[i][0], spans[i][1], spans[i][2], end_pos)

    return spans


def get_section_text(content: str, section_name: str) -> str:
    """提取指定段落文本。如果同一类型有多个匹配，取第一个。"""
    spans = [s for s in _find_section_spans(content) if s[0] == section_name]
    if not spans:
        return ''
    s = spans[0]
    text = content[s[1]:s[3]]
    # 去掉首行标记本身
    text = text[len(s[2]):]
    return clean_text(text)


def get_all_section_texts(content: str) -> OrderedDict:
    """提取文档中所有段落文本。"""
    spans = _find_section_spans(content)
    sections = OrderedDict()
    for sec_name, start, marker, end in spans:
        text = content[start:end]
        text = text[len(marker):]  # 去掉标记行
        text = clean_text(text)
        if sec_name not in sections:
            sections[sec_name] = text
        else:
            # 同名段落追加
            sections[sec_name] += '\n' + text
    return sections


def clean_text(text: str) -> str:
    """清理多余空白但保留有意义换行。"""
    # 替换全角空格为半角空格
    text = text.replace('　', ' ')
    # 压缩连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去掉首尾空白
    text = text.strip()
    return text


# ===========================================================================
# 字段提取函数
# ===========================================================================

def extract_case_link(content: str) -> str:
    """提取 原文链接。"""
    m = re.search(r'原文链接[：:]\s*(https?://[^\s\n]+)', content)
    if m:
        return m.group(1).strip()
    return ''


def extract_pkulaw_ref(content: str) -> str:
    """提取法宝引证码。"""
    m = re.search(r'【法宝引证码】\s*(\S+)', content)
    if m:
        return m.group(1).strip()
    return ''


def extract_title(content: str) -> str:
    """提取文书标题。"""
    # 模式1：标准括号标题 (重庆某餐饮管理有限公司与某集团总公司侵害商标权纠纷二审民事判决书)
    m = re.search(r'[（(]\s*(.{8,100}?(?:纠纷|争议).{0,20}?(?:判决书|裁定书|调解书))', content[:2000])
    if m:
        title = m.group(1).strip()
        if 8 <= len(title) <= 100:
            return _clean_title(title)

    # 模式2：从独立行中找标题
    lines = content[:2000].split('\n')
    for line in lines:
        line = line.strip()
        if 10 <= len(line) <= 120:
            if any(kw in line for kw in ['判决书', '裁定书', '调解书', '判决', '裁定', '民事其他']):
                if '人民法院' not in line and not re.match(r'^[\s　]*民事', line):
                    # 检查是否包含当事人名（以逗号或顿号分隔）
                    if re.search(r'[一-鿿A-Za-z]{2,}[、；;,][一-鿿A-Za-z]{2,}', line):
                        return _clean_title(line)
                    if '纠纷' in line:
                        return _clean_title(line)

    # 模式3：模糊匹配 — 纠纷 + 文书类型
    m = re.search(r'([一-鿿A-Za-z（）()、，,\s]{6,100}?(?:侵害|侵犯|商标|著作权|专利|不正当竞争).{0,30}?(?:纠纷).{0,20}?(?:判决书|裁定书|调解书))',
                  content[:2000])
    if m:
        return _clean_title(m.group(1).strip())

    # 模式4：仅提取"XX纠纷"作为标题回退
    m = re.search(r'([一-鿿A-Za-z（）()、，,\s]{6,60}?纠纷)[一-鿿]{0,10}(?:一审|二审|再审|终审)[一-鿿]{0,10}(?:判决书|裁定书|调解书)',
                  content[:2000])
    if m:
        full = m.group(0).strip()
        if 6 <= len(full) <= 100:
            return _clean_title(full)

    return ''


def _clean_title(title: str) -> str:
    """清理标题中的噪音前缀后缀。"""
    # 去除 PKULaw 搜索页面面包屑残留
    for suffix in ['展开开庭公告', '开庭公告', '判决书展开', '文书全文']:
        idx = title.find(suffix)
        if idx > 0:
            title = title[:idx]
    # 去除开头的数字编号（如 "3189甲公司" → "甲公司"）
    title = re.sub(r'^\d{2,6}(?=[一-鿿A-Z])', '', title)
    # 去除开头的 "陈某," "某某、" 等面包屑残片
    title = re.sub(r'^[一-鿿A-Za-z（）()·]{1,6}[，,、]\s*', '', title)
    return title.strip()


def extract_court_name(content: str) -> str:
    """提取审理法院名称。"""
    # 标准格式：在第一段中独立成行的 "XXX人民法院"
    # 优先取 当事人 之前的最后一个法院名称
    party_pos = content.find('当事人')
    if party_pos < 0:
        party_pos = content.find('当事人')
    header = content[:party_pos] if party_pos > 0 else content[:1500]

    # 逐行查找法院
    lines = header.split('\n')
    for line in reversed(lines):
        line = line.strip()
        if '人民法院' in line and len(line) <= 60:
            return line

    # 回退：在全文中搜索
    m = re.search(r'([一-鿿（）()]{2,20}(?:人民法院))', content[:2000])
    if m:
        return m.group(1).strip()
    return ''


def extract_case_number(content: str) -> str:
    """提取案件字号。

    格式示例：
    - 民事判决书(2023)粤0104民初40327号
    - （2025）沪0104民初6619号
    - (2024)黔01民终12518号

    优先匹配：文书类型标签 后紧跟的 (XXXX)XX...X号 格式的模式
    """
    # 文案标记后的标准格式：民事判决书(2024)粤0604民初30007号
    doc_labels = ['民事判决书', '民事裁定书', '民事调解书',
                  '刑事判决书', '刑事裁定书', '行政判决书', '行政裁定书']
    for label in doc_labels:
        # 匹配 label 之后紧挨的括号案号
        m = re.search(re.escape(label) + r'\s*[（(](\d{4}[）)][一-鿿\d]{4,30}\d+号)', content[:2000])
        if m:
            return m.group(1).strip()
        # 宽松匹配中文括号
        m = re.search(re.escape(label) + r'\s*\（(\d{4}\）[一-鿿\d]{4,30}\d+号)', content[:2000])
        if m:
            return m.group(1).strip()

    # 回退1：独立括号案号 — 严格的案号格式
    m = re.search(r'[（(](\d{4}[）)][一-鿿]{1,6}\d*[民刑行知赔执破认仲]{1,4}[初终再审抗申确重]{1,3}\d+号)',
                  content[:3000])
    if m:
        return m.group(1).strip()

    # 回退2：无括号格式 "2024浙0483民初1234号"
    m = re.search(r'(\d{4}[一-鿿]{1,6}\d*[民刑行]{1,4}[初终再审]{1,3}\d+号)', content[:3000])
    if m:
        return m.group(1).strip()

    return ''


def extract_trial_date(content: str) -> str:
    """提取审结日期（从落款区域提取作为终审日期）。"""
    # 先尝试找"落款"后的日期
    lokuan_pos = content.rfind('落款')
    if lokuan_pos < 0:
        lokuan_pos = max(0, len(content) - 800)

    tail_text = content[lokuan_pos:]
    date_str = parse_chinese_date(tail_text)
    if date_str:
        return date_str

    # 回退：从文档末尾向前搜索，取第一个通过年份校验的日期
    # （避免取到附录中的商标注册日/到期日等噪声日期）
    all_dates = []
    for m in re.finditer(r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)', content):
        all_dates.append(m.group(0))
    for m in re.finditer(
        r'([二○〇一二三四五六七八九]{4,6}\s*年\s*[一二三四五六七八九十]+\s*月\s*[一二三四五六七八九十]+\s*日)',
        content
    ):
        all_dates.append(m.group(0))

    # 从后往前试，取第一个通过 parse_chinese_date 校验的日期
    for date_str in reversed(all_dates):
        parsed = parse_chinese_date(date_str)
        if parsed:
            return parsed
    return ''


def extract_judges(content: str) -> str:
    """提取审理法官姓名（去重）。

    处理落款中的各种格式变体：
    - 审判员 黄媛媛
    - 审 判 员 王 筱  (有空格分隔)
    - 审 判 长  邹辉球
    """
    lokuan_pos = content.rfind('落款')
    if lokuan_pos < 0:
        lokuan_pos = max(0, len(content) - 800)
    tail_text = content[lokuan_pos:]

    # 先规范化角色标题中的空格：'审 判 长' → '审判长', '审 判 员' → '审判员'
    tail_text = re.sub(r'(审)\s+(判)\s*(长|员)', r'\1\2\3', tail_text)

    # 如果落款区域找不到，扩展搜索范围到全文后部
    search_text = tail_text if tail_text else content[-2000:]

    seen_names = set()
    judges = []
    for role in ['审判长', '代理审判员', '人民陪审员', '审判员']:
        # 匹配角色标题后的名字，名字中可能存在空格（如 王 筱 或 鲍  芙  蓉）
        # 模式：角色标题 + 空白 + 姓名（可能含任意数量内部空格）
        pattern = re.escape(role) + r'[ 　\t]+((?:[一-鿿]{1,2}[ 　\t]*)+)'
        for m in re.finditer(pattern, search_text):
            name_raw = m.group(1).strip()
            # 移除姓名内部空格（王 筱 → 王筱）
            name = re.sub(r'[ 　\t]+', '', name_raw)
            if (2 <= len(name) <= 4 and
                name not in seen_names and
                name not in ['审判员', '审判长', '书记员', '代理审判员',
                             '人民陪审员', '法官助理', '书记员']):
                seen_names.add(name)
                judges.append(f"{role} {name}")

    if not judges:
        # 全文搜索
        full_text = re.sub(r'(审)\s+(判)\s*(长|员)', r'\1\2\3', content)
        for role in ['审判长', '代理审判员', '人民陪审员', '审判员']:
            pattern = re.escape(role) + r'[ 　\t]+((?:[一-鿿]{1,2}[ 　\t]*)+)'
            for m in re.finditer(pattern, full_text):
                name_raw = m.group(1).strip()
                name = re.sub(r'[ 　\t]+', '', name_raw)
                if (2 <= len(name) <= 4 and
                    name not in seen_names and
                    name not in ['审判员', '审判长', '书记员', '原告', '被告', '代理审判员']):
                    seen_names.add(name)
                    judges.append(f"{role} {name}")
                if len(judges) >= 5:
                    break
        judges = judges[:5]

    return '; '.join(judges)


def extract_parties(content: str) -> dict:
    """解析当事人段落，提取各诉讼参与主体信息。"""
    party_text = get_section_text(content, '当事人')
    if not party_text:
        # 没有"当事人"标记，尝试从前3000字符内提取
        party_text = content[:3000]

    result = {
        '原告': '',
        '被告': '',
        '上诉人': '',
        '被上诉人': '',
        '第三人': '',
        '再审申请人': '',
        '再审被申请人': '',
        '代理律师': '',
        '代理律所': '',
    }

    # 当事人角色模式 — 用尾部关键词截断避免多余吸附
    # 角色信息的自然边界：住所地、代表人、委托诉讼代理人、投资人 等后续标记
    ROLE_END = (r'(?:\s*(?:原告\s*[：:]|被告\s*[：:]|上诉人\s*[：:]|被上诉人\s*[：:]'
                r'|第三人\s*[：:]|再审申请人\s*[：:]|再审被申请人\s*[：:]'
                r'|代表人|委托诉讼代理人|委托代理人|诉讼代理人'
                r'|\n\s*[一-鿿]{2,8}\s*[：:]'
                r'|\n\n))')

    role_patterns = [
        (r'原告(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '原告'),
        (r'上诉人(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '上诉人'),
        (r'被告(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '被告'),
        (r'被上诉人(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '被上诉人'),
        (r'第三人(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '第三人'),
        (r'再审申请人(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '再审申请人'),
        (r'再审被申请人(?:\([^)]*\))?\s*[：:](\S.{0,200}?)' + ROLE_END, '再审被申请人'),
    ]

    for pattern, role in role_patterns:
        matches = re.findall(pattern, party_text, re.DOTALL)
        if matches:
            # 进一步清理：截断到住所地、投资人、法定代表人、经营者 等附加字段之前
            cleaned = []
            for m_text in matches:
                m_text = m_text.strip()[:200]
                # 截断掉内嵌的 "住所地" "投资人" 等非角色信息
                cut_at = len(m_text)
                for cut_word in ['\n', '代表人', '法定代表人', '经营者', '负责人',
                                 '住所地', '住址', '地址', '投资人',
                                 '统一社会信用代码',
                                 '广东省', '浙江省', '江苏省', '北京市', '上海市',
                                 '天津市', '重庆市', '山东省', '四川省', '湖北省',
                                 '湖南省', '河南省', '福建省', '安徽省', '江西省',
                                 '辽宁省', '吉林省', '黑龙江省', '河北省', '山西省',
                                 '陕西省', '甘肃省', '青海省', '云南省', '贵州省',
                                 '海南省', '广西', '西藏', '宁夏', '新疆', '内蒙古']:
                    idx = m_text.find(cut_word)
                    if 0 < idx < cut_at:
                        cut_at = idx
                m_text = m_text[:cut_at].strip().rstrip('，,。.')
                if m_text:
                    cleaned.append(m_text)
            if cleaned:
                result[role] = ' || '.join(cleaned)

    # 提取代理律师
    lawyers = []
    for m in re.finditer(r'(?:委托诉讼代理人|委托代理人|诉讼代理人|代理人)\s*[：:]\s*([一-鿿]{2,4})',
                         party_text):
        name = m.group(1).strip()
        if name not in lawyers:
            lawyers.append(name)
    result['代理律师'] = '; '.join(lawyers)

    # 提取代理律所
    firms = set()
    for m in re.finditer(r'([一-鿿（）()\w]{2,25}律师事务所)', party_text):
        firms.add(m.group(1).strip())
    result['代理律所'] = '; '.join(sorted(firms))

    return result


def extract_plaintiff_claims(content: str, sections: OrderedDict) -> str:
    """提取诉讼请求。"""
    # 优先从原告诉称段落提取 "诉讼请求"
    plaintiff_text = sections.get('原告诉称', '')
    if not plaintiff_text:
        plaintiff_text = get_section_text(content, '原告诉称')

    if plaintiff_text:
        # 提取"诉讼请求" 到 "事实与理由" 或 "事实和理由" 之间的内容
        m = re.search(r'诉讼请求[：:](.*?)(?:事实[与和]?理由|\Z)', plaintiff_text, re.DOTALL)
        if m:
            return clean_text(m.group(1))[:5000]
        # 若没有明确分段，返回开头部分
        end_markers = ['事实与理由', '事实和理由', '被告辩称']
        end_pos = len(plaintiff_text)
        for marker in end_markers:
            idx = plaintiff_text.find(marker)
            if 0 < idx < end_pos:
                end_pos = idx
        return clean_text(plaintiff_text[:end_pos])[:5000]

    return ''


def extract_defense(content: str, sections: OrderedDict) -> str:
    """提取辩方观点。"""
    defense = sections.get('被告辩称', '')
    if not defense:
        defense = get_section_text(content, '被告辩称')
    return defense[:5000] if defense else ''


def extract_trial_process(content: str, sections: OrderedDict) -> str:
    """提取审理经过。"""
    trial = sections.get('审理经过', '')
    if not trial:
        trial = get_section_text(content, '审理经过')
    return trial[:5000] if trial else ''


def extract_court_findings(content: str, sections: OrderedDict) -> str:
    """提取法院查明（本院查明 / 经审理查明）。"""
    findings = sections.get('法院查明', '')
    if not findings:
        findings = get_section_text(content, '法院查明')
    return findings[:10000] if findings else ''


def extract_court_opinion(content: str, sections: OrderedDict) -> str:
    """提取法院认为。"""
    opinion = sections.get('法院认为', '')
    if not opinion:
        opinion = get_section_text(content, '法院认为')

    if not opinion:
        return ''

    # 截断到 "判决如下" / "裁定如下" 之前
    end_markers = ['判决如下', '裁定如下', '调解如下', '裁判结果', '依照《']
    min_pos = len(opinion)
    for marker in end_markers:
        idx = opinion.find(marker)
        if 0 < idx < min_pos:
            min_pos = idx

    # 但如果截断后太短，保留更多（最后一段"综上所述"后的内容也是法院认为）
    if min_pos > 200:
        opinion = opinion[:min_pos]

    return clean_text(opinion)[:10000]


def extract_judgment_result(content: str, sections: OrderedDict) -> str:
    """提取裁判结果。"""
    # 优先取 "裁判结果" 段落
    result = sections.get('裁判结果', '')
    if result:
        return clean_text(result)[:5000]

    # 其次取 "判决主文"（判决如下）
    result = sections.get('判决主文', '')
    if result:
        return clean_text(result)[:5000]

    # 回退：手动查找
    for marker in ['裁判结果', '判决如下', '裁定如下']:
        idx = content.find(marker)
        if idx >= 0:
            # 从标记到落款之间
            lokuan_pos = content.find('落款', idx)
            if lokuan_pos < 0:
                lokuan_pos = len(content)
            text = content[idx + len(marker):lokuan_pos]
            return clean_text(text)[:5000]

    return ''


def extract_dispute_focus(content: str, court_opinion: str) -> str:
    """提取争议焦点。"""
    text = court_opinion if court_opinion else content
    patterns = [
        r'(?:本案[的之]?\s*争议焦点\s*(?:是|为|：|:))\s*(.+?)(?:。|\n\n)',
        r'(?:争议焦点\s*(?:是|为|：|:))\s*(.+?)(?:。|\n\n)',
        r'(?:本案[的之]?\s*焦点[问题]?\s*(?:是|为|：|:))\s*(.+?)(?:。|\n\n)',
        r'(?:归纳本案[的之]?\s*争议焦点[为是：:])\s*(.+?)(?:。|\n\n)',
    ]
    for pat in patterns:
        m = re.search(pat, text[:5000])
        if m:
            return m.group(1).strip()[:2000]
    return ''


def extract_final_judgment(judgment_text: str, content: str) -> str:
    """从裁判结果文本推断终审结果方向。

    简化为标注：
    - 支持原告诉讼请求 → "支持原告诉请"
    - 部分支持 → "部分支持"
    - 驳回 → "驳回"
    - 维持原判 → "维持原判"
    """
    if not judgment_text:
        judgment_text = content[-3000:]

    text = judgment_text[:3000]

    if '维持原判' in text or '维持原判' in text or '驳回上诉' in text:
        return '维持原判'

    has_support = False
    has_reject = False

    if re.search(r'(?:支持|赔偿|停止|销毁|消除|赔礼|道歉)', text):
        has_support = True
    if re.search(r'(?:驳回|不予支持|不支持)', text):
        has_reject = True

    if has_support and has_reject:
        return '部分支持'
    if has_support:
        return '支持原告诉请'
    if has_reject:
        return '驳回'
    return ''


def extract_key_points(opinion: str, judgment: str) -> str:
    """从法院认为和裁判结果中提取裁判要点摘要。

    提取法院认为最后一段"综上"或关键法律适用段落。
    """
    if not opinion:
        return ''

    # 取"综上所述"段落
    m = re.search(r'(?:综上(?:所述)?[：:,，].+?)(?=\n\n|\Z)', opinion, re.DOTALL)
    if m:
        return m.group(0).strip()[:3000]

    # 取最后一段
    paras = opinion.strip().split('\n\n')
    if paras and len(paras[-1]) > 30:
        return paras[-1].strip()[:3000]

    return ''


# ===========================================================================
# 主解析函数
# ===========================================================================

def parse_document(content: str, filepath: str = '') -> OrderedDict:
    """解析单篇裁判文书，返回所有字段的有序字典。"""
    sections = get_all_section_texts(content)

    # ---- 基础信息 ----
    case_link       = extract_case_link(content)
    pkulaw_ref      = extract_pkulaw_ref(content)
    title           = extract_title(content)
    case_cause      = detect_case_cause(title, content)

    # ---- 法院与程序 ----
    court_name      = extract_court_name(content)
    province        = detect_province(court_name)
    court_level     = detect_court_level(court_name)
    doc_type        = detect_doc_type(content)
    procedure       = detect_procedure(content, title=title)
    judges          = extract_judges(content)

    # ---- 案件字号 ----
    case_number     = extract_case_number(content)
    trial_date      = extract_trial_date(content)

    # ---- 诉讼主体 ----
    parties_info    = extract_parties(content)

    # ---- 案件核心内容 ----
    claims          = extract_plaintiff_claims(content, sections)
    defense         = extract_defense(content, sections)
    trial_process   = extract_trial_process(content, sections)
    court_findings  = extract_court_findings(content, sections)
    court_opinion   = extract_court_opinion(content, sections)

    # ---- 争议焦点 ----
    dispute_focus   = extract_dispute_focus(content, court_opinion)

    # ---- 裁判结果 ----
    judgment_result = extract_judgment_result(content, sections)
    final_judgment  = extract_final_judgment(judgment_result, content)
    key_points      = extract_key_points(court_opinion, judgment_result)

    # ---- 组装 ----
    record = OrderedDict([
        # 基础信息
        ('序号',         ''),  # 由外部按序编号
        ('标题',         title),
        ('案由',         case_cause),
        ('案件字号',      case_number),
        ('审结日期',      trial_date),
        ('公开类型',      ''),
        ('原文链接',      case_link),
        ('法宝引证码',    pkulaw_ref),
        # 法院与程序
        ('审理法院',      court_name),
        ('省份',          province),
        ('法院级别',      court_level),
        ('参照级别',      ''),  # 需要外部知识库标注
        ('审理程序',      procedure),
        ('文书类型',      doc_type),
        ('审理法官',      judges),
        # 诉讼主体
        ('原告/上诉人',    parties_info.get('原告', '') or parties_info.get('上诉人', '')),
        ('被告/被上诉人',  parties_info.get('被告', '') or parties_info.get('被上诉人', '')),
        ('第三人',        parties_info.get('第三人', '')),
        ('再审申请人',    parties_info.get('再审申请人', '')),
        ('再审被申请人',  parties_info.get('再审被申请人', '')),
        ('代理律师',      parties_info.get('代理律师', '')),
        ('代理律所',      parties_info.get('代理律所', '')),
        # 案件核心内容
        ('诉讼请求',      claims),
        ('辩方观点',      defense),
        ('审理经过',      trial_process),
        ('法院查明',      court_findings),
        ('法院认为',      court_opinion),
        ('争议焦点',      dispute_focus),
        # 裁判结果
        ('裁判结果',      judgment_result),
        ('终审结果',      final_judgment),
        ('裁判要点',      key_points),
        # 溯源
        ('源文件',        filepath),
    ])

    return record


# ===========================================================================
# 单文件处理器（用于多进程）
# ===========================================================================

def process_file(filepath: str) -> tuple:
    """处理单个文件，返回 (record_dict, error_msg_or_None)。"""
    try:
        content = read_file_content(filepath)
        if not content or len(content) < 100:
            return (None, f"文件内容过短 ({len(content)} 字符): {filepath}")
        record = parse_document(content, filepath)
        return (record, None)
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return (None, f"文件: {filepath}\n{error_detail}")


# ===========================================================================
# 批量处理 & 主入口
# ===========================================================================

# 字段顺序（与 parse_document 输出保持一致）
FIELD_NAMES = [
    '序号', '标题', '案由', '案件字号', '审结日期', '公开类型', '原文链接', '法宝引证码',
    '审理法院', '省份', '法院级别', '参照级别', '审理程序', '文书类型', '审理法官',
    '原告/上诉人', '被告/被上诉人', '第三人', '再审申请人', '再审被申请人',
    '代理律师', '代理律所',
    '诉讼请求', '辩方观点', '审理经过', '法院查明', '法院认为', '争议焦点',
    '裁判结果', '终审结果', '裁判要点',
    '源文件',
]

BATCH_SAVE_INTERVAL = 500  # 每 500 个文件保存一批


def save_batch_csv(records: list, batch_idx: int, output_dir: str) -> str:
    """将一批记录保存为 CSV 临时文件，返回文件路径。"""
    batch_file = os.path.join(output_dir, f"005_data/output_judgments_batch_{batch_idx:04d}.csv")
    write_csv(batch_file, records)
    return batch_file


def write_csv(filepath: str, records: list):
    """写入 CSV 文件。"""
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, '') for k in FIELD_NAMES})


def merge_csvs_to_excel(csv_files: list, output_path: str):
    """合并多个 CSV 为一个 Excel 文件。"""
    if not csv_files:
        print("[WARN] 没有 CSV 文件可合并。")
        return

    dfs = []
    for cf in csv_files:
        df = pd.read_csv(cf, dtype=str, keep_default_na=False)
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)
    # 重新编号序号
    merged['序号'] = range(1, len(merged) + 1)

    print(f"[INFO] 正在写入 Excel (共 {len(merged)} 条记录)...")
    merged.to_excel(output_path, index=False, engine='openpyxl')
    print(f"[INFO] Excel 已保存至: {output_path}")
    return merged


def main():
    # ---- 配置 ----
    target_dir = "/Users/weiyueshao/Desktop/pipeline_v2/003_案例"
    output_dir = "/Users/weiyueshao/Desktop/pipeline_v2"
    output_excel = os.path.join(output_dir, "006_outputs/output_judgments.xlsx")
    error_log = os.path.join(output_dir, "005_data/error_log.txt")
    max_workers = max(1, os.cpu_count() or 4)

    print("=" * 70)
    print("  中国裁判文书（侵害商标权纠纷）批量结构化解析")
    print("=" * 70)
    print(f"[INFO] 目标文件夹: {target_dir}")
    print(f"[INFO] 并行进程数: {max_workers}")
    print(f"[INFO] 批次保存间隔: 每 {BATCH_SAVE_INTERVAL} 个文件")
    print()

    # ---- 收集文件 ----
    print("[INFO] 正在扫描文件...")
    files = []
    for ext in SUPPORTED_EXTS:
        files.extend(glob.glob(os.path.join(target_dir, f"*{ext}")))
        files.extend(glob.glob(os.path.join(target_dir, f"*{ext.upper()}")))
    files = sorted(set(files))

    total = len(files)
    print(f"[INFO] 找到 {total} 个文件")
    if total == 0:
        print("[ERROR] 未找到任何支持的文件（.txt / .docx / .pdf），退出。")
        sys.exit(1)
    print()

    # ---- 多进程处理 ----
    all_records = []
    all_errors = []
    batch_files = []
    batch_idx = 0
    completed_count = 0

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, f): f for f in files}

        with tqdm(total=total, desc="解析进度", unit="篇", ncols=100,
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:

            for future in as_completed(futures):
                filepath = futures[future]
                try:
                    record, error = future.result(timeout=120)  # 单文件超时 120 秒
                except Exception as e:
                    record, error = None, f"超时或执行异常: {filepath}\n{type(e).__name__}: {e}"
                except KeyboardInterrupt:
                    print("\n[WARN] 用户中断，正在保存已解析数据...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                if error:
                    all_errors.append(error)
                elif record:
                    all_records.append(record)

                completed_count += 1
                pbar.update(1)

                # 每 BATCH_SAVE_INTERVAL 个文件保存一批
                if len(all_records) > 0 and len(all_records) % BATCH_SAVE_INTERVAL == 0:
                    batch_file = save_batch_csv(all_records[-BATCH_SAVE_INTERVAL:], batch_idx, output_dir)
                    batch_files.append(batch_file)
                    batch_idx += 1
                    pbar.set_postfix_str(f"已存批次 {batch_idx}")

    # ---- 保存最后一批（剩余未保存的） ----
    saved_count = batch_idx * BATCH_SAVE_INTERVAL
    remaining = all_records[saved_count:]
    if remaining:
        batch_file = save_batch_csv(remaining, batch_idx, output_dir)
        batch_files.append(batch_file)
        batch_idx += 1

    elapsed = time.time() - start_time

    # ---- 输出统计 ----
    print()
    print("-" * 70)
    print(f"[统计] 总文件数:   {total}")
    print(f"[统计] 成功解析:   {len(all_records)}")
    print(f"[统计] 解析失败:   {len(all_errors)}")
    print(f"[统计] 总耗时:     {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    print(f"[统计] 平均速度:   {total/elapsed:.1f} 篇/秒")
    print()

    # ---- 写入错误日志 ----
    if all_errors:
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write(f"错误日志 — {datetime.now().isoformat()}\n")
            f.write(f"共 {len(all_errors)} 个文件解析失败\n")
            f.write("=" * 70 + "\n\n")
            for i, err in enumerate(all_errors, 1):
                f.write(f"[{i}] {err}\n\n")
        print(f"[INFO] 错误日志已保存至: {error_log}")

    # ---- 合并所有批次为 Excel ----
    if not all_records and not batch_files:
        print("[ERROR] 没有成功解析的记录，无法生成 Excel。")
        sys.exit(1)

    merge_csvs_to_excel(batch_files, output_excel)

    # ---- 清理临时 CSV 文件 ----
    for bf in batch_files:
        try:
            os.remove(bf)
        except OSError:
            pass
    print(f"[INFO] 已清理 {len(batch_files)} 个临时 CSV 文件。")

    print()
    print("=" * 70)
    print("  处理完成！")
    print(f"  输出文件: {output_excel}")
    if all_errors:
        print(f"  错误日志: {error_log}")
    print("=" * 70)


if __name__ == '__main__':
    main()
