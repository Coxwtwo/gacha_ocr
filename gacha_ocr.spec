# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

project_root = os.path.abspath(".")

# -----------------------------
# 需要打包的资源文件
# -----------------------------
datas = [
    # themes
    (os.path.join(project_root, "themes"), "themes"),

    # data 下需要完整保留的目录
    (os.path.join(project_root, "data", "config"), os.path.join("data", "config")),
    (os.path.join(project_root, "data", "catalog"), os.path.join("data", "catalog")),
    (os.path.join(project_root, "data", "history"), os.path.join("data", "history")),
    (os.path.join(project_root, "data", "input_images"), os.path.join("data", "input_images")),
    (os.path.join(project_root, "data", "output_images"), os.path.join("data", "output_images")),

    # Tesseract OCR
    (os.path.join(project_root, "tools", "Tesseract-OCR"), os.path.join("tools", "Tesseract-OCR")),
]

# -----------------------------
# 二进制文件（DLL）
# -----------------------------
binaries = [
    (os.path.join(project_root, "ffi.dll"), "."),
]

# -----------------------------
# 隐式导入（OCR / GUI 常见）
# -----------------------------
hiddenimports = [
    ]

a = Analysis(
    ["main.py"],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gacha_ocr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # GUI 程序
    icon=os.path.join("themes", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="gacha_ocr",
)
