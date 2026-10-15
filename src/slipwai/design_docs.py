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

import base64
import binascii
import json
import re
from pathlib import Path, PurePosixPath

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


def inside(home: Path, named: str, against: Path | None = None) -> Path | None:
    """The file that reference names, or nothing where it is not a file inside `home`.

    Two directories and they are not the same one. A link is relative to **the document that holds it**,
    which is `against`; what nothing may reach outside of is `home`. They are the same for a `--prd` and
    differ for a `--brief`, where the document may sit in a subfolder and point back up into the rest of
    the brief. The containment check is the point either way: `../`, a symlink out of the tree and an
    absolute path are all things the author could reach and this will not copy.
    """
    try:
        path = ((against or home) / named).resolve()
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


def referenced(document: Path, text: str, home: Path | None = None) -> tuple[dict[str, Path], str]:
    """What this document names and where each lands, with the text rewritten to point at it.

    The rewrite is what makes this worth doing: a file carried in under a name the document still spells
    the old way is a file nobody finds, which is the state the document was already in.

    `home` is what the links are resolved against and what nothing may reach outside of — the document's
    own directory for a `--prd`, and the whole brief for a `--brief`, because a PRD sitting in `docs/`
    inside a brief folder quite reasonably points at `../wireframes/`.
    """
    against = document.parent
    home = (home or against).resolve()
    carried: dict[str, Path] = {}

    def land(match: re.Match[str]) -> str:
        named = match.group(2)
        if ELSEWHERE.match(named):
            return match.group(0)
        path = inside(home, named.partition("#")[0], against)
        if path is None:
            return match.group(0)
        where = path.relative_to(home).as_posix()
        carried[f"{DESIGN}/{where}"] = path
        # Relative to `docs/prd.md`, which is where the rewritten document lands.
        return f"{match.group(1)}design/{where}{match.group(3)}"

    return weighed(carried, f"what {document.name} references"), REFERENCE.sub(land, text)


#: What a product requirements document is called, in the order the brief is searched. Exact name first,
#: then a name that says what it is, then a document whose own first heading does.
PRD_NAMES = ("prd.md", "prd.txt", "requirements.md", "brief.md")
PRD_WORDS = ("prd", "requirement", "product brief")
#: A document's own first heading, which is the last thing asked and the most reliable: a file somebody
#: called `v2-final.md` still opens with *# Product Requirements*.
TITLE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def says_it_is_one(path: Path) -> bool:
    """Whether this document's first heading says it is a requirements document."""
    if path.suffix.lower() not in (".md", ".txt"):
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return False
    found = TITLE.search(head)
    return found is not None and any(word in found.group(1).lower() for word in PRD_WORDS)


def briefed(home: Path) -> tuple[Path | None, list[Path]]:
    """One folder of brief, sorted: the document that reads as the PRD, and everything else.

    **Everything else travels whatever it is** — that is the point of handing over a folder rather than
    naming two things. The sorting only has to get the PRD right, and it is asked three ways in order of
    how much it proves: the name a PRD usually has, a name that says what it is, and the document's own
    first heading, which survives a file somebody called `v2-final.md`.

    No PRD is an answer, not a failure: a folder of wireframes and a brand sheet is design material, and
    the specification gets written in the agent the way it always could be.
    """
    found = [path for path in sorted(home.rglob("*"))
             if path.is_file() and not any(part.startswith(".") for part in path.relative_to(home).parts)]
    for named in PRD_NAMES:
        for path in found:
            if path.name.lower() == named:
                return path, [one for one in found if one != path]
    for path in found:
        if path.suffix.lower() in (".md", ".txt") and any(
                word in path.stem.lower() for word in PRD_WORDS):
            return path, [one for one in found if one != path]
    for path in found:
        if says_it_is_one(path):
            return path, [one for one in found if one != path]
    return None, found


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


def unpacked(payload: str, into: Path) -> Path | None:
    """A board's design material, written to a directory `--design` can be pointed at.

    A browser hands a page a file's *contents* and never its path, so what arrives is the name and the
    bytes — base64, because half of this is images and a PNG is not text. Written back to files for the
    length of the run, exactly as the PRD already is; `None` where nothing was picked.

    Every guard `handed_over` applies is applied again here and for a stronger reason: that function reads
    a directory a person typed on their own command line, and this reads a JSON payload. A `path` with
    `..` in it, an absolute one, or one naming `.git` is refused rather than written.
    """
    try:
        found = json.loads(payload or "[]")
    except ValueError as fault:
        raise GenerationError(f"the design material did not arrive as a list of files ({fault})") from None
    if not isinstance(found, list) or not found:
        return None
    if len(found) > FILES:
        raise GenerationError(f"{len(found)} files is over the {FILES} one handed-over tree may carry")
    into.mkdir(parents=True, exist_ok=True)
    total = 0
    for one in found:
        if not isinstance(one, dict):
            raise GenerationError("each piece of design material is a name and its bytes")
        named = str(one.get("path") or "").strip().replace("\\", "/")
        where = PurePosixPath(named)
        if not named or where.is_absolute() or ".." in where.parts or any(
                part.startswith(".") for part in where.parts):
            raise GenerationError(f"{named!r} is not a name this writes to")
        try:
            body = base64.b64decode(str(one.get("data") or ""), validate=True)
        except (binascii.Error, ValueError):
            raise GenerationError(f"{named}'s bytes did not arrive intact") from None
        total += len(body)
        if total > BYTES:
            raise GenerationError(f"the design material is over the {BYTES // (1024 * 1024)}MB one "
                                  f"handed-over tree may carry")
        path = into / where
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return into
