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


class AnalysisTab(QWidget):
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.analyzer = GachaAnalyzer(config_manager) if config_manager else None
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # 游戏选择下拉框
        self.game_combo = QComboBox()
        self.game_combo.currentTextChanged.connect(self.on_game_changed)

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
        if not hasattr(self, 'current_game_id'):
            self.log("请先选择游戏")
            return

        if not hasattr(self, 'json_path'):
            self.log("请先加载JSON文件")
            return

        # 使用GachaAnalyzer进行分析
        if self.analyzer:
            try:
                result = self.analyzer.analyze(self.json_path, self.current_game_id)

                if result['success']:
                    self.log("分析完成！")
                    self.log(f"总共分析了 {len(result['pool_stats'])} 个卡池")

                    # 显示分析报告
                    self.report_area.setPlainText(result['report'])

                    # 显示可视化图表
                    self.display_visualization_images(result['visualizations'])
                else:
                    self.log(f"分析失败: {result.get('error', '未知错误')}")

            except Exception as e:
                self.log(f"分析过程中出现错误: {e}")
        else:
            self.log("分析器未初始化")

    def display_visualization_images(self, visualizations):
        """在图形视图中显示所有可视化图像"""
        self.scene.clear()

        # 加载并显示每张图片
        for image_path in visualizations.values():
            pixmap = QPixmap(image_path)

            if not pixmap.isNull():
                self.scene.addPixmap(pixmap)
                self.log(f"成功加载可视化图表: {image_path}")
            else:
                self.log(f"未找到可视化图表文件: {image_path}")

        # 重置缩放
        self.reset_zoom()

    def display_visualization_image(self, image_path):
        """在图形视图中显示指定路径的可视化图像"""
        pixmap = QPixmap(image_path)

        if not pixmap.isNull():
            # 清除场景中的现有项目
            self.scene.clear()

            # 添加新图片
            self.pixmap_item = self.scene.addPixmap(pixmap)

            # 重置缩放
            self.reset_zoom()

            # 输出找到的文件名
            self.log(f"成功加载可视化图表: {image_path}")
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