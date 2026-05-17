"""感知模块

职责：对每份文书进行"体检"——编码、结构、内容完整性、异常检测。
不修改文书，只产生观察报告。
"""
import os
import re
from dataclasses import dataclass, field, asdict


@dataclass
class DocumentProfile:
    """单份文书的感知结果"""
    filename: str
    encoding_detected: str = "unknown"
    file_size_bytes: int = 0
    total_chars: int = 0

    # 结构完整性
    has_plaintiff_claim: bool = False       # 原告诉称
    has_defendant_argument: bool = False     # 被告辩称
    has_court_finding: bool = False          # 本院查明
    has_court_reasoning: bool = False        # 本院认为
    has_verdict: bool = False                # 判决如下
    has_case_number: bool = False            # 案号

    # 异常标记
    garbled_ratio: float = 0.0              # 乱码比例
    is_duplicate_title: bool = False        # 疑似重复
    structure_anomalies: list = field(default_factory=list)
    quality_score: float = 1.0              # 0-1，1=完美

    # 判决书类型
    doc_type: str = "unknown"               # civil/criminal/admin
    trial_level: str = "unknown"            # first/second/retrial


SECTION_MARKERS = {
    "plaintiff": re.compile(r"(原告诉称|上诉人称|再审申请人称|申诉人称|原告.*诉称|上诉人.*称)"),
    "defendant": re.compile(r"(被告辩称|被上诉人辩称|被申诉人辩称|再审被申请人辩称|被告.*辩称)"),
    "finding": re.compile(r"(本院查明|经审理查明|一审查明|原审查明|再审查明|经审理.*查明)"),
    "reasoning": re.compile(r"(本院认为|再审认为|本院再审认为|本院.*认为|本庭认为)"),
    "verdict": re.compile(r"(判决如下|裁定如下|调解如下|判令|一、|一，)"),
}

CASE_NUMBER_PATTERN = re.compile(r"[(（]\d{4}[)）][一-龥]{0,4}\d{1,4}[一-龥]{0,4}(?:民初|民终|民再|民申|行初|行终|刑初|刑终|知民初|知民终)\S*第?\d+号")

GARBLED_PATTERN = re.compile(r"[�\x00-\x08\x0b\x0c\x0e-\x1f]")


def perceive_document(filepath: str) -> DocumentProfile:
    """感知单份文书，返回DocumentProfile"""
    filename = os.path.basename(filepath)
    size = os.path.getsize(filepath)

    profile = DocumentProfile(
        filename=filename,
        file_size_bytes=size,
    )

    try:
        # 编码检测（简化版：按常见编码依次尝试）
        content = None
        for enc in ["utf-8", "gb18030", "gbk", "gb2312"]:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    content = f.read()
                # 验证是否有中文字符
                if any('一' <= c <= '鿿' for c in content[:200]):
                    profile.encoding_detected = enc
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            # 最后尝试chardet
            try:
                import chardet
                with open(filepath, "rb") as f:
                    raw = f.read()
                enc = chardet.detect(raw).get("encoding", "utf-8")
                content = raw.decode(enc, errors="replace")
                profile.encoding_detected = enc or "unknown"
            except Exception:
                profile.encoding_detected = "unknown"
                profile.quality_score = 0.0
                profile.structure_anomalies.append("无法解码文件内容")
                return profile

        profile.total_chars = len(content)
        first_500 = content[:500]

        # 结构完整性检测
        for key, pattern in SECTION_MARKERS.items():
            found = bool(pattern.search(content))
            setattr(profile, f"has_{key}_claim" if key == "plaintiff" else
                          f"has_{key}_argument" if key == "defendant" else
                          f"has_{key}_finding" if key == "finding" else
                          f"has_{key}_reasoning" if key == "reasoning" else
                          f"has_{key}_verdict" if key == "verdict" else None, found)

        # 案号检测
        profile.has_case_number = bool(CASE_NUMBER_PATTERN.search(content))

        # 乱码比例
        garbled_chars = len(GARBLED_PATTERN.findall(content))
        profile.garbled_ratio = garbled_chars / max(profile.total_chars, 1)

        # 异常检测
        if profile.garbled_ratio > 0.05:
            profile.structure_anomalies.append(f"乱码比例过高: {profile.garbled_ratio:.1%}")

        if not profile.has_case_number:
            profile.structure_anomalies.append("未检测到案号")

        missing_sections = []
        if not profile.has_court_reasoning and not profile.has_court_finding:
            missing_sections.append("本院认为/本院查明")
        if not profile.has_verdict:
            missing_sections.append("判决主文")
        if missing_sections:
            profile.structure_anomalies.append(f"缺失关键段落: {', '.join(missing_sections)}")

        # 判决书类型判断
        if "刑事" in first_500:
            profile.doc_type = "criminal"
        elif "行政" in first_500:
            profile.doc_type = "admin"
        else:
            profile.doc_type = "civil"

        if "二审" in first_500 or "上诉" in first_500:
            profile.trial_level = "second"
        elif "再审" in first_500:
            profile.trial_level = "retrial"
        else:
            profile.trial_level = "first"

        # 综合质量评分
        profile.quality_score = _calculate_quality(profile)

    except Exception as e:
        profile.quality_score = 0.0
        profile.structure_anomalies.append(f"感知异常: {str(e)[:100]}")

    return profile


def _calculate_quality(profile: DocumentProfile) -> float:
    """综合计算文书质量评分 0-1"""
    score = 1.0
    # 乱码扣分
    if profile.garbled_ratio > 0.1:
        score -= 0.5
    elif profile.garbled_ratio > 0.05:
        score -= 0.2
    elif profile.garbled_ratio > 0.01:
        score -= 0.05

    # 缺失关键段落扣分
    if not profile.has_court_reasoning:
        score -= 0.3
    if not profile.has_verdict:
        score -= 0.2
    if not profile.has_case_number:
        score -= 0.1

    # 太小可能是碎片
    if profile.total_chars < 500:
        score -= 0.3

    return max(0.0, score)


def perceive_batch(filepaths: list[str]) -> list[DocumentProfile]:
    """批量感知"""
    return [perceive_document(fp) for fp in filepaths]
