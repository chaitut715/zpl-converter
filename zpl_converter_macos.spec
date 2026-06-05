# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for ZPL Converter — macOS ARM64 app bundle
# Run with: pyinstaller zpl_converter_macos.spec

import os

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the entire assets/ folder (includes labelize binary)
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
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon = os.path.join(SPECPATH, "assets", "icon.icns")
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
    upx=False,              # UPX not recommended on macOS
    console=False,          # GUI application — no console window
    disable_windowed_traceback=False,
    target_arch="arm64",    # Apple Silicon
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
    upx=False,
    name="zpl_converter",
)

app = BUNDLE(
    coll,
    name="ZPL Converter.app",
    icon=_icon_arg,
    bundle_identifier="com.github.chaitut715.zplconverter",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
    },
)
