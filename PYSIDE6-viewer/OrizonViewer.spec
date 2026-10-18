# -*- mode: python ; coding: utf-8 -*-
# Build:  build_exe.bat   (oppure: pyinstaller --noconfirm --clean OrizonViewer.spec)
datas = [
    ('assets/Orizon-com.jpg', 'assets'),
    ('assets/orizon.ico', 'assets'),
    ('assets/icons', 'assets/icons'),
    ('app/styles.qss', 'app'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['openpyxl', 'xlrd', 'pyxlsb', 'odf', 'odf.opendocument', 'odf.table', 'odf.text',
                   'pandas.io.excel._xlrd', 'pandas.io.excel._pyxlsb', 'pandas.io.excel._odfreader',
                   'pandas.io.excel._openpyxl', 'barcode.codex', 'qrcode', 'PySide6.QtSvg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OrizonViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # UPX non serve e aumenta i falsi positivi degli antivirus
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/orizon.ico',
)
