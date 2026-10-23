"""The rung, per service: which answer to `write-model` a project records, and what each is given.

Phase 15's whole claim is that two questions were welded into one. *Is there a model?* is the profile and
is project-wide; *is the log the truth?* is a reading of one service's write side, and a product may own
one context that earns the log beside three that do not. So the two things worth proving here are that
`project.json` says it per deployable, and that the files a service is given follow its own answer and not
the project's profile.

The second half runs against the toy package, because `backing_service_service_files` reads real assets off
disk and a fake with no files behind it would prove only that a dictionary was indexed.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages
import frontend_entry

from slipwai.adopt import wrapped_app
from slipwai.project.backing_services import backing_service_service_files, service_layout
from slipwai.project.metadata import metadata, sourced
from slipwai.rungs import EVENTS, STATE, every_rung, rung_rows
from slipwai.selection import Selection
from slipwai.services import App, service_app


def setUpModule() -> None:  # noqa: N802 - unittest's name
    """A browser app here is `react-vite`, whose catalogue entry is the TypeScript family's (`frontend_entry`)."""
    frontend_entry.install()


def tearDownModule() -> None:  # noqa: N802 - unittest's name
    frontend_entry.remove()

TOY = "toy-plain"  # the backend key; `toy` is the family, and the package that answers for both
EVENT_SOURCED = Selection({"write-model": "events", "persistence": "postgres"})
STATE_STORED = Selection({"write-model": "state", "persistence": "postgres"})


class SourcedTest(unittest.TestCase):
    """`eventSourced`, which used to be the profile and is now the service's own answer."""

    def test_a_service_is_sourced_when_its_own_answer_says_so(self) -> None:
        self.assertTrue(sourced(service_app("orders", TOY, 3000, EVENT_SOURCED)))
        self.assertFalse(sourced(service_app("billing", TOY, 3001, STATE_STORED)))

    def test_a_service_that_was_never_asked_is_state(self) -> None:
        """The standard profile does not offer the axis, and the axis's `absent` answers for it."""
        self.assertEqual(Selection({"persistence": "postgres"}).write_model, STATE)
        self.assertFalse(sourced(service_app("orders", TOY, 3000, Selection({"persistence": "postgres"}))))

    def test_a_browser_app_has_no_write_side_to_be_a_rung_of(self) -> None:
        self.assertFalse(sourced(App("web", "apps/web", "web", "typescript", "react-vite", 5173)))

    def test_an_application_the_keel_did_not_make_claims_no_past(self) -> None:
        """Never `events` by detection alone: `adopt --confirm` is what is allowed to record one (15.9)."""
        wrapped = wrapped_app("legacy", "services/legacy", "java", {}, {}, None, {}, kind="service")
        self.assertFalse(sourced(wrapped))


class ManifestTest(unittest.TestCase):
    """What a mixed project writes down, which is what `check-model` reads back (15.4)."""

    def setUp(self) -> None:
        apps = [
            service_app("orders", TOY, 3000, EVENT_SOURCED, first=True),
            service_app("billing", TOY, 3001, STATE_STORED),
            App("web", "apps/web", "web", "typescript", "react-vite", 5173, api="orders", first=True),
        ]
        self.deployables = json.loads(metadata("shop", "event-modelling", "none", apps))["deployables"]

    def test_one_project_records_both_rungs(self) -> None:
        self.assertEqual(
            {name: row["eventSourced"] for name, row in self.deployables.items()},
            {"orders": True, "billing": False, "web": False},
        )

    def test_the_rung_is_in_the_selection_each_service_carries(self) -> None:
        self.assertEqual(self.deployables["orders"]["selection"]["write-model"], EVENTS)
        self.assertEqual(self.deployables["billing"]["selection"]["write-model"], STATE)

    def test_only_the_sourced_service_claims_event_sourcing(self) -> None:
        """The capability travels with the axis answer now, not with the profile both services share."""
        self.assertIn("event-sourcing", self.deployables["orders"]["capabilities"])
        self.assertNotIn("event-sourcing", self.deployables["billing"]["capabilities"])


class RungRowsTest(unittest.TestCase):
    """Reading one side's declaration at a rung, including the backend that has not written one."""

    DECLARED = {"postgres": {"a.txt": "a"}, "state": {"postgres": {"b.txt": "b"}}}

    def test_the_event_sourced_rung_reads_the_feature_rows_and_not_the_block(self) -> None:
        self.assertEqual(rung_rows(self.DECLARED, EVENTS), {"postgres": {"a.txt": "a"}})

    def test_the_state_rung_reads_the_block_and_not_the_feature_rows(self) -> None:
        self.assertEqual(rung_rows(self.DECLARED, STATE), {"postgres": {"b.txt": "b"}})

    def test_a_backend_that_declared_no_state_block_answers_a_state_service_with_nothing(self) -> None:
        """A hole the conformance suite names (15.6), rather than one a generated page is left with."""
        self.assertEqual(rung_rows({"postgres": {"a.txt": "a"}}, STATE), {})

    def test_a_check_about_a_feature_sees_both_rungs_files(self) -> None:
        """A prune row is written per feature, so it has to cover the files of either rung — and so does the
        loader's check that every asset a package names is a file the package has."""
        self.assertEqual(every_rung(self.DECLARED), {"postgres": {"a.txt": "a", "b.txt": "b"}})


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class ServiceFilesTest(unittest.TestCase):
    """What each rung is actually given, off a real backend's assets."""

    def files(self, selection: Selection) -> dict[str, str]:
        return backing_service_service_files(selection, TOY)

    def test_the_event_sourced_service_is_given_the_log(self) -> None:
        written = self.files(EVENT_SOURCED)
        self.assertIn("adapters/event_store_postgres.txt", written)
        self.assertIn("adapters/event_store_memory.txt", written)
        self.assertNotIn("adapters/repository_postgres.txt", written)

    def test_the_state_stored_service_is_given_the_repository_and_a_versioned_table(self) -> None:
        written = self.files(STATE_STORED)
        self.assertIn("adapters/repository_postgres.txt", written)
        self.assertIn("migrations/0001_state_table.txt", written)
        self.assertNotIn("adapters/event_store_postgres.txt", written)
        self.assertNotIn("adapters/checkpoint_store_postgres.txt", written)

    def test_both_rungs_keep_the_in_memory_adapter_the_contract_runs_against(self) -> None:
        self.assertIn("adapters/repository_memory.txt", self.files(STATE_STORED))
        self.assertIn("adapters/event_store_memory.txt", self.files(EVENT_SOURCED))

    def test_the_store_is_the_persistence_answer_on_either_rung(self) -> None:
        """The rung settles what the store holds; the persistence axis settles which store it is."""
        memory = service_layout(TOY, STATE)
        self.assertIn("memory", memory)
        self.assertNotIn("adapters/repository_postgres.txt", self.files(Selection({"write-model": "state"})))

if __name__ == "__main__":  # pragma: no cover
    unittest.main()
