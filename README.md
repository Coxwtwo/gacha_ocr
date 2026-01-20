# Gacha OCR Export

一款针对手游抽卡记录截图的OCR工具，帮助玩家从抽卡历史截图中提取和分析数据。

## 📋 项目简介

Gacha OCR Export 是一个基于 Tesseract OCR 的桌面应用，专注于从手游抽卡历史截图中提取有效信息，并将其转换为可分析、可导出的结构化数据。

项目计划支持多款游戏，目前已内置对《明日方舟》和《重返未来：1999》的支持。

## ✨ 核心特性

- **🖼️ 抽卡截图 OCR 识别**：从抽卡截图中提取抽卡时间、角色/道具名称、卡池名称
- **📂 批量处理**：支持批量导入图片进行识别
- **📊 抽卡数据分析**：对识别后的数据进行统计分析（如出货率、稀有度分布）
- **🧩 错误条目人工修正**：提供错误条目人工修正功能
- **🎯 OCR 区域编辑与自定义**：支持用户调整OCR识别区域以适配不同分辨率

## 🛠️ 技术栈

- **GUI 框架**：PySide6
- **OCR引擎**：Tesseract OCR
- **数据存储**：JSON格式

## 🎮 使用指南

1. **选择游戏**：在界面上选择要处理的游戏
2. **选择图片**：选择抽卡历史截图进行文本提取测试
3. **批量识别**：选择图片文件夹，批量识别截图并生成结构化历史数据
4. **数据分析**：选择需分析的抽卡记录，查看分析报告和可视化图表

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/gacha_ocr.git
cd gacha_ocr
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Tesseract OCR

#### Windows
- 从 [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包
- 将安装路径文件复制到tools\Tesseract-OCR路径下

### 4. 运行项目

```bash
python main.py
```

## ⚙️ 配置说明

项目配置文件位于 `data/config/` 目录：

- `global_config.json`：全局OCR和日志配置
- `game_processing_config_{game_id}.json`：特定游戏的处理配置
- `game_catalog_{game_id}.json`：游戏物品名称与属性映射表
- `game_name_{game_id}.json`：游戏名称数据（用于OCR校正）

## 📁 项目结构

```
gacha_ocr/
├── main.py                 # 程序入口
├── data/                  # 数据存储目录
│   ├── config/            # 配置文件
│   ├── catalog/           # 游戏物品数据
│   ├── history/           # OCR识别结果的历史记录
│   └── ...
├── modules/               # 核心功能模块
│   ├── config_loader.py   # 配置管理器
│   ├── ocr_test.py        # OCR测试工具
│   ├── perform_ocr.py     # OCR执行模块
│   ├── batch_image2json.py # 批量图像转JSON处理模块
│   ├── data_processor.py  # 数据处理模块
│   ├── history_analyzer.py # 历史数据分析
│   ├── preprocess.py      # 图像预处理模块
│   ├── visualization.py   # 可视化模块
│   └── ...
├── ui/                    # 图形界面模块
│   ├── main_window.py     # 主窗口
│   ├── tabs/              # 功能标签页
│   └── widgets/           # 自定义组件
├── themes/                # 主题样式
└── tools/                 # 工具集（Tesseract-OCR）
```

## 📦 打包发布

本项目使用PyInstaller进行打包，打包配置文件为[gacha_ocr.spec](gacha_ocr.spec)，需要将[ffi.dll](ffi.dll)一起打包以避免importing _ctypes错误。

```bash
pip install pyinstaller
pyinstaller gacha_ocr.spec
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！如果您想添加对新游戏的支持或修复问题，请随时贡献。

## 📄 许可证

本项目采用 GPL 3.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
