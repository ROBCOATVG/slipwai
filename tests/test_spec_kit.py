"""Spec Kit arrives through `./init` and nowhere else, and its managed files are checked for drift."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase


class SpecKitTest(FactoryTestCase):
    def test_init_delegates_bootstrap_to_specify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "spec-driven-product")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            log = Path(directory) / "specify-args"
            fake = fake_bin / "specify"
            fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$SPECIFY_TEST_LOG\"\n")
            fake.chmod(0o755)
            environment = os.environ | {
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "SPECIFY_TEST_LOG": str(log),
            }

            subprocess.run(
                ["./init", "--integration", "codex", "--integration-options=--skills"],
                cwd=repo,
                check=True,
                env=environment,
            )

            self.assertEqual(
                log.read_text().splitlines(),
                ["init", "--here", "--force", "--integration", "codex", "--integration-options=--skills"],
            )
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())
            self.assertTrue((repo / ".agents/skills/drive/SKILL.md").is_file())

    def test_init_exposes_project_skills_and_commands_to_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "cursor-product")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "specify"
            fake.write_text(
                "#!/bin/sh\nmkdir -p .specify\n"
                "printf '%s\\n' "
                "'{\"installed_integrations\":[\"cursor-agent\"],\"default_integration\":\"cursor-agent\"}' "
                "> .specify/integration.json\n"
            )
            fake.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            result = subprocess.run(
                ["./init", "--integration", "cursor-agent"],
                cwd=repo,
                check=True,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
            )

            cursor_testing = (repo / ".cursor/skills/testing/SKILL.md").read_text()
            self.assertIn("Generated from skills/testing/SKILL.md", cursor_testing)
            self.assertIn("name: testing", cursor_testing)
            cursor_drive = (repo / ".cursor/skills/drive/SKILL.md").read_text()
            self.assertIn("name: drive", cursor_drive)
            self.assertIn("Deliver", cursor_drive)
            self.assertTrue((repo / ".cursor/skills/event-modeling/SKILL.md").is_file())
            self.assertIn("installed for Cursor", result.stdout)
            subprocess.run(["make", "check-agents"], cwd=repo, check=True)
            (repo / ".cursor/skills/testing/SKILL.md").write_text("drift\n")
            drift = subprocess.run(
                ["make", "check-agents"], cwd=repo, text=True, capture_output=True
            )
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("projection drift", drift.stderr)
            # The projections are derived and never committed: every harness directory is ignored, and a clone with
            # none — nobody has run `./init` in it — is not drift, which the gate says rather than fails.
            ignored = (repo / ".gitignore").read_text()
            for directory in (".cursor/skills/", ".claude/skills/", ".claude/commands/", ".agents/skills/"):
                self.assertIn(f"{directory}\n", ignored)
            shutil.rmtree(repo / ".cursor/skills")
            absent = subprocess.run(["make", "check-agents"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(absent.returncode, 0, absent.stdout + absent.stderr)
            self.assertIn("check-agents: Cursor: not projected here", absent.stdout)

    def test_speckit_gate_reads_an_absent_projection_directory_as_not_projected(self) -> None:
        """The failure this closes: native Spec Kit installs its own `speckit-*` skills into `.claude/skills/` and
        records their hashes in a committed manifest, and since 1.13.0 that directory is in `.gitignore` for the
        factory's projections, so every fresh clone had the manifest and none of the files and `make verify` was
        red in CI. The gate now reads that the way `check-agents` does; a file that is missing or edited while its
        directory is present is still drift."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "claude-product")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "specify"
            fake.write_text(
                "#!/bin/sh\nmkdir -p .specify\n"
                "printf '%s\\n' "
                "'{\"installed_integrations\":[\"claude\"],\"default_integration\":\"claude\"}' "
                "> .specify/integration.json\n"
            )
            fake.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
            subprocess.run(["./init", "--integration", "claude"], cwd=repo, check=True, env=environment)

            # What `specify init` leaves that the fake did not: its skills in the harness directory, and a manifest
            # per integration with a SHA-256 for each file it owns — Spec Kit's own under `.specify/`, which is
            # committed, and Claude Code's under `.claude/skills/`, which is not.
            def manifest(integration: str, files: list[str]) -> None:
                hashes = {relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest() for relative in files}
                (repo / ".specify/integrations").mkdir(parents=True, exist_ok=True)
                (repo / f".specify/integrations/{integration}.manifest.json").write_text(
                    json.dumps({"integration": integration, "files": hashes})
                )

            skills = [f".claude/skills/speckit-{name}/SKILL.md" for name in ("plan", "specify")]
            for skill in skills:
                (repo / skill).parent.mkdir(parents=True, exist_ok=True)
                (repo / skill).write_text(f"# {Path(skill).parent.name}\n")
            manifest("claude", skills)
            core = [".specify/templates/spec-template.md", ".specify/scripts/bash/common.sh"]
            for owned in core:
                (repo / owned).parent.mkdir(parents=True, exist_ok=True)
                (repo / owned).write_text(f"# {Path(owned).name}\n")
            manifest("speckit", core)
            self.assertIn(".claude/skills/\n", (repo / ".gitignore").read_text())

            complete = subprocess.run(["make", "check-speckit"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
            self.assertIn("2 manifest(s) match", complete.stdout)
            self.assertNotIn("not projected", complete.stdout)

            # A fresh clone: the manifest is committed and the directory it points into is not there.
            shutil.rmtree(repo / ".claude/skills")
            clone = subprocess.run(["make", "check-speckit"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(clone.returncode, 0, clone.stdout + clone.stderr)
            self.assertIn(
                "check-speckit: .claude/skills/: 2 file(s) managed by claude not projected here", clone.stdout
            )
            self.assertIn("2 manifest(s) match", clone.stdout)

            # The directory is there and a listed file is not: drift, exactly as before.
            (repo / skills[0]).parent.mkdir(parents=True)
            (repo / skills[0]).write_text("# speckit-plan\n")
            missing = subprocess.run(["make", "check-speckit"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn(f"{skills[1]}: missing (managed by claude)", missing.stderr)
            self.assertNotIn(skills[0], missing.stderr)
            self.assertNotIn("not projected", missing.stdout)

            # And an edited file, with its directory present, is drift too.
            (repo / skills[1]).parent.mkdir(parents=True)
            (repo / skills[1]).write_text("edited\n")
            edited = subprocess.run(["make", "check-speckit"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(edited.returncode, 0)
            self.assertIn(f"{skills[1]}: edited in place (managed by claude)", edited.stderr)

            # The committed manifest is never excused: its files sit in no projection directory.
            shutil.rmtree(repo / ".claude/skills")
            (repo / ".specify/templates/spec-template.md").write_text("edited\n")
            speckit = subprocess.run(["make", "check-speckit"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(speckit.returncode, 0)
            self.assertIn(".specify/templates/spec-template.md: edited in place (managed by speckit)", speckit.stderr)

    def test_speckit_gate_rejects_a_corrupted_preset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "corrupt-preset", "event-modelling", "python")
            preset = repo / ".specify/presets/event-modelling/preset.yml"

            # Spec Kit itself reports this only from `specify preset list`; resolution limps along off
            # `.registry`, so nothing in the workflow would notice.
            preset.unlink()
            result = subprocess.run(
                ["python3", "scripts/check-speckit.py"],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("corrupted preset", result.stderr)

            preset.write_text('provides:\n  templates:\n    - file: "templates/absent-template.md"\n')
            result = subprocess.run(
                ["python3", "scripts/check-speckit.py"],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("templates/absent-template.md", result.stderr)

            (repo / ".specify/presets/.registry").write_text("{not json")
            result = subprocess.run(
                ["python3", "scripts/check-speckit.py"],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid JSON", result.stderr)
