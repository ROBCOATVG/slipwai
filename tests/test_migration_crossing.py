"""A crossing that was aborted and re-run writes the person's words and the project's history once."""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.layout import layout_of
from slipwai.logs import deck_path, entry
from slipwai.migration_crossing import catch_up, seed
from slipwai.migration_flight import Flight


def flight(*, extra: bool = False) -> Flight:
    """What one run of the crossing prepares. Called again for the retry, so the lines stamped at write
    time carry a second run's clock exactly as they would after `git merge --abort`."""
    logs = [
        ("ordering", "main", replace(entry("told", fairway="main", message="ship the gate first"),
                                     t="2026-01-01T09:00:00Z")),
        ("ordering", "main", replace(entry("told", fairway="main", message="say it twice"),
                                     t="2026-01-01T10:00:00Z")),
        ("ordering", "main", replace(entry("told", fairway="main", message="say it twice"),
                                     t="2026-01-02T10:00:00Z")),
        # The same words at the same instant: version 1 put `cruise-told.jsonl` back ahead of
        # `cruise-inbox.jsonl` and a person can say a thing twice. Nothing here may swallow one of them.
        ("ordering", "main", replace(entry("told", fairway="main", message="do it now"),
                                     t="2026-01-03T10:00:00Z")),
        ("ordering", "main", replace(entry("told", fairway="main", message="do it now"),
                                     t="2026-01-03T10:00:00Z")),
        ("ordering", "ordering", entry("merged", fairway="ordering", slice="ORD-01", commit="abc123")),
        ("ordering", "ordering", entry("claimed", fairway="ordering", slice="ORD-02")),
        ("ordering", "main", entry("parked", fairway="main", why="the gate is red")),
    ]
    if extra:
        logs.append(("ordering", "ordering", entry("merged", fairway="ordering", slice="ORD-02", commit="def456")))
    return Flight(logs=logs)


class SeedTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def written(self) -> dict[str, list[dict]]:
        found: dict[str, list[dict]] = {}
        for feature, fairway in (("ordering", "main"), ("ordering", "ordering")):
            path = self.root / deck_path(feature, fairway)
            lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
            found[fairway] = [json.loads(line) for line in lines if line.startswith("{")]
        return found

    def test_the_same_message_said_twice_in_version_1_crosses_as_two_lines(self) -> None:
        seed(self.root, flight())
        said = [line["message"] for line in self.written()["main"] if line["kind"] == "told"]
        self.assertEqual(said, ["ship the gate first", "say it twice", "say it twice",
                                "do it now", "do it now"])

    def test_an_aborted_crossing_re_run_does_not_say_the_persons_words_a_second_time(self) -> None:
        seed(self.root, flight())
        first = self.written()
        seed(self.root, flight())
        self.assertEqual(self.written(), first)

    def test_a_retry_still_records_what_trunk_gained_since_the_crossing_was_aborted(self) -> None:
        seed(self.root, flight())
        seed(self.root, flight(extra=True))
        merged = [(line["slice"], line["commit"]) for line in self.written()["ordering"] if line["kind"] == "merged"]
        self.assertEqual(merged, [("ORD-01", "abc123"), ("ORD-02", "def456")])

    def test_a_line_this_crossing_did_not_write_is_never_counted_as_one_it_did(self) -> None:
        path = self.root / deck_path("ordering", "ordering")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json at all\n" + entry("claimed", fairway="ordering", slice="ORD-02").line(),
                        encoding="utf-8")
        seed(self.root, flight())
        kinds = [line["kind"] for line in self.written()["ordering"]]
        self.assertEqual(kinds, ["claimed", "merged", "claimed"])


class CatchUpTest(unittest.TestCase):
    """What the crossing could not do is on the page, beside what it asks the person to confirm."""

    def page(self, notes: list[str]) -> str:
        document = {"name": "orders", "layout": {"delivery": "."}}
        return catch_up("orders", "1.5.1", "1.5.1", Flight(), layout_of(document), {}, notes)

    def test_a_clean_crossing_asks_the_person_to_confirm_what_it_wrote(self) -> None:
        page = self.page([])
        self.assertIn("releaseMode", page)
        self.assertNotIn("## What this crossing could not do", page)

    def test_what_the_crossing_could_not_write_is_said_on_the_page(self) -> None:
        page = self.page(["`project.json` conflicted, so releaseMode and state were not written."])
        self.assertIn("## What this crossing could not do", page)
        self.assertIn("`project.json` conflicted", page)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
