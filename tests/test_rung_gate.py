"""`make check-model` read against the rung the slice's service is on, and the two naming rules.

The gate is a toolkit script that ships inside a generated project, so it is loaded here the way a project
runs it — from `assets/toolkit/scripts/event-model/` — rather than reimplemented. `validate()` takes the
services and the rungs so a suite can state both without writing a `project.json`; in a project both are
read from the manifest, which is where `eventSourced` has lived since it was written.

Three claims. **A model with one slice on each rung passes**, which is the project phase 15 exists to make
generatable. **A field that needs a log is refused by name on a service that keeps none** — a `guard` is a
boundary over a tag query and `folds` is a replay, and a slice naming either on a state-stored service is
describing machinery that service was never given. And **the rung is invisible to the chart**: `chart.py`
reads `context`, `service`, `evt` frames and `reads`, and none of the three fields that move, so the
division of work is the same whichever rung either slice is on.

The naming rules are not rung rules and are tested across both: an event is a named business fact wherever
it is kept.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

GATE = TOOLKIT_ROOT / "scripts/event-model"


def gate():
    """`check.py`, loaded from the toolkit the way a generated project runs it."""
    sys.path.insert(0, str(GATE))
    try:
        spec = importlib.util.spec_from_file_location("model_gate_check", GATE / "check.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(GATE))


CHECK = gate()
SERVICES = {"orders": ["orders"], "billing": ["billing"]}
#: One service on each rung, which is the mixed project the phase is named for.
MIXED = {"orders": True, "billing": False}


def slice_of(service: str, **over: object) -> dict:
    """A planned state-change slice that passes on either rung, with `over` applied."""
    item: dict = {
        "id": f"S-{service}",
        "pattern": "state-change",
        "status": "planned",
        "capability": "ordering",
        "service": service,
        "context": service,
        "stream": service,
        "actor": "customer",
        "gwt": ["docs/event-model/model.yaml"],
        "code": ["docs/event-model/model.yaml"],
        # One event name per service: two slices producing the same event is its own finding, and this
        # suite is about the rung rather than about that one.
        "frames": [
            {"type": "ui", "name": f"{service.title()}Screen"},
            {"type": "cmd", "name": f"Place{service.title()}"},
            {"type": "evt", "name": f"{service.title()}Placed"},
        ],
    }
    item.update(over)
    return item


def findings(
    *slices: dict,
    rungs: dict[str, bool] | None = None,
    publishes: dict[str, str] | None = None,
) -> list[str]:
    # Every stream these fixtures name states its invariant, which `stream-states-its-invariant` owes; the
    # rule itself is held in `StreamInvariantTest` below.
    stated = {str(item["stream"]).split("{", 1)[0].rstrip("-_: "): {"because": "one decision per order"}
              for item in slices if item.get("stream")}
    model = {"version": 1, "streams": stated, "slices": list(slices)}
    return CHECK.validate(model, SERVICES, MIXED if rungs is None else rungs, publishes or {})


def view_on(service: str, reads: list[str], **over: object) -> dict:
    """A planned `async` read model on `service`, folding events some other slice produced."""
    item: dict = {
        "id": f"V-{service}", "pattern": "state-view", "status": "planned", "capability": "ordering",
        "service": service, "context": service, "materialisation": "async",
        "reads": reads, "gwt": ["docs/event-model/model.yaml"], "code": ["docs/event-model/model.yaml"],
        "frames": [{"type": "rmo", "name": f"{service.title()}View"}],
    }
    item.update(over)
    return item


class BothRungsTest(unittest.TestCase):
    def test_one_slice_on_each_rung_passes(self) -> None:
        self.assertEqual(findings(slice_of("orders"), slice_of("billing")), [])

    def test_a_service_the_manifest_says_nothing_about_is_read_as_state_stored(self) -> None:
        """`state` is the `write-model` axis's own `absent`, and a log nobody vouched for is a guess."""
        guarded = slice_of("orders", stream=None, guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertTrue(any("keeps current state" in line for line in findings(guarded, rungs={})))


class OutboxTest(unittest.TestCase):
    """A mark nobody can consume, which is the failure `check-chart` exists to prevent (15.13).

    On the `state` rung an event is modelled always and emitted only where something reads it (15.14), and
    the moment the reader is *another service* the outbox stops being optional: the producing service
    raised a fact in its own transaction and nothing carries it across the boundary. The refusal names the
    producing service, because that is whose rung has to move, and `project.json` records the answer as
    `publishes` beside `eventSourced` — `outbox`, `bus` or `cdc`, whichever the project already has.

    Three ways this is *not* a finding, each for its own reason: the reader is the producer's own service
    and the link is a call the use case makes; the producer keeps a log, which is publication; or the
    producer has recorded how it publishes.
    """

    def test_a_cross_service_read_of_a_state_stored_event_is_refused(self) -> None:
        found = findings(slice_of("billing"), view_on("orders", ["BillingPlaced"]))
        said = "\n".join(found)
        self.assertIn("BillingPlaced", said)
        self.assertIn("billing", said, "the refusal names the producing service")
        self.assertIn("outbox", said, "the refusal names the rung that would clear it")

    def test_the_producing_service_is_named_and_not_the_reading_one(self) -> None:
        """`orders` is where the finding is raised and `billing` is whose rung has to move."""
        said = "\n".join(findings(slice_of("billing"), view_on("orders", ["BillingPlaced"])))
        self.assertIn("`billing`", said)

    def test_a_read_inside_the_producers_own_service_is_not_refused(self) -> None:
        """Within one service the next step is a call the use case makes, not a message it sends itself."""
        found = findings(slice_of("billing"), view_on("billing", ["BillingPlaced"]))
        self.assertEqual([line for line in found if "outbox" in line], [])

    def test_a_cross_service_read_of_an_event_sourced_producer_is_not_refused(self) -> None:
        """The log is the publication: there is nothing for an outbox to do that the stream does not."""
        found = findings(slice_of("orders"), view_on("billing", ["OrdersPlaced"]))
        self.assertEqual([line for line in found if "outbox" in line], [])

    def test_a_producer_that_records_how_it_publishes_clears_the_refusal(self) -> None:
        for mechanism in ("outbox", "bus", "cdc"):
            with self.subTest(mechanism=mechanism):
                found = findings(slice_of("billing"), view_on("orders", ["BillingPlaced"]),
                                 publishes={"billing": mechanism})
                self.assertEqual([line for line in found if "outbox" in line], [])


class ManifestTest(unittest.TestCase):
    """`publishes` as `project.json` carries it, which is what a project runs the gate against."""

    def read(self, document: dict) -> dict:
        directory = Path(tempfile.mkdtemp())
        (directory / "project.json").write_text(json.dumps(document), encoding="utf-8")
        was = CHECK.MANIFEST
        CHECK.MANIFEST = directory / "project.json"
        try:
            return CHECK.project_publishes()
        finally:
            CHECK.MANIFEST = was

    def test_a_service_that_names_a_mechanism_is_read(self) -> None:
        found = self.read({"deployables": {"billing": {"kind": "service", "publishes": "outbox"}}})
        self.assertEqual(found, {"billing": "outbox"})

    def test_a_service_that_names_none_is_absent_rather_than_empty(self) -> None:
        self.assertEqual(self.read({"deployables": {"billing": {"kind": "service"}}}), {})

    def test_only_services_answer_it(self) -> None:
        """A browser app has no write side to publish from, so `publishes` on one is not an answer."""
        found = self.read({"deployables": {"web": {"kind": "browser", "publishes": "outbox"}}})
        self.assertEqual(found, {})

    def test_a_manifest_that_is_not_there_is_no_answers_and_not_a_traceback(self) -> None:
        was = CHECK.MANIFEST
        CHECK.MANIFEST = Path(tempfile.mkdtemp()) / "project.json"
        try:
            self.assertEqual(CHECK.project_publishes(), {})
        finally:
            CHECK.MANIFEST = was


class StateStoredTest(unittest.TestCase):
    """The three fields that move, each refused with the reason rather than at a later gate."""

    def refuse(self, **over: object) -> str:
        found = findings(slice_of("billing", **over))
        self.assertTrue(found, "expected a finding")
        return "\n".join(found)

    def test_a_guard_is_refused_and_names_what_to_use_instead(self) -> None:
        said = self.refuse(guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertIn("needs a log to query", said)
        self.assertIn("`stream`", said)

    def test_folds_are_refused_and_say_why_there_is_nothing_to_replay(self) -> None:
        said = self.refuse(folds=["OrdersPlaced"])
        self.assertIn("nothing to replay", said)
        self.assertIn("saves at the version it read", said)

    def test_a_planned_state_change_still_owes_a_stream(self) -> None:
        said = self.refuse(stream=None)
        self.assertIn("row or aggregate one transaction locks", said)

    def test_a_live_state_view_is_not_asked_for_a_budget_it_cannot_have(self) -> None:
        """`liveBudget` bounds the fold a `live` view does on every query, and there is no fold here."""
        view = {
            "id": "V1", "pattern": "state-view", "status": "planned", "capability": "ordering",
            "service": "billing", "context": "billing", "materialisation": "live",
            "reads": ["OrdersPlaced"], "gwt": ["x"], "code": ["x"],
            "frames": [{"type": "rmo", "name": "Invoices"}],
        }
        self.assertEqual([line for line in findings(slice_of("orders"), view) if "liveBudget" in line], [])


class EventSourcedTest(unittest.TestCase):
    """What the event-sourced rung keeps, so the state rung's rules are a reading and not a rewrite."""

    def test_a_guard_instead_of_a_stream_is_still_the_two_answers_to_one_question(self) -> None:
        guarded = slice_of("orders", stream=None, guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertEqual(findings(guarded, slice_of("billing")), [])

    def test_folds_are_what_a_decider_rehydrates_from(self) -> None:
        self.assertEqual(findings(slice_of("orders", folds=["OrdersPlaced"]), slice_of("billing")), [])


class NamingTest(unittest.TestCase):
    """Not rung rules: an event is a named business fact on either rung."""

    def named(self, event: str, service: str = "orders", **frame: object) -> str:
        item = slice_of(service, frames=[
            {"type": "ui", "name": "Screen"},
            {"type": "cmd", "name": "DoIt"},
            {"type": "evt", "name": event, **frame},
        ])
        return "\n".join(findings(item))

    def test_a_crud_verb_is_refused_with_the_name_to_use_instead(self) -> None:
        said = self.named("OrdersUpdated")
        self.assertIn("names the write and not the fact", said)
        self.assertIn("`OrdersPlaced`", said)

    def test_the_crud_rule_holds_on_the_state_stored_rung_too(self) -> None:
        self.assertIn("names the write and not the fact", self.named("OrdersUpdated", "billing"))

    def test_an_honestly_crud_event_says_so_and_says_why(self) -> None:
        self.assertEqual(self.named("PageUpdated", crud=True, because="a CMS page is a document"), "")

    def test_the_exemption_without_a_reason_is_the_one_everything_gets(self) -> None:
        self.assertIn("needs a `because`", self.named("PageUpdated", crud=True))

    def test_a_negative_name_is_refused_for_the_failure_underneath_it(self) -> None:
        said = self.named("OrderNotShipped")
        self.assertIn("nothing raises an absence", said)
        self.assertIn("`reason` attribute", said)

    def test_a_name_that_merely_contains_those_letters_is_left_alone(self) -> None:
        """`UserNotified`, `AccountUnlocked` and `ItemUnpacked` are facts, not absences."""
        for name in ("UserNotified", "AccountUnlocked", "ItemUnpacked", "UnitAssigned"):
            with self.subTest(name=name):
                self.assertEqual(self.named(name), "")

    def test_a_business_verb_passes_on_both_rungs(self) -> None:
        for service in ("orders", "billing"):
            with self.subTest(service=service):
                self.assertEqual(self.named("OrderPlaced", service), "")


class HeldNamesTest(unittest.TestCase):
    """An event already in a log keeps its name: a stored event cannot be renamed (issue 95).

    `slipwai migrate` writes the names a version 1 model's implemented slices hold, once, at the crossing;
    the two naming rules pass exactly those names and hold every other one as before. The pattern is the
    plain-sentence rule's (`.specify/decisions-in-short.json`): no file, no exemption.
    """

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        (self.root / ".specify").mkdir()
        was = CHECK.ROOT
        CHECK.ROOT = self.root
        self.addCleanup(setattr, CHECK, "ROOT", was)

    def hold(self, body: object) -> None:
        text = body if isinstance(body, str) else json.dumps(body)
        (self.root / CHECK.NAMES_FROM).write_text(text, encoding="utf-8")

    def named(self, *events: str, **frame: object) -> list[str]:
        """One slice per event, read through the file as `make check-model` reads it."""
        slices = [slice_of("orders", id=f"S{number}", frames=[
            {"type": "ui", "name": f"Screen{number}"}, {"type": "cmd", "name": f"DoIt{number}"},
            {"type": "evt", "name": event, **frame}]) for number, event in enumerate(events, start=1)]
        return findings(*slices)

    def test_a_project_with_no_file_is_held_on_every_name(self) -> None:
        self.assertEqual(CHECK.held_event_names(), frozenset())
        self.assertEqual(len(self.named("WorkspaceCreated", "DocumentNotReceived")), 2)

    def test_the_names_the_file_holds_pass_both_rules(self) -> None:
        self.hold({"events": ["WorkspaceCreated", "WorkspaceDeleted", "DocumentNotReceived"]})
        self.assertEqual(self.named("WorkspaceCreated", "WorkspaceDeleted", "DocumentNotReceived"), [])

    def test_a_name_the_file_does_not_hold_is_refused_beside_ones_that_pass(self) -> None:
        self.hold({"events": ["WorkspaceCreated", "DocumentNotReceived"]})
        found = self.named("WorkspaceCreated", "ModelVersionCreated", "DocumentNotReceived", "InviteNotSent")
        self.assertEqual(len(found), 2, found)
        self.assertIn("`ModelVersionCreated` names the write and not the fact", found[0])
        self.assertIn("`InviteNotSent` names something that did not happen", found[1])

    def test_a_held_name_is_exact_and_not_a_prefix_or_a_spelling(self) -> None:
        self.hold({"events": ["WorkspaceCreated"]})
        for near in ("WorkspaceCreatedUpdated", "workspaceCreated", "NewWorkspaceCreated"):
            with self.subTest(name=near):
                self.assertEqual(len(self.named(near)), 1)

    def test_no_other_rule_is_lifted_for_a_held_name(self) -> None:
        self.hold({"events": ["WorkspaceCreated"]})
        found = self.named("WorkspaceCreated", "WorkspaceCreated")
        self.assertEqual(len(found), 1, found)
        self.assertNotIn("names the write", found[0], "two slices raising one event is refused, held or not")

    def test_a_file_that_cannot_be_read_is_said_rather_than_forgiving_everything_or_nothing(self) -> None:
        for body in ("{", "[]", "{}", {"events": "WorkspaceCreated"}, {"events": ["WorkspaceCreated", 3]},
                     {"events": ["WorkspaceCreated", ""]}, {"events": None}, "null"):
            with self.subTest(body=body):
                self.hold(body)
                with self.assertRaises(OSError) as refused:
                    self.named("WorkspaceCreated")
                self.assertIn(CHECK.NAMES_FROM, str(refused.exception))
                self.assertIn('{"events": [', str(refused.exception), "it says what the file holds")

    def test_the_gate_as_a_project_runs_it_fails_on_an_unreadable_file(self) -> None:
        self.hold("{")
        with mock.patch.object(CHECK, "load_yaml", return_value={"version": 1, "slices": []}):
            self.assertEqual(self.run_main(), 1)
        self.hold({"events": []})
        with mock.patch.object(CHECK, "load_yaml", return_value={"version": 1, "slices": []}):
            self.assertEqual(self.run_main(), 0)

    def run_main(self) -> int:
        """`check.py`'s own last lines: an `OSError` is a failed gate with its reason, never a traceback."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return CHECK.main()
            except (OSError, ValueError):
                return 1


class ChartTest(unittest.TestCase):
    """The rung is invisible to the division of work, which is what makes it per service at all."""

    def test_the_chart_reads_no_field_the_rung_moves(self) -> None:
        source = (GATE / "chart.py").read_text(encoding="utf-8")
        for field in ("stream", "guard", "folds", "materialisation", "eventSourced", "liveBudget"):
            with self.subTest(field=field):
                self.assertNotIn(f'"{field}"', source)
                self.assertNotIn(f"'{field}'", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class StreamInvariantTest(unittest.TestCase):
    """A stream states, once, the decision that needs it to be one expected-version check.

    `guard.because` was always owed; a stream needed no reason, so one was named from the spec's noun —
    "one record per leaver" — and decided a feature's shape before any seam test could ask what decides
    together. The rule asks for the reason, never for a split.
    """

    def validate(self, streams: object, *slices: dict) -> list[str]:
        model = {"version": 1, "slices": list(slices)} | ({} if streams is None else {"streams": streams})
        return [f for f in CHECK.validate(model, SERVICES, MIXED, {}) if "invariant" in f or "`streams`" in f]

    def test_a_stream_with_no_stated_invariant_is_refused_once_with_the_fix(self) -> None:
        said = self.validate(None, slice_of("orders"), slice_of("orders", id="S-orders-2"))
        self.assertEqual(len(said), 1, said)
        self.assertIn("stream orders (first appended to by S-orders) states no invariant", said[0])
        self.assertIn('streams: {orders: {because: "..."}}', said[0])

    def test_a_stated_invariant_passes(self) -> None:
        self.assertEqual(self.validate({"orders": {"because": "closure refuses every later command (FR-33)"}},
                                       slice_of("orders")), [])

    def test_a_blank_because_is_no_invariant(self) -> None:
        self.assertEqual(len(self.validate({"orders": {"because": " "}}, slice_of("orders"))), 1)

    def test_a_proposed_slice_owes_nothing_yet(self) -> None:
        self.assertEqual(self.validate(None, slice_of("orders", status="proposed")), [])

    def test_streams_must_be_a_mapping(self) -> None:
        self.assertEqual(self.validate(["orders"], slice_of("orders")),
                         ["`streams` is a mapping of stream name to `{because: ...}`"])
