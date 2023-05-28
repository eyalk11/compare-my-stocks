# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['C:\\Users\\ekarni\\compare-my-stocks\\src\\compare_my_stocks\\__main__.py'],
    pathex=['C:\\Users\\ekarni\\compare-my-stocks\\src\\','C:\\Users\\ekarni\\compare-my-stocks\\src\\compare_my_stocks'],
    binaries=[],
    datas=[
    ('C:\\Users\\ekarni\\compare-my-stocks\\venv\Lib\\site-packages\\json_editor\\ui\\json_editor_ui.ui','./json_editor/ui'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\src\\compare_my_stocks\\gui\\mainwindow.ui','./compare_my_stocks/gui'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\src\\compare_my_stocks\\data' , './data'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\install' , './install'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\LICENSE' , '.'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\README.md' , '.'),
    ('C:\\Users\\ekarni\\compare-my-stocks\\dist\\ibsrv.exe' , '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='compare-my-stocks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='compare-my-stocks',
)
