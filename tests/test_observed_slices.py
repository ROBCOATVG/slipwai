"""`observed`, the fifth status: a slice that records what code already does (15.10).

Every other status is a step on the path a slice walks — proposed, modelled, planned, implemented — and
each tightens what the model must contain. `observed` is not on that path. It says *this is what the code
does, and the model did not design it*, which is the honest thing to write about a repository the method
was installed around: a well-kept codebase was designed, just not here.

Three claims. **It owes the same evidence `implemented` owes** — `code` and `gwt` that exist — because a
slice claiming to record real behaviour with nothing to point at is a guess. **It is allowed only on a
service `project.json` records `generated: false`**, because code the keel wrote is code the keel can be
held to: an `observed` slice on a generated service is a way of avoiding `model-matches-code`, and the
move from `observed` to `implemented` is a slice of work rather than an edit to a status field. And **a
later slice may `reads` it**, because it is on the timeline for the joins — which is the whole reason the
model is global rather than one per feature.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

GATE = TOOLKIT_ROOT / "scripts/event-model"


def gate():
    sys.path.insert(0, str(GATE))
    try:
        spec = importlib.util.spec_from_file_location("observed_gate_check", GATE / "check.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(GATE))


CHECK = gate()
SERVICES = {"legacy": ["legacy"], "orders": ["orders"]}
#: `legacy` is the application the method was installed around; `orders` is one the keel made.
GENERATED = {"legacy": False, "orders": True}
#: A path that exists under the toolkit root, which is what `code` and `gwt` are checked against.
REAL = "docs/event-model/model.yaml"


def observed_on(service: str, **over: object) -> dict:
    item: dict = {
        "id": f"O-{service}",
        "pattern": "state-change",
        "status": "observed",
        "capability": "ordering",
        "service": service,
        "context": service,
        "stream": service,
        "actor": "customer",
        "gwt": [REAL],
        "code": [REAL],
        "frames": [
            {"type": "ui", "name": f"{service.title()}Screen"},
            {"type": "cmd", "name": f"Place{service.title()}"},
            {"type": "evt", "name": f"{service.title()}Placed"},
        ],
    }
    item.update(over)
    return item


def findings(*slices: dict, generated: dict[str, bool] | None = None) -> list[str]:
    model = {"version": 1, "slices": list(slices)}
    return CHECK.validate(model, SERVICES, {}, {}, GENERATED if generated is None else generated)


class ObservedTest(unittest.TestCase):
    def test_an_observed_slice_on_a_wrapped_service_passes(self) -> None:
        self.assertEqual(findings(observed_on("legacy")), [])

    def test_the_same_slice_on_a_generated_service_is_refused_by_name(self) -> None:
        said = "\n".join(findings(observed_on("orders")))
        self.assertIn("observed", said)
        self.assertIn("orders", said, "the refusal names the service")

    def test_it_owes_the_evidence_implemented_owes(self) -> None:
        for key in ("code", "gwt"):
            with self.subTest(key=key):
                said = "\n".join(findings(observed_on("legacy", **{key: []})))
                self.assertIn(key, said)

    def test_evidence_that_does_not_exist_is_refused(self) -> None:
        said = "\n".join(findings(observed_on("legacy", code=["docs/nothing-here.md"])))
        self.assertIn("code", said)

    def test_a_later_slice_may_read_what_an_observed_slice_raises(self) -> None:
        """It is on the timeline for the joins, which is why the model is global."""
        view = {
            "id": "V1", "pattern": "state-view", "status": "planned", "capability": "ordering",
            "service": "legacy", "context": "legacy", "materialisation": "live",
            "reads": ["LegacyPlaced"], "gwt": [REAL], "code": [REAL],
            "frames": [{"type": "rmo", "name": "Orders"}],
        }
        found = findings(observed_on("legacy"), view)
        self.assertEqual([line for line in found if "no earlier slice produces" in line], [])


class ReadySetTest(unittest.TestCase):
    """`/sail` never offers an `observed` slice, because it is a record and not work (15.10).

    The ready set comes from the chart and the deck logs, not from the model's status field — so the chart
    has to carry the fact, and `clearance.py` has to read it. Without this a captain would be sent to build
    what already ships, and the slice would sit in the ready set for ever because no `mark-set` line is
    ever written for behaviour nobody is building.
    """

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "observed_clearance", TOOLKIT_ROOT / "scripts/agents/clearance.py")
        assert spec is not None and spec.loader is not None
        self.clearance = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.clearance)
        self.charted = {"slices": {
            "O-1": {"fairway": "legacy", "sets": ["LegacyPlaced"], "steers_by": [], "observed": True},
            "V-1": {"fairway": "legacy", "sets": [], "steers_by": ["LegacyPlaced"]},
        }}

    def test_an_observed_slice_is_never_offered(self) -> None:
        self.assertNotIn("O-1", self.clearance.cleared_slices(self.charted, set()))

    def test_a_slice_steering_by_one_is_cleared_with_no_log_line(self) -> None:
        """Its marks are set by the code existing, and no deck log will ever carry a `mark-set` for them."""
        self.assertIn("V-1", self.clearance.cleared_slices(self.charted, set()))


class ChartTest(unittest.TestCase):
    """The chart is what carries the fact to the ready set, and carries it only where it is true."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "observed_chart", TOOLKIT_ROOT / "scripts/event-model/chart.py")
        assert spec is not None and spec.loader is not None
        sys.path.insert(0, str(GATE))
        try:
            self.chart = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.chart)
        finally:
            sys.path.remove(str(GATE))
        self.deployables = {"legacy": {"kind": "service", "path": "apps/legacy", "context": "legacy"}}

    def drawn(self, status: str) -> dict:
        model = {"slices": [observed_on("legacy", status=status)]}
        return self.chart.render(model, self.deployables)["slices"]["O-legacy"]

    def test_an_observed_slice_is_marked_on_the_chart(self) -> None:
        self.assertIs(self.drawn("observed").get("observed"), True)

    def test_every_other_status_carries_no_such_flag(self) -> None:
        """Absent rather than false: the chart says nothing about a slice that is ordinary work."""
        for status in ("proposed", "modelled", "planned", "implemented"):
            with self.subTest(status=status):
                self.assertNotIn("observed", self.drawn(status))

    def test_the_rung_is_still_invisible_to_the_chart(self) -> None:
        """15.4's rule, which 15.10 must not break: the chart does not know what rung anything is on."""
        drawn = self.drawn("observed")
        # `pattern` and `actor` joined the row for clearance and the feedback ranking (phase 20); neither
        # is the rung, which stays the model's alone.
        self.assertEqual(sorted(drawn), ["actor", "capability", "fairway", "observed", "pattern", "sets", "steers_by"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
