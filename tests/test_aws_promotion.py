"""Whether a project has a production yet, and how it gets one.

`--target aws` applies staging and production on the first green push unless the project says otherwise, and
two environments cost twice one. These are the three places that decision is made and honoured: `make
bootstrap`, which decides it once and writes it down; `promoting`, which answers with a commit staging has
actually run; and the verbs that address an environment nothing has deployed yet. The condition on the
pipeline's own production job is in `test_aws_workflows.py`, with the rest of the workflow.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default


class AwsPromotionTest(FactoryTestCase):
    def generate_aws(
        self, directory: str, name: str, backend: str = "typescript", frontend: str = "react-vite", **axes
    ):
        return self.generate(
            directory, name, "event-modelling", backend, frontend, target="aws",
            event_store=axes.pop("event_store", "postgres"), http=axis_default("http", backend, "aws"),
            **axes,
        )

    def test_bootstrap_decides_how_production_is_deployed_and_writes_it_down(self) -> None:
        """Two environments cost twice one, so whether production is deployed at all is a decision this
        script makes once and records — in `infra/auto-promote` for the next run of itself, and on the forge
        as the `AUTO_PROMOTE` variable, which is the only thing `deploy.yml` reads to decide."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "paid", "go", "none", event_store="memory")
            subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/paid.git"], cwd=repo, check=True)
            script = ["python3", "scripts/bootstrap.py", "--plan"]
            env = {**os.environ, "AWS_REGION": "eu-west-2"}
            # The default is the pipeline this target was designed around: every green commit, all the way.
            default = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env, check=True).stdout
            self.assertIn("auto-promote true: every commit that passes verify on main", default)
            self.assertIn("IMAGE_REGISTRY, AUTO_PROMOTE", default)
            # `--plan` changes nothing, and that has to include the file this decision is written to.
            self.assertFalse((repo / "infra/auto-promote").exists())
            asked = subprocess.run(
                [*script, "--auto-promote", "false"], cwd=repo, text=True, capture_output=True, env=env, check=True
            ).stdout
            self.assertIn("auto-promote false: staging on every green push", asked)
            self.assertIn("`make promote` says so", asked)
            # A run that means it writes the answer down, so a second bootstrap — after `add-service`, or
            # from somebody else's laptop — does not quietly put this project back on the default.
            (repo / "infra/auto-promote").write_text("false\n")
            remembered = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env, check=True).stdout
            self.assertIn("auto-promote false", remembered)
            # Not a terminal here, so nothing is asked and the default stands — and a file saying something
            # this script does not understand is not obeyed.
            (repo / "infra/auto-promote").write_text("whenever\n")
            nonsense = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env, check=True).stdout
            self.assertIn("auto-promote true:", nonsense)

    def test_promoting_answers_with_a_commit_staging_has_run_and_refuses_any_other(self) -> None:
        """What keeps "production only ever runs what staging has run" true even when a person types the
        commit: the verb `production.yml` resolves with reads staging's own release record, and a commit
        that is not in it is refused rather than deployed."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "shipped")
            tools = Path(directory) / "bin"
            tools.mkdir()
            newer, older = "a" * 40, "b" * 40
            # `releases()` lists the bucket and reads each record back; this is a two-release staging.
            # `aws s3 ls <prefix>` and `aws s3 cp <url> -`, so the key is the third argument either way.
            (tools / "aws").write_text(
                "#!/bin/sh\n"
                'if [ "$2" = "ls" ]; then\n'
                f"  echo '2026-09-10 09:00:00 120 20260910T090000Z-{newer}.json'\n"
                f"  echo '2026-09-09 09:00:00 120 20260909T090000Z-{older}.json'\n"
                "  exit 0\n"
                "fi\n"
                'case "$3" in\n'
                f"""  *20260910*) echo '{{"sha": "{newer}", "images": {{}}, "at": "20260910T090000Z"}}' ;;\n"""
                f"""  *) echo '{{"sha": "{older}", "images": {{}}, "at": "20260909T090000Z"}}' ;;\n"""
                "esac\n"
            )
            (tools / "aws").chmod(0o755)
            def promoting(*arguments: str) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["python3", "scripts/deploy.py", "promoting", "staging", *arguments],
                    cwd=repo, text=True, capture_output=True,
                    env={
                        **os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
                        "TOFU_STATE_BUCKET": "shipped-tofu-state", "AWS_REGION": "us-west-2",
                    },
                )
            # Nothing but the commit on stdout: the workflow reads this as a step output.
            newest = promoting()
            self.assertEqual(newest.returncode, 0, newest.stderr)
            self.assertEqual(newest.stdout, newer + "\n")
            # A blank input is what the workflow passes when the field was left empty.
            self.assertEqual(promoting("").stdout, newer + "\n")
            # An older release staging has run, named by a prefix.
            self.assertEqual(promoting(older[:8]).stdout, older + "\n")
            unrun = promoting("c" * 12)
            self.assertEqual(unrun.returncode, 1)
            self.assertIn("production is only ever given a commit staging has run", unrun.stderr)
            self.assertIn("aaaaaaaaaaaa (20260910T090000Z)", unrun.stderr)
            short = promoting("abc")
            self.assertEqual(short.returncode, 1)
            self.assertIn("too short to name a commit", short.stderr)

    def test_an_environment_nothing_has_deployed_says_so_rather_than_failing_on_an_output(self) -> None:
        """Without auto-promotion an empty production workspace is a state a project is in on purpose,
        and `tofu` makes a workspace on selection — so there is nothing to tell it from a fresh environment
        by, and `KeyError: url` is the wrong way to say it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "unpromoted")
            tools = Path(directory) / "bin"
            tools.mkdir()
            (tools / "tofu").write_text(
                "#!/bin/sh\n"
                'for argument in "$@"; do\n'
                '  if [ "$argument" = "output" ]; then echo "{}"; exit 0; fi\n'
                "done\n"
            )
            (tools / "aws").write_text("#!/bin/sh\nexit 0\n")
            for tool in ("tofu", "aws"):
                (tools / tool).chmod(0o755)
            environment = {
                **os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
                "TOFU_STATE_BUCKET": "unpromoted-tofu-state", "AWS_REGION": "us-west-2",
            }
            asked = subprocess.run(
                ["python3", "scripts/deploy.py", "url", "production"],
                cwd=repo, text=True, capture_output=True, env=environment,
            )
            self.assertEqual(asked.returncode, 1)
            self.assertIn("production has not been deployed yet", asked.stderr)
            self.assertIn("make promote", asked.stderr)
            self.assertEqual(asked.stdout, "")
            # Staging is not promoted into existence, so it is told the verb that does create it.
            staging = subprocess.run(
                ["python3", "scripts/deploy.py", "url", "staging"],
                cwd=repo, text=True, capture_output=True, env=environment,
            )
            self.assertEqual(staging.returncode, 1)
            self.assertIn("make deploy ENV=staging", staging.stderr)
            self.assertNotIn("make promote", staging.stderr)
