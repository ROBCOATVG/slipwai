"""What `slipwai adopt` shows and asks in a terminal, and what a flag's answer does to the record.

Experimental (#74; `AGENTS.md` says what the word means here). Split from `cli_adopt`, which owns the parser
and the flags. A terminal is asked one thing — where CI runs, a fact about the forge rather than the code — and
shown the rest: every directory that builds, as a candidate nobody has answered for (ADR 0003). Which of them
is an application, what it is called, what it owns and which of its commands matter are asked by `/ground`,
with the code in front of the agent; a terminal interview that asked all of them, each with Enter as the
default, is how asset bundles and a test suite came to be wrapped as applications on the first monorepo it met.
"""
from __future__ import annotations

from pathlib import Path

from .cli_prompts import prompt_choice
from .origin import FORGES
from .services import App
from .survey import toolchain_as

NOTHING_TO_ASK = "nothing to ask on; pass --yes to accept the survey, with flags for what to change"

FORGE_DESCRIPTIONS = {
    "github": "GitHub — the gate is an Actions workflow under .github/workflows",
    "gitea": "Gitea or Forgejo — the same Actions workflow, which they run too",
    "gitlab": "GitLab — the gate is a job to include from .gitlab-ci.yml",
    "other": "Jenkins, Azure, Bitbucket, CircleCI or another — nothing is written; your CI runs the gate's command",
    "none": "no CI runs this repository — nothing is written until one does",
}


def with_override(root: Path, app: App, **changes: object) -> App:
    """The application with some fields changed, and those fields' provenance saying so.

    A spoken language brings its own toolchain, where the tree has one to bring: the survey reads a directory
    once, by the first ecosystem that recognises it, and saying the language is Python says which of the builds
    there is the application's. Leaving the toolchain as read left `kind: node` under `language: python`, and
    `kind` is what CI installs.
    """
    brought = toolchain_as(root, app.path, str(changes["language"])) if "language" in changes else None
    if brought and brought != dict(app.toolchain or {}):  # unchanged is nobody's word, and stays the tree's
        changes.setdefault("toolchain", brought)
    provenance = {**app.provenance, **{name: "overridden" for name in changes}}
    return App(
        app.name, app.path, str(changes.get("kind", app.kind)), str(changes.get("language", app.language)), None, 0,
        generated=False, commands=changes.get("commands", app.commands),  # type: ignore[arg-type]
        toolchain=changes.get("toolchain", app.toolchain),  # type: ignore[arg-type]
        purpose=changes.get("purpose", app.purpose),  # type: ignore[arg-type]
        structure=changes.get("structure", app.structure),  # type: ignore[arg-type]
        provenance=provenance,
    )


def candidate_table(candidates: list[dict]) -> str:
    """The buildable directories the survey found, shown as facts rather than asked about one at a time."""
    width = max((len(row["path"]) for row in candidates), default=1)
    language = max((len(row["language"]) for row in candidates), default=1)
    lines = []
    for row in candidates:
        answered = sum(1 for command in (row.get("commands") or {}).values() if command)
        total = len(row.get("commands") or {})
        lines.append(
            f"  {row['path']:<{width}}  {row['language']:<{language}}  from {row['evidence']}"
            f"  ({answered} of {total} targets have a command)"
        )
    return "\n".join(lines)


def shape(candidates: list[dict], proposal: dict[str, str | None]) -> dict:
    """The intro (ADR 0003): what the survey found, shown; and the one question a terminal can answer.

    Everything else this used to ask — which of these is an application, what it is called, what it is for,
    which of its commands matter, where the schema and the infrastructure live, how a change reaches
    production, why the work is happening — needs the code read, or needs a conversation. None of that is
    what a terminal is good at, and the record now has somewhere to keep an unanswered question, so they go
    to the agent instead of being answered with Enter.
    """
    print(
        "Adopt the delivery method here (experimental). The survey read the tree; what it\n"
        "found is below. Nothing here is recorded as an application yet: which of these the gate should hold,\n"
        "what each is called and what it owns are questions the code answers, and the agent asks them with the\n"
        "code in front of it. This asks the one thing the tree cannot settle on its own."
    )
    one = len(candidates) == 1
    print(f"\n{len(candidates)} director{'y' if one else 'ies'} that build{'s' if one else ''}:")
    print(candidate_table(candidates))
    print()
    forge = prompt_choice(
        "CI forge", list(FORGES), str(proposal["forge"]), lambda f: FORGE_DESCRIPTIONS[f],
        question="Where does this repository's CI run? (decides what shape the gate's CI configuration can "
        "take, which is a fact about your forge and not about your code)",
    )
    return {"forge": forge, "provenance": "confirmed" if forge == proposal["forge"] else "overridden"}
