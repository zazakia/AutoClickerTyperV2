# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import customtkinter
import os
customtkinter_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('quick_prompts.json', '.'),
        ('config.json', '.'),
        ('README.md', '.'),
        (customtkinter_path, 'customtkinter/'),
    ],
    hiddenimports=[
        'main',
        'config',
        'core.ocr',
        'core.actions',
        'core.verification',
        'utils.logger',
        'core.exceptions',
        'core.config_manager',
        'target_window',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.scrolledtext',
        'tkinter.simpledialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test_harness',
        'test_runner',
        'test_gui_integration',
        'test_gui_unit',
        'test_workflow',
        'test_blue_detection',
        'test_debug',
        'debug_ocr',
        'check_windows',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ZapwebPromptAssist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have an icon file
)
