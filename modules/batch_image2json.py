# modules/batch_image2json.py
import json
import re
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple
from PIL import Image
from .perform_ocr import perform_ocr
from datetime import datetime
import numpy as np
from .config_loader import ConfigManager
from .logger_manager import get_logger
from .preprocess import preprocess_image, crop_image_to_table
from .data_processor import fix_timestamp_format, clean_and_correct_entry, parse_ocr_text_to_entries
from .json_file_handler import load_json_file, save_json_file
from .ocr_error_manager import ErrorEntryManager

CHECK_KEYS = ['game_id', 'uid', 'timezone', 'lang']

MIN_OVERLAP_COUNT = 3  # 至少需要连续3条重叠才算作真正的重叠

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
        
        # 输出错误统计并追加 final_file 路径到 error.json
        if error_manager:
            pending_errors = error_manager.get_pending_errors()
            logger.info(f"发现 {len(pending_errors)} 个待人工修正的错误条目")

            # 追加 final_file 路径到每个错误条目
            if len(pending_errors) > 0:
                with open(error_manager.file_path, 'r+', encoding='utf-8') as f:
                    errors = json.load(f)
                    for error in errors:
                        error['context']['json_path'] = str(final_file)
                    f.seek(0)
                    json.dump(errors, f, ensure_ascii=False, indent=2)
                    f.truncate()

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