#!/usr/bin/env python3
"""Run the adopted UX gates over every browser app, and fail when one of them does.

The gates are plugin87's ux-ui-agent-skills kit, installed under `tools/ux-gates/` by `./init --extension
ux-gates`. Two kinds run here. The file gate always: `lint_hardcodes.py` over each browser app's `src/`,
which fails on a literal colour, pixel size or duration that is not a token — the rule `docs/design.md`
states, measured. The render gates when they can: over every `*.html` under each browser app's `screens/`,
in a real headless browser, contrast in light and dark across default, hover and focus, visible focus,
target size, overflow at phone widths, and axe. The kit's own scripts skip with a line when Playwright is
not resolvable, and this gate reports that as skipped, never as passed.

Three states are not failures, and each is said out loud. Not adopted: the extension is optional, and a
project that never asked for it has nothing to run. Adopted but not installed here: `tools/ux-gates/` is
ignored by Git, so a fresh clone or a CI runner has the election and not the kit — reported as skipped,
or as a failure when `UX_GATES_REQUIRE=1`, which is what to set wherever the kit is expected. No browser
app: nothing to measure.

Standard library only, like every gate script here; the kit's scripts are run as subprocesses.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KEY = "ux-gates"
KIT = "tools/ux-gates"
# Directory-wide render gates, then per-file ones; each with the flags that make light and dark both count.
DIRECTORY_GATES = (
    ("verify_responsive.mjs", ()),
    ("verify_target_size.mjs", ()),
    ("measure_render.mjs", ()),
    ("measure_render.mjs", ("--dark",)),
)
FILE_GATES = (
    ("axe_audit.mjs", ()),
    ("axe_audit.mjs", ("--dark",)),
    ("verify_states.mjs", ()),
    ("verify_states.mjs", ("--dark",)),
)


def project_root(script: Path, depth: int) -> Path:
    """The nearest parent holding `project.json`, with a source-tree fallback."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)


def adopted() -> bool:
    """Elected in the committed record, or marked in `AGENTS.md` by a project older than the record."""
    record = ROOT / ".slipwai/extensions.json"
    if record.is_file():
        try:
            document = json.loads(record.read_text())
        except ValueError:
            document = {}
        if KEY in (document.get("extensions") or []):
            return True
    agents = ROOT / "AGENTS.md"
    return agents.is_file() and f"<!-- extension:{KEY}:begin -->" in agents.read_text()


def browser_apps() -> list[Path]:
    manifest = ROOT / "project.json"
    if not manifest.is_file():
        return []
    deployables = json.loads(manifest.read_text()).get("deployables")
    if not isinstance(deployables, dict):
        return []
    return [
        ROOT / str(deployable["path"])
        for deployable in deployables.values()
        if isinstance(deployable, dict)
        and "frontend" in deployable.get("capabilities", [])
        and (ROOT / str(deployable.get("path", ""))).is_dir()
    ]


def say(line: str) -> None:
    """Flushed, so this script's lines land in order with the kit's, which write straight to the terminal."""
    print(line, flush=True)


def run(script: str, *arguments: str) -> tuple[int, bool]:
    """One kit script, from the kit's own directory so its relative imports resolve. Its output is passed
    through, and read for the one word the kit uses when a gate could not open a browser: a skipped gate
    exits 0 upstream, and this script refuses to count that as a pass."""
    kit = ROOT / KIT
    interpreter = [sys.executable] if script.endswith(".py") else ["node"]
    environment = dict(os.environ)
    if environment.get("UX_GATES_REQUIRE") == "1":
        environment["DS_REQUIRE_BROWSER"] = "1"  # the kit's own switch for the same demand
    completed = subprocess.run(
        [*interpreter, str(kit / "scripts" / script), *arguments],
        cwd=kit, env=environment, check=False, text=True, capture_output=True,
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    sys.stdout.flush()
    return completed.returncode, "SKIPPED" in completed.stdout


def main() -> int:
    if not adopted():
        say("check-ux-gates: not adopted (./init --extension ux-gates); nothing to check")
        return 0
    kit = ROOT / KIT
    required = os.environ.get("UX_GATES_REQUIRE") == "1"
    if not (kit / "scripts/lint_hardcodes.py").is_file():
        say(
            f"check-ux-gates: adopted, but {KIT}/ is not installed in this checkout — "
            + ("REQUIRED, FAILING" if required else "SKIPPED, not passed")
            + "; `./init --extension ux-gates` installs it"
        )
        return 1 if required else 0
    apps = browser_apps()
    if not apps:
        say("check-ux-gates: no browser app to measure")
        return 0
    failures: list[str] = []
    skipped = 0
    for app in apps:
        relative = app.relative_to(ROOT).as_posix()
        source = app / "src"
        if source.is_dir():
            say(f"check-ux-gates: {relative}/src — literal values outside the tokens")
            if run("lint_hardcodes.py", str(source))[0] != 0:
                failures.append(f"{relative}/src carries literal values the tokens should own")
        screens = sorted((app / "screens").glob("*.html")) if (app / "screens").is_dir() else []
        if not screens:
            say(f"check-ux-gates: {relative}/screens/ has no previews; the render gates have nothing to open")
            continue
        if shutil.which("node") is None:
            say(f"check-ux-gates: {relative}/screens/ — node not found, render gates SKIPPED, not passed")
            skipped += len(DIRECTORY_GATES) + len(FILE_GATES) * len(screens)
            continue
        say(f"check-ux-gates: {relative}/screens/ — {len(screens)} preview(s) through the render gates")
        gates = [(script, flags, str(app / "screens")) for script, flags in DIRECTORY_GATES]
        gates += [(script, flags, str(screen)) for screen in screens for script, flags in FILE_GATES]
        for script, flags, target in gates:
            status, was_skipped = run(script, target, *flags)
            if status != 0:
                failures.append(f"{Path(target).relative_to(ROOT).as_posix()}: {script} {' '.join(flags)}".rstrip())
            elif was_skipped:
                skipped += 1
    if failures:
        say("check-ux-gates: FAILED\n  - " + "\n  - ".join(failures))
        return 1
    if skipped:
        say(
            f"check-ux-gates: passed where a gate could run; {skipped} render gate(s) SKIPPED, not passed — "
            "Playwright and a browser are not resolvable from the project root"
        )
        return 1 if required else 0
    say("check-ux-gates: every gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
