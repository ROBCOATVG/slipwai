# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


root = Path(SPECPATH)

analysis = Analysis(
    [str(root / "src/slipwai/__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "assets"), "assets"),
        (str(root / "catalog.json"), "."),
        (str(root / "VERSION"), "."),
        # `migrate` takes its catch-up notes out of the changelog, so the frozen executable carries it for
        # the same reason the wheel does: there is no checkout beside either of them. Unpacked to a
        # temporary directory at run time, which is exactly why the notes are written into the project.
        (str(root / "CHANGELOG.md"), "."),
        # And the entry being written, which is not in the changelog yet: a snapshot of this release is what
        # `slipwai upgrade --pre` installs, and a project migrating onto it is owed what the fragments say.
        (str(root / "changelog.d"), "changelog.d"),
    ],
    # The standard-library modules of `assets/toolkit/scripts/install-tools.py`, which `host.py` loads from the
    # bundled assets at run time: PyInstaller never reads that file, so without these the frozen executable
    # starts and dies on `import platform` (the 1.5.0 release job's smoke test). `winreg` exists only on Windows,
    # where the executable is built too. `tests/test_host.py` holds this list to the script's imports.
    hiddenimports=[
        "json", "platform", "shutil", "subprocess", "tarfile", "tempfile", "urllib.request", "dataclasses", "re",
        *(["winreg"] if __import__("sys").platform == "win32" else []),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
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
