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
                ["init", "--here", "--force", "--integration", "codex", "--integration-options=--skills",
                 "--script", "sh"],
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

    def test_init_gives_spec_kits_scripts_pyyaml_with_no_step_of_yours(self) -> None:
        """From Spec Kit 1.0.9 its bash scripts compose the preset templates with PyYAML on the bare `python3`
        they call, and a project whose python3 lacks it learns so at its first `/speckit-specify`: "PyYAML is
        required", with no remedy, and on a PEP 668 Python the obvious `pip install` is refused too. Those
        scripts take `python3` off the PATH, so `./init` has uv put PyYAML where it looks — its venv, or `--target`
        its user site — never asking for a venv on PATH. Without uv it says the line that installs uv, and a Spec
        Kit whose scripts never mention PyYAML gets no word about it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "yaml-less")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            no_uv_bin = Path(directory) / "no-uv-bin"
            no_uv_bin.mkdir()
            site = Path(directory) / "user-site"
            calls = Path(directory) / "uv-calls"
            (fake_bin / "specify").write_text("#!/bin/sh\nexit 0\n")
            # A python3 whose `yaml` is whatever the user site holds, which answers the question of where it
            # looks as INIT_TEST_HOME says (`venv`, or its user site), and a uv that records what it was
            # asked and puts PyYAML there.
            (fake_bin / "python3").write_text(f"""#!/bin/sh
case "$*" in
  "-c import yaml") [ -f "{site}/yaml/__init__.py" ] && exit 0; exit 1 ;;
  "-c import site, sys;"*) if [ "$INIT_TEST_HOME" = venv ]; then echo venv; else echo "{site}"; fi; exit 0 ;;
esac
exec {shutil.which("python3")} "$@"
""")
            (fake_bin / "uv").write_text(f"""#!/bin/sh
echo "$*" >> "{calls}"
mkdir -p "{site}/yaml" && touch "{site}/yaml/__init__.py"
""")
            for tool in ("specify", "python3", "uv"):
                (fake_bin / tool).chmod(0o755)
            for tool in ("specify", "python3"):
                (no_uv_bin / tool).symlink_to(fake_bin / tool)
            scripts = repo / ".specify/scripts/bash"
            scripts.mkdir(parents=True)
            system_path = ":".join(
                entry for entry in os.environ["PATH"].split(":") if not (Path(entry) / "uv").exists()
            )

            def init(home: str, uv: bool = True) -> subprocess.CompletedProcess[str]:
                shutil.rmtree(site, ignore_errors=True)
                calls.unlink(missing_ok=True)
                return subprocess.run(
                    ["./init", "--integration", "codex"], cwd=repo, text=True, capture_output=True,
                    env=os.environ | {  # its own HOME: `./init` looks under `~/.local/bin` for a uv it installed
                        "PATH": f"{fake_bin if uv else no_uv_bin}:{system_path}", "INIT_TEST_HOME": home,
                        "HOME": directory,
                    },
                )

            (scripts / "common.sh").write_text("#!/usr/bin/env bash\necho 'no composition here'\n")
            silent = init("site")
            self.assertEqual(silent.returncode, 0, silent.stderr)
            self.assertNotIn("PyYAML", silent.stdout + silent.stderr)
            self.assertFalse(calls.exists())

            (scripts / "common.sh").write_text(
                '#!/usr/bin/env bash\necho "Error: PyYAML is required to resolve preset template composition" >&2\n'
            )
            to_site = init("site")
            self.assertEqual(to_site.returncode, 0, to_site.stderr)
            self.assertIn("Installed PyYAML for python3", to_site.stdout)
            self.assertEqual(calls.read_text(), f"pip install --quiet --python python3 --target {site} PyYAML\n")
            self.assertNotIn("export PATH", to_site.stdout + to_site.stderr)
            self.assertFalse((repo / ".delivery-tools/venv").exists())

            in_venv = init("venv")
            self.assertIn("Installed PyYAML for python3", in_venv.stdout)
            self.assertEqual(calls.read_text(), "pip install --quiet --python python3 PyYAML\n")

            # Windows: Spec Kit installs its PowerShell scripts, whose `create-new-feature.ps1` needs PyYAML
            # just the same, and the bash ones never arrive — so the step reads both.
            (scripts / "common.sh").write_text("#!/usr/bin/env bash\necho 'no composition here'\n", encoding="utf-8")
            powershell = repo / ".specify/scripts/powershell"
            powershell.mkdir(parents=True)
            (powershell / "common.ps1").write_text(
                'throw "Python 3 and PyYAML are required to resolve preset template composition"\n', encoding="utf-8"
            )
            on_windows = init("site")
            self.assertIn("Installed PyYAML for python3", on_windows.stdout)
            self.assertEqual(calls.read_text(), f"pip install --quiet --python python3 --target {site} PyYAML\n")

            without_uv = init("site", uv=False)
            self.assertEqual(without_uv.returncode, 0, without_uv.stderr)
            self.assertIn("it could not be\ninstalled for the python3 on PATH here", without_uv.stderr)
            self.assertIn("On this machine, uv installs with:", without_uv.stderr)
            self.assertIn('stops with "PyYAML is required"', without_uv.stderr)

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
