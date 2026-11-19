"""`docs/intake/`: the record written when a person hands over a further feature, to `/sail` or on the board.

The person does not create the directory. `/sail` does, from the words they typed and the documents that
session can read; the board's Next features tab does, through `capture`, at the end of its own conversation
(`intake_talk.py`). Spec Kit's assessment then lives in `.specify/assessments/<slug>/`. A `go` is what
may be specified, and only after `confirmed` says a person — or, under `/cruise`, the skipper — agreed
this was a new feature. `specified.json` names the feature directory and the digest of the sources that
produced it, so a later edit of those sources is seen rather than treated as already done.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

PLACE = "docs/intake"
BRIEF = "brief.md"
CONFIRMED = "confirmed"
RECEIPT = "specified.json"
#: Beside the brief of an idea nobody talked through: captured on the board where it could launch no agent.
UNDISCUSSED = "not-discussed"
#: The surfaces the hand-over's agent thought the idea touches: a hint for the storyboard stage, never an answer.
SURFACES = "surfaces.json"
ASSESSMENTS = ".specify/assessments"
README = "docs/intake/README.md"
#: What Spec Kit's `assess` extension writes as its last word. Anything else is still being decided.
VERDICTS = ("go", "needs-clarification", "kill")
_VERDICT = re.compile(
    r"(?im)^[\s*]*verdict[\s*:]*\s*(go|needs-clarification|kill)\b"
)
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Idea:
    """One feature handed to `/sail`, and how far it has got."""

    slug: str
    state: str
    feature: str = ""
    detail: str = ""
    discussed: bool = True  # False where `not-discussed` is beside the brief: raw words, shaped by nobody
    surfaces: tuple[str, ...] = ()  # what `surfaces.json` suggests the idea touches; a hint, not a finding


def slug_of(words: str, taken: set[str]) -> str:
    """A directory name for the request, that does not collide with one already written."""
    words = _SLUG.sub("-", words.strip().lower()).strip("-") or "feature"
    base = words[:48].strip("-") or "feature"
    name = base
    count = 2
    while name in taken:
        suffix = f"-{count}"
        name = f"{base[:48 - len(suffix)].strip('-')}{suffix}"
        count += 1
    return name


def capture(root: Path, request: str, sources: tuple[Path, ...] | list[Path] = (),
            discussed: bool = True, surfaces: tuple[str, ...] | list[str] = ()) -> tuple[Path, tuple[str, ...]]:
    """Write the request under `docs/intake/` and copy every source the session can read.

    A source that is not a file is named in the second result and not invented. The caller stops on that
    list: a specification built from a document nobody could open would be a guess. `discussed` is False
    where no agent read the idea with the person: the mark is written for the assessment to find. `surfaces`
    are the existing surfaces the hand-over's agent thought the idea touches, kept as `surfaces.json`: a hint.
    """
    home = root / PLACE
    taken = {path.name for path in home.iterdir() if path.is_dir()} if home.is_dir() else set()
    folder = home / slug_of(request, taken)
    folder.mkdir(parents=True)
    text = request.strip()
    (folder / BRIEF).write_text(f"# {text}\n\n{text}\n", encoding="utf-8")
    if not discussed:
        (folder / UNDISCUSSED).write_text("not discussed\ncaptured on the board, which could launch no agent to "
                                          "talk it through\n", encoding="utf-8")
    if surfaces:
        hint = {"suggested": [str(one) for one in surfaces], "by": "hand-over", "authoritative": False,
                "note": "A suggestion from the hand-over conversation: existing surfaces the idea seems to touch. "
                        "The storyboard stage starts from it and may conclude otherwise; nothing treats it as decided."}
        (folder / SURFACES).write_text(json.dumps(hint, indent=2) + "\n", encoding="utf-8")
    missing: list[str] = []
    for source in sources:
        path = Path(source)
        if not path.is_file():
            try:
                missing.append(path.relative_to(root).as_posix())
            except ValueError:
                missing.append(path.as_posix())
            continue
        dest = folder / path.name
        if dest.exists() and dest.resolve() == path.resolve():
            continue
        dest.write_bytes(path.read_bytes())
    return folder, tuple(missing)


def suggested_surfaces(root: Path, slug: str) -> tuple[str, ...]:
    """The surfaces an idea's `surfaces.json` suggests, or none where there is no file or it does not read.
    For whatever draws the idea into the storyboard: a place to start, and nothing to rely on."""
    try:
        held = json.loads((root / PLACE / slug / SURFACES).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    names = held.get("suggested") if isinstance(held, dict) else None
    return tuple(one for one in names if isinstance(one, str) and one.strip()) if isinstance(names, list) else ()


def digest_of(folder: Path) -> str:
    """The sources this idea was captured from, as one sha256.

    `specified.json` and `confirmed` are excluded: one is the receipt this digest is written into, and the
    other is the answer to a different question. Changing either must not look like the requirements changed.
    """
    hasher = hashlib.sha256()
    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.name not in (RECEIPT, CONFIRMED)
        and not any(part.startswith(".") for part in path.relative_to(folder).parts)
    )
    for path in files:
        hasher.update(path.relative_to(folder).as_posix().encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _verdict(root: Path, slug: str) -> str:
    page = root / ASSESSMENTS / slug / "decision.md"
    if not page.is_file():
        return ""
    found = _VERDICT.search(page.read_text(encoding="utf-8", errors="replace"))
    return found.group(1).lower() if found else ""


def _receipt(folder: Path) -> tuple[str, str]:
    """The feature directory and digest a receipt names, or two empty strings where it does not read."""
    path = folder / RECEIPT
    if not path.is_file():
        return "", ""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", ""
    if not isinstance(held, dict):
        return "", ""
    return str(held.get("feature") or ""), str(held.get("digest") or "")


def ideas(root: Path) -> list[Idea]:
    """Every captured idea, in name order, with the state the files prove."""
    home = root / PLACE
    if not home.is_dir():
        return []
    found = []
    for folder in sorted(path for path in home.iterdir() if path.is_dir() and not path.name.startswith(".")):
        if not (folder / BRIEF).is_file() and not (folder / RECEIPT).is_file():
            continue
        feature, recorded = _receipt(folder)
        digest = digest_of(folder)
        if recorded and recorded == digest and feature:
            found.append(Idea(folder.name, "specified", feature, feature))
            continue
        if (folder / RECEIPT).is_file():
            found.append(Idea(folder.name, "changed", feature, "the sources have changed since it was specified"))
            continue
        if not (folder / CONFIRMED).is_file():
            found.append(Idea(folder.name, "confirm", detail="waiting for a yes that this is a new feature"))
            continue
        verdict = _verdict(root, folder.name)
        if verdict == "":
            found.append(Idea(folder.name, "assessing", detail="assessment has not decided"))
        else:
            found.append(Idea(folder.name, verdict, detail=f"verdict: {verdict}"))
    found = [replace(one, surfaces=suggested_surfaces(root, one.slug)) for one in found]
    return [replace(one, discussed=False, detail=f"{one.detail}; not discussed with an agent")
            if (home / one.slug / UNDISCUSSED).is_file() else one for one in found]


def pending(root: Path) -> list[str]:
    """Ideas that are not specified and were not killed."""
    return [one.slug for one in ideas(root) if one.state not in ("specified", "kill")]


def ready(root: Path) -> list[str]:
    """Ideas a `go` has cleared for `/speckit-specify`."""
    return [one.slug for one in ideas(root) if one.state == "go"]


def readme() -> str:
    """The page a generated project gets, so the record has a reader."""
    return """# Intake

A further feature is handed over in one of two places. To `/sail` in the conversation: the request, text
pasted there, or a document that session can read. Or on the board, on the Voyage window's **Next features**
tab: say what it is or attach its document, answer what the agent asks, and press **Capture this idea**.
Either way one directory is written here per idea. Creating the directory by hand is not how a feature
starts.

`brief.md` is the request, exactly as it was handed over. Any other file beside it is a document that
came with it; `conversation.md` is what was asked and answered on the board before it was captured.
`not-discussed` is there where the board could launch no agent: the words and documents are as the person
left them, nobody asked whether they are one clear idea, and the assessment is told to ask first.
`surfaces.json` is a hint from that conversation, where the agent named any: the existing surfaces the idea
seems to touch, as `{"suggested": ["<name>", …], "by": "hand-over", "authoritative": false, "note": "…"}`.
It is a suggestion: the storyboard stage may start from it and conclude otherwise, and the file is read, never edited.
`confirmed` is the yes that this is a new feature — a person in the session, or the skipper
when `/cruise` is driving — and it is written before Spec Kit assesses the idea.

Assessment lives in `.specify/assessments/<slug>/`. Its `decision.md` ends in `go`, `needs-clarification`,
or `kill`. Only a `go`, after that yes, is handed to `/speckit-specify`, then `/speckit-clarify`.
`/speckit-checklist` and the read-only find-gaps survey then run in parallel against the clarified
specification; the host runs the find-gaps conversation after both return. Spec Kit specifies it on the
profile `project.json` already names — `event-modelling` or `standard` — and on the one preset
`.specify/presets/.registry` enables for it. Do not enable the other preset, do not change `project.json`,
and do not scaffold again. `specified.json` then names the `specs/...` directory Spec Kit created and the
digest of the sources it was written from. The same sources edited afterwards are assessed again rather
than treated as a second copy of the feature.

The first feature stays `docs/prd.md`. This directory is everything after it.
"""
