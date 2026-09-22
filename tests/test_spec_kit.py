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

    def test_a_rerun_that_forwards_nothing_leaves_spec_kit_alone(self) -> None:
        """`./init --extension <key>` on an initialized project finishes without Spec Kit's source host.

        Every flag the scan lifts out is answered locally (or at the forge), so rerunning the bootstrap was
        the one step that needed the network — and the step that failed every rerun in an offline sandbox,
        before the rest of `./init` had done any of what it was asked. Generation itself ships presets under
        `.specify/`, so the evidence of a bootstrap is the integration record only `specify init` writes."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "rerun-product")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            log = Path(directory) / "specify-calls"
            fake = fake_bin / "specify"
            # Like real `specify init`, the fake records the installed integration — which is the mark the
            # skip reads, and what the projection step resolves the harness from.
            fake.write_text(
                "#!/bin/sh\nprintf 'ran\\n' >> \"$SPECIFY_TEST_LOG\"\nmkdir -p .specify\n"
                "printf '%s\\n' "
                "'{\"installed_integrations\":[\"codex\"],\"default_integration\":\"codex\"}' "
                "> .specify/integration.json\n"
            )
            fake.chmod(0o755)
            (fake_bin / "codegraph").write_text("#!/bin/sh\nexit 0\n")
            (fake_bin / "codegraph").chmod(0o755)
            environment = os.environ | {
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "SPECIFY_TEST_LOG": str(log),
            }

            # A generated project has presets under `.specify/` but no integration record: the first
            # `./init` must still bootstrap, whatever it was or was not passed.
            subprocess.run(["./init", "--extension", "codegraph"], cwd=repo, check=True, env=environment)
            self.assertEqual(log.read_text().splitlines(), ["ran"])

            rerun = subprocess.run(
                ["./init", "--extension", "codegraph"],
                cwd=repo,
                check=True,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(log.read_text().splitlines(), ["ran"], "the rerun reinstalled Spec Kit")
            self.assertIn("Spec Kit is already installed", rerun.stdout)
            self.assertIn("<!-- extension:codegraph:begin -->", (repo / "AGENTS.md").read_text())
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

            # Anything left to forward is Spec Kit's — a harness switch still delegates.
            subprocess.run(["./init", "--integration", "claude"], cwd=repo, check=True, env=environment)
            self.assertEqual(log.read_text().splitlines(), ["ran", "ran"])

    def test_init_gives_spec_kits_scripts_pyyaml_or_says_exactly_how_to(self) -> None:
        """From Spec Kit 1.0.9 its bash scripts compose the preset templates with PyYAML on the bare `python3`
        they call, and a project whose python3 lacks it learns so at its first `/speckit-specify`: "PyYAML is
        required", with no remedy, and on a PEP 668 Python the obvious `pip install` is refused too. So `./init`
        checks, where the installed scripts mention it, against a `python3` it cannot otherwise reach: a venv
        under `.delivery-tools/` that shares the system's packages, with the PATH line to use it, or the exact
        thing to install by hand. A Spec Kit whose scripts never mention it gets no word about it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "yaml-less")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text("#!/bin/sh\nexit 0\n")
            # A python3 with no `yaml`, whose pip refuses the user site, and whose venv is what the test says.
            (fake_bin / "python3").write_text(f"""#!/bin/sh
case "$*" in
  "-c import yaml") exit 1 ;;
  "-m pip install "*) exit 1 ;;
  "-m venv "*) [ "$INIT_TEST_VENV" = works ] || exit 1
     mkdir -p .delivery-tools/venv/bin && printf '#!/bin/sh\\nexit 0\\n' > .delivery-tools/venv/bin/python
     chmod 755 .delivery-tools/venv/bin/python; exit 0 ;;
esac
exec {shutil.which("python3")} "$@"
""")
            for tool in ("specify", "python3"):
                (fake_bin / tool).chmod(0o755)
            scripts = repo / ".specify/scripts/bash"
            scripts.mkdir(parents=True)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            def init(venv: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["./init", "--integration", "codex"], cwd=repo, text=True, capture_output=True,
                    env=environment | {"INIT_TEST_VENV": venv},
                )

            (scripts / "common.sh").write_text("#!/usr/bin/env bash\necho 'no composition here'\n")
            silent = init("fails")
            self.assertEqual(silent.returncode, 0, silent.stderr)
            self.assertNotIn("PyYAML", silent.stdout + silent.stderr)

            (scripts / "common.sh").write_text(
                '#!/usr/bin/env bash\necho "Error: PyYAML is required to resolve preset template composition" >&2\n'
            )
            by_hand = init("fails")
            self.assertEqual(by_hand.returncode, 0, by_hand.stderr)
            self.assertIn("Spec Kit's scripts need PyYAML on python3 to compose this project's preset templates, "
                          "and neither pip nor a\nvenv could install it here.", by_hand.stderr)
            self.assertIn("`python3 -m pip install --user PyYAML`", by_hand.stderr)
            self.assertIn('stops with "PyYAML is required"', by_hand.stderr)
            self.assertFalse((repo / ".delivery-tools/venv").exists())

            with_venv = init("works")
            self.assertEqual(with_venv.returncode, 0, with_venv.stderr)
            self.assertIn("A venv with it is at .delivery-tools/venv", with_venv.stderr)
            self.assertIn('export PATH="$PWD/.delivery-tools/venv/bin:$PATH"', with_venv.stderr)
            self.assertTrue((repo / ".delivery-tools/venv/bin/python").is_file())
            self.assertIn(".delivery-tools/", (repo / ".gitignore").read_text())

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
