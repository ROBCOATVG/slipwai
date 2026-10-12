"""Language markers in the canonical toolkit, and the disclaimer on what is still TypeScript.

A skill in `assets/toolkit/` is written once and carries `{{example: <skill>/<id>}}` where a code sample
belongs; generated services use `assets/languages/<language>/examples/` from their packages, while adoption
uses the keel's guidance under `assets/examples/`. A project whose services are written
in more than one language gets every one of them at each marker, each block labelled with its language and
the services it is for, so the agent working in a Go service beside a TypeScript one finds the Go version
where it is looking. A skill whose examples have not been translated yet ships with a note saying so rather
than being withheld, because a skill nobody can read is worse guidance than one whose examples are in the
wrong language.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from .assets import PROFILE_ROOT, ROOT, TOOLKIT_ROOT, asset_files, inside
from .errors import GenerationError
from .registry import registry

EXAMPLE_MARKER = re.compile(r"\{\{example:\s*([a-z0-9]+(?:-[a-z0-9]+)*)/([a-z0-9]+(?:-[a-z0-9]+)*)\}\}")
RAW_TYPESCRIPT_FENCE = re.compile(r"^```(?:typescript|ts)$", re.MULTILINE)
SKILL_TITLE = re.compile(r"^(#\s+.+)$", re.MULTILINE)


# Skills whose examples are inherently TypeScript (the frontend, or TypeScript itself) and are exempt
# both from marker conversion and from the pseudocode disclaimer stamped onto still-TypeScript skills.
FRONTEND_INHERENT_SKILLS = {"react-testing", "front-end-testing", "typescript-strict", "bff-entry-points"}


def markers(profile: str) -> frozenset[tuple[str, str]]:
    """Every `(skill, id)` marker a project of `profile` can carry, which is what a language must answer.

    The toolkit's files, each one the profile's overlay replaces read from the overlay instead, and the overlay's
    own. Read off the trees rather than kept as a list, so a marker a skill gains is asked of every language the
    moment it is written. A file the profile drops (`toolkit.toolkit_treatment`, a tier this one cannot read) is
    read too, so the set can only ask for more than a project ships, never less; `tests/test_conformance_markers.py`
    holds it to exactly what each profile ships.
    """
    from .catalog import CATALOG  # at call time: the merged catalog is read once the package directory is known

    if profile not in CATALOG["profiles"]:
        raise ValueError(f"no profile {profile!r}; the catalog has {', '.join(CATALOG['profiles'])}")
    overlay = PROFILE_ROOT / profile
    own = {path.relative_to(overlay).as_posix(): path for path in asset_files(overlay)} if overlay.is_dir() else {}
    sources = [path for path in asset_files(TOOLKIT_ROOT) if path.relative_to(TOOLKIT_ROOT).as_posix() not in own]
    return frozenset(
        (match.group(1), match.group(2))
        for source in [*sources, *own.values()]
        for match in EXAMPLE_MARKER.finditer(source.read_text(encoding="utf-8"))
    )


class Speaker(NamedTuple):
    """One language a project's skills speak: a backend, its family, and how to label its block."""

    backend: str
    family: str
    label: str


def snippet(backend: str, family: str, skill: str, example_id: str, root: Path | None = None) -> str:
    """This backend's snippet for one marker.

    Looked up twice: the backend's own directory first, then its language family's. Most of what a skill
    teaches is the same Java whichever framework owns startup — a Decider, a value object, a projection —
    so the family holds it once, and a backend overrides only the snippets its framework actually changes
    (a composition root, a driven adapter, a test harness). Without the fallback, a second framework would
    mean a second copy of every snippet, and the two would drift.

    Each owner is read from its own root, `registry().root(owner)` — a loaded language's directory, else the keel's —
    unless a caller names one, which then is every owner's.
    """
    relative = f"examples/{skill}/{example_id}.md"
    for owner in dict.fromkeys((backend, family)):
        base = (registry().root(owner) if root is None else root)
        path = _owned(base, owner, relative)
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8").rstrip("\n")
            except UnicodeDecodeError as error:
                raise GenerationError(f"{owner}'s example {relative} is not UTF-8 text") from error
        if path.exists():
            raise GenerationError(f"{owner}'s example {relative} is not a file")
    raise GenerationError(
        f"missing {backend} example snippet for {skill}/{example_id} (expected "
        f"assets/languages/{backend}/{relative}, or assets/languages/{family}/{relative})"
    )


def resolve_canonical_examples(content: str, root: Path = ROOT) -> str:
    """Resolve guidance markers without a language package.

    These snippets belong to the toolkit's prose, under `assets/examples/`, separate from
    a language's idiomatic answers. Adoption has no generated service and no package to ask.
    Keeping this tree outside `assets/toolkit/` also keeps unreferenced snippets out of projects.
    """
    def replace(match: re.Match[str]) -> str:
        relative = f"{match.group(1)}/{match.group(2)}.md"
        try:
            path = inside(root / "assets/examples", relative, root)
        except ValueError as error:
            raise GenerationError(str(error)) from error
        if not path.is_file():
            raise GenerationError(
                f"missing canonical example snippet for {relative}: "
                "restore the keel's assets/examples from the installed release with `slipwai upgrade`"
            )
        try:
            return path.read_text(encoding="utf-8").rstrip("\n")
        except UnicodeDecodeError as error:
            raise GenerationError(f"canonical example {relative} is not UTF-8 text") from error
    return EXAMPLE_MARKER.sub(replace, content)


def _owned(package: Path, owner: str, relative: str) -> Path:
    """`relative` under the owner's own `assets/languages/<owner>/`, or a refusal where a name steers it elsewhere.

    The owner is a family or backend name and the relative path is built from a skill and a snippet id: any
    of them with a separator or a `..` in it would otherwise read another language's snippets, the keel's included,
    or any file the process can see. Held to the owner's directory, which is held to the package.
    """
    if owner in ("", ".", "..") or Path(owner).name != owner or "\\" in owner:
        raise GenerationError(f"{owner!r} reaches outside its directory for {relative}")
    try:
        return inside(package / "assets/languages" / owner, relative, package)
    except ValueError as error:
        raise GenerationError(f"{owner!r} {error}") from error


def resolve_examples(
    content: str, backend: str, family: str | None = None, root: Path | None = None
) -> str:
    """Replace each `{{example: <skill>/<id>}}` marker with this one backend's snippet."""
    family = backend if family is None else family
    return resolve_examples_for(content, [Speaker(backend, family, "")], root)


def resolve_examples_for(content: str, speakers: list[Speaker], root: Path | None = None) -> str:
    """Replace each marker with a snippet per language the project's services are written in.

    One speaker gives the bare snippet, as a single-language project always had. Several give one block
    each, in service order, headed by the speaker's label — and two speakers whose snippets are the same
    text (two Java frameworks sharing the family's version) share one block, with both labels on it,
    rather than the reader being shown the same code twice.
    """

    def replace(match: re.Match[str]) -> str:
        skill, example_id = match.group(1), match.group(2)
        blocks: dict[str, list[str]] = {}
        for speaker in speakers:
            blocks.setdefault(snippet(speaker.backend, speaker.family, skill, example_id, root), []).append(
                speaker.label
            )
        if len(speakers) == 1:
            return next(iter(blocks))
        return "\n\n".join(f"**{', '.join(labels)}**\n\n{code}" for code, labels in blocks.items())

    return EXAMPLE_MARKER.sub(replace, content)


def spoken_list(names: list[str]) -> str:
    """`Go`, `Go and Python`, `Go, Python and Java`."""
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def stamp_pseudocode_note(content: str, family: str | list[str]) -> str:
    match = SKILL_TITLE.search(content)
    if not match:
        return content
    title = match.group(1)
    families = [family] if isinstance(family, str) else family
    languages = spoken_list([name.title() for name in families])
    note = f"> Examples are TypeScript-as-pseudocode until idiomatic {languages} versions land."
    before = content[: match.start()]
    after = content[match.end():].lstrip("\n")
    return f"{before}{title}\n\n{note}\n\n{after}"


def stamp_pseudocode_notes(files: dict[str, str], family: str | list[str]) -> None:
    """Disclaim every file that still carries TypeScript, not only the skill's entry point.

    `family` is the language the note names, or the list of them where the project is written in several
    — none of which is TypeScript, or there would be nothing to disclaim.

    Most of a skill's TypeScript lives under `resources/` or `references/`, and a skill routes the reader
    straight into those files — `cli-design` holds all 44 of its TypeScript blocks there and none in
    `SKILL.md`. A note stamped only on the entry point never reaches whoever opens the resource. The
    entry point is still stamped whenever any file in the skill carries TypeScript, so the warning is
    there before the routing decision as well as after it.
    """
    skills_with_raw_typescript: set[str] = set()
    stamped: set[str] = set()
    for path, content in list(files.items()):
        if not path.startswith("skills/"):
            continue
        skill = path.split("/", 2)[1]
        if skill in FRONTEND_INHERENT_SKILLS:
            continue
        if RAW_TYPESCRIPT_FENCE.search(content):
            skills_with_raw_typescript.add(skill)
            files[path] = stamp_pseudocode_note(content, family)
            stamped.add(path)
    for skill in skills_with_raw_typescript:
        skill_md = f"skills/{skill}/SKILL.md"
        if skill_md in files and skill_md not in stamped:
            files[skill_md] = stamp_pseudocode_note(files[skill_md], family)
