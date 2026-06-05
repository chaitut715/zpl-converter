# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for ZPL Converter — Windows x64 onedir build
# Run with: pyinstaller zpl_converter.spec

import os

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the entire assets/ folder (includes labelize.exe)
        ("assets", "assets"),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "reportlab",
        "reportlab.pdfgen",
        "reportlab.pdfgen.canvas",
        "reportlab.lib",
        "reportlab.lib.units",
        "reportlab.lib.colors",
        "reportlab.lib.pagesizes",
        "PIL",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
        "tkinter",
        "wx",
        "gtk",
        "PyQt5",
        "PySide2",
        "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon = os.path.join(SPECPATH, "assets", "icon.ico")
_icon_arg = _icon if os.path.exists(_icon) else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="zpl_converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI application — no console window
    disable_windowed_traceback=False,
    target_arch="x86_64",
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Do not compress Qt platform plugins — UPX can corrupt them
        "qwindows.dll",
        "qwindowsvistastyle.dll",
    ],
    name="zpl_converter",
)
