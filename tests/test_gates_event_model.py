"""The event-model gate, proved by giving `check-model` each violation it exists to catch.

Its own suite rather than a section of `test_gates.py`, because the model is where the most rules
live: the shape of a slice, where its read model lives and what it costs, what its append is
guarded by, and what its events identify. Every case here runs the gate a generated project
actually invokes — `make check-model` — rather than importing the checker.
"""
from __future__ import annotations

import subprocess
import tempfile

from support import FactoryTestCase


class EventModelGateTest(FactoryTestCase):
    def test_event_model_gate_rejects_an_invalid_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "invalid-model-product")
            (repo / "docs/event-model/model.yaml").write_text(
                "version: 1\nslices:\n  - id: S1\n    name: Broken\n    pattern: automation\n"
                "    status: modelled\n    reads: []\n    frames:\n      - {type: cmd, name: SkipTheProcessor}\n"
            )
            result = subprocess.run(
                ["make", "check-model"], cwd=repo, text=True, capture_output=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames do not match", result.stderr)

    def test_event_model_gate_asks_where_a_planned_read_model_lives(self) -> None:
        """The read side's `stream`: unasked, the answer is whichever read path already exists, and the
        skeleton only has one — a fold over the log on every query. Each model below is the same slice with
        one thing wrong, run through the gate a generated project actually invokes."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "read-model-materialisation")
            model = repo / "docs/event-model/model.yaml"

            def check(*slice_lines: str) -> str:
                model.write_text(
                    "version: 1\nslices:\n"
                    "  - id: S1\n    name: Place an order\n    pattern: state-change\n"
                    "    status: implemented\n    actor: Customer\n    stream: order-{orderId}\n"
                    "    gwt: README.md\n    code: [README.md]\n"
                    "    frames:\n      - {type: ui, name: OrderForm}\n"
                    "      - {type: cmd, name: PlaceOrder}\n      - {type: evt, name: OrderPlaced}\n"
                    "  - id: S2\n    name: See an order confirmation\n"
                    + "".join(f"    {line}\n" for line in slice_lines)
                    + "    frames:\n      - {type: rmo, name: OrderSummary}\n"
                )
                result = subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)
                return result.stderr if result.returncode != 0 else ""

            # Planned with no answer at all: the finding names the three lifecycles, because a reader who
            # has to look them up answers this by taking whichever one is already free.
            unanswered = check("pattern: state-view", "status: planned", "actor: Customer", "reads: [OrderPlaced]")
            self.assertIn("names where its read model lives in `materialisation`", unanswered)
            self.assertIn("`async` (a catch-up subscription with a checkpoint)", unanswered)

            # A per-query fold with no ceiling. "Only viable for short streams" is a condition, and this is
            # the gate that refuses to let it stay an assumption.
            unbounded = check(
                "pattern: state-view", "status: planned", "actor: Customer", "reads: [OrderPlaced]",
                "materialisation: live",
            )
            self.assertIn("`liveBudget.events`", unbounded)
            self.assertIn("`liveBudget.because`", unbounded)

            # The same slice, answered. Nothing about materialisation survives.
            answered = check(
                "pattern: state-view", "status: planned", "actor: Customer", "reads: [OrderPlaced]",
                "materialisation: live", "liveBudget:", "  events: 40",
                "  because: one order stream, closed at delivery",
            )
            self.assertEqual(answered, "", answered)

            # And `async` needs no budget, because the cost belongs to the subscription instead.
            self.assertEqual(
                check(
                    "pattern: state-view", "status: planned", "actor: Customer", "reads: [OrderPlaced]",
                    "materialisation: async",
                ),
                "",
            )

    def test_event_model_gate_holds_identifying_attributes_to_what_a_tag_is_derived_from(self) -> None:
        """An event may say which of its attributes identify something, and that is what a project's
        `tags_of` is generated from — so the gate refuses the three ways the list stops being derivable:
        on a box that is not an event, beside a `data` string that says the same thing differently, and
        with one attribute named twice."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "identifying-attributes")
            model = repo / "docs/event-model/model.yaml"

            def check(*frame_lines: str) -> str:
                model.write_text(
                    "version: 1\nslices:\n"
                    "  - id: S1\n    name: Claim a seat\n    pattern: state-change\n"
                    "    status: modelled\n    actor: Customer\n"
                    "    frames:\n" + "".join(f"      {line}\n" for line in frame_lines)
                )
                result = subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)
                return result.stderr if result.returncode != 0 else ""

            # The shape that is right: the event's own attributes, two of them identifying, and one kind
            # named twice — which is a transfer, and has to be expressible.
            assert not check(
                "- {type: ui, name: SeatMap}",
                "- {type: cmd, name: ClaimSeat}",
                "- type: evt",
                "  name: SeatClaimed",
                "  attributes:",
                "    - {name: seatId, identifies: seat}",
                "    - {name: fromHold, identifies: hold}",
                "    - {name: toHold, identifies: hold}",
                "    - {name: claimedAt, type: instant}",
            )

            on_a_command = check(
                "- {type: ui, name: SeatMap}",
                "- type: cmd",
                "  name: ClaimSeat",
                "  attributes:",
                "    - {name: seatId, identifies: seat}",
                "- {type: evt, name: SeatClaimed}",
            )
            self.assertIn("which only an event has", on_a_command)

            both = check(
                "- {type: ui, name: SeatMap}",
                "- {type: cmd, name: ClaimSeat}",
                "- type: evt",
                "  name: SeatClaimed",
                "  data: seatId, claimedAt",
                "  attributes:",
                "    - {name: seatId, identifies: seat}",
            )
            self.assertIn("two places for one list", both)

            twice = check(
                "- {type: ui, name: SeatMap}",
                "- {type: cmd, name: ClaimSeat}",
                "- type: evt",
                "  name: SeatClaimed",
                "  attributes:",
                "    - {name: seatId, identifies: seat}",
                "    - {name: seatId, identifies: hold}",
            )
            self.assertIn("twice", twice)

            not_a_kind = check(
                "- {type: ui, name: SeatMap}",
                "- {type: cmd, name: ClaimSeat}",
                "- type: evt",
                "  name: SeatClaimed",
                "  attributes:",
                "    - {name: seatId, identifies: Seat}",
            )
            self.assertIn("which is not a kind", not_a_kind)

    def test_event_model_gate_asks_what_an_append_is_guarded_by(self) -> None:
        """`stream` was the only answer this gate accepted, and under a boundary drawn out of tags there
        is no stream to name. So the question generalised: a planned state-change slice declares the guard
        its append is checked against — a stream's version, or a query over tags — and what it folds has
        to be what that guard covers."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "what-guards-the-append")
            model = repo / "docs/event-model/model.yaml"

            def check(*slice_lines: str) -> str:
                model.write_text(
                    "version: 1\nslices:\n"
                    "  - id: S1\n    name: Hold a seat\n    pattern: state-change\n"
                    "    status: modelled\n    actor: Customer\n    stream: hold-{holdId}\n"
                    "    frames:\n      - {type: ui, name: SeatMap}\n"
                    "      - {type: cmd, name: HoldSeat}\n"
                    "      - type: evt\n        name: SeatHeld\n        attributes:\n"
                    "          - {name: holdId, identifies: hold}\n"
                    "  - id: S2\n    name: Claim a seat\n    pattern: state-change\n"
                    "    actor: Customer\n"
                    + "".join(f"    {line}\n" for line in slice_lines)
                    + "    frames:\n      - {type: ui, name: SeatMap}\n"
                    "      - {type: cmd, name: ClaimSeat}\n"
                    "      - type: evt\n        name: SeatClaimed\n        attributes:\n"
                    "          - {name: seatId, identifies: seat}\n"
                )
                result = subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)
                return result.stderr if result.returncode != 0 else ""

            # Planned with neither answer. The finding names both, because a reader who has to look them
            # up picks whichever the last slice used.
            neither = check("status: planned")
            self.assertIn("names what its append is guarded by", neither)
            self.assertIn("a boundary drawn over tags", neither)

            # A tag boundary is an answer, and `stream` is then not owed.
            assert not check(
                "status: planned",
                "guard: {by: [seat], because: a seat may be claimed once}",
            )

            # Both is not an answer: a conflict would mean two different things.
            both = check(
                "status: planned",
                "stream: seat-{seatId}",
                "guard: {by: [seat], because: a seat may be claimed once}",
            )
            self.assertIn("two answers to one question", both)

            # A boundary with no stated invariant is a query somebody widened until the tests passed.
            unstated = check("status: planned", "guard: {by: [seat]}")
            self.assertIn("`guard.because`", unstated)

            # And the rule that makes the pair mean something: folding an event the boundary cannot reach
            # is a decision guarded against something it never read.
            outside = check(
                "status: planned",
                "guard: {by: [seat], because: a seat may be claimed once}",
                "folds: [SeatHeld]",
            )
            self.assertIn("guarded against something it did not read", outside)

            # The same fold, with the boundary widened to the kind that event identifies.
            assert not check(
                "status: planned",
                "guard: {by: [seat, hold], because: a seat may be claimed once, and a hold has a cap}",
                "folds: [SeatHeld]",
            )

    def test_event_model_gate_refuses_a_todo_list_folded_per_request(self) -> None:
        """An automation's read model is not a view: a fold that only knows the streams this request wrote
        cannot be spawned standalone, so the work a dead request abandoned is never recovered."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "todo-list-persisted")
            (repo / "docs/event-model/model.yaml").write_text(
                "version: 1\nslices:\n"
                "  - id: S1\n    name: Claim a place\n    pattern: state-change\n"
                "    status: modelled\n    actor: Attendee\n    stream: registration-{id}\n"
                "    frames:\n      - {type: ui, name: RegistrationForm}\n"
                "      - {type: cmd, name: ClaimPlace}\n      - {type: evt, name: PlaceClaimed}\n"
                "  - id: S2\n    name: Allocate a seat\n    pattern: automation\n"
                "    status: modelled\n    reads: [PlaceClaimed]\n    stream: ticket-pool-{id}\n"
                "    materialisation: live\n"
                "    frames:\n      - {type: rmo, name: UnallocatedClaims}\n"
                "      - {type: pcr, name: AllocateOnClaim}\n      - {type: cmd, name: AllocateSeat}\n"
                "      - {type: evt, name: SeatAllocated}\n"
            )
            result = subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("todo list, so it must be persisted", result.stderr)
            # One finding, not three: a refused `live` is not then asked to bound the fold it may not do.
            self.assertNotIn("liveBudget", result.stderr)

    def test_event_model_gate_holds_depends_on_to_a_dag_of_genuine_build_deps(self) -> None:
        """`depends_on` is build order, not timeline order.

        Needing another slice's events is solved with synthetic fixtures (Principle V), so a depends_on
        that is exactly the producers of this slice's reads is refused. Unknown ids and cycles are too.
        A genuine code dependency that is not only those producers is allowed.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "depends-on-dag")
            model = repo / "docs/event-model/model.yaml"

            def check(body: str) -> str:
                model.write_text("version: 1\nslices:\n" + body)
                result = subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)
                return result.stderr if result.returncode != 0 else ""

            s1 = (
                "  - id: S1\n    name: Place an order\n    pattern: state-change\n"
                "    status: modelled\n    actor: Customer\n    stream: order-{id}\n"
                "    frames:\n      - {type: ui, name: Checkout}\n"
                "      - {type: cmd, name: PlaceOrder}\n      - {type: evt, name: OrderPlaced}\n"
            )
            # Artificial: depends_on is exactly the producer of reads.
            artificial = check(
                s1
                + "  - id: S2\n    name: See confirmation\n    pattern: state-view\n"
                "    status: modelled\n    actor: Customer\n    reads: [OrderPlaced]\n"
                "    depends_on: [S1]\n"
                "    frames:\n      - {type: rmo, name: OrderSummary}\n"
            )
            self.assertIn("exactly the producers of its reads", artificial)

            # Unknown id.
            unknown = check(
                s1
                + "  - id: S2\n    name: See confirmation\n    pattern: state-view\n"
                "    status: modelled\n    actor: Customer\n    reads: [OrderPlaced]\n"
                "    depends_on: [S9]\n"
                "    frames:\n      - {type: rmo, name: OrderSummary}\n"
            )
            self.assertIn("not a slice id", unknown)

            # Cycle.
            cycle = check(
                "  - id: S1\n    name: A\n    pattern: state-change\n"
                "    status: modelled\n    actor: Customer\n    stream: a-{id}\n"
                "    depends_on: [S2]\n"
                "    frames:\n      - {type: ui, name: AUI}\n"
                "      - {type: cmd, name: DoA}\n      - {type: evt, name: ADone}\n"
                "  - id: S2\n    name: B\n    pattern: state-change\n"
                "    status: modelled\n    actor: Customer\n    stream: b-{id}\n"
                "    depends_on: [S1]\n"
                "    frames:\n      - {type: ui, name: BUI}\n"
                "      - {type: cmd, name: DoB}\n      - {type: evt, name: BDone}\n"
            )
            self.assertIn("depends_on cycle", cycle)

            # Genuine: depends_on names a slice that is not merely the reads producer set — here S2
            # depends on S1 for a build reason while reading nothing from it; S3 reads S1's events
            # with empty depends_on (synthetic seed).
            ok = check(
                s1
                + "  - id: S2\n    name: Admin tooling that shares S1's module\n    pattern: state-change\n"
                "    status: modelled\n    actor: Admin\n    stream: admin-{id}\n"
                "    depends_on: [S1]\n"
                "    frames:\n      - {type: ui, name: Admin}\n"
                "      - {type: cmd, name: Adjust}\n      - {type: evt, name: Adjusted}\n"
                "  - id: S3\n    name: See confirmation\n    pattern: state-view\n"
                "    status: modelled\n    actor: Customer\n    reads: [OrderPlaced]\n"
                "    frames:\n      - {type: rmo, name: OrderSummary}\n"
            )
            self.assertEqual(ok, "", ok)
