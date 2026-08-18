# PyInstaller build recipe. Run it from the repository root:
#
#     uv run --extra build pyinstaller packaging/mangame.spec --noconfirm
#
# Produces dist/mangame on Linux, dist/mangame.exe on Windows and
# dist/mangame.app on macOS. The release workflow runs exactly this line.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 — PyInstaller injects SPECPATH
ICONS = ROOT / "packaging" / "icons"

sys.path.insert(0, str(ROOT / "src"))
from mangame import __version__  # noqa: E402

ICON = {
    "win32": str(ICONS / "mangame.ico"),
    "darwin": str(ICONS / "mangame.icns"),
}.get(sys.platform)

# Nothing here is imported by the app, and each one drags a measurable
# amount of weight into the download.
EXCLUDES = [
    "tkinter",
    "unittest",
    "pydoc_data",
    "test",
    "pytest",
    "mypy",
    "ruff",
    "PIL",
]

analysis = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(ROOT / "src" / "mangame" / "assets"), "mangame/assets")],
    hiddenimports=[],
    hookspath=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(analysis.pure)  # noqa: F821

if sys.platform == "darwin":
    # A bundle, not a bare binary: only an .app can carry LSUIElement, and
    # without that a tray-only app still claims a Dock tile.
    exe = EXE(  # noqa: F821
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="mangame",
        console=False,
        icon=ICON,
    )
    collected = COLLECT(  # noqa: F821
        exe,
        analysis.binaries,
        analysis.datas,
        name="mangame",
    )
    app = BUNDLE(  # noqa: F821
        collected,
        name="mangame.app",
        icon=ICON,
        bundle_identifier="io.github.frodo4fingers.mangame",
        info_plist={
            "LSUIElement": True,
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": __version__,
        },
    )
else:
    # One file, because the whole promise is "download it and run it".
    exe = EXE(  # noqa: F821
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name="mangame",
        console=False,
        icon=ICON,
        upx=False,
    )
