from typing import Dict, List, Optional
import re
from datetime import datetime
from .logger_manager import get_logger
from .ocr_error_manager import ErrorEntryManager

# 日期处理相关
DATE_PATTERNS = [
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}:\d{2})',
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2})',
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
]

def extract_timestamp_from_line(line: str) -> Optional[str]:
    """
    从文本行中提取时间戳
    """
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None

def fix_timestamp_format(ts: str) -> Optional[str]:
    """
    修复时间戳格式为标准格式
    """
    if not ts:
        return None

    s = ts.strip().replace("T", " ").replace(".", "-").replace("/", "-")
    s = re.sub(r'[年月日]', '-', s)
    s = re.sub(r'[^0-9\- :]', '', s)

    DATE_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return None

def clean_name_string(name: str, prefix_patterns: List[str], suffix_patterns: List[str]) -> str:
    """清理名称中的前缀和后缀"""
    cleaned = name
    for pattern in prefix_patterns:
        cleaned = re.sub(pattern, "", cleaned).strip()
    for pattern in suffix_patterns:
        cleaned = re.sub(pattern, "", cleaned).strip()
    return cleaned

def calculate_edit_distance(s1: str, s2: str) -> int:
    """
    计算编辑距离（莱文斯坦距离）
    """
    if len(s1) < len(s2):
        return calculate_edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def correct_recognized_name(name: str, valid_names: set, max_distance_ratio: float = 0.5, logger=None) -> Dict[str, Optional[str]]:
    """
    纠正识别错误的名称
    """
    if logger is None:
        logger = get_logger()
    if name in valid_names:
        return {"name": name, "is_valid": True}

    best_match = min(valid_names, key=lambda x: calculate_edit_distance(name, x))
    distance = calculate_edit_distance(name, best_match)

    if distance <= len(name) * max_distance_ratio:
        return {"name": best_match, "is_valid": True}

    logger.warning(f"[警告] 无法纠正名称: {name}")
    return {"name": name, "is_valid": False}

def clean_and_correct_entry(entry: Dict, valid_items: set, valid_pools: set, 
                           clean_config: Dict, error_manager: Optional[ErrorEntryManager] = None, 
                           image_path: Optional[str] = None, position: Optional[int] = None, logger=None) -> Optional[Dict]:
    """
    清洗和修正单个条目
    """
    if logger is None:
        logger = get_logger()

    # 清理名称
    if clean_config.get("enable_clean_name", False):
        entry["item"] = clean_name_string(entry["item"], 
                                           clean_config.get("prefix_patterns", []), 
                                           clean_config.get("suffix_patterns", []))
        entry["pool"] = clean_name_string(entry["pool"], 
                                           clean_config.get("prefix_patterns", []), 
                                           clean_config.get("suffix_patterns", []))

    # 纠正名称
    item_result = correct_recognized_name(entry["item"], valid_items, logger=logger)
    pool_result = correct_recognized_name(entry["pool"], valid_pools, logger=logger)

    # 检查是否有错误需要记录
    has_errors = not item_result["is_valid"] or not pool_result["is_valid"]

    # 应用纠正后的结果
    entry["item"] = item_result["name"]
    entry["pool"] = pool_result["name"]
    entry["is_valid"] = item_result["is_valid"] and pool_result["is_valid"]

    # 修复时间
    entry["time"] = fix_timestamp_format(entry["time"])

    # 如果有错误管理器，记录错误
    if error_manager and has_errors:
        error_manager.add_error_entry(entry, item_result, pool_result, image_path, position)

    # 跳过无效时间的条目
    if not entry["time"]:
        logger.warning(f"[警告] 跳过无效时间条目: {entry}")
        return None

    return entry

def parse_single_line(line: str, column_indices: Dict) -> Optional[Dict]:
    """
    解析单行文本为条目
    """
    timestamp = extract_timestamp_from_line(line)
    if not timestamp:
        return None

    ts_match = re.search(re.escape(timestamp), line)
    if not ts_match:
        return None

    left_part = line[:ts_match.start()].strip(" |,-\t")
    parts = [p.strip() for p in left_part.split("|")] if "|" in left_part else re.split(r"\s{2,}", left_part)

    item = parts[column_indices["item"]].strip() if len(parts) > column_indices["item"] else ""
    pool = parts[column_indices["pool"]].strip() if len(parts) > column_indices["pool"] else ""

    return {"item": item, "pool": pool, "time": timestamp}

def parse_ocr_text_to_entries(ocr_text: str, config: Dict, logger=None) -> List[Dict]:
    """
    将OCR文本解析为条目列表
    """
    if logger is None:
        logger = get_logger()
    if not ocr_text:
        return []

    column_indices = config["table_area"]["column_indices"]
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

    entries = []
    for line in lines:
        entry = parse_single_line(line, column_indices)
        if entry:
            entries.append(entry)

    logger.info(f"解析到 {len(entries)} 个条目")
    return entries