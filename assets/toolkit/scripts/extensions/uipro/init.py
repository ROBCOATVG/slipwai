#!/usr/bin/env python3
"""`./init --extension uipro`: install the ui-ux-pro-max skill into `skills/`, and point the agent at it.

UI/UX Pro Max (https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) is a design-system generator that
runs offline: a Python search over local CSV data — styles, palettes, type pairings, chart types, UX rules
and stack notes keyed by product type — that answers "what should this product's screens look like" with
a coherent system rather than a guess. It ships as a skill with its own installer, and the installer's
job is to write fifteen per-harness copies; this script asks it for the one harness-neutral copy instead,
and puts that in the project's root `skills/`, which is the canonical catalogue `make agents` projects into
every harness and `check-agents` holds the projections to. The copy is ignored by Git (see `ignore` in
`catalog.json`): it is an installed tool, pinned by the CLI version below and reproducible from this one
command, not source this project maintains — the same footing as CodeGraph's index.

Only the `ui-ux-pro-max` skill is taken. The installer also writes `ui-styling` (Tailwind and shadcn, which
the generated browser app deliberately does not use), `design-system`, `design`, `brand`, `banner-design`
and `slides`, none of which is about a delivery project's screens.

A project with no browser app has nothing for it to design, so it is refused politely with the command
that would change that. Never fails `./init`: a missing CLI, a failed install or an unexpected layout is
reported, not fatal. See docs/extensions.md for what every extension's `init.py` owes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guidance import record_extension, replace_block  # noqa: E402

CLI_VERSION = "2.15.0"
SKILL = "ui-ux-pro-max"
INSTALLED_AT = ".agents/skills"  # where `uipro init --ai universal` writes, and the path its text names


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 3)
MARKER_BEGIN = "<!-- extension:uipro:begin -->"
MARKER_END = "<!-- extension:uipro:end -->"
GUIDANCE = f"""
{MARKER_BEGIN}
## UI/UX Pro Max
`skills/{SKILL}/` is a design-system generator that runs offline: a search over local data that answers
which pattern, style, palette, type pairing, chart types and UX rules fit a product of this kind. Reach for
it **before the first screen of a slice that `docs/design.md` has no decision for**, and for one focused
question — a component, a chart, a stack rule — with a single `--domain` or `--stack` search. Read the
skill's own `SKILL.md` for the query contract; the short form is:

    python3 skills/{SKILL}/scripts/search.py "<product type> <industry> <keywords>" --design-system \\
        -p "<project name>" --persist --output-dir .

`--persist` writes `design-system/<slug>/MASTER.md`. **Commit it.** It is the evidence the decision was
made from, and the input the browser app's `tokens.css` is filled from — but it is not the decision.
`docs/design.md` stays the page every slice with a screen reads first: write what was chosen and why
there, in the same commit as the tokens, link the `MASTER.md` it came from, and where the two disagree the
page wins. Then take the plan through `skills/frontend-design`'s second pass — the review against the
brief for defaults that would appear whatever the product — before writing any code.

**Check you can reach it before you trust it.** The search is standard-library Python 3 and travels with
the skill, so the only two ways it is unreachable are a checkout without the skill and a machine without
Python. `skills/{SKILL}/` is ignored by Git and installed by this extension, so a fresh clone, a
container or a CI runner has the pointer and not the tool: when `skills/{SKILL}/scripts/search.py` is
absent, or `command -v python3` fails, say so in as many words ("the extension is adopted here, the skill
is not installed, so this is a decision from `docs/design.md` and `skills/frontend-design` alone") and work
as a project without it would. Restore it with `./init --extension uipro`, which reinstalls the pinned
version. Say which route you used when you report a design decision.

**A sub-agent does not inherit this session's checks.** A fresh delegate looks for the script itself
before it claims to have searched, and says the skill is unavailable rather than inventing a palette.
{MARKER_END}
"""


def browser_apps() -> list[str]:
    """The deployables that declare a `frontend` capability and are still here."""
    manifest = ROOT / "project.json"
    if not manifest.is_file():
        return []
    deployables = json.loads(manifest.read_text()).get("deployables")
    if not isinstance(deployables, dict):
        return []
    return [
        str(deployable.get("path"))
        for deployable in deployables.values()
        if isinstance(deployable, dict)
        and "frontend" in deployable.get("capabilities", [])
        and (ROOT / str(deployable.get("path", ""))).is_dir()
    ]


def installer() -> list[str] | None:
    """The installed CLI when there is one, otherwise the pinned package through `npx`, otherwise nothing."""
    if shutil.which("uipro") is not None:
        return ["uipro"]
    if shutil.which("npx") is not None:
        return ["npx", "-y", f"ui-ux-pro-max-cli@{CLI_VERSION}"]
    return None


def relocated(text: str) -> str:
    """The skill's own text names the path its installer wrote it to; here it lives at the root."""
    return text.replace(f"{INSTALLED_AT}/{SKILL}", f"skills/{SKILL}")


def with_capability(skill_md: str) -> str:
    """Declare `capabilities: frontend`, so `check-agents` names the skill if the browser app ever goes."""
    if not skill_md.startswith("---\n"):
        return skill_md
    front, separator, rest = skill_md[4:].partition("\n---\n")
    if not separator or "\ncapabilities:" in f"\n{front}":
        return skill_md
    return f"---\n{front}\ncapabilities: frontend\n---\n{rest}"


def install(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    for page in destination.rglob("*.md"):
        page.write_text(relocated(page.read_text()))
    skill_md = destination / "SKILL.md"
    skill_md.write_text(with_capability(skill_md.read_text()))


def reproject() -> None:
    """`./init` projected `skills/` before this ran; the new skill has to reach the harness too.

    `./init` names the harness it chose in `SLIPWAI_INTEGRATION`; run by hand later, the projector reads
    the one Spec Kit recorded. Either way a failure is reported by the projector and `make agents` retries.
    """
    projector = ROOT / "scripts/agents/project.py"
    if not projector.is_file():
        return
    chosen = os.environ.get("SLIPWAI_INTEGRATION", "")
    subprocess.run([sys.executable, str(projector), *([chosen] if chosen else [])], cwd=ROOT, check=False)


def project_guidance() -> None:
    """Record this election and make its factory-owned guidance region current."""
    record_extension("uipro")
    replace_block("uipro", GUIDANCE)


def main() -> int:
    if not browser_apps():
        print(
            "UI/UX Pro Max designs screens, and this project has no browser app for it to design: nothing "
            "was installed and AGENTS.md is unchanged.\n"
            "Add one first, then adopt it here:\n"
            "  slipwai add-frontend web\n"
            "  ./init --extension uipro",
            file=sys.stderr,
        )
        return 0
    command = installer()
    if command is None:
        print(
            "Neither the `uipro` CLI nor `npx` was found: nothing was installed and AGENTS.md is unchanged.\n"
            "Install one:\n"
            f"  npm install -g ui-ux-pro-max-cli@{CLI_VERSION}\n"
            "Then adopt it here, which is what points the agent at it:\n"
            "  ./init --extension uipro",
            file=sys.stderr,
        )
        return 0
    with tempfile.TemporaryDirectory() as staging:
        # `check=False`: an extension may not fail `./init` (docs/extensions.md), and a raised error here
        # would also skip the pointer below, leaving the half-adopted state this script exists to avoid.
        installed = subprocess.run([*command, "init", "--ai", "universal", "--force"], cwd=staging, check=False)
        if installed.returncode != 0:
            print(
                f"`{' '.join(command)} init` exited {installed.returncode}: AGENTS.md is unchanged.\n"
                "Fix what it reported, then adopt it here:\n"
                "  ./init --extension uipro",
                file=sys.stderr,
            )
            return 0
        source = Path(staging) / INSTALLED_AT / SKILL
        if not (source / "SKILL.md").is_file():
            print(
                f"The installer did not write {INSTALLED_AT}/{SKILL}/SKILL.md, so nothing was copied and "
                "AGENTS.md is unchanged.\n"
                f"This script knows ui-ux-pro-max-cli {CLI_VERSION}; a newer CLI may lay its files out "
                "differently. Pin the version, or update this script, then:\n"
                "  ./init --extension uipro",
                file=sys.stderr,
            )
            return 0
        install(source, ROOT / "skills" / SKILL)
    project_guidance()
    reproject()
    print(f"UI/UX Pro Max installed at skills/{SKILL}/ (ignored by Git; `./init --extension uipro` reinstalls it).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
