"""`./init`, run in a project that has just been made — in a terminal, and in the background for the board.

No real `./init` runs here and none ever should: the real one installs Spec Kit over the network, and a
suite that reached for it would be a suite nobody can run on a train. What is under test is the part this
keel owns — the command it builds, the lines it says, and the tail the board reads while a child is running
— so the child here is a four-line shell script that says what it was told to say.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.init_run import DECLINED, Fitting, adopted, command, ended, launch, start
from slipwai.session_log import folded_line


def project(says: list[str], code: int = 0) -> Path:
    """A directory with an `init` in it that says those lines and exits with that status."""
    root = Path(tempfile.mkdtemp())
    script = root / "init"
    said = "\n".join(f"echo '{line}'" for line in says)
    script.write_text(f"#!/bin/sh\n{said}\nexit {code}\n", encoding="utf-8")
    script.chmod(0o755)
    return root


def with_makefile(root: Path, targets: dict[str, str]) -> Path:
    """A `Makefile` beside `init`, one echoing recipe per target, for the steps the board runs through make."""
    rules = "".join(f"{name}:\n\t@echo '{says}'\n" for name, says in targets.items())
    (root / "Makefile").write_text(rules, encoding="utf-8")
    return root


def finished(fitting: Fitting, seconds: float = 20.0) -> dict:
    """What it said, once it has stopped. Polled, because the board polls — and bounded, because a test that
    hangs on a child that never ends is a test nobody can read the failure of."""
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        said = fitting.said()
        if said["done"]:
            return said
        time.sleep(0.05)
    raise AssertionError(f"`./init` was still running after {seconds}s: {fitting.said()['lines']}")


class CommandTest(unittest.TestCase):
    def test_the_agent_is_named_where_somebody_named_one(self) -> None:
        self.assertEqual(command("claude"), ["./init", "--integration", "claude"])

    def test_unnamed_it_keeps_spec_kit_s_own_question(self) -> None:
        """Which is right in a terminal, where there is somebody to answer it."""
        self.assertEqual(command(), ["./init"])

    def test_the_forge_is_named_where_somebody_named_one(self) -> None:
        self.assertEqual(command("claude", "git@github.com:you/demo.git"),
                         ["./init", "--integration", "claude", "--repository", "git@github.com:you/demo.git"])

    def test_a_failure_says_the_project_is_written_either_way(self) -> None:
        said = ended(2, "claude")
        self.assertIn("exited 2", said)
        self.assertIn("written and committed either way", said)


class AdoptedTest(unittest.TestCase):
    """An adoption made on the board runs the repository's own copy of `./init`, under its delivery directory."""

    def test_the_adopted_copy_is_the_one_run_with_the_agent_named(self) -> None:
        with mock.patch.object(Fitting, "run"):
            fitting = adopted(Path(tempfile.mkdtemp()), "adopt", "claude")
        self.assertEqual(fitting.steps[0].argv, ["./adopt/init", "--integration", "claude"])

    def test_with_no_agent_named_it_is_left_as_the_next_step(self) -> None:
        with mock.patch.object(Fitting, "run"):
            fitting = adopted(Path(tempfile.mkdtemp()), "adopt", None, ["adopted"])
        self.assertEqual(fitting.steps, [])
        self.assertEqual(fitting.lines, ["adopted", DECLINED])


@unittest.skipIf(sys.platform == "win32",
                 "the board's children run through a pty and `sh`, which Windows has neither of")
class BackgroundTest(unittest.TestCase):
    """The board's face: a child that outlives the request, read by polling."""

    def test_every_line_the_child_said_is_tailed_in_order(self) -> None:
        fitting = start(project(["first", "second", "third"]), "claude")
        lines = finished(fitting)["lines"]
        self.assertEqual([line for line in lines if line in ("first", "second", "third")],
                         ["first", "second", "third"])

    def test_a_poll_is_answered_with_what_was_said_after_the_lines_it_has(self) -> None:
        """The whole of the tail's contract: the page never shows a line twice and never misses one."""
        fitting = start(project(["one", "two"]), "claude")
        said = finished(fitting)
        self.assertEqual(said["at"], len(said["lines"]))
        self.assertEqual(fitting.said(said["at"])["lines"], [])
        self.assertEqual(fitting.said(said["at"] - 1)["lines"], said["lines"][-1:])

    def test_what_it_exited_with_is_what_the_board_is_told(self) -> None:
        fitting = start(project(["trying"], code=3), "claude")
        said = finished(fitting)
        self.assertEqual(said["code"], 3)
        self.assertIn("exited 3", said["lines"][-1])

    def test_an_init_that_cannot_be_run_is_a_line_and_not_a_silence(self) -> None:
        """A board that showed nothing where the child never started would be a board hiding the answer."""
        said = finished(start(Path(tempfile.mkdtemp()), "claude"))
        self.assertTrue(said["done"])
        self.assertNotEqual(said["code"], 0)
        self.assertIn("could not be run here", said["lines"][-1])

    def test_it_cannot_reach_the_terminal_the_board_was_started_from(self) -> None:
        """`./init` asks two of its questions over `/dev/tty` — the repository a production target pushes
        to, and the extension menu. `/dev/tty` is the *controlling* terminal, which a child of the board
        would inherit from whoever started it: the prompt printed into the card and the read blocked on a
        terminal nobody was looking at, which is a board that hangs for ever. Its own session has none."""
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text(
            "#!/bin/sh\nif [ -r /dev/tty ]; then read -r answer </dev/tty || answer=none; fi\n"
            "echo 'went on without being answered'\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        said = finished(start(root, "claude"), seconds=10.0)
        self.assertIn("went on without being answered", said["lines"])

    def test_the_child_is_given_the_login_shells_environment(self) -> None:
        """A board started at login has `PATH=/usr/bin:/bin`, and `./init` run with that found neither brew
        nor uv nor the cloud's tools on a machine that had every one of them. `generate`'s child already gets
        the login shell's environment; this is the other child the board starts."""
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text("#!/bin/sh\necho \"path=$PATH\"\necho \"token=$TOKEN\"\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        login = {"PATH": "/opt/tools/bin:/usr/bin:/bin", "TOKEN": "from-login"}
        with mock.patch("slipwai.init_run.login_environment", lambda: login):
            said = finished(start(root, "claude"), seconds=10.0)
        self.assertIn("path=/opt/tools/bin:/usr/bin:/bin", said["lines"])
        self.assertIn("token=from-login", said["lines"])

    def test_a_prd_continues_into_the_draft_once_init_has_ended_well(self) -> None:
        """The second step the answers asked for: `make draft`, in the project, after `./init` — and only
        after it ended well, because a draft in a tree Spec Kit never reached is a session with no commands."""
        root = with_makefile(project(["init ran"]), {"draft": "drafted the specification"})
        said = finished(start(root, "claude", prd=True))
        self.assertEqual(said["code"], 0)
        lines = said["lines"]
        self.assertLess(lines.index("init ran"), lines.index("drafted the specification"))
        self.assertTrue(any("make draft" in line and "Drafting" in line for line in lines), lines)
        self.assertIn("read it", lines[-1])

    def test_a_failed_init_does_not_go_on_to_draft(self) -> None:
        root = with_makefile(project(["init failed"], code=3), {"draft": "should not run"})
        said = finished(start(root, "claude", prd=True))
        self.assertEqual(said["code"], 3)
        self.assertNotIn("should not run", said["lines"])

    def test_without_a_prd_init_is_the_whole_run(self) -> None:
        root = with_makefile(project(["init ran"]), {"draft": "should not run"})
        said = finished(start(root, "claude"))
        self.assertEqual(said["code"], 0)
        self.assertNotIn("should not run", said["lines"])

    def test_continuing_the_build_is_make_launch_carrying_the_receipt_so_far(self) -> None:
        root = with_makefile(project([]), {"launch": "cast off"})
        said = finished(launch(root, ["made demo", "drafted"]))
        self.assertEqual(said["code"], 0)
        self.assertEqual(said["lines"][:2], ["made demo", "drafted"])
        self.assertIn("cast off", said["lines"])
        self.assertIn("make launch", said["lines"][-1])

    def test_a_launch_that_failed_says_nothing_was_cast_off(self) -> None:
        root = with_makefile(project([]), {"launch": "no spec'; exit 2; echo '"})
        said = finished(launch(root))
        self.assertEqual(said["code"], 2)
        self.assertIn("nothing was cast off", said["lines"][-1])

    def test_the_receipt_says_which_step_it_is_on(self) -> None:
        root = with_makefile(project(["init ran"]), {"draft": "drafted"})
        fitting = start(root, "claude", prd=True)
        self.assertEqual(finished(fitting)["step"], "draft", "the last step it ran")
        (root / "Makefile").write_text("launch:\n\t@echo x\n", encoding="utf-8")
        self.assertEqual(finished(launch(root))["step"], "launch")

    def test_claude_s_json_stream_is_folded_to_the_words_a_person_wants(self) -> None:
        """Print mode writes one event per line; the card says the assistant's text, the tools it reaches
        for and the result with its cost, and drops the harness talking to itself."""
        assistant = json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Reading the PRD.\nTwo requirements."}, {"type": "tool_use", "name": "Bash"}]}})
        self.assertEqual(folded_line(assistant), ["• Reading the PRD.", "• Two requirements.", "→ Bash"])
        result = json.dumps({"type": "result", "result": "Drafted.\nMore.", "usage": {"output_tokens": 1234}})
        self.assertEqual(folded_line(result), ["result: Drafted. — 1,234 output tokens"])
        self.assertEqual(folded_line(json.dumps({"type": "system", "subtype": "init"})), [])
        self.assertEqual(folded_line(json.dumps({"type": "user", "message": {}})), [])
        self.assertEqual(folded_line("plain words"), ["plain words"])
        self.assertEqual(folded_line("{not json"), ["{not json"])
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text(f"#!/bin/sh\nprintf '%s\\n' '{assistant}'\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        self.assertIn("• Reading the PRD.", finished(start(root, "claude"))["lines"])

    def test_declining_is_a_finished_run_that_says_what_the_next_step_is(self) -> None:
        """The board still lands in the project; what it does not do is start anything in it."""
        said = finished(start(project(["never run"]), None), seconds=2.0)
        self.assertEqual(said["code"], 0)
        self.assertEqual(said["lines"][-1], DECLINED)

    def test_a_child_that_writes_slowly_is_read_as_it_writes(self) -> None:
        """The whole point of the pseudo-terminal: `./init` shells out to pip and to Spec Kit, both of which
        block-buffer to a pipe, and the card showed nothing for two minutes and then everything at once."""
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text("#!/bin/sh\necho early\nsleep 2\necho late\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        fitting = start(root, "claude")
        until = time.monotonic() + 1.5
        while time.monotonic() < until and "early" not in fitting.said()["lines"]:
            time.sleep(0.05)
        said = fitting.said()
        self.assertIn("early", said["lines"])  # before the child has finished, which is the point
        self.assertFalse(said["done"])
        self.assertIn("late", finished(fitting)["lines"])

    def test_a_progress_bar_is_lines_and_not_one_line_a_megabyte_long(self) -> None:
        """A child on a terminal redraws its last line with a carriage return rather than ending it."""
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text("#!/bin/sh\nprintf '10%%\\r50%%\\r100%%\\n'\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        lines = finished(start(root, "claude"))["lines"]
        self.assertEqual([line for line in lines if line.endswith("%")], ["10%", "50%", "100%"])

    def test_what_a_terminal_would_have_painted_is_not_in_the_log(self) -> None:
        """It is given a terminal to make the children line-buffer, not to become one."""
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text("#!/bin/sh\nprintf '\\033[31mred\\033[0m\\n'\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        self.assertIn("red", finished(start(root, "claude"))["lines"])
        self.assertNotIn("\x1b", "".join(finished(start(root, "claude"))["lines"]))

    def test_how_long_it_has_been_going_is_part_of_the_answer(self) -> None:
        """The card's clock is the server's, so a page opened late still shows the right one.

        Timed against a child that takes long enough to be timed: one that ends inside the tenth of a
        second the answer is rounded to measures the rounding, and fails on a fast machine.
        """
        root = Path(tempfile.mkdtemp())
        (root / "init").write_text("#!/bin/sh\nsleep 0.4\necho done\n", encoding="utf-8")
        (root / "init").chmod(0o755)
        fitting = start(root, "claude")
        self.assertGreaterEqual(fitting.said()["seconds"], 0)
        self.assertGreater(finished(fitting)["seconds"], 0.2)

    def test_what_generate_said_is_the_head_of_the_same_receipt(self) -> None:
        """One card, not two: where the project went and what is happening in it are one person's question."""
        said = finished(start(project(["ready"]), "claude", ["created: /somewhere/demo"]))
        self.assertEqual(said["lines"][0], "created: /somewhere/demo")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
