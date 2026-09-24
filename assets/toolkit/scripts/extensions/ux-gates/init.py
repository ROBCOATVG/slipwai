#!/usr/bin/env python3
"""`./init --extension ux-gates`: install the ux-ui-agent-skills kit, and put its gates in `make verify`.

plugin87's ux-ui-agent-skills (https://github.com/plugin87/ux-ui-agent-skills, MIT) is a design kit whose
useful half, for a delivery project, is its gates: scripts that measure a screen and either pass or fail
— no literal colour, size or duration outside the design tokens; and, rendered in a real browser, WCAG
contrast in light and dark across default, hover and focus, visible focus, target size, no horizontal
overflow at phone widths, and axe's roles and names. `scripts/check-ux-gates.py` runs them and is part of
`make verify` from the moment this extension is adopted; the kit's WCAG checklists and its review workflow
are files under `tools/ux-gates/` that the `AGENTS.md` block below points at.

The kit is installed, not vendored: `tools/ux-gates/` is ignored by Git (see `ignore` in `catalog.json`),
pinned by the package version below and reproducible from this one command. A checkout without it — a
fresh clone, a CI runner — is what `check-ux-gates` reports as skipped rather than passed, and
`UX_GATES_REQUIRE=1` turns that into a failure wherever the kit is expected to be present.

A project with no browser app has nothing to gate, so it is refused politely with the command that would
change that. Never fails `./init`: a missing `npx`, a failed install or an unexpected layout is reported,
not fatal. See docs/extensions.md for what every extension's `init.py` owes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guidance import record_extension, replace_block  # noqa: E402

KIT_VERSION = "2.8.0"
KIT_DIR = "tools/ux-gates"


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 3)
MARKER_BEGIN = "<!-- extension:ux-gates:begin -->"
MARKER_END = "<!-- extension:ux-gates:end -->"
GUIDANCE = f"""
{MARKER_BEGIN}
## UX gates
`{KIT_DIR}/` holds the ux-ui-agent-skills kit, and `make check-ux-gates` — part of `make verify` — runs
the gates in it that are objective: a screen either passes or it does not.

- **Always:** `{KIT_DIR}/scripts/lint_hardcodes.py` over each browser app's `src/`. A literal colour,
  pixel size or duration outside `tokens.css` fails the build; it is the rule `docs/design.md` already
  states, now measured. A justified exception carries a `ds-allow-hardcode` comment on its line.
- **Where a browser is present** (`node`, `playwright` resolvable from the project root, and Chrome or
  Playwright's own Chromium — `npx playwright install chromium`): the render gates over every `*.html`
  under each browser app's `screens/` — contrast in light and dark across default, hover and focus states,
  visible focus, target size, no overflow at 280/320/414px, and axe. A screen preview under `screens/` is
  what puts a screen under those gates; the live routes are not rendered, because the gates read files and
  the app needs its API. With no browser the render gates are reported as skipped, never as passed, and the
  gate says which browser it ran on. A gate that fails or crashes is never made to pass by editing
  `scripts/check-ux-gates.py` or anything under `{KIT_DIR}/`: fix the screen, install the browser, or
  report the gate's own words.

**Run `make check-ux-gates` before the demo stop of any slice with a screen**, and fix what it finds
rather than carrying it as a note. For the judgement the gates cannot make, the kit's checklists are files:
`{KIT_DIR}/accessibility/wcag-checklist.md` (POUR-organised, P0 first) and
`{KIT_DIR}/workflows/design-review.md` (six weighted dimensions and Nielsen's heuristics), read alongside
`skills/web-interface-guidelines`. Never state a contrast ratio you did not measure; the gates print theirs.

**Check you can reach it before you trust it.** `{KIT_DIR}/` is ignored by Git and installed by this
extension, so a fresh clone, a container or a CI runner has the pointer and not the kit. When
`{KIT_DIR}/scripts/lint_hardcodes.py` is absent, `check-ux-gates` says so and passes, and you say so too
("the gates are adopted here and not installed, so this screen is unmeasured") rather than reporting a pass.
Restore it with `./init --extension ux-gates`, which reinstalls the pinned version. Say which gates
actually ran when you report a screen as checked.

**A sub-agent does not inherit this session's run.** A fresh delegate runs `make check-ux-gates` itself
before claiming a screen passed.
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


def project_guidance() -> None:
    """Record this election and make its factory-owned guidance region current."""
    record_extension("ux-gates")
    replace_block("ux-gates", GUIDANCE)


def main() -> int:
    if not browser_apps():
        print(
            "The UX gates measure screens, and this project has no browser app to measure: nothing was "
            "installed and AGENTS.md is unchanged.\n"
            "Add one first, then adopt it here:\n"
            "  slipwai add-frontend web\n"
            "  ./init --extension ux-gates",
            file=sys.stderr,
        )
        return 0
    if shutil.which("npx") is None:
        print(
            "`npx` was not found, so the ux-ui-agent-skills kit was not installed and AGENTS.md is "
            "unchanged.\n"
            "Install Node.js, then adopt it here, which is what points the agent at it:\n"
            "  ./init --extension ux-gates",
            file=sys.stderr,
        )
        return 0
    # `check=False`: an extension may not fail `./init` (docs/extensions.md), and a raised error here would
    # also skip the pointer below, leaving the half-adopted state this script exists to avoid.
    installed = subprocess.run(
        ["npx", "-y", f"ux-ui-agent-skills@{KIT_VERSION}", "init", KIT_DIR, "--force"],
        cwd=ROOT,
        check=False,
    )
    if installed.returncode != 0:
        print(
            f"`npx ux-ui-agent-skills@{KIT_VERSION} init` exited {installed.returncode}: AGENTS.md is "
            "unchanged.\nFix what it reported, then adopt it here:\n"
            "  ./init --extension ux-gates",
            file=sys.stderr,
        )
        return 0
    if not (ROOT / KIT_DIR / "scripts/lint_hardcodes.py").is_file():
        print(
            f"The installer did not write {KIT_DIR}/scripts/lint_hardcodes.py, so AGENTS.md is unchanged.\n"
            f"This script knows ux-ui-agent-skills {KIT_VERSION}; a newer kit may lay its files out "
            "differently. Pin the version, or update this script, then:\n"
            "  ./init --extension ux-gates",
            file=sys.stderr,
        )
        return 0
    project_guidance()
    print(f"UX gates installed at {KIT_DIR}/ (ignored by Git); `make check-ux-gates` now runs them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
