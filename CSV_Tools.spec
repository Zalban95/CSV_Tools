# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CSV_Tools.
#
# Build with:
#   pyinstaller CSV_Tools.spec --noconfirm
#
# Produces a single-file windowed executable in dist/.
# Only the Python standard library is bundled; no third-party runtime deps.

from pathlib import Path

APP_NAME = "CSV_Tools"
ENTRY = "csv_tool.py"

# Assets bundled inside the executable. They are extracted to sys._MEIPASS at
# runtime and resolved by csv_tool.RESOURCE_DIR. The input/output folders are
# intentionally NOT bundled -- they live next to the .exe so the user can drop
# CSVs into them.
datas = [
    ("README.md", "."),
]

a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim down the bundle: no numpy/pandas/etc. are actually imported.
        "numpy",
        "pandas",
        "matplotlib",
        "scipy",
        "PIL",
        "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
