# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


root = Path(SPECPATH)

analysis = Analysis(
    [str(root / "src/slipwai/__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
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
    ],
    # A language package is loaded from the package directory at run time and imports the keel by name,
    # so every keel module stays in the executable whether or not a static import from `__main__`
    # reaches it. The executable bundles no package: it is the keel alone, the same as the wheel, so
    # there is one artefact to build and sign and no bundled copy to drift from the chandlery's.
    hiddenimports=collect_submodules("slipwai"),
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
