"""Which optional dev tooling a project adopts, asked on the board rather than nowhere.

`./init`'s extension menu reads `/dev/tty` and **prints nothing where there is none** — so every `./init`
the board has ever run elected nothing, silently, because an empty capture is indistinguishable from a
person checking no boxes. The form did not ask and the card did not say. What is held here is that the
question is asked where there is anything to ask about, that the answer reaches `./init` as an explicit
`--extension`, and that nothing a person did not check gets elected.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.init_run import announced, command
from slipwai.interview_form import field_html, form
from slipwai.interview_page import elected_in, extensions_asked

#: Two installed extensions, as `catalogue` hands them over: a key and its manifest.
INSTALLED = [("codegraph", {"name": "CodeGraph", "description": "a code index the agent can search"}),
             ("uipro", {"name": "UI Pro", "description": "a browser-UI review gate"})]


def row(answers: dict[str, str]) -> str:
    """The question's row, with the assertion that there is one: `extensions_asked` answers `None` where
    the machine has nothing to offer, and every caller here has mocked something in."""
    question = extensions_asked(answers)
    assert question is not None
    return field_html(question)


def offering(found: list[tuple[str, dict]]):
    """The interview, with this machine's installed extensions replaced by `found`."""
    return mock.patch("slipwai.interview_page.catalogue", lambda _directory: found)


class QuestionTest(unittest.TestCase):
    def test_the_question_is_asked_only_where_the_machine_has_one_to_offer(self) -> None:
        """The rule the settings box follows too: a question whose every answer is unavailable is a
        question not worth asking, and the keel ships no extensions at all."""
        with offering([]):
            self.assertIsNone(extensions_asked({}))
            self.assertNotIn('name="extensions"', form({}, Path(tempfile.mkdtemp())))
        with offering(INSTALLED):
            self.assertIsNotNone(extensions_asked({}))
            self.assertIn('name="extensions"', form({}, Path(tempfile.mkdtemp())))

    def test_each_row_says_what_it_is_for_rather_than_only_its_key(self) -> None:
        """Which is why this is checkboxes and not a multiple-select: a key on its own tells somebody who
        has never heard of the package nothing about whether they want it."""
        with offering(INSTALLED):
            said = row({})
        self.assertIn('type="checkbox"', said)
        self.assertIn('value="codegraph"', said)
        self.assertIn("CodeGraph — a code index the agent can search", said)
        self.assertNotIn("checked", said, "nothing is elected for somebody by default")

    def test_what_was_checked_last_time_is_checked_again_when_the_form_re_renders(self) -> None:
        """The form is re-rendered whenever an answer changes what comes after it, and an answer that
        reset on every re-render is an answer nobody can give."""
        with offering(INSTALLED):
            said = row({"extensions": "uipro"})
        self.assertIn('value="uipro" checked', said)
        self.assertNotIn('value="codegraph" checked', said)


class AnswerTest(unittest.TestCase):
    def test_the_keys_checked_are_the_keys_elected(self) -> None:
        with offering(INSTALLED):
            self.assertEqual(elected_in({"extensions": "codegraph,uipro"}), ("codegraph", "uipro"))
            self.assertEqual(elected_in({"extensions": " uipro "}), ("uipro",))
            self.assertEqual(elected_in({}), ())
            self.assertEqual(elected_in({"extensions": ""}), ())

    def test_a_key_this_machine_does_not_have_is_not_an_election(self) -> None:
        """The payload is JSON a browser sent, so it is whatever reached the route. `./init` would refuse
        an unknown key anyway; refusing it here is the board not asking for a refusal."""
        with offering(INSTALLED):
            self.assertEqual(elected_in({"extensions": "codegraph,not-installed,../../etc"}), ("codegraph",))


class CommandTest(unittest.TestCase):
    def test_every_checked_key_is_an_explicit_flag_on_init(self) -> None:
        """`./init` never second-guesses an explicit answer, which is what makes this work at all: the
        menu it would otherwise show is the thing that cannot run without a terminal."""
        self.assertEqual(command("claude", None, ("codegraph", "uipro")),
                         ["./init", "--integration", "claude",
                          "--extension", "codegraph", "--extension", "uipro"])

    def test_no_extensions_is_the_command_it_always_was(self) -> None:
        self.assertEqual(command("claude"), ["./init", "--integration", "claude"])
        self.assertEqual(command("claude", "git@forge:me/x.git"),
                         ["./init", "--integration", "claude", "--repository", "git@forge:me/x.git"])

    def test_the_card_says_what_it_elected_before_it_runs(self) -> None:
        """An election nobody can see happening is the fault this fixes, so the line carries the flags."""
        said = announced(Path("/tmp/x"), "claude", None, ("codegraph",))
        self.assertIn("--extension codegraph", said)
        self.assertNotIn("--extension", announced(Path("/tmp/x"), "claude"))


class ThroughTheBoardTest(unittest.TestCase):
    def test_the_board_hands_the_answer_to_the_init_it_starts(self) -> None:
        """The board runs `./init` as a child of the server, which is exactly the case the menu cannot
        serve. The answer has to arrive as a flag or it does not arrive."""
        with offering(INSTALLED):
            keys = elected_in({"extensions": "uipro"})
        self.assertIn("--extension", command("claude", None, keys))
        self.assertIn("uipro", json.dumps(command("claude", None, keys)))


if __name__ == "__main__":
    unittest.main()
