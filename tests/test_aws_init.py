"""`./init` in a project going to `aws`: the first-day step, and what a rerun of it does and does not do.

Split out of `test_aws_target.py` when that suite reached its budget. What the generated `init` says is
asserted there, alongside the rest of what an AWS project is given; what it *does* when run is here, with
every tool it looks for faked onto the PATH so the outcome is the script's decision and not the machine's.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default


class AwsInitTest(FactoryTestCase):
    def test_a_rerun_of_init_in_a_bootstrapped_project_leaves_the_account_alone(self) -> None:
        """`./init` is run again to answer an axis, add an extension or switch agent — local work — and
        every rerun on an AWS project used to end in `make bootstrap`, so an expired `aws` session failed a
        run whose real work was done. The committed bootstrap state is the evidence it already ran:
        present, `./init` says so and never calls `make bootstrap`; absent, the first-day path is unchanged.
        Every tool the preflight looks for is faked onto the PATH so the skip is proved to come from the
        state and not from a machine that happens to lack `tofu`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "rerun", "event-modelling", "go", "none", target="aws", event_store="memory",
                http=axis_default("http", "go", "aws"),
            )
            subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/rerun.git"], cwd=repo, check=True)
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            make_log = Path(directory) / "make-args"
            (fake_bin / "specify").write_text(
                "#!/bin/sh\nmkdir -p .specify\n"
                "printf '%s\\n' '{\"installed_integrations\":[\"claude\"],\"default_integration\":\"claude\"}' "
                "> .specify/integration.json\n"
            )
            (fake_bin / "make").write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" >> \"$MAKE_TEST_LOG\"\nexit 1\n")
            for tool in ("tofu", "aws", "gh"):
                (fake_bin / tool).write_text("#!/bin/sh\nexit 0\n")
            for fake in fake_bin.iterdir():
                fake.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}", "MAKE_TEST_LOG": str(make_log)}
            state = repo / "infra/bootstrap/terraform.tfstate"

            state.write_text("{}\n")
            rerun = subprocess.run(
                ["./init", "--integration", "claude"], cwd=repo, env=environment, text=True, capture_output=True
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertFalse(make_log.exists(), "make bootstrap ran in a bootstrapped project")
            self.assertIn("Already bootstrapped", rerun.stdout.splitlines()[-1])
            self.assertIn("make bootstrap", rerun.stdout.splitlines()[-1])
            self.assertNotIn("bootstrapping it needs", rerun.stdout)
            self.assertTrue((repo / ".claude/commands/drive.md").is_file())  # the local work was done

            state.unlink()
            first = subprocess.run(
                ["./init", "--integration", "claude"], cwd=repo, env=environment, text=True, capture_output=True
            )
            self.assertEqual(make_log.read_text().splitlines(), ["bootstrap"])
            self.assertEqual(first.returncode, 1)  # a first bootstrap that fails is still a failed ./init
            self.assertIn("run `make bootstrap` again", first.stderr)
