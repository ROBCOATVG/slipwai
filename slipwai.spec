# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# The roots the executable verifies HTTPS against, beside the machine's own (`slipwai/certificates.py`).
# Imported here so that a build without them stops, rather than making an executable that cannot fetch
# on a new Windows.
import certifi  # noqa: F401
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


root = Path(SPECPATH)
# `collect_submodules` below imports the package to list it, and nothing installs it where the build's
# Python looks: without this it lists almost nothing, and every module only a language package imports —
# `slipwai.project.composition`, say — is left out of the executable, which then cannot load a language.
sys.path.insert(0, str(root / "src"))

DATAS = [
        (str(root / "assets"), "assets"),
        (str(root / "catalog.json"), "."),
        (str(root / "VERSION"), "."),
        # Carried because `migrate` takes its catch-up notes out of them and `slipwai upgrade` prints the
        # entries between the version you had and the one you got. A frozen command has no checkout beside
        # it, so what it does not carry it cannot read.
        (str(root / "CHANGELOG.md"), "."),
        (str(root / "changelog.d"), "changelog.d"),
        # The rename table `migrate` applies to a version 1 project, for the same reason.
        (str(root / "docs/rename.json"), "docs"),
        # The worked quickstarts `generate` offers before its first question, read from beside the keel.
        (str(root / "docs/reference"), "docs/reference"),
        # `cacert.pem`, where `certifi.where()` looks for it.
        *collect_data_files("certifi"),
]


def analysed(entry):
    """One keel, analysed from `entry`: the command's `__main__`, or the app's `app.py`."""
    return Analysis(
        [str(root / entry)],
        pathex=[str(root / "src")],
        binaries=[],
        datas=DATAS,
        # A language package is loaded from the package directory at run time and imports the keel by name,
        # so every keel module stays in the executable whether or not a static import from `__main__`
        # reaches it. The executable bundles no package: it is the keel alone, the same as the wheel, so
        # there is one artefact to build and sign and no bundled copy to drift from the chandlery's.
        hiddenimports=[*collect_submodules("slipwai"), "certifi"],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        optimize=0,
    )


analysis = analysed("src/slipwai/__main__.py")
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="slipwai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

# The app (phase 23): the same keel from `app.py`, windowed, so a double-click opens the board and no
# terminal. A bundle on macOS, built as a folder because that is the shape an `.app` and its signature
# want; one file on Windows, which places itself on first launch. Linux keeps the command alone.
if sys.platform in ("darwin", "win32"):
    # The mark, made by `scripts/build-icons.py`; given no icon, PyInstaller stamps on its own Python one.
    icons = root / "assets" / "brand"
    app = analysed("src/slipwai/app.py")
    app_pyz = PYZ(app.pure)
    if sys.platform == "darwin":
        app_exe = EXE(app_pyz, app.scripts, [], exclude_binaries=True, name="slipwai", debug=False,
                      bootloader_ignore_signals=False, strip=False, upx=False, console=False)
        collected = COLLECT(app_exe, app.binaries, app.datas, strip=False, upx=False, name="slipwai-app")
        BUNDLE(collected, name="Slipwai.app", bundle_identifier="ai.slipwai.app",
               icon=str(icons / "slipwai.icns"),
               version=(root / "VERSION").read_text(encoding="utf-8").strip(),
               info_plist={"LSMinimumSystemVersion": "12.0", "NSHighResolutionCapable": True,
                           "CFBundleDisplayName": "slipwai"})
    else:
        EXE(app_pyz, app.scripts, app.binaries, app.datas, [], name="slipwai-board", debug=False,
            bootloader_ignore_signals=False, strip=False, upx=False, console=False,
            icon=str(icons / "slipwai.ico"))
