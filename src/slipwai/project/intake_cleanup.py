"""What a migration finds that was never handed to `/sail`, proposed and not moved.

`docs/prd.md` and every `specs/<feature>/spec.md` stay where they are. A loose document that reads as
requirements is proposed as an intake record. Anything else is listed for a person. Nothing is moved until
that person confirms the row and the project's own script applies it.
"""
from __future__ import annotations

import json
from pathlib import Path

PROPOSAL = ".slipwai/intake-cleanup.json"
#: Pages the factory writes. A migration does not offer to refile them.
KEPT = {
    "docs/README.md",
    "docs/getting-started.md",
    "docs/gates.md",
    "docs/skills-and-commands.md",
    "docs/whats-included.md",
    "docs/workflow.md",
    "docs/evolving-the-project.md",
    "docs/design.md",
    "docs/architecture.md",
    "docs/first-slice.md",
    "docs/adoption.md",
    "docs/convergence.md",
    "docs/change-strategy.md",
    "docs/deployment.md",
    "docs/speckit-preset.md",
    "docs/agent-harnesses.md",
    "docs/delegated-agent-safety.md",
    "docs/event-modeling-to-code.md",
    "docs/intake/README.md",
    "docs/prd.md",
}
_WORDS = ("prd", "requirement", "brief")


def _looks_like_requirements(path: Path) -> bool:
    if any(word in path.stem.lower() for word in _WORDS):
        return True
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return False
    title = next((line[2:].strip().lower() for line in head.splitlines() if line.startswith("# ")), "")
    return any(word in title for word in _WORDS)


def propose(root: Path) -> dict[str, list[dict[str, str | bool]]]:
    """Every row a person can confirm. `confirmed` starts false, and apply refuses a row that is still false."""
    rows: list[dict[str, str | bool]] = []
    if (root / "docs/prd.md").is_file():
        rows.append({"path": "docs/prd.md", "action": "keep", "destination": "",
                     "reason": "the first feature", "confirmed": False})
    specs = root / "specs"
    if specs.is_dir():
        for path in sorted(specs.glob("*/spec.md")):
            rows.append({"path": path.relative_to(root).as_posix(), "action": "keep", "destination": "",
                         "reason": "already a specification", "confirmed": False})
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in (".md", ".txt"):
                continue
            relative = path.relative_to(root).as_posix()
            if relative in KEPT or relative.startswith(("docs/intake/", "docs/adr/", "docs/event-model/",
                                                        "docs/design/")):
                continue
            if _looks_like_requirements(path):
                rows.append({"path": relative, "action": "intake",
                             "destination": f"docs/intake/{path.stem.lower()}/",
                             "reason": "reads as requirements and is not the first feature or a specification",
                             "confirmed": False})
            else:
                rows.append({"path": relative, "action": "ask", "destination": "",
                             "reason": "a document the migration will not classify", "confirmed": False})
    return {"rows": rows}


def write_proposal(root: Path) -> Path:
    """Leave the proposal where `/catch-up` reads it. Git-ignored, like the catch-up notes."""
    destination = root / PROPOSAL
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(propose(root), indent=2) + "\n", encoding="utf-8")
    return destination
