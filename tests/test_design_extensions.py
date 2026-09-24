"""The two extensions that only make sense with a browser app: `uipro` and `ux-gates`.

Both are installs rather than vendored source — a design-system generator taken into the root `skills/`
as one skill, and a kit of objective gates put under `tools/` and into `make verify` — and both refuse a
project with nothing to design or measure. The fakes here are the installers reduced to what the
extension reads back; see `docs/extensions.md` for what every `init.py` owes and `test_extensions.py`
for the contract as CodeGraph meets it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

FAKE_SPECIFY = "#!/bin/sh\nexit 0\n"

# What `uipro init --ai universal` writes, reduced to what the extension reads: the skill, its text naming
# the harness path the installer put it at, and the search script beside it.
FAKE_UIPRO = """#!/bin/sh
mkdir -p .agents/skills/ui-ux-pro-max/scripts .agents/skills/ui-styling
printf '%s\\n' "$@" > "$UIPRO_LOG"
cat > .agents/skills/ui-ux-pro-max/SKILL.md <<'SKILL'
---
name: ui-ux-pro-max
description: "UI/UX design intelligence."
---
# ui-ux-pro-max
Run: python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system
SKILL
printf '%s\\n' 'print("searched")' > .agents/skills/ui-ux-pro-max/scripts/search.py
printf '%s\\n' '# not taken' > .agents/skills/ui-styling/SKILL.md
"""

# What `npx ux-ui-agent-skills init <dest>` copies, reduced to the two files the gate and the pointer name.
# The fake lint fails on a red hex, which is enough to prove the gate carries the kit's verdict.
FAKE_NPX = """#!/bin/sh
printf '%s\\n' "$@" > "$NPX_LOG"
dest="$4"
mkdir -p "$dest/scripts" "$dest/accessibility" "$dest/workflows"
cat > "$dest/scripts/lint_hardcodes.py" <<'LINT'
import sys
from pathlib import Path
hits = [p for p in Path(sys.argv[1]).rglob("*.css") if "#ff0000" in p.read_text()]
print("FAIL: hardcoded" if hits else "OK: no hardcoded values found")
raise SystemExit(1 if hits else 0)
LINT
printf '%s\\n' '# WCAG checklist' > "$dest/accessibility/wcag-checklist.md"
printf '%s\\n' '# Design review' > "$dest/workflows/design-review.md"
"""


# `node` as the gate sees it: the probe (`--input-type=module`) answers with the browser the test names, and a kit
# script behaves as `FAKE_GATE` says — passes, fails, skips in the kit's own word, or crashes the way Playwright does
# where no browser opens. Every call is logged — the probe as one word — and the preload a call was started
# with is kept once.
FAKE_NODE = """#!/bin/sh
if [ "$1" = "--input-type=module" ]; then echo "probe" >> "$NODE_LOG"; echo "$FAKE_BROWSER"; exit 0; fi
echo "$*" >> "$NODE_LOG"
if [ "$1" = "--require" ]; then cp "$2" "$NODE_LOG.preload"; fi
case "$FAKE_GATE" in
  crash) echo "browserType.launch: Chromium distribution 'chrome' is not found at /opt/google/chrome" >&2; exit 1;;
  fail) echo "gate: FAIL — 1 finding"; exit 1;;
  skipped) echo "gate: playwright not installed — SKIPPED"; exit 0;;
  *) echo "gate: OK"; exit 0;;
esac
"""


def without(directory: str, tools: tuple[str, ...]) -> str:
    """A PATH on which none of `tools` resolves — arranged, not assumed, because the machine running the
    suite may have the real thing installed. A directory holding one of them is not dropped, since `npx`
    shares `/usr/bin` with `head` and `sh`; it is replaced by a directory of links to everything else in it."""
    entries = []
    for index, entry in enumerate(os.environ["PATH"].split(os.pathsep)):
        source = Path(entry)
        if not source.is_dir() or not any((source / tool).exists() for tool in tools):
            entries.append(entry)
            continue
        shadow = Path(directory) / f"shadow-{index}"
        shadow.mkdir()
        for item in source.iterdir():
            if item.name not in tools:
                (shadow / item.name).symlink_to(item)
        entries.append(str(shadow))
    return os.pathsep.join(entries)


class DesignExtensionsTest(FactoryTestCase):
    """`uipro` and `ux-gates`: the two extensions that only make sense with a browser app."""

    def fake_bin(self, directory: str, **scripts: str) -> Path:
        fake_bin = Path(directory) / "fake-bin"
        fake_bin.mkdir()
        (fake_bin / "specify").write_text(FAKE_SPECIFY)
        (fake_bin / "specify").chmod(0o755)
        for name, body in scripts.items():
            (fake_bin / name).write_text(body)
            (fake_bin / name).chmod(0o755)
        return fake_bin

    def test_uipro_installs_the_one_skill_into_the_root_catalogue_and_points_the_agent_at_it(self) -> None:
        """The installer writes fifteen per-harness copies; the project wants one, at the root, where
        `make agents` projects it and `check-agents` holds the projections to it. Its text names the path
        the installer wrote it to, which is wrong everywhere but that harness, so it is rewritten to the
        root; and it declares the capability it serves so a project that drops its browser app is told."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "designed", frontend="react-vite")
            fake_bin = self.fake_bin(directory, uipro=FAKE_UIPRO)
            log = Path(directory) / "uipro-args"
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "UIPRO_LOG": str(log)}

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "uipro"], cwd=repo, check=True, env=environment
            )

            self.assertEqual(log.read_text().split(), ["init", "--ai", "universal", "--force"])
            skill = (repo / "skills/ui-ux-pro-max/SKILL.md").read_text()
            self.assertIn("python3 skills/ui-ux-pro-max/scripts/search.py", skill)
            self.assertNotIn(".agents/skills/ui-ux-pro-max", skill)
            self.assertIn("capabilities: frontend", skill)
            self.assertTrue((repo / "skills/ui-ux-pro-max/scripts/search.py").is_file())
            self.assertFalse((repo / "skills/ui-styling").exists(), "a skill the project does not use was taken")
            # Projected to the harness `./init` chose, although the projection ran before the extension.
            self.assertTrue((repo / ".agents/skills/ui-ux-pro-max/SKILL.md").is_file())
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:uipro:begin -->", agents)
            self.assertIn("--persist --output-dir .", agents)
            self.assertIn("`docs/design.md` stays the page", agents)
            self.assertIn("./init --extension uipro", agents)
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text()),
                {"schemaVersion": 1, "extensions": ["uipro"]},
            )
            self.assertIn("skills/ui-ux-pro-max/\n", (repo / ".gitignore").read_text())
            # And the projection still agrees with the root once the skill is there.
            check = subprocess.run(
                ["make", "check-agents"], cwd=repo, env=environment, text=True, capture_output=True
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_uipro_falls_back_to_the_pinned_package_when_the_cli_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "designed-npx", frontend="react-vite")
            # A fake `npx` that only answers for the pinned package, the way the real one would.
            answers_only_the_pin = 'case "$2" in ui-ux-pro-max-cli@*) ;; *) exit 9 ;; esac\nshift 2\nmkdir -p'
            npx = FAKE_UIPRO.replace("mkdir -p", answers_only_the_pin, 1)
            fake_bin = self.fake_bin(directory, npx=npx)
            log = Path(directory) / "npx-args"
            environment = os.environ | {
                "PATH": f"{fake_bin}:{without(directory, ('uipro',))}",
                "UIPRO_LOG": str(log),
            }

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "uipro"], cwd=repo, check=True, env=environment
            )

            self.assertEqual(log.read_text().split(), ["init", "--ai", "universal", "--force"])
            self.assertTrue((repo / "skills/ui-ux-pro-max/SKILL.md").is_file())

    def test_uipro_and_the_gates_refuse_a_project_with_no_browser_app_and_say_what_would_change_that(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", frontend="none")
            fake_bin = self.fake_bin(directory, uipro=FAKE_UIPRO, npx=FAKE_NPX)
            environment = os.environ | {
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "UIPRO_LOG": str(Path(directory) / "u"),
                "NPX_LOG": str(Path(directory) / "n"),
            }

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "uipro", "--extension", "ux-gates"],
                cwd=repo, env=environment, text=True, capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("no browser app", result.stderr)
            self.assertIn("slipwai add-frontend web", result.stderr)
            self.assertNotIn("<!-- extension:uipro:begin -->", (repo / "AGENTS.md").read_text())
            self.assertNotIn("<!-- extension:ux-gates:begin -->", (repo / "AGENTS.md").read_text())
            self.assertFalse((repo / "skills/ui-ux-pro-max").exists())
            self.assertFalse((repo / "tools/ux-gates").exists())
            self.assertFalse((repo / ".slipwai/extensions.json").exists())

    def test_a_missing_installer_is_non_fatal_and_names_the_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "designed-no-tools", frontend="react-vite")
            fake_bin = self.fake_bin(directory)
            environment = os.environ | {"PATH": f"{fake_bin}:{without(directory, ('uipro', 'npx'))}"}

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "uipro", "--extension", "ux-gates"],
                cwd=repo, env=environment, text=True, capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Neither the `uipro` CLI nor `npx` was found", result.stderr)
            self.assertIn("./init --extension uipro", result.stderr)
            self.assertIn("`npx` was not found", result.stderr)
            self.assertIn("./init --extension ux-gates", result.stderr)
            self.assertNotIn("<!-- extension:", (repo / "AGENTS.md").read_text())
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

    def test_ux_gates_installs_the_kit_and_make_verify_carries_its_verdict(self) -> None:
        """The gate is the extension. Adopted, it runs the kit's file gate over the browser app's source and
        fails when the kit does; a preview directory with nothing in it says so rather than passing."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "gated", frontend="react-vite")
            fake_bin = self.fake_bin(directory, npx=FAKE_NPX)
            log = Path(directory) / "npx-args"
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "NPX_LOG": str(log)}

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "ux-gates"], cwd=repo, check=True, env=environment
            )

            self.assertEqual(
                log.read_text().split(), ["-y", "ux-ui-agent-skills@2.8.0", "init", "tools/ux-gates", "--force"]
            )
            self.assertTrue((repo / "tools/ux-gates/scripts/lint_hardcodes.py").is_file())
            self.assertIn("tools/ux-gates/\n", (repo / ".gitignore").read_text())
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:ux-gates:begin -->", agents)
            self.assertIn("make check-ux-gates", agents)
            self.assertIn("tools/ux-gates/accessibility/wcag-checklist.md", agents)
            self.assertIn("SKIPPED", (repo / "scripts/check-ux-gates.py").read_text())
            makefile = (repo / "Makefile").read_text()
            self.assertIn("check-codegraph check-ux-gates check-constitution", makefile)
            self.assertIn("check-ux-gates: ## Fail when a browser app breaks the adopted UX gates", makefile)

            clean = subprocess.run(["make", "check-ux-gates"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            self.assertIn("apps/web/src — literal values outside the tokens", clean.stdout)
            self.assertIn("apps/web/screens/ has no previews", clean.stdout)
            self.assertIn("check-ux-gates: every gate passed", clean.stdout)

            (repo / "apps/web/src/styles/slice.css").write_text(".hero { color: #ff0000; }\n")
            red = subprocess.run(["make", "check-ux-gates"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(red.returncode, 0)
            self.assertIn("check-ux-gates: FAILED", red.stdout)
            self.assertIn("apps/web/src carries literal values the tokens should own", red.stdout)

    def test_the_gate_is_a_no_op_until_adopted_and_a_skip_not_a_pass_where_the_kit_is_absent(self) -> None:
        """A fresh clone has the election and not the kit, because `tools/ux-gates/` is ignored. That is
        reported as skipped, and `UX_GATES_REQUIRE=1` makes it the failure it is wherever the kit is
        expected — never a silent pass either way."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ungated", frontend="react-vite")

            fresh = subprocess.run(["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(fresh.returncode, 0)
            self.assertIn("not adopted", fresh.stdout)

            fake_bin = self.fake_bin(directory, npx=FAKE_NPX)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "NPX_LOG": f"{directory}/n"}
            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "ux-gates"], cwd=repo, check=True, env=environment
            )
            shutil.rmtree(repo / "tools/ux-gates")

            skipped = subprocess.run(["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(skipped.returncode, 0)
            self.assertIn("SKIPPED, not passed", skipped.stdout)
            self.assertIn("./init --extension ux-gates", skipped.stdout)

            required = subprocess.run(
                ["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True, capture_output=True,
                env=os.environ | {"UX_GATES_REQUIRE": "1"},
            )
            self.assertEqual(required.returncode, 1)
            self.assertIn("REQUIRED, FAILING", required.stdout)

    def test_the_render_gates_open_the_browser_they_can_and_a_crash_is_a_skip_and_never_a_pass(self) -> None:
        """The kit launches Chrome, and two of its scripts crash where Chrome is absent instead of falling back to
        Playwright's Chromium as the other three do. So the gate asks once which browser opens: `bundled` runs every
        render gate with a preload that retries a launch without the channel, `chrome` runs them plainly, and
        `none` or `no-playwright` counts them skipped without running one. A gate that still crashes on its launch
        is a skip, not a pass and not a failure; a gate that fails is a failure; `UX_GATES_REQUIRE=1` makes every
        skip the failure it is where a browser is expected."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "rendered", frontend="react-vite")
            fake_bin = self.fake_bin(directory, npx=FAKE_NPX, node=FAKE_NODE)
            log = Path(directory) / "node-calls"
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "NPX_LOG": f"{directory}/n",
                                        "NODE_LOG": str(log)}
            subprocess.run(["./init", "--integration", "codex", "--extension", "ux-gates"], cwd=repo, check=True,
                           env=environment)
            (repo / "apps/web/screens").mkdir()
            (repo / "apps/web/screens/one.html").write_text("<!doctype html><button>Go</button>\n")

            def gate(**more: str) -> subprocess.CompletedProcess:
                log.unlink(missing_ok=True)
                return subprocess.run(["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True,
                                      capture_output=True, env=environment | more)

            for word, why in (("none", "no browser opens — neither Chrome nor Playwright's Chromium "
                                       "(`npx playwright install chromium`)"),
                              ("no-playwright", "playwright is not resolvable from the kit")):
                unopened = gate(FAKE_BROWSER=word)
                self.assertEqual(unopened.returncode, 0, unopened.stdout + unopened.stderr)
                self.assertIn(f"apps/web/screens/ — {why}; 8 render gate(s) SKIPPED, not passed", unopened.stdout)
                self.assertNotIn("every gate passed", unopened.stdout)
                self.assertEqual(len(log.read_text().splitlines()), 1, "only the probe ran")
                self.assertEqual(gate(FAKE_BROWSER=word, UX_GATES_REQUIRE="1").returncode, 1)

            bundled = gate(FAKE_BROWSER="bundled")
            self.assertEqual(bundled.returncode, 0, bundled.stdout + bundled.stderr)
            self.assertIn("1 preview(s) through the render gates on Playwright's Chromium, Chrome not being installed",
                          bundled.stdout)
            self.assertIn("check-ux-gates: every gate passed", bundled.stdout)
            calls = log.read_text().splitlines()
            self.assertEqual(len(calls), 9, calls)
            self.assertTrue(all(call.startswith("--require ") and "/preload.cjs " in call for call in calls[1:]), calls)
            self.assertEqual([call.split("/scripts/")[-1] for call in calls[1:]],
                             ["verify_responsive.mjs " + str(repo / "apps/web/screens"),
                              "verify_target_size.mjs " + str(repo / "apps/web/screens"),
                              "measure_render.mjs " + str(repo / "apps/web/screens"),
                              "measure_render.mjs " + str(repo / "apps/web/screens") + " --dark",
                              "axe_audit.mjs " + str(repo / "apps/web/screens/one.html"),
                              "axe_audit.mjs " + str(repo / "apps/web/screens/one.html") + " --dark",
                              "verify_states.mjs " + str(repo / "apps/web/screens/one.html"),
                              "verify_states.mjs " + str(repo / "apps/web/screens/one.html") + " --dark"])
            preload = Path(f"{log}.preload").read_text()
            self.assertIn(f'createRequire("{repo / "tools/ux-gates/scripts/preload.cjs"}")("playwright")', preload)
            self.assertIn("if (!options.channel) throw error;", preload)

            chrome = gate(FAKE_BROWSER="chrome")
            self.assertEqual(chrome.returncode, 0, chrome.stdout)
            self.assertIn("check-ux-gates: every gate passed", chrome.stdout)
            self.assertNotIn("Playwright's Chromium", chrome.stdout)
            self.assertFalse(any("--require" in call for call in log.read_text().splitlines()))

            crashed = gate(FAKE_BROWSER="chrome", FAKE_GATE="crash")
            self.assertEqual(crashed.returncode, 0, crashed.stdout + crashed.stderr)
            self.assertIn("check-ux-gates: verify_responsive.mjs could not open a browser — SKIPPED, not passed",
                          crashed.stdout)
            self.assertIn("8 render gate(s) SKIPPED, not passed", crashed.stdout)
            self.assertNotIn("FAILED", crashed.stdout)
            self.assertEqual(gate(FAKE_BROWSER="chrome", FAKE_GATE="crash", UX_GATES_REQUIRE="1").returncode, 1)
            self.assertIn("check-ux-gates: FAILED\n  - apps/web/screens: verify_responsive.mjs",
                          gate(FAKE_BROWSER="chrome", FAKE_GATE="fail").stdout)
