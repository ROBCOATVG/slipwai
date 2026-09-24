"""Which coding agent the delivery material is projected into, and how a run establishes it without asking.

`./init` has always asked, after `adopt` had already finished — one step too late to be any use to the
adoption, since the questions worth handing to an agent are asked before there is one. It is also mostly
answerable without asking: the environment a run started in says so, a repository whose team already uses one
says so in the tree, and once `./init` *has* asked, Spec Kit's own record is a person's answer rather than
anybody's reading. What none of them says stays `unrecorded`, because a thirty-six-row list is not a question
a terminal can ask well and a tree that reads for two harnesses names neither.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_adopt_next import BARE, NODE
from test_replay import git

from slipwai.harness import registry


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

    def test_the_record_catches_up_with_the_harness_init_settled(self) -> None:
        """Where `adopt` could not tell, it hands the question to `./init` — which then asks it. The record
        follows, or it stays behind the truth: a fact nobody wrote down reads as one nobody established."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": NODE["package.json"],
                ".claude/skills/a.md": "a\n",
                "GEMINI.md": "g\n",
            })
            first = slipwai(repo, "adopt", "--yes", "--no-init", environment=BARE)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(
                json.loads((repo / "project.json").read_text())["agent"], {"provenance": "unrecorded"},
                "two harnesses read this tree, so adopt records neither",
            )
            (repo / ".specify").mkdir(exist_ok=True)
            (repo / ".specify/integration.json").write_text('{"integration": "gemini"}')
            recorded = slipwai(repo, "adopt", "--next", environment=BARE)
            self.assertEqual(recorded.returncode, 0, recorded.stderr)

    def test_spec_kits_answer_outranks_what_the_tree_and_the_environment_read(self) -> None:
        from slipwai.harness import detect

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".claude/skills").mkdir(parents=True)
            (root / ".specify").mkdir()
            (root / ".specify/integration.json").write_text('{"integration": "gemini"}')
            settled = detect(root, {"CLAUDECODE": "1"})
            self.assertEqual(settled.harness, "gemini", "a person answered it; the rest are readings")
            self.assertEqual(settled.provenance, "confirmed")

    def test_a_spec_kit_record_that_says_nothing_usable_is_not_read_as_an_answer(self) -> None:
        from slipwai.harness import from_spec_kit

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".specify").mkdir()
            for written in ("not json at all", '{"integration": "no-such-harness"}', '{"integration": 7}', "{}"):
                (root / ".specify/integration.json").write_text(written)
                self.assertIsNone(from_spec_kit(root), written)


class EveryHarnessReachesTest(FactoryTestCase):
    """Whether an adopted repository's own commands reach a harness that is not Claude Code.

    Thirty-six harnesses are declared and nobody is going to install thirty-six coding agents to find out.
    The registry is the contract they are held to, so the registry is what this asks: project an adoption
    into every harness it declares and require `/ground` to land somewhere a person can invoke it. Fifteen
    harnesses declare no `commandsDir` at all — Codex, Zed, Cursor and a dozen others — and for those a
    command is projected as a skill instead, which is the branch that had never been exercised for an
    adoption's own commands.
    """

    def adopted_repo(self, directory: str) -> Path:
        repo = repository(Path(directory), "shop", {
            "package.json": json.dumps({"name": "shop", "scripts": {"lint": "eslint ."}}),
        })
        done = slipwai(repo, "adopt", "--yes", "--experimental-intro", "--no-init", environment=BARE)
        self.assertEqual(done.returncode, 0, done.stderr)
        return repo

    def test_every_harness_either_has_somewhere_for_a_command_or_says_why_not(self) -> None:
        """The cheap half, and the one that catches a harness added tomorrow: the projector puts a command
        under `commandsDir`, or — where there is none — as a skill under `skillsDir`. A harness declaring
        neither would take the second branch with nowhere to write and lose the command set silently, so
        one declaring neither has to say so outright: `projectable: false` with the reason, which today is
        Hermes keeping its skills at `~/.hermes/skills`, outside any repository."""
        for row in registry():
            with self.subTest(harness=row["key"]):
                if row.get("projectable") is False:
                    self.assertTrue(
                        (row.get("unprojectableReason") or "").strip(),
                        f"{row['key']} is not projectable and does not say why",
                    )
                    continue
                self.assertTrue(
                    row.get("commandsDir") or row.get("skillsDir"),
                    f"{row['key']} declares neither, so a command has nowhere to go",
                )

    def test_ground_lands_for_every_harness_the_registry_knows(self) -> None:
        """The behavioural half: not an assertion about the table, but thirty-six projections that have to
        put the command on disk where that harness reads it."""
        description = "Ask the person what the tree cannot say"
        with tempfile.TemporaryDirectory() as directory:
            repo = self.adopted_repo(directory)
            projector = repo / "delivery/scripts/agents/project.py"
            self.assertTrue(projector.is_file(), "adopt writes the projector")
            for row in registry():
                key = row["key"]
                with self.subTest(harness=key):
                    done = subprocess.run(
                        ["python3", "delivery/scripts/agents/project.py", key],
                        cwd=repo, text=True, capture_output=True, check=False,
                    )
                    if row.get("projectable") is False:
                        # The declared exception is exercised rather than skipped: it has to refuse, and the
                        # refusal has to carry the reason the registry gives, or the exemption is a comment.
                        self.assertNotEqual(done.returncode, 0, f"{key} claims it cannot be projected")
                        said = done.stdout + done.stderr
                        self.assertIn("cannot be projected", said, f"{key} refused without saying why")
                        self.assertIn(row["name"], said, f"{key} refused without saying which harness")
                        continue
                    self.assertEqual(done.returncode, 0, f"{key}: {done.stderr}")
                    places = [row[field] for field in ("commandsDir", "skillsDir") if row.get(field)]
                    landed = [
                        found for place in places
                        for found in (repo / place).rglob("*")
                        if found.is_file() and description in found.read_text(errors="replace")
                    ]
                    self.assertTrue(
                        landed,
                        f"{key}: /ground reached none of {places} — a harness this factory says it supports "
                        f"whose person has no way to run the adoption's own question set",
                    )
