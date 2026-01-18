# main.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from modules.config_loader import ConfigManager


def main():
    app = QApplication(sys.argv)
    
    # ========== 基础信息 ==========
    app.setApplicationName("Gacha OCR Export")
    app.setOrganizationName("GachaTools")
    
    # 设置应用图标
    icon_path = Path("themes/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        
    # ========== 加载主题 ==========
    style_file = Path("themes/styles.qss")
    if style_file.exists():
        with open(style_file, 'r', encoding='utf-8') as f:
            style = f.read()
            app.setStyleSheet(style)
    else:
        print(f"警告: 找不到样式文件 {style_file}")
    
    # ========== 初始化配置管理器 ==========
    try:
        config_manager = ConfigManager()
    except Exception as e:
        print(f"配置管理器初始化失败：{e}")
        QMessageBox.critical(None, "初始化失败", f"配置管理器初始化失败：\n{e}")
        sys.exit(1)
    
    # ========== 启动主窗口 ==========
    try:
        window = MainWindow(config_manager)
        window.show()
    except Exception as e:
        print(f"程序启动时发生错误：{e}")
        QMessageBox.critical(None, "启动失败", f"程序启动时发生错误：\n{e}")
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()