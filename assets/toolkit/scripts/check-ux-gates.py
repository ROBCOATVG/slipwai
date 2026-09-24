#!/usr/bin/env python3
"""Run the adopted UX gates over every browser app, and fail when one of them does.

The gates are plugin87's ux-ui-agent-skills kit, installed under `tools/ux-gates/` by `./init --extension
ux-gates`. Two kinds run here. The file gate always: `lint_hardcodes.py` over each browser app's `src/`,
which fails on a literal colour, pixel size or duration that is not a token — the rule `docs/design.md`
states, measured. The render gates when they can: over every `*.html` under each browser app's `screens/`,
in a real headless browser, contrast in light and dark across default, hover and focus, visible focus,
target size, overflow at phone widths, and axe. Which browser is asked once, before any of them runs: the
kit launches Chrome (`channel: 'chrome'`), and in 2.8.0 two of its scripts — `verify_responsive.mjs` and
`verify_target_size.mjs` — crash where Chrome is not installed instead of falling back to Playwright's own
Chromium the way the other three do. So where Chrome is absent and that Chromium opens, every render gate
runs with a Node preload that retries a launch without the channel; where no browser opens, or Playwright
is not resolvable, the render gates are reported as skipped, never as passed, and a gate that still could
not open a browser is reported the same way rather than as a failure.

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
import tempfile
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
# Which browser the kit's scripts can open, Playwright resolved from the kit's directory the way its scripts resolve
# it from `scripts/` beneath — the same `node_modules` chain — and answered in one word: `chrome` (the channel the kit asks for), `bundled` (Playwright's own Chromium, which
# `npx playwright install chromium` puts in place), `none`, or `no-playwright`.
PROBE = """
let chromium;
try { ({ chromium } = await import("playwright")); }
catch { console.log("no-playwright"); process.exit(0); }
if (!chromium) { console.log("no-playwright"); process.exit(0); }
for (const [word, options] of [["chrome", { channel: "chrome" }], ["bundled", {}]]) {
  try { const browser = await chromium.launch(options); await browser.close(); console.log(word); process.exit(0); }
  catch {}
}
console.log("none");
"""
# What every render gate is started with where only the bundled Chromium opens: the same Playwright the kit imports,
# its `chromium.launch` retried without the channel when the channel is what failed. A CommonJS preload runs before
# an ES module entry, and the kit's `import('playwright')` returns the same object this patched.
PRELOAD = """
const { createRequire } = require("node:module");
const playwright = createRequire({scripts})("playwright");
const launch = playwright.chromium.launch.bind(playwright.chromium);
playwright.chromium.launch = async (options = {}) => {
  try { return await launch(options); }
  catch (error) {
    if (!options.channel) throw error;
    const { channel, ...rest } = options;
    return launch(rest);
  }
};
"""
# The words Playwright's launch failure carries, on stderr, when a kit script could not open a browser.
LAUNCH_FAILED = "browserType.launch"


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


def browser() -> str:
    """Which browser the render gates can open, asked once: `chrome`, `bundled`, `none` or `no-playwright`. A probe
    that could not answer — node failing before the question — is `none`, with what it said on stderr."""
    completed = subprocess.run(["node", "--input-type=module", "-e", PROBE], cwd=ROOT / KIT, check=False,
                               text=True, capture_output=True)
    word = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    if completed.returncode == 0 and word in ("chrome", "bundled", "none", "no-playwright"):
        return word
    sys.stderr.write(completed.stderr)
    return "none"


def run(script: str, *arguments: str, preload: Path | None = None) -> str:
    """One kit script, from the kit's own directory so its relative imports resolve, started with the preload where
    one is given. Its output is passed through, and the verdict is one of three words: `passed`, `failed`, or
    `skipped` — the kit's own word when a gate could not open a browser, which exits 0 upstream and is refused as
    a pass here, or a launch failure on stderr, which is the same fact told as a crash."""
    kit = ROOT / KIT
    interpreter = [sys.executable] if script.endswith(".py") else ["node"]
    if preload is not None and script.endswith(".mjs"):
        interpreter += ["--require", str(preload)]
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
    if completed.returncode != 0 and LAUNCH_FAILED in completed.stderr:
        say(f"check-ux-gates: {script} could not open a browser — SKIPPED, not passed")
        return "skipped"
    if completed.returncode != 0:
        return "failed"
    return "skipped" if "SKIPPED" in completed.stdout else "passed"


def render_gates(app: Path, screens: list[Path], opened: str, preload: Path | None) -> tuple[list[str], int]:
    """Every render gate over one app's previews, or all of them counted as skipped where no browser opens."""
    relative = app.relative_to(ROOT).as_posix()
    gates = [(script, flags, str(app / "screens")) for script, flags in DIRECTORY_GATES]
    gates += [(script, flags, str(screen)) for screen in screens for script, flags in FILE_GATES]
    if opened in ("none", "no-playwright"):
        why = ("playwright is not resolvable from the kit" if opened == "no-playwright"
               else "no browser opens — neither Chrome nor Playwright's Chromium (`npx playwright install chromium`)")
        say(f"check-ux-gates: {relative}/screens/ — {why}; {len(gates)} render gate(s) SKIPPED, not passed")
        return [], len(gates)
    say(f"check-ux-gates: {relative}/screens/ — {len(screens)} preview(s) through the render gates"
        + (" on Playwright's Chromium, Chrome not being installed" if opened == "bundled" else ""))
    failures, skipped = [], 0
    for script, flags, target in gates:
        verdict = run(script, target, *flags, preload=preload)
        if verdict == "failed":
            failures.append(f"{Path(target).relative_to(ROOT).as_posix()}: {script} {' '.join(flags)}".rstrip())
        elif verdict == "skipped":
            skipped += 1
    return failures, skipped


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
    opened: str | None = None  # asked the first time a preview needs a browser, and once
    with tempfile.TemporaryDirectory() as scratch:
        preload = Path(scratch) / "preload.cjs"
        preload.write_text(PRELOAD.replace("{scripts}", json.dumps(str(kit / "scripts/preload.cjs"))))
        for app in apps:
            relative = app.relative_to(ROOT).as_posix()
            source = app / "src"
            if source.is_dir():
                say(f"check-ux-gates: {relative}/src — literal values outside the tokens")
                if run("lint_hardcodes.py", str(source)) == "failed":
                    failures.append(f"{relative}/src carries literal values the tokens should own")
            screens = sorted((app / "screens").glob("*.html")) if (app / "screens").is_dir() else []
            if not screens:
                say(f"check-ux-gates: {relative}/screens/ has no previews; the render gates have nothing to open")
                continue
            if shutil.which("node") is None:
                say(f"check-ux-gates: {relative}/screens/ — node not found, render gates SKIPPED, not passed")
                skipped += len(DIRECTORY_GATES) + len(FILE_GATES) * len(screens)
                continue
            opened = browser() if opened is None else opened
            failed, unopened = render_gates(app, screens, opened, preload if opened == "bundled" else None)
            failures += failed
            skipped += unopened
    if failures:
        say("check-ux-gates: FAILED\n  - " + "\n  - ".join(failures))
        return 1
    if skipped:
        say(f"check-ux-gates: passed where a gate could run; {skipped} render gate(s) SKIPPED, not passed — "
            "each says above what it could not open")
        return 1 if required else 0
    say("check-ux-gates: every gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
