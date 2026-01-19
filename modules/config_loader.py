# modules/config_loader.py
import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""
    def __init__(self, config_dir: str = "data/config"):
        self.config_dir = Path(config_dir)
        self.game_configs = {}
        self.catalog_data = {}
        self.global_config = self._load_global_config()
        
    def _load_global_config(self) -> Dict[str, Any]:
        """加载全局配置"""
        global_config_path = self.config_dir / "global_config.json"
        default_config = {
            "ocr": {
                "default_language": "chi_sim+eng"
            },
            "logging": {
                "level": "INFO",
                "file_path": "logs/app.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        
        if global_config_path.exists():
            with open(global_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置，确保新加入的配置项存在
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
        else:
            config = default_config
            # 创建默认全局配置文件
            global_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(global_config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        return config
    
    def get_ocr_config(self) -> Dict[str, Any]:
        """获取OCR配置"""
        return self.global_config.get("ocr", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.global_config.get("logging", {})
    def load_game_config(self, game_id: str) -> Dict[str, Any]:
        """加载游戏处理配置"""
        config_path = self.config_dir / f"game_processing_config_{game_id}.json"
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        self.game_configs[game_id] = config
        return config
    
    def load_catalog_data(self, game_id: str) -> Dict[str, Any]:
        """加载游戏目录数据"""
        catalog_path = Path(f"data/catalog/game_catalog_{game_id}.json")
        if not catalog_path.exists():
            raise FileNotFoundError(f"目录文件不存在: {catalog_path}")
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
            
        self.catalog_data[game_id] = catalog
        return catalog
    
    def load_name_data(self, game_id: str) -> Dict[str, Any]:
        """加载游戏名称数据（用于OCR校正）"""
        name_path = Path(f"data/catalog/game_name_{game_id}.json")
        if not name_path.exists():
            raise FileNotFoundError(f"名称数据文件不存在: {name_path}")
        
        with open(name_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    def get_available_games_with_names(self):
        """获取可用游戏列表，格式为 [(game_id, game_name), ...]"""
        games = []
        for config_file in self.config_dir.glob("game_processing_config_*.json"):
            # 从文件名提取game_id
            game_id = config_file.stem.replace("game_processing_config_", "")
            # 从配置文件中读取游戏名称
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                game_id = config.get("game_info").get("game_id")
                game_name = config.get("game_info").get("game_name")
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"无法读取配置文件: {config_file}")
            games.append((game_id, game_name))
        return sorted(games, key=lambda x: x[1])  # 按游戏名称排序
