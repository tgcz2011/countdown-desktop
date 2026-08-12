# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：onedir 打包主程序。"""
import os

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/icon.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'pytest',
              'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineCore',
              'PySide6.QtWebEngineQuick', 'PySide6.QtQuick', 'PySide6.QtQml',
              'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.QtCharts',
              'PySide6.QtMultimedia', 'PySide6.QtBluetooth', 'PySide6.QtSql'],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CountdownDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CountdownDesktop',
)
