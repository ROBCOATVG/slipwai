"""How AGENTS.md reaches the file a harness actually reads — `contextMode` in
`scripts/agents/registry.json`, projected by `scripts/agents/project.py`. A `canonical` harness reads
AGENTS.md under its own name and needs nothing; an `import` one reads it through an include; a `copy` one
gets the marker-fenced regions carried into a file Spec Kit wrote before the extension hooks ran. See
docs/agent-harnesses.md."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

FAKE_SPECIFY = "#!/bin/sh\nexit 0\n"


class AgentContextTest(FactoryTestCase):
    def fixture(self, directory: str, name: str) -> tuple[Path, dict[str, str]]:
        """A generated repository with `specify` and `codegraph` stubbed on PATH, so `./init` runs its
        whole sequence — projection, extension hooks, then the context-only pass — without either CLI."""
        repo = self.generate(directory, name)
        fake_bin = Path(directory) / "fake-bin"
        fake_bin.mkdir()
        for tool, body in (("specify", FAKE_SPECIFY), ("codegraph", "#!/bin/sh\nexit 0\n")):
            (fake_bin / tool).write_text(body)
            (fake_bin / tool).chmod(0o755)
        return repo, os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

    def test_a_copy_mode_harness_gains_the_extension_guidance_it_missed(self) -> None:
        """A `contextMode: copy` harness reads a file Spec Kit wrote before the extension hooks, so the
        context-only pass carries each extension's marker-fenced guidance into it. Gemini is the copy-mode
        case; `codex` is canonical and reads AGENTS.md itself."""
        with tempfile.TemporaryDirectory() as directory:
            repo, environment = self.fixture(directory, "codegraph-copy-mode")
            # What `specify init` leaves behind for a copy-mode harness, which the fake specify does not.
            (repo / "GEMINI.md").write_text("# Gemini\n\nSpec Kit's own copy of the project context.\n")

            for _ in range(2):
                subprocess.run(
                    ["./init", "--integration", "gemini", "--extension", "codegraph"],
                    cwd=repo, check=True, env=environment,
                )

            context = (repo / "GEMINI.md").read_text()
            self.assertEqual(context.count("<!-- extension:codegraph:begin -->"), 1)
            self.assertIn("codegraph_explore", context)
            # The rest belongs to Spec Kit; copying AGENTS.md whole would duplicate its baseline context.
            self.assertIn("Spec Kit's own copy of the project context.", context)

    def test_check_agents_reports_a_context_file_that_missed_extension_guidance(self) -> None:
        """AGENTS.md carries an extension pointer and the copy the agent reads does not."""
        with tempfile.TemporaryDirectory() as directory:
            repo, environment = self.fixture(directory, "codegraph-drift")
            (repo / "GEMINI.md").write_text("# Gemini\n")

            subprocess.run(
                ["./init", "--integration", "gemini", "--extension", "codegraph"],
                cwd=repo, check=True, env=environment,
            )

            def check() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["python3", "scripts/agents/project.py", "--check", "gemini"],
                    cwd=repo, env=environment, text=True, capture_output=True,
                )

            self.assertEqual(check().returncode, 0)

            # Put the copy back the way a stale one looks.
            (repo / "GEMINI.md").write_text("# Gemini\n")
            gone = check()
            self.assertEqual(gone.returncode, 1)
            self.assertIn("GEMINI.md", gone.stderr)

            # Presence is not currency: a copy with the right markers and old factory text must fail too.
            stale = (repo / "AGENTS.md").read_text().split(
                "<!-- extension:codegraph:begin -->", 1
            )[1].split("<!-- extension:codegraph:end -->", 1)[0]
            (repo / "GEMINI.md").write_text(
                "# Gemini\n\n<!-- extension:codegraph:begin -->\n"
                + stale.replace("CodeGraph", "OldGraph")
                + "<!-- extension:codegraph:end -->\n"
            )
            drifted = check()
            self.assertEqual(drifted.returncode, 1)
            self.assertIn("out of date", drifted.stderr)
            subprocess.run(
                ["python3", "scripts/agents/project.py", "--context", "gemini"],
                cwd=repo, check=True, env=environment,
            )
            self.assertEqual(check().returncode, 0)

    def test_an_import_mode_harness_is_given_the_include_that_reaches_agents_md(self) -> None:
        """`contextMode: import` was declared for Claude Code and built nowhere, so a session saw no part
        of AGENTS.md — not the CodeGraph pointer, and not `Delegated agents` or the continuation contract
        either. The include is one line in a region the projector owns; everything in AGENTS.md follows
        from it, and what the user wrote around it survives."""
        with tempfile.TemporaryDirectory() as directory:
            repo, environment = self.fixture(directory, "claude-import-mode")
            # A CLAUDE.md somebody wrote in before this factory ever ran, which must come through intact.
            house_rules = "# House rules\n\nAsk before force-pushing.\n"
            (repo / "CLAUDE.md").write_text(house_rules)
            # What a real `specify init` records and the fake one does not, so `make agents` — which takes
            # no harness argument — can find the integration the way it does in a generated project.
            (repo / ".specify").mkdir(exist_ok=True)
            (repo / ".specify/integration.json").write_text(
                json.dumps({"installed_integrations": ["claude"], "default_integration": "claude"})
            )

            for _ in range(2):
                subprocess.run(
                    ["./init", "--integration", "claude", "--extension", "codegraph"],
                    cwd=repo, check=True, env=environment,
                )

            context = (repo / "CLAUDE.md").read_text()
            # Running twice is running once: `claude` is multiInstallSafe, so this pass repeats.
            self.assertEqual(context.count("<!-- slipwai:agents-import:begin -->"), 1)
            self.assertIn("@AGENTS.md", context)
            self.assertIn("Ask before force-pushing.", context)
            # The point of the include: the whole file arrives, not just the extension pointer.
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:codegraph:begin -->", agents)
            self.assertIn("## Delegated agents", agents)
            # ...and precisely because it arrives by reference, none of it is duplicated here.
            self.assertNotIn("codegraph_explore", context)

            def check() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["python3", "scripts/agents/project.py", "--check", "claude"],
                    cwd=repo, env=environment, text=True, capture_output=True,
                )

            self.assertEqual(check().returncode, 0)

            # Delete the region and the gate must say so — a mode that cannot fail the gate is a mode that
            # quietly stops working. `make agents` then puts it back without touching what is around it.
            (repo / "CLAUDE.md").write_text(house_rules)
            failed = check()
            self.assertEqual(failed.returncode, 1)
            self.assertIn("CLAUDE.md", failed.stderr)
            self.assertIn("AGENTS.md", failed.stderr)
            # By reference, so an edit to AGENTS.md can never put this one out of date.
            with (repo / "AGENTS.md").open("a") as handle:
                handle.write("\n## Something added later\n")

            made = subprocess.run(
                ["make", "agents"], cwd=repo, env=environment, text=True, capture_output=True,
            )
            self.assertEqual(made.returncode, 0, made.stderr)
            restored = (repo / "CLAUDE.md").read_text()
            self.assertIn("@AGENTS.md", restored)
            self.assertIn("Ask before force-pushing.", restored)
            self.assertEqual(check().returncode, 0)

            # No context file at all is the state the bug actually produced, where Claude Code walked up
            # and loaded a stranger's CLAUDE.md. That must fail too, not pass silently.
            (repo / "CLAUDE.md").unlink()
            absent = check()
            self.assertEqual(absent.returncode, 1)
            self.assertIn("CLAUDE.md", absent.stderr)
