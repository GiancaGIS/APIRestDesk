# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys
import subprocess

from api_rest_desk.config import APP_BUNDLE_ID, APP_FOLDER_NAME, APP_NAME, APP_VERSION


ROOT_DIR = Path(SPECPATH).parents[1]
ASSETS_DIR = ROOT_DIR / "api_rest_desk" / "assets"
ICON_FILE = ASSETS_DIR / ("app_icon.icns" if sys.platform == "darwin" else "app_icon.ico")
subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "prepare_licenses.py"), "--check"], check=True)


a = Analysis(
    [str(ROOT_DIR / "launch_api_rest_desk.py")],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        (str(ASSETS_DIR / "app_icon.png"), "api_rest_desk/assets"),
        (str(ROOT_DIR / "api_rest_desk" / "legal"), "api_rest_desk/legal"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
# Widgets use neither PDF rendering nor the optional software OpenGL fallback.
# Excluding these avoids redistributing unrelated native components and notices.
a.binaries = [entry for entry in a.binaries if not any(
    name in entry[0].lower().replace("\\", "/")
    for name in ("qpdf", "qtpdf", "qt6pdf", "opengl32sw")
)]
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_FOLDER_NAME,
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
        icon=str(ICON_FILE),
    )
    app = BUNDLE(
        exe,
        name=f"{APP_FOLDER_NAME}.app",
        icon=str(ICON_FILE),
        bundle_identifier=APP_BUNDLE_ID,
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_FOLDER_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        runtime_tmpdir=None,
        icon=str(ICON_FILE),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=APP_FOLDER_NAME,
    )
