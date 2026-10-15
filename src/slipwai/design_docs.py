"""The files a product requirements document stands on, carried into the project with it.

`--prd` read one document's text and wrote it to `docs/prd.md`, and that was the whole of it. A PRD worth
handing over is rarely one file: it names a brand sheet, it embeds the wireframes somebody drew, it cites a
competitor teardown. Every one of those is a relative link, and every one of them dangled the moment the
document landed somewhere else — a *Look and feel* section pinning the direction down, pointing at nothing.

So two things travel now. **What the document itself names**, resolved against the directory it was read
from, with its links rewritten to where they landed; and **`--design <dir>`**, a folder handed over whole,
for the material the PRD happens not to link. Both land under `docs/design/`, which `commands/mockups.md`
reads before it draws a surface: the stage exists to stop a screen being invented, and a direction somebody
already settled is the best reason it has not to invent one.

**Nothing outside the document's own directory travels.** A link to `../../.ssh/id_rsa` is a link this
refuses rather than carries: the PRD is a file somebody was handed, and a generate that copied whatever it
pointed at would be a generate that reads anything the author could name.
"""
from __future__ import annotations

import re
from pathlib import Path

from .errors import GenerationError

#: Where handed-over material lands, beside the document that cites it.
DESIGN = "docs/design"
#: A markdown link or image. The target is group 2; `!` in front makes it an image, which does not matter
#: here because both are a path somebody has to be able to follow.
REFERENCE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
#: What is already somewhere else, and is not this to carry: a URL, a mail address, an in-page anchor.
ELSEWHERE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)
#: What one handed-over tree may be. A PRD's references are a handful of files; a design folder is a
#: handful more. These are here so that a directory somebody pointed at by mistake — a home directory, a
#: node_modules — is a refusal naming the size rather than a generate that appears to hang.
FILES = 200
BYTES = 50 * 1024 * 1024


def inside(home: Path, named: str) -> Path | None:
    """The file that reference names, or nothing where it is not a file inside `home`.

    The containment check is the point. `home` is the directory the document was read from, and anything
    the document names outside it — `../`, a symlink out of the tree, an absolute path — is something the
    author could reach and this will not copy.
    """
    try:
        path = (home / named).resolve()
    except (OSError, ValueError):
        return None
    return path if path.is_relative_to(home.resolve()) and path.is_file() else None


def weighed(found: dict[str, Path], what: str) -> dict[str, Path]:
    """Those files, or a refusal naming what is too much of them."""
    if len(found) > FILES:
        raise GenerationError(f"{what} holds {len(found)} files, over the {FILES} one handed-over tree may "
                              f"carry; point it at the design material rather than at its parent")
    total = sum(path.stat().st_size for path in found.values())
    if total > BYTES:
        raise GenerationError(f"{what} is {total // (1024 * 1024)}MB, over the {BYTES // (1024 * 1024)}MB one "
                              f"handed-over tree may carry")
    return found


def referenced(document: Path, text: str) -> tuple[dict[str, Path], str]:
    """What this document names and where each lands, with the text rewritten to point at it.

    The rewrite is what makes this worth doing: a file carried in under a name the document still spells
    the old way is a file nobody finds, which is the state the document was already in.
    """
    home = document.parent
    carried: dict[str, Path] = {}

    def land(match: re.Match[str]) -> str:
        named = match.group(2)
        if ELSEWHERE.match(named):
            return match.group(0)
        path = inside(home, named.partition("#")[0])
        if path is None:
            return match.group(0)
        where = path.relative_to(home.resolve()).as_posix()
        carried[f"{DESIGN}/{where}"] = path
        # Relative to `docs/prd.md`, which is where the rewritten document lands.
        return f"{match.group(1)}design/{where}{match.group(3)}"

    return weighed(carried, f"what {document.name} references"), REFERENCE.sub(land, text)


def handed_over(named: str) -> dict[str, Path]:
    """Every file under `--design <dir>`, by where it lands. A refusal where it is not a directory."""
    home = Path(named).expanduser()
    if not home.is_dir():
        raise GenerationError(f"--design {home} is not a directory; it is the folder of design material — "
                              f"a brand sheet, wireframes, a stylesheet — carried in beside the PRD")
    found = {f"{DESIGN}/{path.relative_to(home).as_posix()}": path
             for path in sorted(home.rglob("*"))
             if path.is_file() and not any(part.startswith(".") for part in path.relative_to(home).parts)}
    if not found:
        raise GenerationError(f"--design {home} holds no files")
    return weighed(found, f"--design {home}")
