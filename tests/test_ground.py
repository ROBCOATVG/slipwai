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
        self.assertEqual(ground.count("**Ask:**"), len(AXES))
        self.assertEqual(ground.count("**Write:**"), len(AXES))
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
