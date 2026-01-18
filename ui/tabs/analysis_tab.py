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
    QLabel
)
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

        # 默认历史文件目录
        self.default_history_dir = "data/history"
        
        layout = QVBoxLayout(self)

        # 游戏选择布局
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("选择游戏:"))
        game_layout.addWidget(self.game_combo)
        
        btn_load = QPushButton("加载历史记录 JSON")
        btn_load.clicked.connect(self.load_json)

        btn_analyze = QPushButton("开始分析")
        btn_analyze.clicked.connect(self.run_analysis)

        layout.addLayout(game_layout)
        layout.addWidget(btn_load)
        layout.addWidget(btn_analyze)
        layout.addWidget(self.log_output)
        
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
                result = self.analyzer.analyze(self.json_path, self.current_game)
                if result['success']:
                    self.log("分析完成！")
                    self.log(f"总共分析了 {len(result['pool_stats'])} 个卡池")
                else:
                    self.log(f"分析失败: {result['error']}")
            except Exception as e:
                self.log(f"分析过程中出现错误: {e}")
        else:
            self.log("分析器未初始化")

    def log(self, text):
        self.log_output.append(text)