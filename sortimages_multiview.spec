# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sortimages_multiview.py'],
    pathex=[],
    binaries=[],
    datas=[
	('libvips-cpp-42.dll', '.'),
	('libvips-42.dll', '.'),
	('libglib-2.0-0.dll', '.'),
	('libgobject-2.0-0.dll', '.')
	],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sortimages_multiview',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sortimages_multiview',
)
