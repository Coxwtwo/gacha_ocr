from typing import List, Dict, Optional
import re
from .logger_manager import get_logger

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