"""The standing briefs as assets: that the substitution is closed, and that moving them changed no byte.

Two things are held here and they answer different fears.

**The substitution is closed, both ways.** Nothing under `assets/` was templated before the briefs moved
there, so `{{make}}` is a new kind of mistake this repository has no habit of catching: a file that is valid
markdown whether or not its placeholders resolved, copied into somebody's repository, where the literal
`{{make}}` reads as a typo in the method rather than as a bug in the keel. So every token an asset names must
be one `briefs.values` provides — otherwise generation refuses, and this says so before a person finds out —
and every value `briefs.values` provides must be named by some asset, because a token nothing uses is a value
somebody will keep in step with a path that moved for no reader at all.

**The move changed nothing a project receives.** `tests/fixtures/agent-briefs.sha256` is what the generator
rendered at 9679053, the commit before the briefs left `agents.py`, and the test below is the only reason
that file exists: the eleven types, under two layouts, have to come back byte for byte. Two layouts because
`{{make}}` is the one value most briefs interpolate, and a record taken at the default layout alone would
pass with the substitution stubbed out to the empty string.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.errors import GenerationError
from slipwai.layout import Layout
from slipwai.project import briefs, prose
from slipwai.project.agents import agent_files, types

RECORD = Path(__file__).resolve().parent / "fixtures/agent-briefs.sha256"


def recorded() -> dict[tuple[str, str], str]:
    """The record, as `(delivery, path) -> digest`, with its header read as the comment it is."""
    rows = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, delivery, path = line.split()
        rows[(delivery, path)] = digest
    return rows


def assets() -> dict[str, str]:
    """Every brief under `assets/toolkit/agents/`, by type name, as it is written."""
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(briefs.BRIEFS.glob("*.md"))}


class SubstitutionTest(unittest.TestCase):
    """The gate on the first templated assets the keel has: a closed set, used in full."""

    def setUp(self) -> None:
        self.assets = assets()
        self.values = briefs.values(Layout())

    def test_every_token_an_asset_names_is_one_the_substitution_provides(self) -> None:
        for name, text in self.assets.items():
            for token in prose.MARKER.findall(text):
                with self.subTest(brief=name, token=token):
                    self.assertIn(token, self.values,
                                  f"{name}.md names {{{{{token}}}}}, which no brief value provides")

    def test_every_value_the_substitution_provides_is_named_by_some_asset(self) -> None:
        """The direction that rots quietly: a value nothing names is a path somebody keeps in step for
        nobody, and it is still there to be interpolated into the next brief by accident."""
        named = {token for text in self.assets.values() for token in prose.MARKER.findall(text)}
        self.assertEqual(sorted(set(self.values) - named), [],
                         "these brief values are provided and no asset names them")

    def test_a_token_no_value_provides_is_refused_rather_than_left_in_the_text(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            briefs.resolve("sail-tasks-quartermaster", "run {{mke}} verify", self.values)
        self.assertIn("mke", str(raised.exception))

    def test_nothing_the_generator_writes_still_carries_a_marker(self) -> None:
        """The failure the gate is for: a placeholder shipped literally into somebody's repository, in a
        file that is valid markdown either way, so nothing downstream would have noticed."""
        for path, text in agent_files().items():
            with self.subTest(file=path):
                self.assertNotIn("{{", text)

    def test_the_marker_leaves_prose_alone(self) -> None:
        """Why this is a closed set and not `str.format`: a brief is markdown, and a shell variable or a
        JSON example in one must not become an escaping question for whoever writes the prose."""
        text = "set `${HOME}` and write `{\"writes\": \"none\"}`, then run {{make}} verify"
        self.assertEqual(briefs.resolve("x", text, {"make": "make"}),
                         "set `${HOME}` and write `{\"writes\": \"none\"}`, then run make verify")


class FrontmatterTest(unittest.TestCase):
    """A brief carries its description and never its scope."""

    def test_every_type_has_a_brief_and_every_brief_has_a_type(self) -> None:
        """A missing one fails generation, which is loud. The other direction is the quiet one: every file
        under `assets/toolkit/` is copied into a project at the path it sits at, and only the eleven the
        generator also writes are written over. A twelfth file here — a shared preamble, a note to whoever
        edits these — would ship into somebody's repository raw, with its `{{make}}` still in it."""
        self.assertEqual(sorted(assets()), sorted(agent.name for agent in types()))

    def test_a_brief_carries_exactly_one_field(self) -> None:
        for name in assets():
            with self.subTest(brief=name):
                self.assertTrue(briefs.read(name).summary)

    def test_a_brief_that_declares_its_own_scope_is_refused(self) -> None:
        """The whole reason `name`, `stage`, `writes` and `commands` stay generated from
        `stage_models.STAGES`: an asset that hand-wrote `writes: none` could disagree with the table every
        harness is projected from, and the harness would enforce whichever it was handed."""
        for field in briefs.DECLARED:
            with self.subTest(field=field), self.assertRaises(GenerationError) as raised:
                briefs.parse("sail-gaps-lookout", f"---\ndescription: a line\n{field}: none\n---\n\nbody\n")
            self.assertIn(field, str(raised.exception))

    def test_a_brief_with_no_frontmatter_is_refused_by_name(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            briefs.parse("sail-gaps-lookout", "You read, and you report what is missing.\n")
        self.assertIn("sail-gaps-lookout.md", str(raised.exception))

    def test_a_type_with_no_brief_says_which_file_is_missing(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            briefs.read("sail-navigator")
        self.assertIn("sail-navigator.md", str(raised.exception))


class ByteForByteTest(unittest.TestCase):
    """What the generator rendered before the briefs moved, and what it renders now."""

    def test_the_record_covers_every_type_it_was_taken_of_under_both_layouts(self) -> None:
        """A record that lost a row would pass by not asking about the file that changed.

        It is the types that *moved* that are recorded, not every type the keel will ever have: a type
        added afterwards has no "before" at that commit and nothing to be compared against. The count is
        therefore two per recorded path, and a path that lost one of its two layouts fails here.
        """
        rows = recorded()
        paths = {path for _delivery, path in rows}
        self.assertEqual(len(rows), 2 * len(paths))
        self.assertLessEqual(paths, {f"agents/{agent.name}.md" for agent in types()},
                             "the record names a type the keel no longer has")

    def test_every_file_is_what_it_was_before_the_briefs_left_the_module(self) -> None:
        rows = recorded()
        for delivery in sorted({key[0] for key in rows}):
            rendered = agent_files(Layout(delivery))
            for path, digest in sorted((path, digest) for (held, path), digest in rows.items()
                                       if held == delivery):
                with self.subTest(layout=delivery, file=path):
                    self.assertIn(path, rendered, f"{path} is recorded in {RECORD.name} and no longer rendered")
                    self.assertEqual(hashlib.sha256(rendered[path].encode("utf-8")).hexdigest(), digest,
                                     f"{path} is no longer the text recorded in {RECORD.name}")

    def test_a_moved_layout_reaches_every_brief_that_names_make(self) -> None:
        """The two records differ for exactly the briefs that interpolate `{{make}}`, which is what makes
        the second layout worth recording rather than a copy of the first."""
        rows = recorded()
        names = {token for text in assets().values() for token in prose.MARKER.findall(text)}
        self.assertIn("make", names)
        moved = {path for (delivery, path), digest in rows.items()
                 if delivery != "." and rows[(".", path)] != digest}
        recorded_names = {path for _delivery, path in rows}
        self.assertEqual(
            sorted(moved),
            sorted(path for name, text in assets().items() if "{{make}}" in text
                   for path in [f"agents/{name}.md"] if path in recorded_names),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
