# ui/tabs/ocr_test_tab.py
from pathlib import Path
import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout,
    QPushButton, 
    QFileDialog, 
    QTextEdit, 
    QComboBox, 
    QLabel,
    QDoubleSpinBox
)
from PySide6.QtGui import QPainter, QPen, QColor

from ui.widgets.image_viewer import ImageViewer


class OcrTestTab(QWidget):
    def __init__(self, config_manager=None, main_window=None):
        super().__init__()
        self.config_manager = config_manager
        self.main_window = main_window  # 保存主窗口引用
        self.image_viewer = ImageViewer()  # 使用修改后的ImageViewer
        
        # 连接区域变化信号
        self.image_viewer.region_changed.connect(self._on_region_changed_from_viewer)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # 游戏选择下拉框
        self.game_combo = QComboBox()
        self.game_combo.currentTextChanged.connect(self.on_game_changed)

        # 默认图片目录
        self.default_image_dir = "data/input_images"

        # 区域编辑控件
        self.left_spinbox = QDoubleSpinBox()
        self.left_spinbox.setRange(0.0, 1.0)
        self.left_spinbox.setSingleStep(0.01)
        self.left_spinbox.setValue(0.2)
        self.left_spinbox.valueChanged.connect(self._on_region_changed_from_spinbox)

        self.top_spinbox = QDoubleSpinBox()
        self.top_spinbox.setRange(0.0, 1.0)
        self.top_spinbox.setSingleStep(0.01)
        self.top_spinbox.setValue(0.2)
        self.top_spinbox.valueChanged.connect(self._on_region_changed_from_spinbox)

        self.right_spinbox = QDoubleSpinBox()
        self.right_spinbox.setRange(0.0, 1.0)
        self.right_spinbox.setSingleStep(0.01)
        self.right_spinbox.setValue(0.8)
        self.right_spinbox.valueChanged.connect(self._on_region_changed_from_spinbox)

        self.bottom_spinbox = QDoubleSpinBox()
        self.bottom_spinbox.setRange(0.0, 1.0)
        self.bottom_spinbox.setSingleStep(0.01)
        self.bottom_spinbox.setValue(0.8)
        self.bottom_spinbox.valueChanged.connect(self._on_region_changed_from_spinbox)

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧：图片预览和区域编辑
        left = QVBoxLayout()
        
        # 图片预览
        left.addWidget(self.image_viewer)
        
        # 区域编辑面板
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("左:"))
        region_layout.addWidget(self.left_spinbox)
        region_layout.addWidget(QLabel("上:"))
        region_layout.addWidget(self.top_spinbox)
        region_layout.addWidget(QLabel("右:"))
        region_layout.addWidget(self.right_spinbox)
        region_layout.addWidget(QLabel("下:"))
        region_layout.addWidget(self.bottom_spinbox)
        
        left.addLayout(region_layout)

        # 右侧：控制
        right = QVBoxLayout()
        
        # 添加游戏选择
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("选择游戏:"))
        game_layout.addWidget(self.game_combo)
        right.addLayout(game_layout)

        btn_load = QPushButton("加载图片")
        btn_load.clicked.connect(self.load_image)

        btn_set_region = QPushButton("按数值设定区域")
        btn_set_region.clicked.connect(self.set_region)

        btn_save_region = QPushButton("保存区域设置到配置")
        btn_save_region.clicked.connect(self.save_region_settings_to_config)

        btn_ocr = QPushButton("执行 OCR")
        btn_ocr.clicked.connect(self.run_ocr)

        right.addWidget(btn_load)
        right.addWidget(btn_set_region)
        right.addWidget(btn_save_region)
        right.addWidget(btn_ocr)
        right.addWidget(self.log_output)

        main_layout.addLayout(left, stretch=3)
        main_layout.addLayout(right, stretch=1)
        
        # 初始化游戏列表
        self._init_games()

    def _init_games(self):
        """初始化游戏列表"""
        if self.config_manager:
            # 获取游戏列表，返回格式为 [(game_id, game_name), ...]
            games = self.config_manager.get_available_games_with_names()
            
            for game_id, game_name in games:
                self.game_combo.addItem(game_name, game_id)  # 显示名称，存储ID
                
            if games:
                self.current_game_id = games[0][0]  # 设置第一个游戏的ID
                self.current_game_name = games[0][1]  # 设置第一个游戏的名称
        else:
            self.log("配置管理器未初始化")

    def on_game_changed(self, game_name):
        """当游戏改变时的处理"""
        # 获取选中项的数据（存储的游戏ID）
        current_index = self.game_combo.currentIndex()
        if current_index >= 0:
            self.current_game_id = self.game_combo.itemData(current_index)
            self.current_game_name = game_name
            
            self.log(f"切换到游戏: {game_name}")
            
            # 加载该游戏的配置中的区域设置
            self.load_region_from_config()

    def load_region_from_config(self):
        """从游戏配置文件中加载区域设置"""
        if not hasattr(self, 'current_game_id'):
            return

        try:
            # 使用游戏ID加载配置
            config = self.config_manager.load_game_config(self.current_game_id)
            
            # 获取区域边界
            bounds = config["table_area"]["bounds"]
            left = bounds["left_ratio"]
            top = bounds["top_ratio"]
            right = bounds["right_ratio"]
            bottom = bounds["bottom_ratio"]
            
            # 更新SpinBox和图像查看器
            self.left_spinbox.setValue(left)
            self.top_spinbox.setValue(top)
            self.right_spinbox.setValue(right)
            self.bottom_spinbox.setValue(bottom)
            
            self.image_viewer.set_region(left, top, right, bottom)
            
            self.log(f"已从配置文件加载区域设置: 左={left}, 上={top}, 右={right}, 下={bottom}")
        except Exception as e:
            self.log(f"加载区域设置失败: {e}")

    def _on_region_changed_from_spinbox(self):
        """当SpinBox区域调整时的处理（来自SpinBox）"""
        left = self.left_spinbox.value()
        top = self.top_spinbox.value()
        right = self.right_spinbox.value()
        bottom = self.bottom_spinbox.value()
        
        # 更新图像查看器中的区域
        self.image_viewer.set_region(left, top, right, bottom)

    def _on_region_changed_from_viewer(self, left, top, right, bottom):
        """当区域调整时的处理（来自图像查看器）"""
        # 阻止信号循环 - 临时断开SpinBox的信号
        self.left_spinbox.blockSignals(True)
        self.top_spinbox.blockSignals(True)
        self.right_spinbox.blockSignals(True)
        self.bottom_spinbox.blockSignals(True)
        
        # 更新SpinBox的值
        self.left_spinbox.setValue(left)
        self.top_spinbox.setValue(top)
        self.right_spinbox.setValue(right)
        self.bottom_spinbox.setValue(bottom)
        
        # 重新连接SpinBox的信号
        self.left_spinbox.blockSignals(False)
        self.top_spinbox.blockSignals(False)
        self.right_spinbox.blockSignals(False)
        self.bottom_spinbox.blockSignals(False)

    def set_region(self):
        """设置当前图片的区域"""
        if not hasattr(self, 'current_image_path'):
            self.log("请先加载图片")
            return
        
        # 从SpinBox获取区域值
        left = self.left_spinbox.value()
        top = self.top_spinbox.value()
        right = self.right_spinbox.value()
        bottom = self.bottom_spinbox.value()
        
        # 更新图像查看器中的区域
        self.image_viewer.set_region(left, top, right, bottom)
        self.log(f"区域已设置: 左={left}, 上={top}, 右={right}, 下={bottom}")

    def save_region_settings_to_config(self):
        """将区域设置保存到游戏配置文件"""
        if not hasattr(self, 'current_game_id'):
            self.log("请先选择游戏")
            return

        try:
            # 获取当前配置
            config_path = self.config_manager.config_dir / f"game_processing_config_{self.current_game_id}.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新区域参数
            config["table_area"]["bounds"]["left_ratio"] = self.left_spinbox.value()
            config["table_area"]["bounds"]["top_ratio"] = self.top_spinbox.value()
            config["table_area"]["bounds"]["right_ratio"] = self.right_spinbox.value()
            config["table_area"]["bounds"]["bottom_ratio"] = self.bottom_spinbox.value()
            
            # 保存回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.log(f"区域设置已保存到配置文件: {config_path}")
            self.log(f"新的区域设置: 左={self.left_spinbox.value():.3f}, "
                    f"上={self.top_spinbox.value():.3f}, "
                    f"右={self.right_spinbox.value():.3f}, "
                    f"下={self.bottom_spinbox.value():.3f}")
        except Exception as e:
            self.log(f"保存区域设置到配置文件失败: {e}")

    def load_image(self):
        # 使用默认图片目录作为起始路径
        start_dir = self.default_image_dir
        if not Path(start_dir).exists():
            start_dir = ""  # 如果默认目录不存在，使用当前工作目录
            
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            start_dir,
            "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return

        self.image_viewer.load_image(path)
        self.log("加载图片：" + path)
        # 存储图片路径，以便在OCR时使用
        self.current_image_path = path
        # 更新主窗口共享图片路径
        if self.main_window:
            # 同时更新共享的目录
            self.main_window.shared_image_dir = str(Path(path).parent)

    def run_ocr(self):
        if not hasattr(self, 'current_game_id'):
            self.log("请先选择游戏")
            return
            
        if not hasattr(self, 'current_image_path'):
            self.log("请先加载图片")
            return
            
        try:
            # 从SpinBox获取区域值
            left = self.left_spinbox.value()
            top = self.top_spinbox.value()
            right = self.right_spinbox.value()
            bottom = self.bottom_spinbox.value()
            
            # 获取当前配置
            config = self.config_manager.load_game_config(self.current_game_id) if self.config_manager else {}
            
            # 创建带有自定义区域的配置
            custom_bounds = {
                "left_ratio": left,
                "top_ratio": top,
                "right_ratio": right,
                "bottom_ratio": bottom
            }
            
            # 从模块导入函数并使用自定义区域
            from modules.ocr_test import test_ocr_with_config
            result = test_ocr_with_config(
                self.current_image_path, 
                config, 
                custom_bounds=custom_bounds
            )
            self.log(f"执行 OCR (游戏: {self.current_game_name})")
            self.log(f"识别结果：{result}")
        except Exception as e:
            self.log(f"OCR处理过程中出现错误: {e}")

    def log(self, message):
        """向日志输出添加消息"""
        from modules.logger_manager import get_logger
        logger = get_logger(self.config_manager)
        logger.info(message)
        self.log_output.append(message)