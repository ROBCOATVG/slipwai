"""The interview `slipwai generate` runs when it is given nothing, and the quickstart it offers first.

The slice this suite holds is the one that serves the person the whole idea is for: somebody who has never
heard of a chandlery, does not know which of six languages answers the npm workspace, and has no way to
know an extension has to be elected as well as installed. They are asked one question — *start from one of
these?* — and every row is a sentence about the product it suits.

Two things are held here as hard as the offer itself. **Declining is the interview exactly as it is
today**, so a person who has never saved a quickstart is asked nothing new and nobody's muscle memory
breaks. And **what was chosen on their behalf is printed**, each answer against the flag that would have
given it, because a tool that answers nine questions silently is a tool that decided in the dark.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_generate, quickstart
from slipwai.catalog import CATALOG

DOCUMENT = {
    "quickstart": 1,
    "name": "toy-ui",
    "suits": "A product whose browser app is the product, with the review gates already on.",
    "answers": {"profile": "standard", "target": "none", "language": "toy", "framework": "plain",
                "frontend": "react-vite", "axes": {"persistence": "memory"}},
    "languages": [{"name": "toy", "version": ">=1.0,<2"}],
}
#: Every question the interview asks, by the name `cli_generate` calls it: what a test counts.
QUESTIONS = ("prompt_profile", "prompt_target", "prompt_axis", "prompt_project_name", "prompt_purpose",
             "prompt_context", "prompt_application_name", "prompt_output", "prompt_choice", "ask_language")


def written(into: Path, document: dict) -> Path:
    into.mkdir(parents=True, exist_ok=True)
    path = into / f"{document['name']}.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def axes(*names: str) -> dict[str, str | None]:
    """The axis answers the flags parse into: one key per axis, unanswered."""
    return dict.fromkeys(names)


def answers() -> SimpleNamespace:
    """The namespace `generate`'s flags parse into, as far as the interview touches it."""
    return SimpleNamespace(name=None, profile=None, target=None, language=None, framework=None,
                           backend=None, frontend=None, frontend_name=None, service_name=None,
                           purpose=None, context=None, output=None, quickstart=None, skip_checks=True)


class MenuTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = tempfile.TemporaryDirectory()
        self.addCleanup(self.area.cleanup)
        self.where = Path(self.area.name)
        written(self.where, DOCUMENT)
        patched = mock.patch.dict("os.environ", {quickstart.VARIABLE: str(self.where)})
        patched.start()
        self.addCleanup(patched.stop)

    def test_each_one_is_offered_by_what_it_suits_rather_than_by_what_it_installs(self) -> None:
        """The row a person reads is a sentence about their product. A row saying `toy >=1.0,<2` would be
        addressed to somebody who already knows what that is, and they are not who this is for."""
        choices, describe = cli_generate.quickstart_menu()
        self.assertIn("toy-ui", choices)
        self.assertEqual(describe("toy-ui"), DOCUMENT["suits"])

    def test_declining_is_the_first_row_and_the_default_and_says_what_it_does(self) -> None:
        """Declining is one keystroke: the default is the row that asks every question, because a default
        quickstart would be this keel choosing somebody's third-party tooling for them."""
        choices, describe = cli_generate.quickstart_menu()
        self.assertEqual(choices[0], cli_generate.DECLINE)
        self.assertIn("every question", describe(cli_generate.DECLINE))

    def test_one_whose_packages_are_not_here_is_offered_as_unavailable_with_the_install(self) -> None:
        """Said rather than hidden: a person who wrote that quickstart should see that it is theirs and be
        told the one command that makes it work, not conclude it was lost."""
        written(self.where, {**DOCUMENT, "name": "absent-ui", "languages": [{"name": "absent"}]})
        absent = cli_generate.unavailable_quickstarts()
        self.assertIn("absent-ui", absent)
        self.assertIn("install absent", absent["absent-ui"])
        self.assertNotIn("absent-ui", cli_generate.quickstart_menu()[0])

    def test_with_none_saved_nothing_is_asked_at_all(self) -> None:
        """The interview is exactly what it is today for somebody who has never saved one."""
        with tempfile.TemporaryDirectory() as empty, \
                mock.patch.dict("os.environ", {quickstart.VARIABLE: empty}), \
                mock.patch.object(cli_generate, "prompt_choice", side_effect=AssertionError("asked")):
            self.assertEqual(cli_generate.offer_quickstart(answers(), {}), {})

    def test_choosing_one_answers_the_questions_and_prints_every_answer_it_gave(self) -> None:
        args, named = answers(), axes("persistence", "http")
        said = io.StringIO()
        with mock.patch.object(cli_generate, "prompt_choice", return_value="toy-ui"), redirect_stdout(said):
            given = cli_generate.offer_quickstart(args, named)
        self.assertEqual(given["profile"], "standard")
        self.assertEqual(args.profile, "standard")
        self.assertEqual(args.language, "toy")
        self.assertEqual(named["persistence"], "memory")
        self.assertIn("--profile standard", said.getvalue())
        self.assertIn("--persistence memory", said.getvalue())

    def test_declining_answers_nothing(self) -> None:
        args, named = answers(), axes("persistence")
        with mock.patch.object(cli_generate, "prompt_choice", return_value=cli_generate.DECLINE), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(cli_generate.offer_quickstart(args, named), {})
        self.assertIsNone(args.profile)
        self.assertIsNone(named["persistence"])


class OrderTest(unittest.TestCase):
    """Which questions are asked, with a quickstart answering and without one."""

    def setUp(self) -> None:
        self.asked: list[str] = []
        for name in QUESTIONS:
            patched = mock.patch.object(cli_generate, name, side_effect=self.record(name))
            patched.start()
            self.addCleanup(patched.stop)
        for name, answer in (("check_requirements", None), ("check_project_name", None),
                             ("frontend_menu", (["none"], "none", {}))):
            patched = mock.patch.object(cli_generate, name, return_value=answer)
            patched.start()
            self.addCleanup(patched.stop)

    #: What a recorded question answers, where the answer decides whether a later one is asked at all: a
    #: profile and a backend that can be given a choice are what make an axis a question.
    ANSWERED = {"prompt_profile": "event-modelling", "ask_language": "toy-plain", "prompt_target": "none"}

    def record(self, name: str):
        def remember(*_: object, **__: object) -> str:
            self.asked.append(name)
            return self.ANSWERED.get(name, "none")
        return remember

    def interview(self, given: dict[str, str]) -> SimpleNamespace:
        args: SimpleNamespace = answers()
        named: dict[str, str | None] = dict.fromkeys(CATALOG["axes"])
        with mock.patch.object(cli_generate, "offer_quickstart", side_effect=self.offer(given)), \
                redirect_stdout(io.StringIO()):
            cli_generate.interview(args, named)
        return args

    def offer(self, given: dict[str, str]):
        def asked(args: SimpleNamespace, named: dict) -> dict[str, str]:
            self.asked.append("offer_quickstart")
            for flag, value in given.items():
                if flag in named:
                    named[flag] = value
                else:
                    setattr(args, flag, value)
            return given
        return asked

    def test_the_quickstart_is_offered_before_the_delivery_foundation(self) -> None:
        """Before it, because the foundation is the first thing a quickstart answers — and because a
        question asked after the answers were given is a question nobody needed."""
        self.interview({})
        self.assertLess(self.asked.index("offer_quickstart"), self.asked.index("prompt_profile"))

    def test_with_no_quickstart_every_question_is_asked_as_it_is_today(self) -> None:
        self.interview({})
        for question in ("prompt_profile", "prompt_target", "ask_language", "prompt_axis"):
            with self.subTest(question=question):
                self.assertIn(question, self.asked)

    def test_the_questions_a_quickstart_answered_are_not_asked_again(self) -> None:
        """One question, and the chandlery never comes up: this is the slice's whole claim."""
        args = self.interview(quickstart.answered(quickstart.read(DOCUMENT)))
        for question in ("prompt_profile", "prompt_target", "ask_language", "prompt_axis"):
            with self.subTest(question=question):
                self.assertNotIn(question, self.asked)
        self.assertEqual(args.profile, "standard")
        self.assertEqual(args.backend, "toy-plain")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
