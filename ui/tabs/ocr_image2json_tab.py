# ui/tabs/ocr_image2json_tab.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QPushButton,
    QFileDialog, 
    QTextEdit, 
    QComboBox,
    QLineEdit, 
    QHBoxLayout, 
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QFormLayout
)
from PySide6.QtGui import QPixmap, QPainter, QTransform
from PySide6.QtWidgets import QScrollArea, QGraphicsView, QGraphicsScene, QSlider
from modules.ocr_image2json import OcrImageProcessor, ErrorEntryManager
from functools import partial


class BatchTab(QWidget):
    def __init__(self, config_manager=None, main_window=None):
        super().__init__()
        self.config_manager = config_manager
        self.main_window = main_window  # 保存主窗口引用
        self.processor = OcrImageProcessor(config_manager) if config_manager else None
        self.error_manager = ErrorEntryManager()
        self.current_errors = []
        
        # 左侧：批量处理组件
        self.game_combo = QComboBox()
        self.game_combo.currentTextChanged.connect(self.on_game_changed)
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("请输入UID")
        self.timezone_input = QLineEdit("8")
        self.timezone_input.setMaximumWidth(50)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # 右侧：错误修正组件
        self.error_table = QTableWidget()
        self.error_log_output = QTextEdit()
        self.error_log_output.setReadOnly(True)
        
        self._init_ui()

    def _init_ui(self):
        # 整体布局
        main_layout = QHBoxLayout(self)
        
        # 左侧：批量处理区域
        left_layout = QVBoxLayout()
        
        # 游戏选择布局
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("选择游戏:"))
        game_layout.addWidget(self.game_combo)
        game_layout.addWidget(QLabel("UID:"))
        game_layout.addWidget(self.uid_input)
        game_layout.addWidget(QLabel("时区:"))
        game_layout.addWidget(self.timezone_input)

        # 图片目录布局
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("图片目录:"))
        self.dir_input = QLineEdit()
        self.default_image_dir = "data/input_images"  # 默认图片目录
        # 如果共享的目录不为空，使用它作为默认值
        if self.main_window and self.main_window.shared_image_dir != None:
            self.default_image_dir = self.main_window.shared_image_dir
        self.dir_input.setText(self.default_image_dir)
        dir_layout.addWidget(self.dir_input)
        btn_select = QPushButton("选择图片目录")
        btn_select.clicked.connect(self.select_dir)
        dir_layout.addWidget(btn_select)

        btn_run = QPushButton("开始批量处理")
        btn_run.clicked.connect(self.run_batch)

        left_layout.addLayout(game_layout)
        left_layout.addWidget(btn_select)
        left_layout.addWidget(btn_run)
        left_layout.addWidget(QLabel("处理日志:"))
        left_layout.addWidget(self.log_output)
        
        # 右侧：错误修正区域
        right_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("错误条目修正")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(title_label)
        
        # 错误表
        self.error_table.setColumnCount(5)  # 移除"建议"列，减少一列
        self.error_table.setHorizontalHeaderLabels([
            "序号", "原始物品", "原始卡池", "时间", "操作"
        ])
        header = self.error_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        right_layout.addWidget(self.error_table)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("刷新错误列表")
        btn_refresh.clicked.connect(self.load_errors)
        
        control_layout.addWidget(btn_refresh)
        control_layout.addStretch()
        
        right_layout.addLayout(control_layout)
        
        # 日志输出
        right_layout.addWidget(QLabel("错误日志:"))
        right_layout.addWidget(self.error_log_output)
        
        # 将左右两侧添加到主布局
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        # 初始化游戏列表
        self._init_games()
        
        # 初始加载错误列表
        self.load_errors()

    def _init_games(self):
        """初始化游戏列表"""
        if self.config_manager:
            games = self.config_manager.get_available_games()
            self.game_combo.addItems(games)
            if games:
                self.current_game = games[0]
        else:
            self.log("配置管理器未初始化")

    def on_game_changed(self, game_id):
        """当游戏改变时的处理"""
        self.current_game = game_id
        self.log(f"切换到游戏: {game_id}")

    def select_dir(self):
        start_dir = self.default_image_dir
        path = QFileDialog.getExistingDirectory(self, "选择图片目录", start_dir)
        if path:
            self.dir_input.setText(path)
            self.log("选择目录：" + path)
            self.image_dir = path

    def run_batch(self):
        if not hasattr(self, 'current_game'):
            self.log("请先选择游戏")
            return
            
        if not hasattr(self, 'image_dir'):
            self.log("请先选择图片目录")
            return
            
        uid = self.uid_input.text()
        if not uid:
            self.log("请输入UID")
            return
            
        try:
            timezone = int(self.timezone_input.text())
        except ValueError:
            self.log("时区必须是整数")
            return
            
        try:
            result = self.processor.process_images(
                image_source=self.image_dir,
                game_id=self.current_game,
                uid=uid,
                timezone=timezone
            )
            if result:
                self.log(f"批量处理完成！结果保存至: {result}")
                # 重新加载错误列表
                self.load_errors()
            else:
                self.log("批量处理失败，请查看日志")
        except Exception as e:
            self.log(f"批量处理过程中出现错误: {e}")

    def log(self, message):
        """向日志输出添加消息"""
        from modules.logger_manager import get_logger
        logger = get_logger(self.config_manager)
        logger.info(message)
        self.log_output.append(message)

    def load_errors(self):
        """加载错误列表"""
        try:
            self.current_errors = self.error_manager.get_pending_errors()
            self.update_error_table()
            self.error_log(f"加载了 {len(self.current_errors)} 个待修正的错误条目")
        except Exception as e:
            self.error_log(f"加载错误列表失败: {e}")

    def update_error_table(self):
        """更新错误表格显示"""
        self.error_table.setRowCount(len(self.current_errors))
        
        for row, error in enumerate(self.current_errors):
            # 序号
            item_widget = QTableWidgetItem(str(row + 1))
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
            self.error_table.setItem(row, 0, item_widget)
            
            # 原始物品
            item_widget = QTableWidgetItem(error["original"]["item"])
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
            self.error_table.setItem(row, 1, item_widget)
            
            # 原始卡池
            item_widget = QTableWidgetItem(error["original"]["pool"])
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
            self.error_table.setItem(row, 2, item_widget)
            
            # 时间
            time_widget = QTableWidgetItem(error["original"]["time"])
            time_widget.setFlags(time_widget.flags() & ~Qt.ItemIsEditable)
            self.error_table.setItem(row, 3, time_widget)
            
            # 操作按钮 - 使用委托或单独的widget
            button_layout = QHBoxLayout()
            
            # 使用partial创建绑定函数
            btn_correct = QPushButton("修正")
            btn_correct.setStyleSheet('padding: 2px;')
            btn_correct.clicked.connect(partial(self.correct_error, row))
            
            btn_ignore = QPushButton("忽略")
            btn_ignore.setStyleSheet('padding: 2px;')
            btn_ignore.clicked.connect(partial(self.ignore_error, row))
            
            container = QWidget()
            button_layout.addWidget(btn_correct)
            button_layout.addWidget(btn_ignore)
            button_layout.setContentsMargins(2, 2, 2, 2)
            button_layout.setAlignment(Qt.AlignCenter)
            container.setLayout(button_layout)
            
            self.error_table.setCellWidget(row, 4, container)  # 更新列索引

    def correct_error(self, row):
        """修正错误条目"""
        if row >= len(self.current_errors):
            return
            
        error_entry = self.current_errors[row]
        
        # 创建修正对话框
        dialog = CorrectionDialog(error_entry, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            corrected_data = dialog.get_corrected_data()
            self.error_manager.update_error_status(error_entry, "corrected", corrected_data)
            self.error_log(f"已修正条目: {error_entry['original']}")
            self.load_errors()  # 重新加载列表

    def ignore_error(self, row):
        """忽略错误条目"""
        if row >= len(self.current_errors):
            return
            
        error_entry = self.current_errors[row]
        self.error_manager.update_error_status(error_entry, "ignored")
        self.error_log(f"已忽略条目: {error_entry['original']}")
        self.load_errors()  # 重新加载列表
    def error_log(self, message):
        """向错误修正模块日志输出添加消息"""
        from modules.logger_manager import get_logger
        logger = get_logger(self.config_manager)
        logger.info(message)
        self.error_log_output.append(message)


class CorrectionDialog(QDialog):
    """错误修正对话框"""
    
    def __init__(self, error_entry, parent=None):
        super().__init__(parent)
        self.error_entry = error_entry
        self.setWindowTitle("修正错误条目")
        self.resize(800, 700)  # 增加窗口大小以适应图片显示和缩放控件
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 添加图片显示
        image_path = error_entry["context"].get("image_path", "")
        position = error_entry["context"].get("position", "")
        if image_path:
            # 显示图片路径
            path_label = QLabel(f"图片路径: {image_path}")
            path_label.setWordWrap(True)
            main_layout.addWidget(path_label)
            
            # 显示行号
            pos_label = QLabel(f"可能的行号: {position}" if position is not None else "行号: 未知")
            main_layout.addWidget(pos_label)
            
            # 图片显示
            try:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # 创建图形视图以支持缩放
                    self.graphics_view = QGraphicsView()
                    self.scene = QGraphicsScene()
                    self.pixmap_item = self.scene.addPixmap(pixmap)
                    self.graphics_view.setScene(self.scene)
                    
                    # 设置视图选项以改善显示效果
                    self.graphics_view.setRenderHint(QPainter.Antialiasing)
                    self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
                    self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
                    
                    # 设置初始缩放级别
                    self.current_scale = 1.0
                    
                    # 创建缩放控件
                    zoom_layout = QHBoxLayout()
                    zoom_out_btn = QPushButton("缩小 (-)")
                    zoom_out_btn.clicked.connect(self.zoom_out)
                    
                    zoom_in_btn = QPushButton("放大 (+)")
                    zoom_in_btn.clicked.connect(self.zoom_in)
                    
                    reset_zoom_btn = QPushButton("重置")
                    reset_zoom_btn.clicked.connect(self.reset_zoom)
                    
                    # 使用滑块进行缩放
                    self.zoom_slider = QSlider(Qt.Horizontal)
                    self.zoom_slider.setMinimum(10)  # 10%
                    self.zoom_slider.setMaximum(200)  # 200%
                    self.zoom_slider.setValue(100)  # 100%
                    self.zoom_slider.valueChanged.connect(self.on_slider_changed)
                    
                    zoom_layout.addWidget(zoom_out_btn)
                    zoom_layout.addWidget(self.zoom_slider)
                    zoom_layout.addWidget(zoom_in_btn)
                    zoom_layout.addWidget(reset_zoom_btn)
                    
                    main_layout.addWidget(self.graphics_view)
                    main_layout.addLayout(zoom_layout)
                else:
                    error_label = QLabel("无法加载图片")
                    main_layout.addWidget(error_label)
            except Exception as e:
                error_label = QLabel(f"图片加载错误: {str(e)}")
                main_layout.addWidget(error_label)
        else:
            no_image_label = QLabel("没有可用的图片路径")
            main_layout.addWidget(no_image_label)
        
        # 添加分割线
        separator = QLabel()
        main_layout.addWidget(separator)
        
        # 添加修正表单
        form_layout = QFormLayout()
        
        # 物品名称
        self.item_input = QLineEdit(error_entry["original"]["item"])
        form_layout.addRow("物品名称:", self.item_input)
        
        # 卡池名称
        self.pool_input = QLineEdit(error_entry["original"]["pool"])
        form_layout.addRow("卡池名称:", self.pool_input)
        
        # 时间
        self.time_input = QLineEdit(error_entry["original"]["time"])
        form_layout.addRow("时间:", self.time_input)
        
        main_layout.addLayout(form_layout)
        
        # 按钮
        from PySide6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
    
    def zoom_in(self):
        """放大图片"""
        self.current_scale *= 1.2
        self.apply_zoom()
    
    def zoom_out(self):
        """缩小图片"""
        self.current_scale /= 1.2
        self.apply_zoom()
    
    def reset_zoom(self):
        """重置缩放"""
        self.current_scale = 1.0
        self.apply_zoom()
    
    def on_slider_changed(self, value):
        """滑块值改变时的处理"""
        # 计算缩放比例，从10%到200%
        target_scale = value / 100.0
        self.current_scale = target_scale
        self.apply_zoom()
    
    def apply_zoom(self):
        """应用缩放"""
        # 限制缩放范围
        self.current_scale = max(0.1, min(self.current_scale, 3.0))
        
        # 更新滑块值
        slider_value = int(self.current_scale * 100)
        self.zoom_slider.setValue(slider_value)
        
        # 应用变换
        transform = QTransform()
        transform.scale(self.current_scale, self.current_scale)
        self.graphics_view.setTransform(transform)

    def get_corrected_data(self):
        """获取修正后的数据"""
        return {
            "item": self.item_input.text().strip(),
            "pool": self.pool_input.text().strip(),
            "time": self.time_input.text().strip()
        }