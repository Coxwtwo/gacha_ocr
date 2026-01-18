import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .logger_manager import get_logger

def load_json_file(file_path: str, logger=None) -> dict:
    """
    加载JSON文件
    """
    if logger is None:
        logger = get_logger()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件 {file_path} 失败: {e}")
        raise

def save_json_file(data: dict, file_path: str, logger=None) -> None:
    """
    保存JSON文件
    """
    if logger is None:
        logger = get_logger()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存JSON文件 {file_path} 失败: {e}")
        raise