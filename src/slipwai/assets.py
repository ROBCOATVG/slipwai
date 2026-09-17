"""Where the factory's own material lives, and the scripts it shares with what it generates.

Every path here is resolved from this file rather than the working directory, so `./slipwai generate` behaves
the same whichever directory it is invoked from, and an installed or frozen `slipwai` reads the assets bundled
into it.
"""
from __future__ import annotations

import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
# What the wheel carries beside the package: `assets/`, `catalog.json` and `VERSION`, placed there by the
# `force-include` table in pyproject.toml. Absent in a checkout, where the same three sit at the repository root.
BUNDLE = Path(__file__).resolve().parent / "_bundle"
INSTALLED = BUNDLE.is_dir()
if FROZEN:
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
elif INSTALLED:
    ROOT = BUNDLE
else:
    ROOT = Path(__file__).resolve().parents[2]
# A checkout scaffolds beside itself; a command installed or frozen has no "beside", so it scaffolds where it
# is run.
DEFAULT_OUTPUT = Path.cwd() if FROZEN or INSTALLED else ROOT.parent
VERSION = (ROOT / "VERSION").read_text().strip()
# Where a factory command leaves something for the project to act on and then throw away: `migrate` writes
# its catch-up notes here and `/catch-up` reads them. Spelled here, in the tier every other may read, because
# three of them need it — the module that writes the page, the `.gitignore` that keeps it out of the history,
# and the command file that tells an agent where to look.
NOTES = ".slipwai/catch-up.md"
TOOLKIT_ROOT = ROOT / "assets/toolkit"
PROFILE_ROOT = ROOT / "assets/profiles"
FRONTEND_ROOT = ROOT / "assets/frontends"
LANGUAGE_ROOT = ROOT / "assets/languages"
BACKING_SERVICE_ROOT = ROOT / "assets/backing-services"
# What only a repository the method was installed around takes: the ratchet (brownfield adoption; experimental).
ADOPTION_ROOT = ROOT / "assets/adoption"


def asset_tree(root: Path) -> dict[str, str]:
    """Every file under an asset directory, keyed by its path relative to that directory.

    The asset directories that hold a *tree* of files — a language's walking skeleton, the frontend app —
    are laid out at the paths the files land on, so reading one is a copy and nothing else. That is what
    makes adding a file to a skeleton an edit under `assets/` with no code change anywhere: there is no
    list of filenames to also remember.

    Read with `newline=""` so the string holds whatever line endings the file on disk holds, and
    `write_project` writes it back the same way. Universal-newline translation would be invisible for the
    whole of `assets/` bar one file and silently wrong for that one: `mvnw.cmd` is CRLF throughout, and it
    is a batch/PowerShell polyglot that re-reads itself with `Get-Content -Raw`, so flattening it is not a
    cosmetic difference. A pipeline that is faithful to the bytes needs no exception for it.
    """
    return {path.relative_to(root).as_posix(): read_faithfully(path) for path in asset_files(root)}


def asset_files(root: Path) -> list[Path]:
    """Every file under an asset directory, in path order, leaving the interpreter's caches out.

    A script under `assets/` that Python has imported or compiled leaves a `__pycache__` beside it — a test
    that imported the pruner, or `pip` byte-compiling the bundle when the package is installed — and a
    `.pyc` read as text is a UnicodeDecodeError on the first project. The one walker every reader of the
    tree goes through is where that is excluded, so no reader has to remember to.
    """
    return sorted(
        path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    )


def read_faithfully(path: Path) -> str:
    """The file's text with its own line endings — `read_text(newline="")`, spelled for Python 3.11.

    `Path.read_text` only grew a `newline` parameter in 3.13; on the 3.11 the README promises it raises
    `TypeError` before the first asset is read. `open` has taken `newline` all along.
    """
    with path.open(newline="") as handle:
        return handle.read()


def _load_pruner():
    """The generated project's own prune script, imported rather than reimplemented.

    `assets/backing-services/prune.py` is emitted as `scripts/backing-services.py` so a project can prune
    its backing services at `./init` time. The factory needs the same operation to cut a generated project
    down to what was selected here, and two implementations of one prune would be two sets of bugs — so
    this loads that file and calls it.
    """
    import importlib.util

    source = BACKING_SERVICE_ROOT / "prune.py"
    spec = importlib.util.spec_from_file_location("delivery_backing_services", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the backing-service pruner from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRUNER = _load_pruner()


def _load_style_checker():
    """The generated style gate, shared with replay so both identify imported token files alike."""
    import importlib.util

    source = TOOLKIT_ROOT / "scripts/check-styles.py"
    spec = importlib.util.spec_from_file_location("delivery_check_styles", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the style checker from {source}")
    module = importlib.util.module_from_spec(spec)
    # Unlike the pruner, this source sits inside the canonical toolkit. Its self-containment test reads
    # every file there as text, so an import cache beside the script would become binary toolkit material.
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


STYLE_CHECKER = _load_style_checker()
