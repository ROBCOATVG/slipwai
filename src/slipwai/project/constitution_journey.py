"""The constitution as a journey: the profile's constitution template, adapted to where an adopted repository stands.

A generated project ratifies the whole floor on day one, because it starts at the top of every ladder. A
repository the method was installed around (brownfield adoption; experimental as `AGENTS.md` defines the
word) does not, and a constitution that says "trunk MUST be releasable at every commit" over a repository on
long-lived branches is a fiction the gate would then hold. So the template an adopted repository drafts from is
the profile's own with a difference: each principle whose axis on the convergence map stands below the rung it
comes into force at is written as **a target, not yet in force** — the rung this repository stands on, the rung
the principle needs, what holds here today (a placeholder only this repository can fill), and the principle as
it will read when in force, kept as a quotation. A marker names the rung, so `check-constitution` can hold the
constitution to the map: a marker at another rung is drift, and a principle claimed in force while the map says
otherwise is the fiction this exists to prevent. When a row reaches its rung, the marker comes out, the
quotation becomes the text, and the check asks for the principle in full.

`JOURNEY` is the table the gate script carries too (`assets/toolkit/scripts/check-constitution.py`); a test
holds the two copies equal.
"""
from __future__ import annotations

import re

from ..assets import PROFILE_ROOT
from ..convergence import BY_KEY, Row

# Requirement key -> (axis on the map, the rung the principle comes into force at, the template heading's words).
JOURNEY: dict[str, tuple[str, str, str]] = {
    "trunk-based-integration": ("integration", "trunk", "Continuous Integration on Trunk"),
    "one-path-to-production": ("path-to-production", "one-path", "One Path to Production"),
    "build-once-deploy-is-not-release": ("path-to-production", "pipeline-decides", "Build Once"),
    "fast-feedback": ("safety-net", "fast", "Fast Feedback"),
    "acceptance-driven-testing": ("safety-net", "tests-pass", "Acceptance-Driven Development"),
    "hexagonal-boundary": ("structure", "hexagonal", "Hexagonal Architecture"),
    "ubiquitous-language-and-domain-types": ("structure", "typed", "Ubiquitous Language"),
    "strict-typing": ("structure", "typed", "Technology Stack"),
}


def journey_rows(rows: list[Row]) -> dict[str, tuple[str, str, str]]:
    """The requirements that are targets here rather than principles in force: key -> (axis, rung now, in force at)."""
    standing = {row["axis"]: row["rung"] for row in rows if isinstance(row, dict)}
    targets = {}
    for key, (axis_key, in_force, _) in JOURNEY.items():
        axis = BY_KEY[axis_key]
        rung = standing.get(axis_key, axis.rungs[0])
        if axis.index(rung) < axis.index(in_force):
            targets[key] = (axis_key, rung, in_force)
    return targets


def journey_preamble(key: str, axis_key: str, rung: str, in_force: str) -> str:
    """What a target principle says before the quoted text of the principle itself."""
    axis = BY_KEY[axis_key]
    return f"""<!-- journey: {key} at {rung} -->
**A target, not yet in force.** On the *{axis.title.lower()}* ladder this repository stands at `{rung}`
(`docs/convergence.md`). This principle comes into force at `{in_force}`; a generated project sits at
`{axis.target}`. Until it does, what holds here is written below, and the map's *planned* column names the slice
that climbs.

- [What holds here today for this principle, in a sentence or two: the practice as it is, not as it should be.]
- [The next rung, and what has to be true for it: name the slice planned to reach it, or say none is planned yet.]

When in force, this principle reads:
"""


def quoted(body: str) -> str:
    return "\n".join(f"> {line}" if line.strip() else ">" for line in body.strip("\n").splitlines()) + "\n"


def journey_template(profile: str, rows: list[Row]) -> str:
    """The profile's constitution template with every target principle written as a target."""
    path = PROFILE_ROOT / f"{profile}/.specify/presets/{profile}/templates/constitution-template.md"
    text = path.read_text()
    targets = journey_rows(rows)
    for key, (axis_key, rung, in_force) in targets.items():
        words = JOURNEY[key][2]
        if key == "strict-typing":
            # Not a principle of its own: the typing bullets under Technology Stack become the target.
            bullets = re.compile(r"- Strict type checking MUST[\s\S]*?(?=\n- \*\*Schema-first|\n- Identifiers)")
            match = bullets.search(text)
            if match:
                text = text[:match.start()] + journey_preamble(key, axis_key, rung, in_force) + "\n" + quoted(
                    match.group(0)
                ) + text[match.end():]
            continue
        section = re.compile(rf"(^### [^\n]*{re.escape(words)}[^\n]*\n)([\s\S]*?)(?=^### |^## |\Z)", re.MULTILINE)
        match = section.search(text)
        if match is None:
            continue
        heading, body = match.group(1), match.group(2)
        text = text[:match.start()] + heading + "\n" + journey_preamble(key, axis_key, rung, in_force) + "\n" + quoted(
            body
        ) + "\n" + text[match.end():]
    note = (
        "\n<!-- This template was adapted by slipwai adopt to where this repository stands (docs/convergence.md):\n"
        "     a principle marked `journey:` is a target, not yet in force, and check-constitution holds it to the\n"
        "     map. Experimental, with the rest of adoption. -->\n"
    ) if targets else ""
    return text.rstrip("\n") + "\n" + note
