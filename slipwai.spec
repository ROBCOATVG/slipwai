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
    hiddenimports=[],
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
