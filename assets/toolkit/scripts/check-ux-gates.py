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

What it costs is per screen, and that is the part a project feels. Each per-file gate launches its own
browser, four of them per preview, so the time is linear in `screens/` and every UX slice adds to it — a
project with 225 previews spent 24 minutes here, two at a time on a two-processor runner. Three switches
spread that, and none changes what passing means:

- `UX_GATES_JOBS=<n>` runs that many gates at once; the default is one per processor.
- `UX_GATES_SHARD=<k>/<n>` runs every n-th gate from the k-th, so n CI jobs cover every gate exactly once
  between them. `verify.yml`'s `ux-gates` matrix, which the extension writes, is the one that sets it.
- `UX_GATES_SINCE=<ref>` renders only the previews whose own file, or a local stylesheet they link or
  `@import`, changed since the merge base with `<ref>` (the working tree counts), and the directory gates
  only for an app with such a preview. Every preview again when this script, the extension, the lockfile
  or `verify.yml` moved, or when Git cannot answer. A pull request sets it; `main` never does, because
  `main` deploys and a browser upgrade arrives without a diff. The file gate over `src/` always runs.

Standard library only, like every gate script here; the kit's scripts are run as subprocesses.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

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
FILE_GATE = "lint_hardcodes.py"
# A local stylesheet a preview links or imports, which is what `UX_GATES_SINCE` follows from a changed file to
# the previews that render it. A reference with a scheme, protocol-relative or rooted at `/` is not a file here.
LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
HREF = re.compile(r"""\bhref\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
STYLESHEET = re.compile(r"""\brel\s*=\s*["']?[^"'>]*\bstylesheet\b""", re.IGNORECASE)
IMPORT = re.compile(r"""@import\s+(?:url\(\s*)?["']?([^"')\s;]+)""", re.IGNORECASE)
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


OUTPUT = threading.Lock()


def say(line: str) -> None:
    """Flushed and whole, so this script's lines never interleave with a gate's output written beside them."""
    with OUTPUT:
        print(line, flush=True)


class Gate(NamedTuple):
    """One run of one kit script: over an app's `src/`, its `screens/` directory, or one preview in it. A tuple
    rather than a dataclass, which looks its module up in `sys.modules`: a project's test that loads this file with
    `importlib` and does not register it there would crash on the class instead of testing it."""

    app: Path
    script: str
    flags: tuple[str, ...]
    target: Path

    @property
    def render(self) -> bool:
        return self.script.endswith(".mjs")

    def label(self) -> str:
        return f"{self.target.relative_to(ROOT).as_posix()}: {self.script} {' '.join(self.flags)}".rstrip()


def screens_of(app: Path) -> list[Path]:
    return sorted((app / "screens").glob("*.html")) if (app / "screens").is_dir() else []


def planned(apps: list[Path]) -> list[Gate]:
    """Every gate over every app, in the order a whole run takes them."""
    gates: list[Gate] = []
    for app in apps:
        if (app / "src").is_dir():
            gates.append(Gate(app, FILE_GATE, (), app / "src"))
        screens = screens_of(app)
        if not screens:
            say(f"check-ux-gates: {app.relative_to(ROOT).as_posix()}/screens/ has no previews; "
                "the render gates have nothing to open")
            continue
        gates += [Gate(app, script, flags, app / "screens") for script, flags in DIRECTORY_GATES]
        gates += [Gate(app, script, flags, screen) for screen in screens for script, flags in FILE_GATES]
    return gates


def shard(gates: list[Gate], spec: str) -> list[Gate] | None:
    """Every n-th gate from the k-th, for `k/n`; None for a spec that is not one."""
    found = re.fullmatch(r"(\d+)/(\d+)", spec)
    if not found or not 1 <= int(found.group(1)) <= int(found.group(2)):
        return None
    index, count = int(found.group(1)), int(found.group(2))
    return [gate for position, gate in enumerate(gates) if position % count == index - 1]


def git(*arguments: str) -> str | None:
    completed = subprocess.run(["git", *arguments], cwd=ROOT, check=False, text=True, capture_output=True)
    return completed.stdout if completed.returncode == 0 else None


def changed_since(ref: str) -> set[str] | None:
    """What differs from the merge base with `ref`, working tree and untracked files included, relative to
    this project; None when Git cannot say, or when something every preview depends on is among it."""
    base = git("merge-base", ref, "HEAD")
    diff = git("diff", "--name-only", "--relative", base.strip()) if base else None
    untracked = git("ls-files", "--others", "--exclude-standard")
    if diff is None or untracked is None:
        say(f"check-ux-gates: UX_GATES_SINCE={ref} — Git cannot name a merge base, so every preview is in scope")
        return None
    changed = set(diff.split()) | set(untracked.split())
    here = Path(__file__).resolve()
    everything = {here, here.parent / "extensions/ux-gates/init.py", ROOT / "package-lock.json",
                  ROOT / ".github/workflows/verify.yml"}
    moved = sorted(path.relative_to(ROOT).as_posix() for path in everything
                   if path.is_relative_to(ROOT) and path.relative_to(ROOT).as_posix() in changed)
    if moved:
        say(f"check-ux-gates: UX_GATES_SINCE={ref} — {', '.join(moved)} changed, so every preview is in scope")
        return None
    return changed


def local(reference: str, beside: Path) -> Path | None:
    reference = reference.split("?")[0].split("#")[0]
    if not reference or reference.startswith(("/", "data:")) or re.match(r"^[a-z][a-z0-9+.-]*:", reference, re.I):
        return None
    return (beside / reference).resolve()


def styles_of(page: Path) -> set[Path]:
    """Every local stylesheet a preview links or imports, and every one those import in turn."""
    text = page.read_text(errors="replace")
    pending = [local(href.group(1), page.parent) for link in LINK.findall(text) if STYLESHEET.search(link)
               for href in [HREF.search(link)] if href]
    pending += [local(reference, page.parent) for reference in IMPORT.findall(text)]
    found: set[Path] = set()
    while pending:
        sheet = pending.pop()
        if sheet is None or sheet in found:
            continue
        found.add(sheet)
        if sheet.is_file():
            imported = IMPORT.findall(sheet.read_text(errors="replace"))
            pending += [local(reference, sheet.parent) for reference in imported]
    return found


def scoped(gates: list[Gate], changed: set[str]) -> list[Gate]:
    """The gates a change can move: every file gate, a preview's gates where it or a stylesheet it renders
    with changed, and an app's directory gates where any of its previews is in scope or one was removed."""
    def relative(path: Path) -> str:
        return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else ""

    previews = {gate.target for gate in gates if gate.render and gate.target.is_file()}
    touched = {page for page in previews if {relative(page), *map(relative, styles_of(page))} & changed}
    moved_apps = {page.parent.parent for page in touched}
    moved_apps |= {gate.app for gate in gates
                   if any(path.startswith(relative(gate.app / "screens") + "/") for path in changed)}
    return [gate for gate in gates if not gate.render or gate.target in touched
            or (gate.target.is_dir() and gate.app in moved_apps)]




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


def run(gate: Gate, preload: Path | None = None) -> str:
    """One kit script, from the kit's own directory so its relative imports resolve, started with the preload where
    one is given. Its output is passed through whole once it exits, and the verdict is one of three words:
    `passed`, `failed`, or `skipped` — the kit's own word when a gate could not open a browser, which exits 0
    upstream and is refused as a pass here, or a launch failure on stderr, which is the same fact told as a crash."""
    kit = ROOT / KIT
    interpreter = [sys.executable] if gate.script.endswith(".py") else ["node"]
    if preload is not None and gate.render:
        interpreter += ["--require", str(preload)]
    environment = dict(os.environ)
    if environment.get("UX_GATES_REQUIRE") == "1":
        environment["DS_REQUIRE_BROWSER"] = "1"  # the kit's own switch for the same demand
    completed = subprocess.run(
        [*interpreter, str(kit / "scripts" / gate.script), str(gate.target), *gate.flags],
        cwd=kit, env=environment, check=False, text=True, capture_output=True,
    )
    with OUTPUT:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        sys.stdout.flush()
    if completed.returncode != 0 and LAUNCH_FAILED in completed.stderr:
        say(f"check-ux-gates: {gate.script} could not open a browser — SKIPPED, not passed")
        return "skipped"
    if completed.returncode != 0:
        return "failed"
    return "skipped" if "SKIPPED" in completed.stdout else "passed"


def jobs() -> int:
    try:
        return max(1, int(os.environ.get("UX_GATES_JOBS", "")))
    except ValueError:
        return os.cpu_count() or 1


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
    gates = planned(apps)
    whole = len(gates)
    spec = os.environ.get("UX_GATES_SHARD", "").strip()
    if spec:
        sharded = shard(gates, spec)
        if sharded is None:
            say(f"check-ux-gates: UX_GATES_SHARD={spec} is not k/n with 1 <= k <= n — FAILING rather than guessing; "
                "leave it unset to run every gate")
            return 1
        gates = sharded
        say(f"check-ux-gates: shard {spec} — {len(gates)} of {whole} gate(s)")
    since = os.environ.get("UX_GATES_SINCE", "").strip()
    changed = changed_since(since) if since else None
    unchanged = 0
    if changed is not None:
        kept = scoped(gates, changed)
        unchanged, gates = len(gates) - len(kept), kept
        say(f"check-ux-gates: UX_GATES_SINCE={since} — {unchanged} render gate(s) over previews nothing changed, "
            "not rendered")
    skipped = 0
    render = [gate for gate in gates if gate.render]
    opened = ("no-node" if shutil.which("node") is None else browser()) if render else "chrome"
    for app in dict.fromkeys(gate.app for gate in render):
        relative = app.relative_to(ROOT).as_posix()
        mine = [gate for gate in render if gate.app == app]
        if opened in ("no-node", "none", "no-playwright"):
            why = {"no-node": "node not found",
                   "no-playwright": "playwright is not resolvable from the kit",
                   "none": "no browser opens — neither Chrome nor Playwright's Chromium "
                           "(`npx playwright install chromium`)"}[opened]
            say(f"check-ux-gates: {relative}/screens/ — {why}; {len(mine)} render gate(s) SKIPPED, not passed")
            skipped += len(mine)
            continue
        previews = len({gate.target for gate in mine if gate.target.is_file()})
        say(f"check-ux-gates: {relative}/screens/ — {previews} preview(s) through the render gates"
            + (" on Playwright's Chromium, Chrome not being installed" if opened == "bundled" else ""))
    if opened in ("no-node", "none", "no-playwright"):
        gates = [gate for gate in gates if not gate.render]
    for gate in gates:
        if not gate.render:
            say(f"check-ux-gates: {gate.app.relative_to(ROOT).as_posix()}/src — literal values outside the tokens")
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        preload = Path(scratch) / "preload.cjs"
        preload.write_text(PRELOAD.replace("{scripts}", json.dumps(str(kit / "scripts/preload.cjs"))))
        with ThreadPoolExecutor(max_workers=jobs()) as pool:
            verdicts = list(pool.map(lambda gate: run(gate, preload if opened == "bundled" else None), gates))
    for gate, verdict in zip(gates, verdicts, strict=True):
        if verdict == "failed":
            failures.append(f"{gate.app.relative_to(ROOT).as_posix()}/src carries literal values the tokens should own"
                            if not gate.render else gate.label())
        elif verdict == "skipped":
            skipped += 1
    scope = (f" in shard {spec}" if spec else "") + (f"; {unchanged} unchanged since {since}, not rendered"
                                                     if unchanged else "")
    if failures:
        say("check-ux-gates: FAILED\n  - " + "\n  - ".join(failures))
        return 1
    if skipped:
        say(f"check-ux-gates: passed where a gate could run{scope}; {skipped} render gate(s) SKIPPED, not passed — "
            "each says above what it could not open")
        return 1 if required else 0
    say(f"check-ux-gates: every gate passed{scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
