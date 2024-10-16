# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kitsu_publisher_standalone.py'],
    pathex=[],
    binaries=[],
    datas=[('./icons', 'icons'), ('./ui', 'ui'), ('./ffmpeg', '.')],
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
    a.binaries,
    a.datas,
    [],
    name='kitsu_publisher_standalone',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons/icon.png'],
)
app = BUNDLE(
    exe,
    name='kitsu_publisher_standalone.app',
    icon='./icons/icon.png',
    bundle_identifier=None,
)
