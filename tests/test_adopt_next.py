"""`slipwai adopt --next`, and the intro questions a terminal cannot answer well.

The adoption report names a sequence — `./init`, `/ground`, the gate, the root Makefile, a strategy ADR —
that takes longer than one sitting, and prints it once, at the end of the longest output the factory
produces. What is gated here is that the sequence is *derived* rather than remembered: every step leaves a
mark on the tree, so `--next` reads the marks and says where somebody is, and keeps saying it correctly as
the marks appear. Gated beside it is the first question to leave the terminal interview under
`--experimental-intro`: the language, which the line above it has already printed.
"""
from __future__ import annotations

import json
import os
import pty
import select
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_replay import git

from slipwai.assets import ROOT
from slipwai.convergence import AXES
from slipwai.harness import ENVIRONMENT

# This suite's own runs must not inherit the harness that is running the suite: a developer running
# `make test` from inside a coding agent would otherwise have every detection test see that agent. Derived
# from the table rather than listed, so a row added there is stripped here too.
BARE = {
    name: value for name, value in os.environ.items()
    if name not in {variable for variables in ENVIRONMENT.values() for variable in variables}
}

NODE = {
    "package.json": json.dumps({"name": "shop", "scripts": {"lint": "eslint .", "test": "jest"}}),
    "sub/package.json": json.dumps({"name": "widget", "scripts": {"lint": "eslint ."}}),
    "Makefile": "all:\n\t@echo theirs\n",
}


def in_terminal(repo: Path, *arguments: str, keys: int = 40, environment: dict | None = None) -> str:
    """`slipwai` run against a pseudo-terminal, so the interview asks rather than refusing, with Enter
    pressed at every question — the walk this is about, and the one that wrapped four theme bundles.

    Enter is sent when the child goes quiet rather than all at once up front: the interview reads the
    terminal a keystroke at a time once a list is live, and a buffer handed to it whole deadlocks against
    its own echo. One key per quiet second is also what a person does.
    """
    primary, secondary = pty.openpty()
    process = subprocess.Popen(
        [str(ROOT / "slipwai"), *arguments], cwd=repo, stdin=secondary, stdout=secondary, stderr=secondary,
        env={**os.environ, **(environment or {})},
    )
    os.close(secondary)
    output = bytearray()
    sent = 0
    deadline = time.monotonic() + 180
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([primary], [], [], 1.0)
            if ready:
                try:
                    chunk = os.read(primary, 4096)
                except OSError:  # the child closed its end: it is done
                    break
                if not chunk:
                    break
                output += chunk
            elif process.poll() is not None:
                break
            elif sent < keys:
                os.write(primary, b"\r")
                sent += 1
    finally:
        os.close(primary)
        if process.poll() is None:
            process.kill()
        process.wait(timeout=30)
    return output.decode(errors="replace")


class NextStepsTest(FactoryTestCase):
    def test_a_fresh_adoption_puts_init_now_and_everything_after_it_then(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", NODE)
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            result = slipwai(repo, "adopt", "--next")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("now:  ./delivery/init", result.stdout)
            self.assertIn("then: /ground, in the agent", result.stdout)
            self.assertIn(f"{len(AXES)} of {len(AXES)} rows of the map are nobody's word yet", result.stdout)
            self.assertIn("then: make -f delivery/Makefile verify", result.stdout)
            self.assertIn("then: add `-include delivery/Makefile` to the root Makefile", result.stdout)
            self.assertIn("then: an accepted ADR with a `Strategy:` line", result.stdout)
            self.assertNotIn("done:", result.stdout, "nothing has been done yet")

    def test_each_step_turns_to_done_as_the_mark_it_leaves_appears(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", NODE)
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            (repo / ".specify").mkdir(exist_ok=True)
            (repo / ".specify/integration.json").write_text('{"ai": "claude"}')
            after_init = slipwai(repo, "adopt", "--next").stdout
            self.assertIn("done: ./delivery/init", after_init)
            self.assertIn("now:  /ground, in the agent", after_init)

            (repo / "delivery/baseline.json").write_text("{}")
            with (repo / "Makefile").open("a") as makefile:
                makefile.write("-include delivery/Makefile\n")
            after_gate = slipwai(repo, "adopt", "--next").stdout
            self.assertIn("done: make -f delivery/Makefile verify", after_gate)
            self.assertIn("done: add `-include delivery/Makefile` to the root Makefile", after_gate)
            self.assertIn("now:  /ground, in the agent", after_gate, "the order stands; only the marks moved")

    def test_a_row_a_person_placed_is_counted_off_the_open_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", NODE)
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            manifest = repo / "project.json"
            document = json.loads(manifest.read_text())
            document["convergence"][0] = {**document["convergence"][0], "provenance": "confirmed"}
            manifest.write_text(json.dumps(document, indent=2))
            result = slipwai(repo, "adopt", "--next")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"{len(AXES) - 1} of {len(AXES)} rows of the map are nobody's word yet", result.stdout)

    def test_an_application_nobody_has_started_is_said_and_named(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", NODE)
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            result = slipwai(repo, "adopt", "--next")
            self.assertIn("2 of 2 application(s) have no `smoke` recorded", result.stdout)
            self.assertIn("shop, sub", result.stdout)

    def test_a_generated_project_is_refused_because_it_stands_in_no_such_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate(Path(directory), "shop")
            result = slipwai(project, "adopt", "--next")
            self.assertEqual(result.returncode, 2)
            self.assertIn("generated, not adopted", result.stderr)

    def test_the_adoption_report_says_the_list_it_just_printed_can_be_asked_for_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", NODE)
            result = slipwai(repo, "adopt", "--yes")
            self.assertIn("`slipwai adopt --next` says where you are in it", result.stdout)


class ReshapedIntroTest(FactoryTestCase):
    def test_the_interview_asks_the_language_it_has_just_printed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            output = in_terminal(repo, "adopt")
            self.assertIn("Found a node build at the repository root (.): javascript.", output)
            self.assertIn("Language [javascript]", output, "today it asks again; the switch is what removes it")

    def test_the_reshaped_intro_shows_the_language_instead_of_asking_for_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            output = in_terminal(repo, "adopt", "--experimental-intro")
            self.assertIn("Found a node build at the repository root (.): javascript.", output)
            self.assertNotIn("Language [javascript]", output)
            self.assertIn("`--language NAME=LANGUAGE` is where to correct one", output)
            self.assertEqual(json.loads((repo / "project.json").read_text())["deployables"]["shop"]["language"],
                             "javascript")

    def test_the_switch_is_the_environment_too_so_a_test_run_does_not_retype_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            output = in_terminal(repo, "adopt", environment={"SLIPWAI_EXPERIMENTAL_INTRO": "1"})
            self.assertNotIn("Language [javascript]", output)
            self.assertIn("`--language NAME=LANGUAGE` is where to correct one", output)


class HarnessTest(FactoryTestCase):
    """Which coding agent the material is projected into. `./init` has always asked, after `adopt` had already
    finished — one step too late to be any use to the adoption, since the questions worth handing to an agent
    are asked before there is one. It is also mostly answerable without asking: the environment a run started
    in says so, and a repository a team already uses an agent in says so in the tree. What neither says stays
    `unrecorded`, because a thirty-six-row list is not a question a terminal can ask well."""

    def test_nothing_saying_which_agent_is_recorded_as_nobody_having_said(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", environment=BARE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent: not recorded — nothing here says which one", result.stdout)
            self.assertEqual(
                json.loads((repo / "project.json").read_text())["agent"], {"provenance": "unrecorded"}
            )

    def test_the_harness_a_run_started_from_is_detected_from_its_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", environment={**BARE, "CLAUDECODE": "1"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent: Claude Code (Claude Code set CLAUDECODE", result.stdout)
            recorded = json.loads((repo / "project.json").read_text())["agent"]
            self.assertEqual(recorded["harness"], "claude")
            self.assertEqual(recorded["provenance"], "detected")

    def test_an_agent_the_tree_already_reads_for_is_detected_from_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": NODE["package.json"], ".claude/skills/theirs/SKILL.md": "# theirs\n",
            })
            result = slipwai(repo, "adopt", "--yes", environment=BARE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("which only Claude Code reads", result.stdout)
            self.assertEqual(json.loads((repo / "project.json").read_text())["agent"]["harness"], "claude")

    def test_a_tree_that_reads_for_two_records_neither_because_that_is_a_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": NODE["package.json"],
                ".cursor/skills/a.md": "a\n",
                ".gemini/commands/b.md": "b\n",
            })
            result = slipwai(repo, "adopt", "--yes", environment=BARE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("this tree reads for more than one (Cursor, Gemini CLI)", result.stdout)
            self.assertEqual(
                json.loads((repo / "project.json").read_text())["agent"], {"provenance": "unrecorded"}
            )

    def test_a_directory_two_harnesses_read_names_neither(self) -> None:
        from slipwai.harness import marks

        self.assertEqual(marks().get(".claude/skills"), "claude")
        self.assertIsNone(marks().get(".agents/skills"), "Codex, Zed and Antigravity all read it")
        self.assertIsNone(marks().get("AGENTS.md"), "every canonical harness writes it")

    def test_naming_the_agent_outranks_what_was_detected_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", "--integration", "cursor-agent",
                             environment={**BARE, "CLAUDECODE": "1"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent: Cursor (named)", result.stdout)
            recorded = json.loads((repo / "project.json").read_text())["agent"]
            self.assertEqual(recorded["harness"], "cursor-agent")
            self.assertEqual(recorded["provenance"], "overridden")

    def test_a_harness_the_registry_does_not_know_is_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", "--integration", "nonsense")
            self.assertEqual(result.returncode, 2)
            self.assertIn("the agent registry has no such harness", result.stderr)
            self.assertFalse((repo / "project.json").exists(), "refused before a byte was written")

    def test_a_recorded_agent_changes_what_the_report_says_init_will_ask(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            known = slipwai(repo, "adopt", "--yes", environment={**BARE, "CLAUDECODE": "1"}).stdout
            self.assertIn("projects the skills and commands into Claude Code, which this record already names, "
                          "so it asks nothing", known)
            self.assertNotIn("asks which coding agent", known)
        with tempfile.TemporaryDirectory() as directory:
            bare = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            self.assertIn("asks which coding agent", slipwai(bare, "adopt", "--yes", environment=BARE).stdout)

    def test_a_re_survey_carries_the_recorded_agent_rather_than_re_reading_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            self.assertEqual(
                slipwai(repo, "adopt", "--yes", "--integration", "cursor-agent").returncode, 0
            )
            # `adopt` commits its own work, so the tree a re-survey needs clean already is.
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertEqual(slipwai(repo, "adopt", "--refresh", environment=BARE).returncode, 0)
            self.assertEqual(
                json.loads((repo / "project.json").read_text())["agent"]["harness"], "cursor-agent",
                "a re-survey reads the tree; which agent gets the material is not something the tree says",
            )


class RunInitTest(FactoryTestCase):
    """`./init` is the one step that reaches the network, so `adopt` runs it last, after its own commit, and
    never inside it: an unreachable source then costs the adoption nothing. Off unless asked for, because
    every `--yes` in a script or a test would otherwise need the network."""

    def test_it_is_not_run_unless_asked_and_the_tree_is_left_clean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Running ./delivery/init", result.stdout)
            # `adopt` writes presets under `.specify/` itself; `integration.json` is Spec Kit's own, and the
            # only thing in that directory that says `./init` has run. `--next` reads the same file.
            self.assertTrue((repo / ".specify").is_dir(), "the constitution preset is adopt's own")
            self.assertFalse((repo / ".specify/integration.json").exists())
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_no_init_says_the_same_thing_out_loud(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", "--no-init")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Running ./delivery/init", result.stdout)

    def test_init_and_no_init_cannot_both_be_asked_for(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"package.json": NODE["package.json"]})
            result = slipwai(repo, "adopt", "--yes", "--init", "--no-init")
            self.assertEqual(result.returncode, 2)
            self.assertIn("not allowed with argument", result.stderr)
