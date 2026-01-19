from pathlib import Path
from datetime import datetime
import json
from .logger_manager import get_logger

class ErrorEntryManager:
    def __init__(self, output_dir="data/errors", filename="errors.json", config_manager=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.output_dir / filename
        self.logger = get_logger(config_manager)

    def clear_errors(self):
        """
        清空错误记录文件
        """
        if self.file_path.exists():
            self.file_path.unlink()
            self.logger.info("已清空错误记录文件")

    def add_error_entry(self, entry, item_result, pool_result, image_path=None, position=None):
        """
        添加错误条目到待处理队列
        """
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
        """
        获取待处理的错误条目
        """
        if not self.file_path.exists():
            return []

        with open(self.file_path, 'r', encoding='utf-8') as f:
            errors = json.load(f)

        return [e for e in errors if e["correction_status"] == "pending"]
    

    def update_error_status(self, error_entry, new_status, corrected_data=None):
        """更新错误条目的状态，并将修正后的数据写回 JSON 数据文件"""

        with open(self.file_path, 'r', encoding='utf-8') as f:
            try:
                errors = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"无法解析错误文件 {self.file_path}: {e}")
                return

        updated = False
        for i, e in enumerate(errors):
            if (e["original"] == error_entry["original"] and 
                e["timestamp"] == error_entry["timestamp"]):
                errors[i]["correction_status"] = new_status
                if corrected_data:
                    errors[i]["corrected"] = corrected_data
                    errors[i]["corrected_at"] = datetime.now().isoformat()

                    # 写回 JSON 数据文件
                    json_path = e["context"].get("json_path")
                    if json_path and Path(json_path).exists():

                        try:
                            with open(json_path, 'r+', encoding='utf-8') as data_file:
                                try:
                                    data = json.load(data_file)
                                except json.JSONDecodeError as e:
                                    self.logger.error(f"无法解析 JSON 数据文件 {json_path}: {e}")
                                    continue

                                # 更新数据条目
                                for entry in data.get("data", []):
                                    if (entry["item"] == error_entry["original"]["item"] and
                                        entry["pool"] == error_entry["original"]["pool"] and
                                        entry["time"] == error_entry["original"]["time"] ):
                                        entry.update(corrected_data)
                                        # 将 is_valid 设置为 True
                                        entry['is_valid'] = True

                                # 写回文件
                                data_file.seek(0)
                                json.dump(data, data_file, ensure_ascii=False, indent=2)
                                data_file.truncate()
                        except Exception as e:
                            self.logger.error(f"无法更新 JSON 数据文件 {json_path}: {e}")

                updated = True
                break

        if updated:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(errors, f, ensure_ascii=False, indent=2)
