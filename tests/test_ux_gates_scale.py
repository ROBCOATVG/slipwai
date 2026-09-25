"""What the render gates cost is per screen, so `check-ux-gates` has three ways to spread it.

A generated project measured it: 225 previews, four per-file gates each, one browser per gate, two at a
time on a two-processor runner — 24 of a 33-minute `verify`. Nothing about that is a defect in any one
screen; it is what a gate linear in `screens/` does to a project that keeps adding screens. So the gates
run side by side (`UX_GATES_JOBS`), split across CI jobs that between them run every gate exactly once
(`UX_GATES_SHARD=k/n`), and on a pull request only over the previews the change can move
(`UX_GATES_SINCE=<ref>`) — and the extension writes the sharded job into `verify.yml`, which is where a
deploy waits, from the first screen rather than after the budget is spent.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_design_extensions import FAKE_NODE, FAKE_NPX, FAKE_SPECIFY

SCREENS = {
    "linked.html": '<!doctype html><link rel="stylesheet" href="../src/styles/linked.css"><button>Go</button>\n',
    "imported.html": "<!doctype html><style>@import url('../src/styles/entry.css');</style><button>Go</button>\n",
    "plain.html": '<!doctype html><link rel="stylesheet" href="https://cdn.example/x.css"><button>Go</button>\n',
}


class UxGatesScaleTest(FactoryTestCase):
    def adopted(self, directory: str) -> tuple[Path, dict[str, str], Path]:
        """A project with the gates adopted, three previews committed, and `node` answering as the kit would."""
        repo = self.generate(directory, "scaled", frontend="react-vite")
        fake_bin = Path(directory) / "fake-bin"
        fake_bin.mkdir()
        for name, body in (("npx", FAKE_NPX), ("node", FAKE_NODE), ("specify", FAKE_SPECIFY)):
            (fake_bin / name).write_text(body)
            (fake_bin / name).chmod(0o755)
        log = Path(directory) / "node-calls"
        environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "NPX_LOG": f"{directory}/n",
                                    "NODE_LOG": str(log), "FAKE_BROWSER": "chrome"}
        subprocess.run(["./init", "--integration", "codex", "--extension", "ux-gates"], cwd=repo, check=True,
                       env=environment, capture_output=True)
        (repo / "apps/web/screens").mkdir()
        for name, text in SCREENS.items():
            (repo / "apps/web/screens" / name).write_text(text)
        styles = repo / "apps/web/src/styles"
        (styles / "linked.css").write_text(".a { color: var(--ink); }\n")
        (styles / "entry.css").write_text('@import "./deep.css";\n')
        (styles / "deep.css").write_text(".b { color: var(--ink); }\n")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "screens"], cwd=repo,
                       check=True)
        return repo, environment, log

    def gate(self, repo: Path, environment: dict[str, str], log: Path, **more: str) -> tuple[str, list[str]]:
        log.unlink(missing_ok=True)
        completed = subprocess.run(["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True,
                                   capture_output=True, env=environment | more)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        calls = log.read_text().splitlines() if log.exists() else []
        return completed.stdout, sorted(call.split("/scripts/")[-1] for call in calls if call != "probe")

    def test_shards_run_every_gate_exactly_once_between_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, environment, log = self.adopted(directory)
            said, whole = self.gate(repo, environment, log)
            self.assertEqual(len(whole), 4 + 4 * len(SCREENS), whole)
            together, lints = [], 0
            for index in (1, 2, 3):
                said, calls = self.gate(repo, environment, log, UX_GATES_SHARD=f"{index}/3")
                self.assertIn(f"check-ux-gates: shard {index}/3 — ", said)
                self.assertIn(f"every gate passed in shard {index}/3", said)
                lints += said.count("literal values outside the tokens")
                together += calls
            self.assertEqual(sorted(together), whole)
            self.assertEqual(lints, 1, "the file gate is one gate, and runs in one shard")
            refused = subprocess.run(["python3", "scripts/check-ux-gates.py"], cwd=repo, text=True,
                                     capture_output=True, env=environment | {"UX_GATES_SHARD": "4/3"})
            self.assertEqual(refused.returncode, 1)
            self.assertIn("UX_GATES_SHARD=4/3 is not k/n", refused.stdout)

    def test_a_project_test_can_load_the_script_without_registering_it(self) -> None:
        """A project's own test loaded the script with `importlib` and did not put it in `sys.modules`; a
        dataclass there crashed on its class before the test could run. Loaded that way, it now loads."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "loaded", frontend="react-vite")
            loaded = subprocess.run(
                ["python3", "-c", "import importlib.util, sys\n"
                 "spec = importlib.util.spec_from_file_location('gates', 'scripts/check-ux-gates.py')\n"
                 "module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n"
                 "assert 'gates' not in sys.modules\nprint(module.Gate.__name__)"],
                cwd=repo, text=True, capture_output=True)
            self.assertEqual((loaded.returncode, loaded.stdout.strip()), (0, "Gate"), loaded.stderr)

    def test_since_renders_only_what_a_change_can_move(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, environment, log = self.adopted(directory)
            styles = repo / "apps/web/src/styles"

            said, calls = self.gate(repo, environment, log, UX_GATES_SINCE="HEAD")
            self.assertEqual(calls, [])
            self.assertIn("16 render gate(s) over previews nothing changed, not rendered", said)
            self.assertIn("literal values outside the tokens", said, "the file gate always runs")

            (styles / "deep.css").write_text(".b { color: var(--accent); }\n")  # reached only through entry.css
            _, calls = self.gate(repo, environment, log, UX_GATES_SINCE="HEAD")
            previews = {call.split()[1].rsplit("/", 1)[-1] for call in calls}
            self.assertEqual(previews, {"imported.html", "screens"}, calls)
            self.assertEqual(len(calls), 8)

            subprocess.run(["git", "checkout", "-q", "--", "."], cwd=repo, check=True)
            (repo / "apps/web/screens/plain.html").write_text(SCREENS["plain.html"] + "<p>more</p>\n")
            _, calls = self.gate(repo, environment, log, UX_GATES_SINCE="HEAD")
            self.assertEqual({call.split()[1].rsplit("/", 1)[-1] for call in calls}, {"plain.html", "screens"})

            (repo / "package-lock.json").write_text((repo / "package-lock.json").read_text() + "\n")
            said, calls = self.gate(repo, environment, log, UX_GATES_SINCE="HEAD")
            self.assertIn("package-lock.json changed, so every preview is in scope", said)
            self.assertEqual(len(calls), 16)

            said, calls = self.gate(repo, environment, log, UX_GATES_SINCE="no-such-ref")
            self.assertIn("Git cannot name a merge base, so every preview is in scope", said)
            self.assertEqual(len(calls), 16)

    def test_the_extension_writes_the_sharded_job_into_verify_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, environment, _ = self.adopted(directory)
            workflow = (repo / ".github/workflows/verify.yml").read_text()
            self.assertEqual(workflow.count("# extension:ux-gates:begin"), 1)
            job = workflow.split("# extension:ux-gates:begin", 1)[1]
            for line in ("  ux-gates:\n", "        shard: [1, 2, 3, 4, 5, 6]\n", "          fetch-depth: 0\n",
                         "      - run: python3 scripts/extensions/ux-gates/init.py\n",
                         "      - run: npx playwright install --with-deps chromium\n",
                         "      - run: python3 scripts/check-ux-gates.py\n", "          UX_GATES_REQUIRE: '1'\n",
                         "          UX_GATES_SHARD: ${{ matrix.shard }}/6\n",
                         "          UX_GATES_SINCE: ${{ github.event.pull_request.base.sha }}\n",
                         "          node-version: 24\n"):
                self.assertIn(line, job)
            self.assertNotIn("needs:", job)
            subprocess.run(["./init", "--integration", "codex", "--extension", "ux-gates"], cwd=repo, check=True,
                           env=environment, capture_output=True)
            self.assertEqual((repo / ".github/workflows/verify.yml").read_text(), workflow)
