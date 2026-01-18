# ui/main_window.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QStatusBar,
    QFileDialog,
    QMessageBox,
    QWidget,
    QLabel
)

from ui.tabs.ocr_test_tab import OcrTestTab
from ui.tabs.ocr_image2json_tab import BatchTab
from ui.tabs.analysis_tab import AnalysisTab
from modules.config_loader import ConfigManager
from modules.logger_manager import get_logger


class MainWindow(QMainWindow):
    def __init__(self, config_manager=None):
        super().__init__()

        self.setWindowTitle("Gacha OCR Export")
        self.resize(1100, 720)

        # 配置管理器
        self.config_manager = config_manager
        self.logger = get_logger(config_manager)

        # 共享图片路径
        self.shared_image_dir = None

        # ====== 中央 Tab 区域 ======
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._init_tabs()
        self._init_menu()
        self._init_status_bar()

    def init_config_manager(self, config_manager):
        """初始化配置管理器"""
        try:
            self.config_manager = config_manager
            self.logger = get_logger(config_manager)
            self.statusBar().showMessage("配置管理器初始化成功")
        except Exception as e:
            self.statusBar().showMessage(f"配置管理器初始化失败: {e}")
            QMessageBox.warning(self, "警告", f"配置管理器初始化失败: {e}")

    # ------------------------------------------------------------------
    # 初始化 Tab
    # ------------------------------------------------------------------


    # 修改 ui/main_window.py，在 _init_tabs 方法中添加错误修正标签页
    def _init_tabs(self):
        """
        初始化四个核心 Tab
        """
        # OCR 测试标签页
        self.ocr_test_tab = OcrTestTab(self.config_manager, main_window=self)
        self.tabs.addTab(self.ocr_test_tab, "OCR 测试")

        # 批量处理标签页
        self.batch_tab = BatchTab(self.config_manager, main_window=self)
        self.tabs.addTab(self.batch_tab, "批量处理")

        # 历史分析标签页
        self.analysis_tab = AnalysisTab(self.config_manager)
        self.tabs.addTab(self.analysis_tab, "历史分析")

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------
    def _init_menu(self):
        menubar = self.menuBar()

        # ===== 工具 =====
        tool_menu = menubar.addMenu("工具")
        
        refresh_config_action = QAction("刷新配置", self)
        refresh_config_action.triggered.connect(self.refresh_config)
        tool_menu.addAction(refresh_config_action)

        # ===== 帮助 =====
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------
    def _init_status_bar(self):
        status = QStatusBar(self)
        status.showMessage("就绪")
        self.setStatusBar(status)

    # ------------------------------------------------------------------
    # 菜单动作
    # ------------------------------------------------------------------

    def refresh_config(self):
        """刷新配置"""
        try:
            self.config_manager = ConfigManager()
            self.statusBar().showMessage("配置已刷新")
            QMessageBox.information(self, "提示", "配置已刷新")
        except Exception as e:
            self.statusBar().showMessage(f"配置刷新失败: {e}")
            QMessageBox.warning(self, "警告", f"配置刷新失败: {e}")

    def show_about(self):
        QMessageBox.information(
            self,
            "关于",
            "Gacha OCR Export\n\n"
            "基于 OCR 的抽卡记录导出与分析工具\n"
            "支持多个游戏的抽卡记录处理\n"
            "Author: 慕克"
        )