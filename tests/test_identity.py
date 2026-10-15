"""Who signs in, asked once, and the two axes it answers — in both faces of the interview.

The keel carries two identity axes and it is right that it does: `auth` is the people who run the product
and `users` is the people it is for, and a system with both genuinely has two answers. What was wrong was
asking both of everybody. Two prompts a paragraph apart, worded alike, each offering the same list of
providers, is a question most projects cannot answer — and answering the same provider twice quietly asked
for two realms.

So the question put first is the one about people, and these are the cases that hold it to meaning what it
says:

* **Each answer writes both axes.** The axis nobody was asked about gets the no-infrastructure answer
  rather than being left for the generator to default — "you were not asked" and "you said there are none"
  have to be the same answer or the question decides less than it appears to.
* **One provider for everybody is the external axis**, because that is the half whose browser login is
  real; **staff only is the internal axis**, because an internal tool given the external answer would ship
  with public self-registration switched on. That is the one mistake the question exists to prevent, and it
  is the one asserted here by name.
* **Both faces ask it.** The terminal's `ask_identity` and the board's `signing_in` are driven with the
  same answers and compared, because an interview that asked this on a page and not in a terminal would be
  two interviews wearing one name.

The toy backend answers no identity option, so none of this applies under the pinned catalogue as it
stands. `offering` puts the two providers on the toy backend for the length of a case: the catalogue is
the thing being read, so a case that could not read one would be proving the readers agreed about nothing.
"""
from __future__ import annotations

import contextlib
import io
import unittest
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import identity
from slipwai.catalog import CATALOG, axis_applies
from slipwai.cli_generate import ask_identity
from slipwai.interview_page import asked, flags, signing_in

#: The answers every case here is driven with: the backend and target the pinned catalogue has.
BACKEND, TARGET, PROFILE = "toy-plain", "none", "event-modelling"


@contextlib.contextmanager
def offering(*providers: str):
    """Put these providers on both identity axes for this backend and target, and take them off again."""
    held = [(CATALOG["axes"][axis]["options"][name], list(CATALOG["axes"][axis]["options"][name]["backends"]))
            for axis in identity.AXES for name in providers]
    try:
        for option, _ in held:
            option["backends"] = [BACKEND]
        yield
    finally:
        for option, backends in held:
            option["backends"] = backends


class AxesTest(unittest.TestCase):
    """What each answer means, in the two flags it becomes."""

    def test_one_provider_for_everybody_is_the_external_axis(self) -> None:
        """The half whose sign-up, reset and browser login are real. The internal axis is told there is
        nobody on it rather than left unsaid."""
        self.assertEqual(identity.asks(identity.EVERYONE), (identity.EXTERNAL,))
        self.assertEqual(identity.settled(identity.EVERYONE, {identity.EXTERNAL: "keycloak"}),
                         {"auth": "none", "users": "keycloak"})

    def test_staff_only_is_the_internal_axis_and_never_the_external_one(self) -> None:
        """The case that made this question worth asking. An internal tool handed the external answer gets
        a realm with public self-registration on it, which is precisely what "no public sign-up" means
        nobody wanted."""
        self.assertEqual(identity.asks(identity.STAFF), (identity.INTERNAL,))
        self.assertEqual(identity.settled(identity.STAFF, {identity.INTERNAL: "keycloak"}),
                         {"auth": "keycloak", "users": "none"})

    def test_separately_is_the_pair_as_it_always_was(self) -> None:
        self.assertEqual(identity.asks(identity.SEPARATELY), identity.AXES)
        self.assertEqual(identity.settled(identity.SEPARATELY, {"auth": "keycloak", "users": "auth0"}),
                         {"auth": "keycloak", "users": "auth0"})

    def test_an_axis_nobody_answered_is_written_down_as_nobody(self) -> None:
        """Not left as None for the generator to default: the page and the prompt both show what this
        answer did to the other axis, and a flag that was never passed would make them liars."""
        self.assertEqual(identity.settled(identity.EVERYONE, {}), {"auth": "none", "users": "none"})

    def test_the_answers_a_quickstart_gives_are_read_back_as_the_shape_it_chose(self) -> None:
        """A quickstart answers both axes, so the question has to be able to show which of its three rows
        that pair *is* — otherwise choosing one on the board would move the reader's answer under them."""
        self.assertEqual(identity.implied({"auth": "cognito", "users": "cognito"}), identity.SEPARATELY)
        self.assertEqual(identity.implied({"auth": "entra", "users": "none"}), identity.STAFF)
        self.assertEqual(identity.implied({"auth": "none", "users": "keycloak"}), identity.EVERYONE)
        self.assertEqual(identity.implied({}), identity.EVERYONE)

    def test_it_is_not_asked_where_the_catalogue_would_not_have_asked_either_axis(self) -> None:
        """A service with no inbound HTTP has nobody to sign in. A question standing in for two that are
        not being asked would be a question about nothing."""
        self.assertFalse(any(axis_applies(axis, PROFILE, BACKEND, TARGET) for axis in identity.AXES))
        self.assertFalse(identity.applies(PROFILE, BACKEND, TARGET))
        self.assertEqual([one.name for one in signing_in({}, PROFILE, BACKEND, TARGET)], [])


class BoardTest(unittest.TestCase):
    """The page: one question, and the two flags it ends as."""

    def test_the_two_axes_are_one_question_and_the_answer_it_leads_to(self) -> None:
        with offering("keycloak"):
            rows = [one.name for one in asked({"name": "demo"})]
            self.assertIn(identity.WHO, rows)
            self.assertEqual([name for name in rows if name in identity.AXES], [identity.EXTERNAL])
            self.assertLess(rows.index(identity.WHO), rows.index(identity.EXTERNAL))

    def test_the_provider_question_is_headed_by_the_answer_that_led_to_it(self) -> None:
        """"External authentication" is the right heading for one of a pair and the wrong one for a product
        that has said it has one set of people."""
        with offering("keycloak"):
            one = next(q for q in asked({"name": "demo"}) if q.name == identity.EXTERNAL)
            self.assertEqual(one.label, "Authentication")
            staff = next(q for q in asked({"name": "demo", identity.WHO: identity.STAFF})
                         if q.name == identity.INTERNAL)
            self.assertEqual(staff.label, "Staff authentication")
            pair = {q.name: q.label for q in asked({"name": "demo", identity.WHO: identity.SEPARATELY})}
            self.assertEqual(pair[identity.INTERNAL], str(CATALOG["axes"]["auth"]["prompt"]))
            self.assertEqual(pair[identity.EXTERNAL], str(CATALOG["axes"]["users"]["prompt"]))

    def test_both_flags_are_passed_whichever_one_was_asked(self) -> None:
        with offering("keycloak"):
            argv = flags({"name": "demo", "output": "/tmp", identity.WHO: identity.STAFF,
                          identity.INTERNAL: "keycloak"})
        self.assertEqual(argv[argv.index("--auth") + 1], "keycloak")
        self.assertEqual(argv[argv.index("--users") + 1], "none")


class InStepTest(unittest.TestCase):
    """The terminal asks it too, with the same words, and ends at the same pair of answers."""

    def drive(self, who: str, provider: str) -> tuple[dict[str, str | None], str]:
        """`ask_identity`, with `who` typed at the first question and `provider` at the one after it."""
        said = io.StringIO()
        answers = iter([who, provider, provider])

        def typed(prompt: str = "") -> str:
            said.write(prompt)
            return next(answers)

        named: dict[str, str | None] = {axis: None for axis in identity.AXES}
        args: Any = mock.Mock(profile=PROFILE, backend=BACKEND, target=TARGET)
        with (contextlib.redirect_stdout(said), mock.patch("builtins.input", typed),
              mock.patch("slipwai.cli_prompts.terminal_can_select", lambda: False)):
            ask_identity(args, named)
        return named, said.getvalue()

    def test_the_terminal_asks_the_question_the_page_asks(self) -> None:
        with offering("keycloak"):
            named, transcript = self.drive(identity.EVERYONE, "keycloak")
        self.assertIn(identity.PROMPT, transcript)
        for _name, line in identity.ROWS:
            self.assertIn(line, transcript)
        self.assertIn("Authentication:", transcript)
        self.assertNotIn("External authentication", transcript)
        self.assertEqual(named, {"auth": "none", "users": "keycloak"})

    def test_the_terminal_and_the_page_end_at_the_same_pair(self) -> None:
        for who in (identity.EVERYONE, identity.STAFF, identity.SEPARATELY):
            with self.subTest(who=who), offering("keycloak"):
                named, _ = self.drive(who, "keycloak")
                argv = flags({"name": "demo", "output": "/tmp", identity.WHO: who,
                              **{axis: "keycloak" for axis in identity.asks(who)}})
                page = {axis: argv[argv.index(f"--{axis}") + 1] for axis in identity.AXES}
                self.assertEqual(named, page)

    def test_an_axis_already_answered_is_not_asked_about_a_second_time(self) -> None:
        """A quickstart or a flag has said there are staff accounts. Asking whether there are would be the
        interview arguing with an answer it was given."""
        named: dict[str, str | None] = {"auth": "keycloak", "users": None}
        said = io.StringIO()
        args: Any = mock.Mock(profile=PROFILE, backend=BACKEND, target=TARGET)
        with (offering("keycloak"), contextlib.redirect_stdout(said),
              mock.patch("builtins.input", lambda prompt="": said.write(prompt) and "" or ""),
              mock.patch("slipwai.cli_prompts.terminal_can_select", lambda: False)):
            ask_identity(args, named)
        self.assertNotIn(identity.PROMPT, said.getvalue())
        self.assertEqual(named, {"auth": "keycloak", "users": "none"})


if __name__ == "__main__":
    unittest.main()
