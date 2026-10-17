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
from slipwai.migration_crossing import (
    blocks,
    catch_up,
    implemented_elsewhere,
    infrastructure,
    off_infrastructure,
    seed,
)
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


class InfraTest(unittest.TestCase):
    """A crossing does not write `infra/`.

    Those files describe resources that already exist — a Terraform resource address is state — and which
    of them are real is not something the keel can know. It is not hypothetical: a crossing restored one of
    the factory's own identity stacks under its 2.x name, into a project that had deleted it months before
    and written its own beside it, and the deploy stopped on a duplicate declaration. The rename is why no
    merge caught it: the base and the offering share a path the project has never had, so "ours deleted it"
    reads as "theirs added it".
    """

    def test_infrastructure_is_the_whole_directory_and_nothing_that_merely_starts_like_it(self) -> None:
        self.assertTrue(infrastructure("infra"))
        self.assertTrue(infrastructure("infra/service/cognito_external.tf"))
        self.assertFalse(infrastructure("infrastructure.md"))
        self.assertFalse(infrastructure("docs/infra/notes.md"))

    def sides(self) -> tuple[dict, dict]:
        """The warbook crossing in miniature: a renamed file, a new one, one taken away, and code."""
        return ({"infra/service/sign_in_customers.tf": b"old", "infra/service/store.tf": b"same",
                 "infra/service/gone.tf": b"dropped", "apps/web/main.ts": b"code"},
                {"infra/service/sign_in_external.tf": b"renamed", "infra/service/store.tf": b"same",
                 "infra/service/added.tf": b"offered", "apps/web/main.ts": b"other"})

    def test_neither_factory_side_brings_any_infrastructure_into_the_merge(self) -> None:
        """Out of the offering so nothing is written, and out of the base so a path the project deleted
        cannot come back as `theirs added a file` — which is precisely how a renamed one did."""
        before, theirs, _ = off_infrastructure(*self.sides())
        self.assertEqual(list(before), ["apps/web/main.ts"])
        self.assertEqual(list(theirs), ["apps/web/main.ts"])

    def test_what_it_would_have_changed_is_named_rather_than_done(self) -> None:
        """Written, added and taken away — all three are changes to somebody's deployed stack."""
        _, _, declined = off_infrastructure(*self.sides())
        self.assertEqual(declined, ["infra/service/added.tf", "infra/service/gone.tf",
                                    "infra/service/sign_in_customers.tf",
                                    "infra/service/sign_in_external.tf"])

    def test_an_unchanged_stack_is_not_reported_as_something_it_declined(self) -> None:
        same = {"infra/service/store.tf": b"same"}
        self.assertEqual(off_infrastructure(same, dict(same))[2], [])

    def test_the_merge_then_keeps_the_project_s_own_copy_of_every_infra_file(self) -> None:
        """With neither factory side holding the path, the project's is the only version there is."""
        from slipwai.migration_merge import merge
        before, theirs, _ = off_infrastructure(*self.sides())
        own = {"infra/service/sign_in_ours.tf": b"ours", "apps/web/main.ts": b"code"}
        result = merge(before, own, theirs)
        self.assertEqual(result.files["infra/service/sign_in_ours.tf"], b"ours")
        self.assertNotIn("infra/service/sign_in_external.tf", result.files)
        self.assertEqual(result.conflicts, {})

    def test_the_notes_name_every_path_it_declined_to_write(self) -> None:
        said = catch_up("demo", "1.3.0", "1.3.0", flight(), layout_of({}), {}, [],
                        ["infra/service/sign_in_external.tf"])
        self.assertIn("Infrastructure, left alone", said)
        self.assertIn("infra/service/sign_in_external.tf", said)
        self.assertIn("tofu plan", said)

    def test_a_crossing_that_conflicted_opens_by_setting_the_project_up(self) -> None:
        """The page a person reads after resolving opens with the steps that leave the project set up, and
        names the files it stopped at — before the fairways, which cannot be confirmed over a merge."""
        said = catch_up("demo", "1.3.0", "1.3.0", flight(), layout_of({}), {}, [],
                        conflicts=("commands/sail.md",))
        self.assertLess(said.index("First: set the project up"), said.index("Then: confirm the fairways"))
        self.assertIn("- `commands/sail.md`", said)
        self.assertIn("make check-agents", said)

    def test_a_crossing_that_would_not_have_touched_infra_has_no_such_section(self) -> None:
        self.assertNotIn("Infrastructure, left alone",
                         catch_up("demo", "1.3.0", "1.3.0", flight(), layout_of({}), {}, []))


class BlockTest(unittest.TestCase):
    """A backing-service block is identified by its marker, never by the file it happens to sit in.

    The factory's identity stack and the project's replacement for it both said
    `backing-service:users-keycloak`. The migration had everything it needed to see one block implemented
    twice and looked at the filenames instead — and because a rename makes the factory's file an addition
    rather than a change, nothing conflicted and both landed.
    """

    def test_a_marker_naming_two_features_is_both_of_them(self) -> None:
        """A region two features need names both, and stays while either remains."""
        self.assertEqual(blocks(b"# backing-service:keycloak|users-keycloak:begin\nx\n"),
                         {"keycloak", "users-keycloak"})
        self.assertEqual(blocks(b"nothing marked here"), set())

    def test_a_block_the_project_implements_under_another_name_is_not_taken(self) -> None:
        own = {"infra/sign_in_ours.tf": b"# backing-service:users-keycloak:begin\nours\n"}
        theirs = {"infra/sign_in_theirs.tf": b"# backing-service:users-keycloak:begin\ntheirs\n"}
        kept, said = implemented_elsewhere(own, theirs)
        self.assertEqual(kept, {})
        self.assertIn("users-keycloak", said[0])
        self.assertIn("infra/sign_in_ours.tf", said[0])

    def test_a_file_the_project_has_at_that_path_is_left_to_the_merge(self) -> None:
        """It is a change, not an addition, and three-way merging is exactly what that wants."""
        same = {"a.tf": b"# backing-service:users-keycloak:begin\nmine\n"}
        kept, said = implemented_elsewhere(same, {"a.tf": b"# backing-service:users-keycloak:begin\nnew\n"})
        self.assertEqual(list(kept), ["a.tf"])
        self.assertEqual(said, [])

    def test_a_block_nobody_else_implements_is_taken(self) -> None:
        kept, said = implemented_elsewhere({}, {"new.tf": b"# backing-service:http-fastify:begin\n"})
        self.assertEqual(list(kept), ["new.tf"])
        self.assertEqual(said, [])

    def test_a_file_that_also_brings_something_new_is_a_question_for_a_person(self) -> None:
        """Dropping it would take the new block away with the duplicated one."""
        own = {"ours.tf": b"# backing-service:users-keycloak:begin\n"}
        theirs = {"both.tf": b"# backing-service:users-keycloak:begin\n# backing-service:store-rds:begin\n"}
        kept, said = implemented_elsewhere(own, theirs)
        self.assertEqual(list(kept), ["both.tf"])
        self.assertEqual(said, [])

    def test_a_file_with_no_markers_is_none_of_this_rule_s_business(self) -> None:
        kept, _ = implemented_elsewhere({"ours.md": b"# backing-service:users-keycloak:begin\n"},
                                        {"README.md": b"prose"})
        self.assertEqual(list(kept), ["README.md"])

    def test_the_notes_name_what_was_not_taken_and_what_already_holds_it(self) -> None:
        said = catch_up("demo", "1.3.0", "1.3.0", flight(), layout_of({}), {}, [], [],
                        ["`theirs.tf` — `users-keycloak` is already implemented by `ours.tf`"])
        self.assertIn("Blocks you already implement", said)
        self.assertIn("theirs.tf", said)


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
