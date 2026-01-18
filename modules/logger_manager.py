import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LoggerManager:
    """全局日志管理器"""
    _instance: Optional['LoggerManager'] = None
    _initialized = False

    def __new__(cls) -> 'LoggerManager':
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.logger: Optional[logging.Logger] = None
        self._initialized = True

    def setup_logger(self, config_manager) -> logging.Logger:
        """根据配置初始化日志系统"""
        if self.logger is not None:
            return self.logger

        log_config = config_manager.get_logging_config()
        
        # 获取日志级别
        level_str = log_config.get("level", "INFO")
        level = getattr(logging, level_str.upper(), logging.INFO)
        
        # 获取日志文件路径
        log_file_path = Path(log_config.get("file_path", "logs/app.log"))
        
        # 创建日志目录
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取日志大小限制和备份数量
        max_bytes = self._parse_size(log_config.get("max_size", "10MB"))
        backup_count = log_config.get("backup_count", 5)
        
        # 创建logger实例
        self.logger = logging.getLogger("gacha_ocr_app")
        self.logger.setLevel(level)
        
        # 移除已有的处理器，防止重复
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 创建RotatingFileHandler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        return self.logger

    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串，例如 "10MB" -> 10485760"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # 默认认为是字节
            return int(size_str)

    def get_logger(self) -> Optional[logging.Logger]:
        """获取logger实例"""
        return self.logger


# 全局日志实例
logger_manager = LoggerManager()


def get_logger(config_manager=None) -> logging.Logger:
    """获取全局日志实例"""
    if config_manager:
        return logger_manager.setup_logger(config_manager)
    else:
        return logger_manager.get_logger()