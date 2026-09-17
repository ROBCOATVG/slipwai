"""The adoption phases of `/drive`: Ground before Principles, Pin before Implementation, the map at Convergence.

What this gates is the shape of the loop in a repository the method was installed around (brownfield adoption,
experimental). The ladder gains stages rather than paragraphs, so that "enter at the first incomplete
stage" reaches them; the hooks say the same three things to a session that never typed `/drive`; the split
knows a method slice; and a generated project carries none of it, because a generated project starts at the
top of every ladder and has nothing to ground, pin or converge on.
"""
from __future__ import annotations

import re
import unittest

from slipwai.convergence import detected
from slipwai.layout import AT_ROOT, Layout
from slipwai.origin import Adoption
from slipwai.scaffold import project_files
from slipwai.services import App
from slipwai.toolkit import TOOLKIT_ROOT


def wrapped(name: str, path: str, kind: str = "service") -> App:
    commands = {"install": "npm ci", "typecheck": None, "lint": None, "test": "npm test", "integration": None,
                "adversarial": None, "audit": None, "mutation": None}
    return App(name, path, kind, "javascript", None, 0, generated=False, commands=commands,
               provenance={"language": "detected", "commands": "detected", "kind": "confirmed"})


DELIVERY = Layout("delivery")


def adopted(apps: list[App], layout: Layout = DELIVERY) -> dict[str, str]:
    adoption = Adoption(
        why="the runtime is end of life", ci={"forge": "none", "gate": None, "provenance": "detected"},
        release={"path": "unknown", "evidence": [], "provenance": "unrecorded"},
        database={"schema": "none", "provenance": "confirmed"},
        infrastructure={"home": "none", "provenance": "confirmed"},
    )
    adoption = Adoption(**{**adoption.__dict__, "convergence": detected(apps, adoption)})
    return project_files("shop", "standard", "existing", apps, layout, adoption)


def stages(drive: str) -> list[str]:
    return re.findall(r"^\d+\. \*\*([^*]+)\*\*", drive, re.M)


def hooks_of(text: str) -> dict[str, list[dict[str, str]]]:
    """The hooks file read the way Spec Kit reads it — one phase key, a list of hooks, each a flat mapping with a
    folded prompt — without a YAML library, which the factory's own gates do not carry."""
    phases: dict[str, list[dict[str, str]]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if re.match(r"^  \w+:$", line):
            phases[line.strip()[:-1]] = []
            current = None
        elif re.match(r"^    - ", line) and phases:
            current = {}
            list(phases.values())[-1].append(current)
            line = "      " + line[6:]
        if current is not None and re.match(r"^      \w+: ", line):
            key, _, value = line.strip().partition(": ")
            current[key] = value.strip('"')
        elif current is not None and line.startswith("        "):
            current["prompt"] = current.get("prompt", "") + " " + line.strip()
    return phases


class DriveAdoptionTest(unittest.TestCase):
    def test_the_ladder_grounds_first_pins_before_implementing_and_holds_the_map_at_convergence(self) -> None:
        files = adopted([wrapped("shop", "."), wrapped("worker", "services/worker", kind="tool")])
        drive = files["delivery/commands/drive.md"]
        ladder = stages(drive)
        self.assertEqual(ladder[:2], ["Ground", "Principles"], "no map, no principles")
        self.assertEqual(ladder[ladder.index("Implementation") - 1], "Pin", "pin before changing what was here")
        self.assertLess(ladder.index("Convergence"), ladder.index("Demo"))
        ground = drive.split("**Ground**")[1].split("**Principles**")[0]
        # The map, where the layout puts it; the unrecorded row as a question, never a default; the release
        # path first, because the map says it is the first Minimum CD fact.
        self.assertIn("`delivery/docs/convergence.md` exists", ground)
        self.assertIn("`make check-convergence`", ground)
        self.assertIn("`unrecorded`", ground)
        self.assertIn("or `detected`, the tree's reading and nobody's answer", ground)
        self.assertIn("*Safety net*, *Structure* and *Strategy*", ground)
        self.assertIn("an ADR's `Accepted` is the person's word, never yours", ground)
        self.assertIn("release path first of all", ground)
        self.assertIn("never filled in from context", ground)
        self.assertIn("Asking is this stage's work", ground)
        self.assertIn("the repository root, `services/worker/`", ground, "the slice knows which code was here")
        pin = drive.split("**Pin**")[1].split("**Implementation**")[0]
        # The decided strategy governs the home: under a strangler fig a product slice lands in a new home, or the
        # plan quotes the owner's exception — the first strangler adoption built every slice in the old one.
        plan = drive.split("**Plan and tasks**")[1].split("**Pin**")[0]
        self.assertIn("Under an accepted `strangler-fig`", plan)
        self.assertIn("names a deployable that is **not** one that was here", plan)
        self.assertIn("the repository root, `services/worker/`", plan)
        self.assertIn("`delivery/retirement.md`", plan, "the ledger, where the layout puts it")
        self.assertIn("or it quotes the owner's written", plan)
        self.assertIn('"Confirmed at plan time" by the plan alone is not a decision', plan)
        self.assertIn("cites the artefact it was read from", plan, "research.md's claims are verified or assumed")
        self.assertIn("`delivery/survey/pinned.md`", pin, "the ledger, where the layout puts it")
        self.assertIn("/characterise <behaviour>", pin)
        self.assertIn('refuses "everything"', pin)
        self.assertIn("Code the factory generated needs no pin", pin)
        # Before any pin, the application has to start: the first adoptions each merged a slice that had stopped it.
        self.assertIn("**And before any pin, the application has to start.**", pin)
        self.assertIn("`delivery/survey/running.md` still reads *Not yet proven*", pin)
        self.assertIn("has no `smoke` command, this stage refuses the slice", pin)
        self.assertIn("the slice that proves it", pin)
        # New code beside what was here is written at Implementation, which never reads `/characterise`: the second
        # real adoption was offered JUnit 4 with Mockito there, over a JUnit 3 tree.
        implementation = drive.split("**Implementation**")[1].split("**Convergence**")[0]
        self.assertIn("never a mocking framework added for the purpose", implementation)
        self.assertIn("Mockito, Moq, gomock, `unittest.mock`", implementation)
        self.assertIn("ecosystem's *current* framework", implementation)
        self.assertIn("JUnit 5 through its vintage engine", implementation)
        self.assertIn("never the next-oldest version", implementation)
        convergence = drive.split("**Convergence**")[1].split("**Demo**")[0]
        self.assertIn("converged verdict", convergence, "Spec Kit's converge is still the stage's first half")
        self.assertIn("`make check-convergence`", convergence)
        self.assertIn("`planned` cleared", convergence)
        self.assertIn("never moved to match a hope", convergence)
        self.assertIn("next method slice", convergence)
        self.assertIn("/story-splitting", convergence)
        # A slice that touched how the application starts has converged only once it has started with the change.
        self.assertIn("has converged only once that application has started", convergence)
        self.assertIn("`make smoke` where a `smoke` command is recorded", convergence)
        self.assertIn("a converged verdict that rests on the suite alone is not one", convergence)
        # What is offered next: an open CRITICAL before everything, a platform move as its own slice, demo feedback
        # that is neither an actor's path nor a rung as a task.
        self.assertIn("**An open `CRITICAL` in `specs/<feature>/adversary-log.md` comes\n   first**", convergence)
        self.assertIn("a secret and an open `CRITICAL` excepted", convergence)
        self.assertIn("moves on the Platform row, as a slice of its own and never inside\n   another", convergence)
        self.assertIn("is a task in the next\n   slice, never a slice with acceptance criteria of its own", convergence)
        self.assertIn("names each constitution principle", convergence, "the verdict is per principle, with the line")
        self.assertIn("then an application\n   nobody has proved starts", convergence, "offered right after the build")
        demo = drive.split("### What the demo stop has to contain")[1]
        self.assertIn("**When the slice touched how the application starts**", demo)
        self.assertIn("never the suite passing in its place", demo)

    def test_a_generated_project_has_none_of_it(self) -> None:
        generated = project_files("shop", "standard", "none", [App("shop", "apps/shop", "service", "python", None, 0)])
        drive = generated["commands/drive.md"]
        self.assertEqual(stages(drive)[0], "Principles")
        self.assertNotIn("**Ground**", drive)
        self.assertNotIn("**Pin**", drive)
        self.assertNotIn("check-convergence", drive)
        hooks = generated[".specify/extensions.yml"]
        self.assertNotIn("before_specify", hooks)
        self.assertNotIn("convergence-map", hooks)

    def test_the_hooks_say_the_same_three_things_to_a_session_that_never_typed_drive(self) -> None:
        files = adopted([wrapped("shop", ".")])
        text = files[".specify/extensions.yml"]
        self.assertNotIn("delivery/.specify", "".join(files), "Spec Kit reads its hooks at the root")
        hooks = hooks_of(text)
        self.assertEqual([h["extension"] for h in hooks["before_specify"]], ["convergence-map"])
        self.assertEqual([h["extension"] for h in hooks["before_plan"]], ["pin"])
        self.assertEqual([h["extension"] for h in hooks["after_converge"]], ["promise-tracing", "convergence-map"])
        # They print; none of them is a second route through the workflow, and the two that run are still the
        # two a generated project has.
        for phase in ("before_specify", "before_plan"):
            self.assertTrue(all(h["optional"] == "true" for h in hooks[phase]), phase)
        self.assertEqual(text.count("optional: false"), 2)
        self.assertIn("delivery/docs/convergence.md", hooks["before_specify"][0]["prompt"])
        self.assertIn("`unrecorded` or `detected`", hooks["before_specify"][0]["prompt"])
        self.assertIn("a change strategy the map only recommends", hooks["before_specify"][0]["prompt"])
        self.assertIn("delivery/survey/pinned.md", hooks["before_plan"][0]["prompt"])
        self.assertIn("never moved to match a hope", hooks["after_converge"][1]["prompt"])
        # Every hook names a command that exists in the adopted repository.
        commands = {path.removeprefix("delivery/commands/").removesuffix(".md") for path in files
                    if path.startswith("delivery/commands/")}
        for entries in hooks.values():
            for hook in entries:
                self.assertIn(hook["command"], commands | {"compact", "speckit-converge"}, hook["extension"])

    def test_at_the_root_layout_the_pointers_are_root_pointers(self) -> None:
        files = adopted([wrapped("shop", ".")], AT_ROOT)
        self.assertIn("`docs/convergence.md` exists", files["commands/drive.md"])
        self.assertIn("`survey/pinned.md`", files["commands/drive.md"])
        self.assertIn("`survey/pinned.md`", files[".specify/extensions.yml"])

    def test_the_split_knows_a_method_slice(self) -> None:
        skill = (TOOLKIT_ROOT / "skills/story-splitting/SKILL.md").read_text()
        section = skill.split("## Method Slices")[1].split("## Validation Checklist")[0]
        self.assertIn("one rung on one axis", section)
        self.assertIn("One rung per slice", section)
        self.assertIn("`planned`", section)
        self.assertIn("not ahead of all of them", section)
        self.assertIn("A decision is not a slice", section)
        files = adopted([wrapped("shop", ".")])
        self.assertIn("## Method Slices", files["delivery/skills/story-splitting/SKILL.md"])


if __name__ == "__main__":
    unittest.main()
