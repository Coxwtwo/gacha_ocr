# modules/ocr_image2json.py
import json
import re
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple
from PIL import Image
import pytesseract
from datetime import datetime
import numpy as np
from .config_loader import ConfigManager
from .logger_manager import get_logger
from .preprocess import preprocess_image




# 设置 Tesseract 路径（Windows 用户）
pytesseract.pytesseract.tesseract_cmd = r'tools\Tesseract-OCR\tesseract.exe'

# ===========================================================
# 常量定义
# ===========================================================
DATE_PATTERNS = [
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}:\d{2})',
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2})',
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
]

CHECK_KEYS = ['game_id', 'uid', 'timezone', 'lang']

MIN_OVERLAP_COUNT = 3  # 至少需要连续3条重叠才算作真正的重叠

"""错误条目管理器"""
class ErrorEntryManager:
    
    def __init__(self, output_dir="data/errors", filename="errors.json", config_manager=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.output_dir / filename
        self.logger = get_logger(config_manager)
    
    def clear_errors(self):
        """清空错误记录文件"""
        if self.file_path.exists():
            self.file_path.unlink()
            self.logger.info("已清空错误记录文件")
    
    def add_error_entry(self, entry, item_result, pool_result, image_path=None, position=None):
        """添加错误条目到待处理队列"""
        error_entry = {
            "original": {
                "item": entry["item"],
                "pool": entry["pool"],
                "time": entry["time"]
            },
            "errors": {
                "item_invalid": not item_result["is_valid"],
                "pool_invalid": not pool_result["is_valid"],
                "time_invalid": not entry["time"]
            },
            "context": {
                "image_path": image_path,
                "position": position
            },
            "correction_status": "pending",  # pending, corrected, ignored
            "timestamp": datetime.now().isoformat()
        }
        
        # 读取现有的错误条目，如果文件存在的话
        errors = []
        if self.file_path.exists():
            with open(self.file_path, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        
        errors.append(error_entry)
        
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"记录错误条目: {error_entry['original']}")
        return self.file_path
    
    def get_pending_errors(self):
        """获取待处理的错误条目"""
        if not self.file_path.exists():
            return []
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            errors = json.load(f)
        
        # 只返回待处理的错误
        return [e for e in errors if e["correction_status"] == "pending"]
    
    def update_error_status(self, error_entry, new_status, corrected_data=None):
        """更新错误条目的状态"""
        if not self.file_path.exists():
            return
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            errors = json.load(f)
        
        updated = False
        for i, e in enumerate(errors):
            if (e["original"] == error_entry["original"] and 
                e["timestamp"] == error_entry["timestamp"]):
                errors[i]["correction_status"] = new_status
                if corrected_data:
                    errors[i]["corrected"] = corrected_data
                    errors[i]["corrected_at"] = datetime.now().isoformat()
                updated = True
                break
        
        if updated:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(errors, f, ensure_ascii=False, indent=2)

# ===========================================================
# 图像处理函数
# ===========================================================
def crop_image_to_table(img: Image.Image, config: Dict) -> Image.Image:
    """裁剪图像到表格区域"""
    bounds = config["table_area"]["bounds"]
    w, h = img.size
    left = int(w * bounds["left_ratio"])
    right = int(w * bounds["right_ratio"])
    top = int(h * bounds["top_ratio"])
    bottom = int(h * bounds["bottom_ratio"])
    return img.crop((left, top, right, bottom))



# ===========================================================
# OCR识别函数
# ===========================================================
def perform_ocr(img: Image.Image, lang: str = "chi_sim", logger=None) -> Optional[str]:
    """执行OCR识别"""
    if logger is None:
        logger = get_logger()
    try:
        text = pytesseract.image_to_string(img, lang=lang)
        logger.info(f"OCR识别结果:\n{text}")
        return text.strip() if text else None
    except Exception as e:
        logger.error(f"[OCR] 识别失败: {e}")
        return None



# ===========================================================
# 文本解析函数
# ===========================================================
def extract_timestamp_from_line(line: str) -> Optional[str]:
    """从文本行中提取时间戳"""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def parse_single_line(line: str, column_indices: Dict) -> Optional[Dict]:
    """解析单行文本为条目"""
    timestamp = extract_timestamp_from_line(line)
    if not timestamp:
        return None
    
    # 查找时间戳位置
    ts_match = re.search(re.escape(timestamp), line)
    if not ts_match:
        return None
    
    # 提取时间戳前的部分
    left_part = line[:ts_match.start()].strip(" |,-\t")
    
    # 分割字段
    if "|" in left_part:
        parts = [p.strip() for p in left_part.split("|")]
    else:
        parts = re.split(r"\s{2,}", left_part)
    
    # 提取条目信息
    item = parts[column_indices["item"]].strip() if len(parts) > column_indices["item"] else ""
    pool = parts[column_indices["pool"]].strip() if len(parts) > column_indices["pool"] else ""
    
    return {"item": item, "pool": pool, "time": timestamp}


def parse_ocr_text_to_entries(ocr_text: str, config: Dict, logger=None) -> List[Dict]:
    """将OCR文本解析为条目列表"""
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


# ===========================================================

# ===========================================================
# 数据清洗和修正函数
# ===========================================================
def fix_timestamp_format(ts: str) -> Optional[str]:
    """修复时间戳格式为标准格式"""
    if not ts:
        return None
    
    # 标准化分隔符
    s = ts.strip().replace("T", " ").replace(".", "-").replace("/", "-")
    s = re.sub(r'[年月日]', '-', s)
    s = re.sub(r'[^0-9\- :]', '', s)
    
    # 定义日期格式
    DATE_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]
    
    # 尝试多种格式解析
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    # 尝试纯数字解析
    digits = re.sub(r'\D', '', s)
    if len(digits) >= 14:
        try:
            dt = datetime.strptime(digits[:14], "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    elif len(digits) >= 8:
        try:
            dt = datetime.strptime(digits[:8], "%Y%m%d")
            return dt.strftime("%Y-%m-%d 00:00:00")
        except ValueError:
            pass
    
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
    """计算编辑距离（莱文斯坦距离）"""
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


def correct_recognized_name(name: str, valid_names: set, max_distance_ratio: float = 0.5, logger=None) -> Dict[str, Union[str, bool]]:
    """纠正识别错误的名称"""
    if logger is None:
        logger = get_logger()
    if name in valid_names:
        return {"name": name, "is_valid": True}
    
    # 寻找最相似的名称
    if not valid_names:
        logger.warning(f"[警告] 无法纠正名称 '{name}'：有效名称列表为空")
        return {"name": name, "is_valid": False}
    
    best_match = min(valid_names, key=lambda x: calculate_edit_distance(name, x))
    distance = calculate_edit_distance(name, best_match)
    
    if distance <= len(name) * max_distance_ratio:
        return {"name": best_match, "is_valid": True}
    
    logger.warning(f"[警告] 无法纠正名称: {name}")
    return {"name": name, "is_valid": False}

def clean_and_correct_entry(entry: Dict, valid_items: set, valid_pools: set, 
                           clean_config: Dict, error_manager: ErrorEntryManager = None, 
                           image_path: str = None, position: int = None, logger=None) -> Optional[Dict]:
    """清洗和修正单个条目"""
    if logger is None:
        logger = get_logger()
    # 清理名称
    if clean_config["enable_clean_name"]:
        entry["item"] = clean_name_string(entry["item"], 
                                         clean_config["prefix_patterns"], 
                                         clean_config["suffix_patterns"])
        entry["pool"] = clean_name_string(entry["pool"], 
                                         clean_config["prefix_patterns"], 
                                         clean_config["suffix_patterns"])
    
    # 纠正名称
    item_result = correct_recognized_name(entry["item"], valid_items, logger=logger)
    pool_result = correct_recognized_name(entry["pool"], valid_pools, logger=logger)
    
    # 检查是否有错误需要记录
    has_errors = not item_result["is_valid"] or not pool_result["is_valid"]
    
    # 应用纠正确实的结果
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



# ===========================================================
# 文件合并和兼容性检查
# ===========================================================
def check_info_compatibility(info1: Dict, info2: Dict, logger=None) -> bool:
    """检查两个文件的info字段是否兼容"""
    if logger is None:
        logger = get_logger()
    for key in CHECK_KEYS:
        if info1.get(key) != info2.get(key):
            logger.warning(f"[警告] 文件的 info 字段 {key} 不一致：{info1.get(key)} vs {info2.get(key)}")
            return False
    return True


def find_compatible_history_files(new_file_path: Path, existing_files: List[Path], logger=None) -> List[Path]:
    """查找与当前文件兼容的历史文件"""
    if logger is None:
        logger = get_logger()
    compatible_files = []
    
    try:
        new_data = load_json_file(new_file_path)
        new_info = new_data['info']
        
        for file_path in existing_files:
            try:
                old_data = load_json_file(file_path)
                if check_info_compatibility(new_info, old_data['info'], logger):
                    compatible_files.append(file_path)
            except Exception as e:
                logger.error(f"读取文件 {file_path} 失败: {e}")
                continue
                
    except Exception as e:
        logger.error(f"读取新文件 {new_file_path} 失败: {e}")
    
    return compatible_files


def get_latest_history_file(files: List[Path], logger=None) -> Tuple[Optional[Path], int]:
    """获取最新的历史文件"""
    if logger is None:
        logger = get_logger()
    if not files:
        return None, 0
    
    latest_file = None
    latest_timestamp = 0
    
    for file_path in files:
        try:
            data = load_json_file(file_path)
            timestamp = data['info']['export_timestamp']
            
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
                latest_file = file_path
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {e}")
            continue
    
    return latest_file, latest_timestamp


def find_overlapping_entries(data1: List[Dict], data2: List[Dict]) -> Tuple[int, int, int, int]:
    """查找两个数据集中的重叠条目"""
    
    for i in range(len(data1)):
        for j in range(len(data2)):
            if (data1[i]['time'] == data2[j]['time'] and 
                data1[i]['pool'] == data2[j]['pool'] and 
                data1[i]['item'] == data2[j]['item']):
                
                # 检查连续重叠
                k = 0
                while (i + k < len(data1) and j + k < len(data2) and 
                       data1[i + k]['time'] == data2[j + k]['time'] and 
                       data1[i + k]['pool'] == data2[j + k]['pool'] and 
                       data1[i + k]['item'] == data2[j + k]['item']):
                    k += 1
                
                if k >= MIN_OVERLAP_COUNT:
                    return i, i + k, j, j + k
    
    return -1, -1, -1, -1


def merge_json_files(file1: str, file2: str, output_file: str, logger=None) -> None:
    """合并两个JSON文件"""
    if logger is None:
        logger = get_logger()
    # 加载文件
    data1 = load_json_file(file1)
    data2 = load_json_file(file2)
    
    # 检查兼容性
    if not check_info_compatibility(data1['info'], data2['info'], logger):
        raise ValueError("两个文件的 info 字段不一致，无法合并")
    
    # 使用较晚导出的info
    info = data2['info'] if data2['info']['export_timestamp'] > data1['info']['export_timestamp'] else data1['info']
    
    # 查找重叠
    start1, end1, start2, end2 = find_overlapping_entries(data1['data'], data2['data'])
    if start1 == -1:
        raise ValueError(f"未找到连续 {MIN_OVERLAP_COUNT} 条以上的重叠条目")
    
    # 分割数据
    before1 = data1['data'][:start1]
    overlap = data1['data'][start1:end1]  # 使用第一个数据集的重叠部分
    after1 = data1['data'][end1:]
    
    before2 = data2['data'][:start2]
    after2 = data2['data'][end2:]
    
    # 选择较长的前后部分
    before_merged = before1 if len(before1) > len(before2) else before2
    after_merged = after1 if len(after1) > len(after2) else after2
    
    # 合并数据
    merged_data = before_merged + overlap + after_merged
    
    # 保存合并结果
    merged_json = {"info": info, "data": merged_data}
    save_json_file(merged_json, output_file, logger)


def load_json_file(file_path: str, logger=None) -> dict:
    """加载JSON文件"""
    if logger is None:
        logger = get_logger()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件 {file_path} 失败: {e}")
        raise


def save_json_file(data: dict, file_path: str, logger=None) -> None:
    """保存JSON文件"""
    if logger is None:
        logger = get_logger()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存JSON文件 {file_path} 失败: {e}")
        raise


# ===========================================================
# 主处理流程函数
# ===========================================================
def create_output_directory(output_dir: str = "data/history", logger=None) -> Path:
    """创建输出目录"""
    if logger is None:
        logger = get_logger()
    output_folder = Path(output_dir)
    output_folder.mkdir(exist_ok=True)
    return output_folder


def get_image_paths(image_source: Union[str, List[str]], logger=None) -> List[str]:
    """获取所有图像文件路径"""
    if logger is None:
        logger = get_logger()
    if isinstance(image_source, str) and Path(image_source).is_dir():
        return [str(p) for p in Path(image_source).rglob("*.png")]
    elif isinstance(image_source, str):
        return [image_source]
    else:
        return list(image_source)


def process_single_image(game_id: str, image_path: str, config: Dict, clean_config: Dict, 
                        valid_items: set, valid_pools: set, error_manager: ErrorEntryManager = None, logger=None) -> List[Dict]:
    """处理单张图像"""
    if logger is None:
        logger = get_logger()
    logger.info(f"处理图像: {Path(image_path).name}")
    
    # 图像处理
    img = Image.open(image_path)
    cropped_img = crop_image_to_table(img, config)
    processed_img = preprocess_image(cropped_img, game_id)
    
    # OCR识别
    ocr_text = perform_ocr(processed_img, logger=logger)
    if not ocr_text:
        logger.warning(f"[警告] 图像 {Path(image_path).name} OCR识别失败")
        return []
    
    # 解析文本
    raw_entries = parse_ocr_text_to_entries(ocr_text, config, logger)
    
    # 清洗和修正
    cleaned_entries = []
    for i, entry in enumerate(raw_entries):
        cleaned_entry = clean_and_correct_entry(
            entry, 
            valid_items, 
            valid_pools, 
            clean_config, 
            error_manager, 
            image_path, 
            i,
            logger
        )
        if cleaned_entry:
            cleaned_entries.append(cleaned_entry)
    
    logger.info(f"从 {Path(image_path).name} 提取到 {len(cleaned_entries)} 个有效条目")
    return cleaned_entries


def create_export_data(all_entries: List[Dict], game_id: str, game_name: str, 
                      uid: str, timezone: int, lang: str, logger=None) -> Dict:
    """创建导出数据结构"""
    if logger is None:
        logger = get_logger()
    # 按时间排序（从新到旧）
    sorted_entries = sorted(all_entries, key=lambda x: x["time"], reverse=True)
    
    # 当前时间
    export_timestamp = int(datetime.now().timestamp())
    
    return {
        "info": {
            "game_id": game_id,
            "game_name": game_name,
            "export_timestamp": export_timestamp,
            "export_app": "ocr_export",
            "export_app_version": "v0.0.1",
            "export_time": datetime.fromtimestamp(export_timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "uid": uid,
            "timezone": timezone,
            "lang": lang,
            "total_entries": len(sorted_entries),
        },
        "data": sorted_entries,
    }


def save_and_merge_file(export_data: Dict, output_folder: Path, game_id: str, logger=None) -> Path:
    """保存文件并尝试与历史文件合并"""
    if logger is None:
        logger = get_logger()
    # 生成文件名
    export_time_str = datetime.fromtimestamp(export_data["info"]["export_timestamp"]).strftime("%Y%m%d_%H%M%S")
    output_file = output_folder / f"{game_id}_{export_time_str}.json"
    
    # 保存新文件
    save_json_file(export_data, output_file, logger)
    logger.info(f"已创建新文件: {output_file}")
    
    # 查找历史文件
    existing_files = list(output_folder.glob(f"{game_id}_*.json"))
    existing_files = [f for f in existing_files if f != output_file]
    
    if not existing_files:
        logger.info("未找到历史文件，无需合并")
        return output_file
    
    logger.info(f"找到 {len(existing_files)} 个历史文件")
    
    # 查找兼容文件
    compatible_files = find_compatible_history_files(output_file, existing_files, logger)
    logger.info(f"其中 {len(compatible_files)} 个文件与当前账号兼容")
    
    if not compatible_files:
        logger.info("未找到兼容的历史文件")
        return output_file
    
    # 获取最新兼容文件
    latest_file, latest_timestamp = get_latest_history_file(compatible_files, logger)
    if not latest_file:
        logger.info("未找到有效的兼容文件")
        return output_file
    
    logger.info(f"找到最新兼容文件: {latest_file.name} (导出时间: {datetime.fromtimestamp(latest_timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 尝试合并
    try:
        logger.info(f"尝试合并: {latest_file.name} → {output_file.name}")
        merge_json_files(str(latest_file), str(output_file), str(output_file), logger)
        logger.info(f"合并完成，结果已保存到 {output_file}")
        
        # 删除旧文件
        try:
            latest_file.unlink()
            logger.info(f"已删除旧文件: {latest_file.name}")
        except Exception as e:
            logger.warning(f"[警告] 无法删除旧文件 {latest_file.name}: {e}")
            
    except ValueError as e:
        logger.error(f"合并失败: {e}")
        logger.info(f"保留两个独立文件")
    
    return output_file


def run_pipeline(
    image_source: Union[str, List[str]],
    uid: str = "1234567890",
    timezone: int = 8,
    lang: str = "zh-cn",
    config_manager = None,  # 参数：配置管理器
    game_id: str = "ark",   # 参数：游戏ID
    output_dir: str = "data/history",  # 参数：json输出目录
    enable_error_handling: bool = True  # 新增参数：是否启用错误处理
) -> Optional[Path]:
    """
    主处理流程
    
    Args:
        image_source: 图像路径或目录
        uid: 用户ID
        timezone: 时区
        lang: 语言
        config_manager: 配置管理器
        game_id: 游戏ID
        output_dir: 输出目录
        enable_error_handling: 是否启用错误处理功能
        
    Returns:
        最终保存的文件路径，如果失败则返回None
    """
    logger = get_logger(config_manager)
    logger.info("=" * 60)
    logger.info("开始处理抽卡记录图像")
    logger.info("=" * 60)
    
    try:
        # 加载配置和数据
        config = config_manager.load_game_config(game_id)
        game_data = config_manager.load_name_data(game_id)
        
        # 获取配置信息
        game_id = config["game_info"]["game_id"]
        game_name = config["game_info"]["game_name"]
        
        # 有效名称集合
        valid_items = set(game_data["character"])
        valid_pools = set(game_data["pool"])
        
        # 清理配置
        clean_config = {
            "enable_clean_name": config["text_processing"]["enable_clean_name"],
            "prefix_patterns": config["text_processing"]["patterns"]["prefix_patterns"],
            "suffix_patterns": config["text_processing"]["patterns"]["suffix_patterns"]
        }
        
        # 创建错误管理器
        error_manager = None
        if enable_error_handling:
            error_manager = ErrorEntryManager(config_manager=config_manager)
            # 清空之前的错误记录
            error_manager.clear_errors()
        
        # 创建输出目录
        output_folder = create_output_directory(output_dir, logger)
        
        # 获取图像路径
        image_paths = get_image_paths(image_source, logger)
        if not image_paths:
            logger.error("未找到任何图像文件")
            return None
        
        logger.info(f"找到 {len(image_paths)} 张图像")
        
        # 处理所有图像
        all_entries = []
        for img_path in image_paths:
            entries = process_single_image(game_id, img_path, config, clean_config, valid_items, valid_pools, error_manager, logger)
            all_entries.extend(entries)
        
        if not all_entries:
            logger.error("未提取到任何有效记录")
            return None
        
        logger.info(f"\n成功提取 {len(all_entries)} 条抽卡记录")
        
        # 创建导出数据
        export_data = create_export_data(all_entries, game_id, game_name, uid, timezone, lang, logger)
        
        # 保存并合并文件
        final_file = save_and_merge_file(export_data, output_folder, game_id, logger)
        
        # 输出错误统计
        if error_manager:
            pending_errors = error_manager.get_pending_errors()
            logger.info(f"发现 {len(pending_errors)} 个待人工修正的错误条目")
            logger.info("错误条目已保存，可在错误修正标签页中处理")
        
        logger.info("\n" + "=" * 60)
        logger.info("处理完成")
        logger.info("=" * 60)
        
        return final_file
        
    except Exception as e:
        logger.error(f"[错误] 处理过程中发生异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# 更新 OcrImageProcessor 类
class OcrImageProcessor:
    """OCR图像处理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = get_logger(config_manager)
    
    def process_images(self, image_source: Union[str, List[str]], game_id: str, uid: str, 
                      timezone: int = 8, lang: str = "zh-cn", output_dir: str = "data/history",
                      enable_error_handling: bool = True) -> Optional[Path]:
        """处理图像并生成抽卡记录"""
        return run_pipeline(
            image_source=image_source,
            uid=uid,
            timezone=timezone,
            lang=lang,
            config_manager=self.config_manager,
            game_id=game_id,
            output_dir=output_dir,
            enable_error_handling=enable_error_handling
        )