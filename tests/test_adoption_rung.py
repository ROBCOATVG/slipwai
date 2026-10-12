"""The rung, where the method is installed around code that was already here (15.9).

Phase 15 split Event Modeling from event sourcing. Adoption is where the bundle was spelled out most
plainly and where it did the most harm: `docs/change-strategy.md` opened by saying the generated method
carries the two as one, which is the claim this phase exists to retire. What replaces it is a sharpened
rule — the model is the same on every rung, the rung is a product decision per service — and the honest
reading for a capability that was already there, which is rung 2 of the ladder: events raised in process,
no log, and therefore no genesis event.

Four claims. **The essay says the sharpened rule and the rung-2 reading, and no longer says bundle.**
**`/survey` says the code that was here is an external system *or* a state-stored service of this
project**, by whether its behaviour has been modelled or only read. **`/strangle` names the rung in
*Decide the new home*** — `state` with change data capture or an outbox and no genesis event, `events`
with one. And **a wrapped application is `state` until somebody says otherwise**: the survey proposes
`events` off an event-store dependency, and only a person confirming it records it. The strangler's other
precondition, the freeze, is `tests/test_freeze.py`.

The fifth claim is a negative and is held here because nothing else would notice it: **no persistence row
is added to the convergence map.** The map says where an adopted repository stands on each axis of the
keel's own shape, and every row on it has one top. A rung has no top — a service that honestly is field
updates is *finished* at `state` — so a row would say every service should climb to the log, which is the
claim this phase exists to stop making. `project.json` is the rung's record, per deployable.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.adopt import candidates_of
from slipwai.convergence import AXES
from slipwai.layout import AT_ROOT, Layout
from slipwai.origin import Adoption
from slipwai.project.metadata import sourced
from slipwai.project.pin_commands import pin_command_files
from slipwai.project.strangle_command import strangle_files
from slipwai.services import App
from slipwai.survey import survey

DELIVERY = Layout("delivery")


def wrapped(name: str = "shop", write_model: str | None = None, provenance: dict[str, str] | None = None) -> App:
    return App(name, ".", "service", "javascript", None, 0, generated=False, commands={"test": None},
               write_model=write_model, provenance=dict(provenance or {}))


def essay(adoption: Adoption | None = None) -> str:
    return strangle_files([wrapped()], DELIVERY, "existing", adoption)["docs/change-strategy.md"]


def strangle(adoption: Adoption | None = None) -> str:
    return strangle_files([wrapped()], DELIVERY, "existing", adoption)["commands/strangle.md"]


class HonestyTest(unittest.TestCase):
    """`docs/change-strategy.md`, *Be honest about the event model*."""

    def test_the_bundle_sentence_is_gone(self) -> None:
        page = essay()
        self.assertNotIn("as one bundle", page)
        self.assertNotIn("Event Modeling and event sourcing as one", page)

    def test_the_rule_is_sharpened_to_two_decisions(self) -> None:
        page = essay()
        section = page[page.index("## Be honest about the event model"):]
        section = section[:section.index("\n## ", 1)]
        self.assertIn("two decisions", section)
        self.assertIn("the same on every rung", section)
        self.assertIn("`eventSourced`", section, "the rung's record is `project.json`, per deployable")

    def test_the_rung_2_reading_of_a_capability_that_was_already_there(self) -> None:
        """A capability that moves rarely has a past worth keeping, so the honest rung is in-process events."""
        page = essay()
        section = page[page.index("## Be honest about the event model"):]
        section = section[:section.index("\n## ", 1)]
        self.assertIn("rung 2", section)
        self.assertIn("in-process events", section)
        self.assertIn("`--write-model state`", section)
        self.assertIn("no genesis event", section)

    def test_the_genesis_event_belongs_to_the_events_rung_alone(self) -> None:
        section = essay()
        section = section[section.index("## Be honest about the event model"):]
        section = section[:section.index("\n## ", 1)]
        genesis = section.index("genesis event", section.index("`--write-model events`"))
        self.assertGreater(genesis, section.index("`--write-model events`"),
                           "a genesis event is named under the rung that has a log to open")

    def test_nothing_in_the_legacy_tables_becomes_an_event_by_being_renamed(self) -> None:
        self.assertIn("by being renamed", essay())


class SurveySaysTest(unittest.TestCase):
    """`/survey`'s event-model section: two readings of the code that was already here."""

    def section(self) -> str:
        command = pin_command_files([wrapped()], DELIVERY, event=True)["commands/survey.md"]
        return command[command.index("## The event model"):command.index("\n## ", command.index("## The event model"))]

    def test_the_code_that_was_here_is_an_external_system_or_a_state_stored_service(self) -> None:
        section = self.section()
        self.assertIn("external system", section)
        self.assertIn("state-stored service", section)
        self.assertIn("whether its behaviour", section, "which it is turns on whether anybody modelled it")

    def test_the_profile_without_a_model_says_none_of_it(self) -> None:
        self.assertNotIn("## The event model", pin_command_files([wrapped()], DELIVERY, event=False)
                         ["commands/survey.md"])


class NewHomeTest(unittest.TestCase):
    """`/strangle`'s *Decide the new home* names the rung."""

    def section(self) -> str:
        command = strangle()
        start = command.index("## Decide the new home")
        return command[start:command.index("\n## ", start)]

    def test_the_rung_is_asked_before_add_service_runs(self) -> None:
        section = self.section()
        self.assertIn("`--write-model state`", section)
        self.assertIn("`--write-model events`", section)
        self.assertIn("change data capture", section)
        self.assertIn("outbox", section)

    def test_state_takes_no_genesis_event_and_events_takes_one(self) -> None:
        section = self.section()
        state = section.index("`--write-model state`")
        events = section.index("`--write-model events`")
        self.assertIn("no genesis event", section[state:events])
        self.assertIn("genesis event", section[events:])


class WrappedRungTest(unittest.TestCase):
    """A wrapped application's rung: `state` until somebody vouches for the log."""

    def test_a_wrapped_application_nobody_has_answered_for_is_not_event_sourced(self) -> None:
        self.assertFalse(sourced(wrapped()))

    def test_one_recorded_events_by_a_person_is(self) -> None:
        app = wrapped(write_model="events", provenance={"writeModel": "confirmed"})
        self.assertTrue(sourced(app))
        self.assertEqual(app.record()["writeModel"], "events")

    def test_state_recorded_by_a_person_is_a_written_no_and_not_a_silence(self) -> None:
        app = wrapped(write_model="state", provenance={"writeModel": "confirmed"})
        self.assertFalse(sourced(app))
        self.assertEqual(app.record()["writeModel"], "state")
        self.assertNotIn("writeModel", wrapped().record(), "silence is not an answer")

    def test_a_generated_service_still_reads_its_own_selection(self) -> None:
        from slipwai.selection import Selection

        generated = App("api", "apps/api", "service", "typescript", "express", 3000,
                        Selection({"write-model": "events"}))
        self.assertTrue(sourced(generated))

    def test_the_survey_proposes_events_off_an_event_store_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({
                "name": "shop", "scripts": {"test": "vitest"},
                "dependencies": {"@eventstore/db-client": "^6.0.0", "express": "^4"},
            }), encoding="utf-8")
            candidate = candidates_of(survey(root), "shop")[0]
            self.assertEqual(candidate["writeModel"], "events")
            self.assertEqual(candidate["writeModelEvidence"], "eventstore in package.json")

    def test_a_repository_with_no_event_store_proposes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({
                "name": "shop", "scripts": {"test": "vitest"}, "dependencies": {"express": "^4"},
            }), encoding="utf-8")
            candidate = candidates_of(survey(root), "shop")[0]
            self.assertNotIn("writeModel", candidate)

    def test_the_manifest_carries_the_rung_and_its_provenance(self) -> None:
        from slipwai.manifest import apps_from_manifest
        from slipwai.project.metadata import metadata

        app = wrapped(write_model="events", provenance={"language": "confirmed", "writeModel": "confirmed"})
        document = json.loads(metadata("shop", "event-modelling", "existing", [app], AT_ROOT,
                                       Adoption(why="a new capability has to ship")))
        self.assertTrue(document["deployables"]["shop"]["eventSourced"])
        self.assertEqual(document["deployables"]["shop"]["writeModel"], "events")
        read_back = apps_from_manifest(document)
        self.assertEqual(read_back[0].write_model, "events")
        self.assertEqual(read_back[0].provenance["writeModel"], "confirmed")


class ConfirmTest(unittest.TestCase):
    """`slipwai adopt --confirm <name> --write-model events`, and what confirming without it means."""

    def flags(self, *given: str) -> dict:
        import argparse

        from slipwai.cli_adopt import adopt_parser
        from slipwai.cli_confirm import confirmations

        parser: argparse.ArgumentParser = adopt_parser()
        return confirmations(parser.parse_args(list(given)))

    def test_the_bare_form_names_the_one_candidate_being_confirmed(self) -> None:
        self.assertEqual(self.flags("--confirm", "shop", "--write-model", "events"),
                         {"shop": {"write_model": "events"}})

    def test_the_paired_form_says_which_of_several(self) -> None:
        self.assertEqual(
            self.flags("--confirm", "shop", "--confirm", "till", "--write-model", "shop=events"),
            {"shop": {"write_model": "events"}, "till": {}},
        )

    def test_the_bare_form_is_refused_where_it_could_mean_either(self) -> None:
        from slipwai.errors import GenerationError

        with self.assertRaises(GenerationError) as raised:
            self.flags("--confirm", "shop", "--confirm", "till", "--write-model", "events")
        self.assertIn("--write-model NAME=events", str(raised.exception))

    def test_a_rung_the_axis_has_not_got_is_refused(self) -> None:
        from slipwai.errors import GenerationError

        with self.assertRaises(GenerationError) as raised:
            self.flags("--confirm", "shop", "--write-model", "sourced")
        self.assertIn("events", str(raised.exception))
        self.assertIn("state", str(raised.exception))

    def test_confirming_without_it_records_no_rung_at_all(self) -> None:
        self.assertEqual(self.flags("--confirm", "shop"), {"shop": {}})

    def test_the_application_records_it_with_confirmed_provenance(self) -> None:
        from slipwai.confirm import as_application

        candidate = {"name": "shop", "path": ".", "language": "javascript", "kind": "service",
                     "commands": {"test": "npm test"}, "toolchain": {}, "evidence": "package.json",
                     "writeModel": "events", "writeModelEvidence": "@eventstore/db-client in package.json"}
        # The proposal is on the candidate, where every proposal lives. Confirming it is a person's word.
        with tempfile.TemporaryDirectory() as directory:
            recorded = as_application(Path(directory), candidate, {"write_model": "events"})
            self.assertEqual(recorded.write_model, "events")
            self.assertEqual(recorded.provenance["writeModel"], "confirmed")

    def test_a_candidate_proposed_events_and_confirmed_in_silence_stays_state(self) -> None:
        """Detection is not a person. A log nobody vouched for is a guess wearing a fact's clothes."""
        from slipwai.confirm import as_application

        candidate = {"name": "shop", "path": ".", "language": "javascript", "kind": "service",
                     "commands": {"test": "npm test"}, "toolchain": {}, "evidence": "package.json",
                     "writeModel": "events", "writeModelEvidence": "@eventstore/db-client in package.json"}
        with tempfile.TemporaryDirectory() as directory:
            recorded = as_application(Path(directory), candidate, {})
            self.assertIsNone(recorded.write_model)
            self.assertNotIn("writeModel", recorded.provenance)
            self.assertFalse(sourced(recorded))


class NoMapRowTest(unittest.TestCase):
    """The rung is a product decision per service, and the map is not where product decisions live."""

    def test_the_convergence_map_has_no_persistence_row(self) -> None:
        keys = {axis.key for axis in AXES}
        for absent in ("persistence", "write-model", "event-store", "rung"):
            self.assertNotIn(absent, keys)

    def test_every_axis_on_the_map_has_a_top_every_repository_should_reach(self) -> None:
        """Which is why the rung is not one of them: a service that honestly is field updates is finished."""
        for axis in AXES:
            self.assertEqual(axis.rungs[-1], axis.target, axis.key)


class GroundTest(unittest.TestCase):
    """`/ground` asks the rung where, and only where, the survey proposed one."""

    def command(self, candidates: list[dict]) -> str:
        from slipwai.project.ground_command import ground_command_files

        adoption = Adoption(candidates=candidates, convergence=[])
        return ground_command_files([wrapped()], DELIVERY, adoption)["commands/ground.md"]

    def test_a_proposed_log_becomes_a_question_with_its_evidence(self) -> None:
        command = self.command([{"name": "shop", "path": ".", "language": "javascript", "kind": "service",
                                 "commands": {}, "toolchain": {}, "evidence": "package.json",
                                 "writeModel": "events",
                                 "writeModelEvidence": "@eventstore/db-client in package.json"}])
        self.assertIn("--write-model events", command)
        self.assertIn("@eventstore/db-client in package.json", command)

    def test_a_repository_the_survey_proposed_none_for_is_not_asked(self) -> None:
        command = self.command([{"name": "shop", "path": ".", "language": "javascript", "kind": "service",
                                 "commands": {}, "toolchain": {}, "evidence": "package.json"}])
        self.assertNotIn("--write-model", command)


if __name__ == "__main__":
    unittest.main()
