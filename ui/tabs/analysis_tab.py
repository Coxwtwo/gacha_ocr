# ui/tabs/analysis_tab.py
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QPushButton,
    QFileDialog, 
    QTextEdit, 
    QComboBox,
    QHBoxLayout, 
    QLabel,
    QTabWidget,
    QScrollArea,
    QSlider
)
from PySide6.QtGui import QPixmap, QPainter, QTransform
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel as ImageLabel, QGraphicsView, QGraphicsScene
from modules.history_analyzer import GachaAnalyzer
import io
import sys
from contextlib import redirect_stderr, redirect_stdout


class AnalysisTab(QWidget):
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.analyzer = GachaAnalyzer(config_manager) if config_manager else None
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # 游戏选择下拉框
        self.game_combo = QComboBox()

        # 默认历史文件目录
        self.default_history_dir = "data/history"

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧：分析报告和可视化图表
        left = QVBoxLayout()

        self.report_area = QTextEdit()
        self.report_area.setReadOnly(True)
        
        # 创建图形视图组件
        self.graphics_view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # 图像项
        self.pixmap_item = None
        
        # 创建缩放滑块
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(5)  # 5%
        self.zoom_slider.setMaximum(300)  # 300%
        self.zoom_slider.setValue(100)  # 100%
        self.zoom_slider.valueChanged.connect(self.on_slider_changed)
        
        # 缩放控制按钮布局
        zoom_layout = QHBoxLayout()
        zoom_out_btn = QPushButton("缩小 (-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        
        zoom_in_btn = QPushButton("放大 (+)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        
        reset_zoom_btn = QPushButton("重置")
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(zoom_in_btn)
        zoom_layout.addWidget(reset_zoom_btn)
        
        # 创建包含图形视图和缩放控件的容器
        visualization_container = QVBoxLayout()
        visualization_container.addWidget(self.graphics_view)
        visualization_container.addLayout(zoom_layout)
        
        visualization_widget = QWidget()
        visualization_widget.setLayout(visualization_container)
        
        tabs = QTabWidget()
        tabs.addTab(self.report_area, "分析报告")
        tabs.addTab(visualization_widget, "可视化图表")

        left.addWidget(tabs)

        # 右侧：控制面板
        right = QVBoxLayout()

        # 游戏选择布局
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("选择游戏:"))
        game_layout.addWidget(self.game_combo)
        right.addLayout(game_layout)

        btn_load = QPushButton("加载历史记录 JSON")
        btn_load.clicked.connect(self.load_json)

        btn_analyze = QPushButton("开始分析")
        btn_analyze.clicked.connect(self.run_analysis)

        right.addWidget(btn_load)
        right.addWidget(btn_analyze)
        right.addWidget(self.log_output)

        # 设置左右布局比例
        main_layout.addLayout(left, stretch=3)
        main_layout.addLayout(right, stretch=1)

        # 初始化游戏列表
        self._init_games()

    def _init_games(self):
        """初始化游戏列表"""
        if self.config_manager:
            games = self.config_manager.get_available_games()
            self.game_combo.addItems(games)
            if games:
                self.current_game = games[0]
        else:
            self.log("配置管理器未初始化")

    def load_json(self):
        # 使用默认历史目录作为起始路径
        start_dir = self.default_history_dir
        if not Path(start_dir).exists():
            start_dir = ""  # 如果默认目录不存在，使用当前工作目录

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 JSON 文件",
            start_dir,
            "JSON (*.json)"
        )
        if path:
            self.json_path = path
            self.log("加载历史文件：" + path)

    def run_analysis(self):
        if not hasattr(self, 'current_game'):
            self.log("请先选择游戏")
            return

        if not hasattr(self, 'json_path'):
            self.log("请先加载JSON文件")
            return

        # 使用GachaAnalyzer进行分析
        if self.analyzer:
            try:
                # 重定向输出以捕获日志内容
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                captured_output = io.StringIO()
                
                try:
                    sys.stdout = captured_output
                    sys.stderr = captured_output
                    
                    result = self.analyzer.analyze(self.json_path, self.current_game)
                    
                    # 恢复标准输出
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # 获取捕获的输出
                    output_text = captured_output.getvalue()
                    
                    if result['success']:
                        self.log("分析完成！")
                        self.log(f"总共分析了 {len(result['pool_stats'])} 个卡池")

                        # 显示分析报告（使用捕获的日志输出作为报告内容）
                        self.report_area.setPlainText(output_text)

                        # 显示可视化图表 - 通过QGraphicsView显示
                        self.display_visualization_image()

                    else:
                        self.log(f"分析失败: {result['error']}")
                        # 也显示捕获的错误输出
                        if output_text:
                            self.report_area.setPlainText(output_text)
                        
                finally:
                    # 确保始终恢复标准输出
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

            except Exception as e:
                self.log(f"分析过程中出现错误: {e}")
        else:
            self.log("分析器未初始化")

    def display_visualization_image(self):
        """在图形视图中显示可视化图像"""
        # 尝试从JSON中提取UID以确定正确的图像文件名
        uid = self.extract_uid_from_json()
        
        # 尝试多个可能的文件名
        possible_filenames = [
            f'gacha_analysis_{uid}.png' if uid else None,
            'gacha_analysis.png',
            f'gacha_analysis_{uid}.jpg' if uid else None,
            'gacha_analysis.jpg'
        ]
        
        # 过滤掉None值
        possible_filenames = [f for f in possible_filenames if f is not None]
        
        pixmap = None
        found_file = None
        
        for filename in possible_filenames:
            temp_pixmap = QPixmap(filename)
            if not temp_pixmap.isNull():
                pixmap = temp_pixmap
                found_file = filename
                break
        
        if pixmap and not pixmap.isNull():
            # 清除场景中的现有项目
            self.scene.clear()
            
            # 添加新图片
            self.pixmap_item = self.scene.addPixmap(pixmap)
            
            # 重置缩放
            self.reset_zoom()
            
            # 输出找到的文件名
            self.log(f"成功加载可视化图表: {found_file}")
        else:
            # 如果找不到图片，显示提示文本
            self.scene.clear()
            text_item = self.scene.addText("未找到可视化图表文件")
            self.log("未找到可视化图表文件")

    def extract_uid_from_json(self):
        """从JSON文件中提取UID"""
        if hasattr(self, 'json_path') and self.json_path:
            try:
                import json
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('info', {}).get('uid', '')
            except Exception as e:
                self.log(f"无法从JSON文件中提取UID: {e}")
                return ''
        return ''

    def zoom_in(self):
        """放大图片"""
        current_value = self.zoom_slider.value()
        new_value = min(current_value + 10, self.zoom_slider.maximum())
        self.zoom_slider.setValue(new_value)

    def zoom_out(self):
        """缩小图片"""
        current_value = self.zoom_slider.value()
        new_value = max(current_value - 10, self.zoom_slider.minimum())
        self.zoom_slider.setValue(new_value)

    def reset_zoom(self):
        """重置缩放"""
        self.zoom_slider.setValue(100)

    def on_slider_changed(self, value):
        """滑块值改变时的处理"""
        # 计算缩放比例
        scale_factor = value / 100.0
        
        # 应用变换
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        self.graphics_view.setTransform(transform)

    def log(self, text):
        self.log_output.append(text)