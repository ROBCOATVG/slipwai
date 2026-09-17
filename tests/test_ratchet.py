"""The ratchet: a recorded gate held to a committed baseline, red only on what is new — and the import gate
passing over code it was not written for.

An adopted repository's linter is usually red on day one, because the rule arrived after the code. The
promise the ratchet keeps is the one this suite gates: `verify` is green on day one, having recorded what was
there; it goes red the moment a change adds a finding, naming it; fixing findings never fails anything and is
recorded on request; and a baseline is never recorded on CI, where nobody would read it. Beside it, the
hexagonal import rule holds a wrapped application only where that application declares the layout.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_replay import git

LINTER = """
const fs = require("node:fs");
let bad = 0;
for (const file of fs.readdirSync("src")) {
  const lines = fs.readFileSync(`src/${file}`, "utf8").split("\\n");
  lines.forEach((line, index) => {
    if (line.includes("FOO")) { console.log(`src/${file}:${index + 1}:1: no-foo: FOO is not allowed`); bad += 1; }
  });
}
process.exit(bad ? 1 : 0);
"""


def make(repo: Path, *targets: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    clean = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
    return subprocess.run(
        ["make", "-f", "delivery/Makefile", *targets],
        cwd=repo, text=True, capture_output=True, env={**clean, **(env or {})},
    )


class RatchetTest(FactoryTestCase):
    def test_a_red_linter_is_green_on_day_one_and_red_the_moment_something_new_appears(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps(
                    {"name": "shop", "scripts": {"lint": "node lint.js", "test": "node --test"}}
                ),
                "lint.js": LINTER,
                "src/a.js": "// FOO lives here\nexports.a = 1;\n",
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("python3 delivery/scripts/ratchet.py shop lint -- 'npm run lint'", makefile)
            self.assertIn("ratchet-tighten:", makefile)
            self.assertTrue(os.access(repo / "delivery/scripts/ratchet.py", os.X_OK))

            # Day one: red linter, green gate, baseline recorded and said so.
            first = make(repo, "verify")
            self.assertEqual(first.returncode, 0, first.stdout[-3000:] + first.stderr[-3000:])
            self.assertIn("ratchet: baseline recorded for shop lint — 1 finding(s)", first.stdout)
            self.assertIn("commit delivery/baseline.json", first.stdout)
            baseline = json.loads((repo / "delivery/baseline.json").read_text())
            self.assertEqual(
                baseline["shop"]["lint"], {"exit": 1, "findings": ["src/a.js: no-foo: FOO is not allowed"]}
            )
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "baseline")
            second = make(repo, "verify")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("ratchet: shop lint — 1 known finding(s), none new", second.stdout)

            # A known finding moving down the file is not new; a new one anywhere is, and is named.
            (repo / "src/a.js").write_text("// moved\n// FOO lives here\nexports.a = 1;\n")
            self.assertEqual(make(repo, "lint").returncode, 0)
            (repo / "src/b.js").write_text("exports.b = 'FOO';\n")
            red = make(repo, "verify")
            self.assertNotEqual(red.returncode, 0)
            self.assertIn("ratchet: 1 new finding(s) in shop lint since the baseline (1 known)", red.stderr)
            self.assertIn("src/b.js: no-foo: FOO is not allowed", red.stderr)

            # Fixing tightens on request, and never fails anything.
            (repo / "src/b.js").write_text("exports.b = 'bar';\n")
            (repo / "src/a.js").write_text("exports.a = 1;\n")
            clean = make(repo, "lint")
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertIn("shop lint is clean; its baseline can go", clean.stdout)
            self.assertEqual(json.loads((repo / "delivery/baseline.json").read_text())["shop"]["lint"]["exit"], 1)
            tightened = make(repo, "ratchet-tighten")
            self.assertEqual(tightened.returncode, 0, tightened.stderr)
            self.assertEqual(
                json.loads((repo / "delivery/baseline.json").read_text())["shop"]["lint"], {"exit": 0, "findings": []}
            )

            # On CI a missing baseline is a failure with the reason, never a baseline nobody looked at.
            (repo / "src/a.js").write_text("// FOO\n")
            (repo / "delivery/baseline.json").unlink()
            ci = make(repo, "lint", env={"CI": "true"})
            self.assertNotEqual(ci.returncode, 0)
            self.assertIn("has no baseline for it", ci.stderr)
            self.assertFalse((repo / "delivery/baseline.json").exists())

    def test_a_tool_that_is_not_on_this_machine_is_named_and_never_baselined(self) -> None:
        """`mvn` on a laptop that builds from the IDE: the shell's `command not found` is not a red linter, so it is
        refused rather than recorded — a baseline of "exit 127" would pass forever on every machine without the
        tool. `adopt` says which tools are missing before the first `verify` gets there."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "scripts": {"test": "node --test"}}),
                "src/a.js": "exports.a = 1;\n",
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            adopted = slipwai(repo, "adopt", "--yes", "--command", "shop:lint=no-such-linter --strict src")
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            self.assertIn("`no-such-linter` is not on PATH here, and shop's lint run it", adopted.stdout)
            self.assertIn("make -f delivery/Makefile verify stops there", adopted.stdout)

            red = make(repo, "verify")
            self.assertNotEqual(red.returncode, 0)
            self.assertIn(
                "ratchet: shop lint could not run — `no-such-linter` is not on this machine (exit 127)", red.stderr
            )
            self.assertIn("nothing is recorded", red.stderr)
            self.assertFalse((repo / "delivery/baseline.json").exists(), "a missing tool is not a baseline")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_the_import_gate_passes_over_wrapped_code_unless_it_declares_the_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "apps/legacy/package.json": json.dumps({"name": "legacy", "scripts": {}}),
                "apps/legacy/src/domain/thing.ts": "import { db } from '../adapters/db';\nexport const t = db;\n",
                "apps/legacy/src/adapters/db.ts": "export const db = 1;\n",
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            passing = make(repo, "check-imports")
            self.assertEqual(passing.returncode, 0, passing.stdout + passing.stderr)
            self.assertIn("inward dependency rule holds", passing.stdout)

            manifest = repo / "project.json"
            document = json.loads(manifest.read_text())
            document["deployables"]["legacy"]["layout"] = "hexagonal"
            manifest.write_text(json.dumps(document, indent=2) + "\n")
            held = make(repo, "check-imports")
            self.assertNotEqual(held.returncode, 0)
            self.assertIn("apps/legacy/src/domain/thing.ts:1: domain imports an outer layer", held.stdout + held.stderr)

    def test_a_suite_too_slow_for_verify_is_recorded_as_test_full(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "scripts": {"test": "node --test 'test/fast/*.test.js'"}}),
                "test/fast/a.test.js": 'require("node:test")("fast", () => {});\n',
                "test/slow/b.test.js": 'require("node:test")("slow", () => {});\n',
            })
            adopted = slipwai(
                repo, "adopt", "--yes", "--command", "shop:test-full=node --test 'test/slow/*.test.js'",
                "--hexagonal", "shop",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            shop = json.loads((repo / "project.json").read_text())["deployables"]["shop"]
            self.assertEqual(shop["commands"]["test-full"], "node --test 'test/slow/*.test.js'")
            self.assertEqual(shop["layout"], "hexagonal")
            self.assertEqual(shop["provenance"]["structure"], "overridden")
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("test-full: ## Run the full suites recorded as too slow for verify", makefile)
            full = make(repo, "test-full")
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertIn("slow", full.stdout)

    def test_a_smoke_command_is_recorded_started_by_make_smoke_and_run_by_ci_apart_from_verify(self) -> None:
        """The one command the gate cannot compose from the eight: the application started and proved to answer.
        Recorded as `smoke`, it has a target, `ci` runs it, the gate's workflow runs it as a job of its own, and
        `verify` never does; where nothing is recorded, the target says nobody has proved how the application starts
        and the workflow has one job. The first four real adoptions each merged a slice that had stopped the
        application starting, and no suite saw it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps(
                    {"name": "shop", "scripts": {"test": "node --test", "start": "node app.js"}}
                ),
                "app.js": "console.log('listening');\n",
                "smoke.js": "console.log('shop answers'); process.exit(0);\n",
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            adopted = slipwai(repo, "adopt", "--yes", "--forge", "github", "--command", "shop:smoke=node smoke.js")
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            shop = json.loads((repo / "project.json").read_text())["deployables"]["shop"]
            self.assertEqual(shop["commands"]["smoke"], "node smoke.js")
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("smoke: ## Start each application by its recorded smoke command", makefile)
            self.assertRegex(makefile, r"\nci: [^\n]*\bsmoke\b")
            verify_line = next(line for line in makefile.splitlines() if line.startswith("verify:"))
            self.assertNotIn("smoke", verify_line, "verify stays the fast gate; smoke needs what the application needs")
            smoked = make(repo, "smoke")
            self.assertEqual(smoked.returncode, 0, smoked.stdout + smoked.stderr)
            self.assertIn("shop answers", smoked.stdout)
            workflow = (repo / ".github/workflows/verify-delivery.yml").read_text()
            self.assertIn("\n  smoke:\n", workflow)
            self.assertIn("needs: verify", workflow)
            self.assertIn("- run: make -f delivery/Makefile smoke", workflow)

            unproven = repository(Path(directory), "depot", {
                "package.json": json.dumps({"name": "depot", "scripts": {"test": "node --test"}}),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            self.assertEqual(slipwai(unproven, "adopt", "--yes", "--forge", "github").returncode, 0)
            said = make(unproven, "smoke")
            self.assertEqual(said.returncode, 0, said.stdout + said.stderr)
            self.assertIn("depot: no smoke command is recorded — nobody has proved how it starts", said.stdout)
            self.assertIn("delivery/survey/running.md", said.stdout)
            self.assertNotIn("\n  smoke:\n", (unproven / ".github/workflows/verify-delivery.yml").read_text())

    def test_a_red_test_suite_is_quarantined_on_day_one_and_released_when_green(self) -> None:
        """A suite that arrives red does not make the gate red on day one: the ratchet records its state, says
        the suite is quarantined on every run, refuses to record that on CI, and clears the quarantine only once
        the suite is green and somebody asks."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "scripts": {"test": "node --test"}}),
                "test/a.test.js": (
                    'const t = require("node:test"); const a = require("node:assert");\n'
                    't("adds", () => a.equal(1 + 1, 3));\n'
                ),
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("python3 delivery/scripts/ratchet.py shop test -- 'npm run test'", makefile)
            # Day one: the red suite stops the run and says so. Nothing is recorded behind anybody's back — two real
            # adoptions found a red suite passing `verify` on a laptop with nobody having decided that.
            day_one = make(repo, "verify")
            self.assertNotEqual(day_one.returncode, 0, day_one.stdout[-3000:])
            self.assertIn("shop test is red (exit 1; 1 finding(s))", day_one.stderr)
            self.assertIn("is not quarantined behind your back", day_one.stderr)
            self.assertIn("`make ratchet-tighten` records them as the quarantine", day_one.stderr)
            self.assertFalse((repo / "delivery/baseline.json").exists(), "a red suite is a decision, not a record")
            # The person, having read the failures, quarantines it by name — and the runner's own failure name is the
            # finding, so the quarantine holds one test and not an exit code.
            tightened = make(repo, "ratchet-tighten")
            self.assertEqual(tightened.returncode, 0, tightened.stdout + tightened.stderr)
            self.assertIn("shop test is red and is now QUARANTINED — 1 finding(s) recorded", tightened.stdout)
            baseline = json.loads((repo / "delivery/baseline.json").read_text())
            self.assertEqual(baseline["shop"]["test"], {"exit": 1, "findings": ["test: adds"]})
            again = make(repo, "test")
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertIn("shop test — 1 known finding(s), none new", again.stdout)
            self.assertIn("still QUARANTINED", again.stdout)
            # The same one failure under node's other reporter — `✖ adds (1.06ms)` and a `test at` pointer instead of
            # TAP's `not ok 1 - adds` — is the same finding: a baseline recorded on a laptop holds on a runner whose
            # node picks the other reporter, which is how CI first found this.
            spec = make(repo, "test", env={"NODE_OPTIONS": "--test-reporter=spec"})
            self.assertEqual(spec.returncode, 0, spec.stdout + spec.stderr)
            self.assertIn("shop test — 1 known finding(s), none new", spec.stdout)
            # A second failure beside the known one is new, and named — never passed on the exit code alone.
            (repo / "test/b.test.js").write_text(
                'const t = require("node:test"); const a = require("node:assert");\n'
                't("subtracts", () => a.equal(2 - 1, 0));\n'
            )
            worse = make(repo, "test")
            self.assertNotEqual(worse.returncode, 0)
            self.assertIn("ratchet: 1 new finding(s) in shop test since the baseline (1 known)", worse.stderr)
            self.assertIn("test: subtracts", worse.stderr)
            (repo / "test/b.test.js").unlink()
            # On CI a quarantine nobody committed fails with the reason, exactly as a linter's baseline does.
            recorded = (repo / "delivery/baseline.json").read_text()
            (repo / "delivery/baseline.json").unlink()
            on_ci = make(repo, "test", env={"CI": "1"})
            self.assertNotEqual(on_ci.returncode, 0)
            self.assertIn("has no baseline", on_ci.stderr)
            (repo / "delivery/baseline.json").write_text(recorded)
            # Green: the suite is fixed, the run says the quarantine can go, and ratchet-tighten clears it.
            (repo / "test/a.test.js").write_text(
                'const t = require("node:test"); const a = require("node:assert");\n'
                't("adds", () => a.equal(1 + 1, 2));\n'
            )
            fixed = make(repo, "test")
            self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
            self.assertIn("shop test is clean; its baseline can go", fixed.stdout)
            tightened = make(repo, "ratchet-tighten")
            self.assertEqual(tightened.returncode, 0, tightened.stdout + tightened.stderr)
            baseline = json.loads((repo / "delivery/baseline.json").read_text())
            self.assertEqual(baseline["shop"]["test"], {"exit": 0, "findings": []})
