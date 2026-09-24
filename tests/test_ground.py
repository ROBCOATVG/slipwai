"""`/ground`: the question set the tree cannot answer, asked by the agent one row at a time and recorded.

What this gates: only an adopted repository gets the command; it opens with the map as it stands, so a refresh
regenerates it with the record; every axis is asked with its rungs and their meanings except the constitution,
which only the gate establishes; each answer has a place in the record and `confirmed` provenance; "I don't
know" stays unrecorded; the tree wins over an answer it contradicts; and `/drive`'s Ground stage, the hook, the
adoption page and the report all send the person to it. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import unittest

from slipwai.convergence import AXES, detected
from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.scaffold import project_files
from slipwai.services import App

DELIVERY = Layout("delivery")


def wrapped(name: str, path: str, kind: str = "application", provenance: str = "unrecorded") -> App:
    return App(name, path, kind, "javascript", None, 0, generated=False, commands={"test": "npm test"},
               provenance={"language": "detected", "commands": "detected", "kind": provenance})


def adopted(apps: list[App], why: str | None = None) -> dict[str, str]:
    adoption = Adoption(why=why, release={"path": "unknown", "evidence": [], "provenance": "unrecorded"})
    adoption = Adoption(**{**adoption.__dict__, "convergence": detected(apps, adoption)})
    return project_files("shop", "standard", "existing", apps, DELIVERY, adoption)


class GroundTest(unittest.TestCase):
    def test_the_command_asks_every_axis_but_the_constitution_with_its_rungs_and_opens_with_the_map(self) -> None:
        apps = [wrapped("shop", "."), wrapped("worker", "services/worker", "tool", "confirmed")]
        ground = adopted(apps)["delivery/commands/ground.md"]
        for axis in AXES:
            self.assertIn(f"### {axis.title}", ground)
            for rung in axis.rungs if axis.key != "constitution" else ():
                self.assertIn(f"`{rung}` — {axis.means[rung]}", ground, f"{axis.key}: every rung says what it means")
        self.assertIn("Not asked. The constitution is established by `/speckit-constitution`", ground)
        # Every axis but the constitution, and one question that is not a row: how each application starts.
        # Every axis but the constitution, plus the opening question about how much to explain, and one
        # question that is not a row: how each application starts.
        self.assertEqual(ground.count("**Ask:**"), len(AXES) + 1)
        self.assertEqual(ground.count("**Write:**"), len(AXES) + 1)
        starts = ground.split("## How each application starts")[1].split("## Then")[0]
        self.assertIn("the floor beside the build", starts)
        self.assertIn("`/drive`'s Pin stage refuses to change one", starts)
        self.assertIn("What proves it answers", starts)
        self.assertIn("`shop` at `.`: no `smoke` recorded — nobody has proved how it starts", starts)
        self.assertIn("`delivery/survey/running.md`", starts, "the run path is written where the layout puts it")
        self.assertIn("as `smoke` under the application's\n`commands` in `project.json`", starts)
        self.assertIn("a written `null`", starts)
        self.assertIn("`verify` never does", starts)
        # The map as it stands, so the agent shows the evidence before asking.
        self.assertIn("| Path to production | `unknown` | `unrecorded` |", ground)
        self.assertIn("| Strategy | `open` | `unrecorded` |", ground)
        self.assertIn("an application whose role nobody has established (`application`, `unrecorded`)", ground)
        self.assertIn("`worker` at `services/worker`: recorded as `tool` (confirmed)", ground)
        # The rules that keep it honest.
        for rule in ("One question at a time", "Evidence and rungs first", "A rung is claimed only from a fact",
                     "the tree wins", '"I don\'t know" stays `unrecorded`', "Record, do not paraphrase",
                     "`provenance` `confirmed`"):
            self.assertIn(rule, ground)
        self.assertIn("`delivery/docs/convergence.md`", ground, "the map where the layout puts it")
        self.assertIn("1. `/survey` (`slipwai adopt --refresh`)", ground)
        # The strategy is a question of its own, with every strategy named and Accepted the person's word: the second
        # real adoption reached `decided` without the person ever being asked.
        strategy = ground.split("### Strategy")[1].split("### ")[0]
        self.assertIn("Two questions, asked apart", strategy)
        for name in ("`leave-it`", "`in-place`", "`modular-monolith`", "`strangler-fig`", "`rewrite`"):
            self.assertIn(name, strategy)
        self.assertIn("never a default you decide for them", strategy)
        self.assertIn("the word `Accepted` is the person's", strategy)
        self.assertIn("quoting them in the", strategy)
        self.assertIn("**`detected` is the tree's reading, not the person's answer.**", ground)

    def test_the_command_follows_the_record_and_the_loop_sends_the_person_to_it(self) -> None:
        placed = adopted([wrapped("shop", ".", "service", "confirmed")], why="Python 2 is end of life")
        ground = placed["delivery/commands/ground.md"]
        self.assertIn("| Strategy | `why-recorded` | `detected` | why: Python 2 is end of life |", ground,
                      "regenerated with the record")
        self.assertIn("`shop` at `.`: recorded as `service` (confirmed)", ground)
        drive = placed["delivery/commands/drive.md"]
        self.assertIn("/ground", drive.split("**Ground**")[1].split("**Principles**")[0])
        self.assertIn("`/ground` asks it, one row at a time", placed[".specify/extensions.yml"])
        page = placed["delivery/docs/adoption.md"]
        self.assertLess(page.index("1. `./delivery/init`"), page.index("2. `/ground`, in the agent"))
        self.assertLess(page.index("2. `/ground`, in the agent"), page.index("3. `make -f delivery/Makefile verify`"))

    def test_a_generated_project_has_no_ground_to_cover(self) -> None:
        generated = project_files("shop", "standard", "none", [App("shop", "apps/shop", "service", "python", None, 0)])
        self.assertNotIn("commands/ground.md", generated)
        self.assertNotIn("/ground", generated["commands/drive.md"])


if __name__ == "__main__":
    unittest.main()



def with_candidates(candidates: list[dict]) -> str:
    """The command as it reads while buildable directories are still candidates (ADR 0003)."""
    adoption = Adoption(candidates=candidates, release={"path": "unknown", "evidence": [], "provenance": "unrecorded"})
    adoption = Adoption(**{**adoption.__dict__, "convergence": detected([], adoption)})
    return project_files("shop", "standard", "existing", [], DELIVERY, adoption)["delivery/commands/ground.md"]


class QuestionDisciplineTest(unittest.TestCase):
    """How a question is *put*, which is a different thing from which questions are asked.

    The first real run of this command produced a page of sound reasoning per candidate and then collapsed it
    into option labels — `Yes — hold its lint`, `Yes, as recommended` — and the person answering said "Not
    sure, what do you think?" and, once, "check yourself". A person reads the options, not the paragraph above
    them, so the options are where the consequence has to be.
    """

    def test_every_option_has_to_say_what_it_does(self) -> None:
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("**In full, every answer on offer says what it does.**", ground)
        self.assertIn("is a label, and a label is what gets", ground)
        self.assertIn("Never offer one whose consequence you have not stated", ground)

    def test_a_readable_question_goes_back_to_the_tree_rather_than_to_the_person(self) -> None:
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("**Settle from the tree whatever the tree settles", ground)
        self.assertIn("asks somebody to guess at their own repository", ground)

    def test_not_knowing_is_offered_rather_than_merely_accepted(self) -> None:
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("is one of the answers, every time, and offered as one.", ground)
        self.assertIn("manufactures an answer", ground)

    def test_a_recommendation_comes_with_its_reasoning_and_never_a_bare_menu(self) -> None:
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("**Say what you think, and why, from what you read.**", ground)
        self.assertIn("Never a bare menu.", ground)

    def test_how_much_to_explain_is_asked_first_and_is_not_a_row(self) -> None:
        """Somebody who knows the codebase and the method does not need webpack explained, and being told
        anyway is how a question set becomes a wall to skim. Asked once, before anything about the
        repository, and it writes nothing: it is how the agent talks, not a fact about the tree."""
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("## The first question", ground)
        self.assertIn("**Ask:** how much should each answer explain itself?", ground)
        self.assertIn("**Write:** nothing. It is how you talk, not a fact about the repository", ground)
        self.assertIn("**Ask how much to explain, first, and hold to the answer.**", ground)
        self.assertLess(
            ground.index("## The first question"), ground.index("## The rows, as they stand"),
            "asked before any row",
        )
        self.assertEqual(ground.count("**Ask:**"), len(AXES) + 1, "the axes, plus this one")

    def test_the_short_form_drops_the_elaboration_and_not_the_honesty(self) -> None:
        ground = adopted([wrapped("shop", ".")])["delivery/commands/ground.md"]
        self.assertIn("**In short, the labels stand alone — and two things never go.**", ground)
        self.assertIn("drops the elaboration, not", ground)
        self.assertIn("the honesty", ground)
        self.assertIn("**In full, every answer on offer says what it does.**", ground)

    def test_the_candidate_section_holds_its_options_to_the_same_standard(self) -> None:
        ground = with_candidates([
            {"name": "themes", "path": "themes", "language": "javascript", "kind": "application",
             "commands": {"lint": "cd themes && npm run lint"}, "evidence": "themes/package.json"},
        ])
        self.assertIn("each answer says what confirming it does", ground)
        self.assertIn("Where they asked for the short form, the labels stand alone", ground)
        self.assertIn("and *No* are not.", ground, "a bare yes/no is not an answer")
