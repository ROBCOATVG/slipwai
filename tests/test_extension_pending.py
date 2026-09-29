"""An extension chosen before it can be set up waits, and sets itself up the moment it can.

UI/UX Pro Max and the UX gates need a browser app. In an adopted repository the frontend is only a candidate until
`/ground` confirms it, and the first real adoption ticked both and was told to come back with a command; in a
headless generated project the same. Now the choice is kept, `make verify` holds it to nothing yet, and the
re-projection that confirming or adding a frontend runs installs them — nothing for anyone to run again.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import test_design_extensions as design  # the module, not its class, so its tests are not collected here twice
from support import FactoryTestCase


class PendingExtensionsTest(FactoryTestCase):
    fake_bin = design.DesignExtensionsTest.fake_bin

    def test_chosen_before_there_is_a_browser_app_they_wait_and_install_themselves_once_one_exists(self) -> None:
        """Ticked in a project with no screen yet — an adopted repository whose frontend is still a candidate, or a
        headless one — the extensions are not refused with a command to come back and run. They are recorded and
        wait, and `make verify` holds them to nothing yet; the first re-projection that finds a browser app (what
        confirming a frontend, or adding one, runs) sets both up, with nothing for anyone to run again."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", frontend="none")
            fake_bin = self.fake_bin(directory, uipro=design.FAKE_UIPRO, npx=design.FAKE_NPX)
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
            self.assertIn("UI/UX Pro Max is chosen, and waits for a browser app", result.stdout)
            self.assertIn("The UX gates are chosen, and wait for a browser app", result.stdout)
            self.assertNotIn("slipwai add-frontend web\n", result.stderr)
            self.assertNotIn("<!-- extension:uipro:begin -->", (repo / "AGENTS.md").read_text())
            self.assertFalse((repo / "skills/ui-ux-pro-max").exists())
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text())["extensions"], ["uipro", "ux-gates"]
            )
            checked = subprocess.run(
                ["python3", "scripts/extensions/project.py", "--check"], cwd=repo, env=environment,
                text=True, capture_output=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)

            # A browser app arrives — what `/ground` confirming a frontend, or `add-frontend`, leaves in the record.
            manifest = json.loads((repo / "project.json").read_text())
            manifest["deployables"]["web"] = {"path": "apps/web", "capabilities": ["frontend"]}
            (repo / "project.json").write_text(json.dumps(manifest, indent=2) + "\n")
            (repo / "apps/web/src").mkdir(parents=True)
            subprocess.run(["python3", "scripts/extensions/project.py"], cwd=repo, env=environment, check=True)

            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:uipro:begin -->", agents)
            self.assertIn("<!-- extension:ux-gates:begin -->", agents)
            self.assertTrue((repo / "skills/ui-ux-pro-max/SKILL.md").is_file())
            self.assertTrue((repo / "tools/ux-gates/scripts/lint_hardcodes.py").is_file())

