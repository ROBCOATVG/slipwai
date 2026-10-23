"""Every quickstart this repository ships, held to being readable, honest and still true of the catalogue.

`docs/reference/` carries six worked quickstarts and no code. That is exactly the shape of thing that rots:
nothing imports them, nothing runs them, and the catalogue underneath them moves. An axis that stops being
offered under a target, an option renamed, a profile that no longer carries the axis — every one of those
turns a shipped example into a file that is offered in the interview, chosen by somebody who does not know
any better, and refused by the generator afterwards. The refusal is a good one; being handed it by a document
this repository publishes is not.

So this suite is the gate the documents are kept honest by, and it reads them the way a person would: through
the keel's own reader, against the merged catalogue, and against the README beside each one. Three of its
cases exist because of a specific way a quickstart can be wrong while still parsing:

* **An answer the profile does not ask for.** `resolve_selection` refuses `--persistence postgres` under
  `--profile standard` outright — the store is the driven port the modelled write side is written against,
  and `standard` has no such port. `internal-tool` is the example that names neither axis, and this is what
  holds it to that.
* **An answer the target cannot carry.** `sqlite` and `keycloak` are offered under `none` and `existing`
  only; `cognito` under `aws`; `entra` under `azure`. A quickstart that crossed those would generate a
  project claiming a destination it cannot reach.
* **A language answered but not named.** `missing()` greys a quickstart out by what it lists under
  `languages`, so one that answered `language: go` without naming the package would be offered on a machine
  that cannot carry it out.

What is **not** checked here is the language answer against the catalogue, because this suite pins
`packages/` and the language packages are published elsewhere: `toy` is the only family loaded. Checking
`python` against a catalogue that has never heard of it would be a case that passed by being vacuous. The
language answer is held to the quickstart's own `languages` list instead, which is the thing the interview
actually reads.
"""
from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import quickstart
from slipwai.catalog import CATALOG, CORE, TARGETS
from slipwai.cli_quickstart import check_quickstart
from slipwai.errors import GenerationError
from slipwai.index_schema import QUICKSTART
from slipwai.package_new import core_range
from slipwai.package_release import kind_of
from slipwai.quickstart import Quickstart

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/reference"
#: The index that lists them. A directory nothing links to is a directory nobody finds.
INDEX = REFERENCE / "README.md"
#: `0.1.0`, and nothing else: a package's version is a number, not a range or a word.
VERSION = re.compile(r"\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?")


def shipped() -> list[Path]:
    """Every directory under `docs/reference/` holding a quickstart, by name."""
    return sorted(path.parent for path in REFERENCE.glob(f"*/{quickstart.MANIFEST}"))


def loaded() -> list[tuple[Path, Quickstart]]:
    """Every shipped quickstart that reads at all, with the one that does not left out.

    Left out rather than raised, because one document with a stray key would otherwise turn every case in
    this file into the same error about that one file, and the four real faults in the other five would not
    be reported until somebody had fixed it and run the suite again. `DocumentTest` is where not reading is
    the failure; everywhere else it is a document that cannot be asked the question.
    """
    found = []
    for root in shipped():
        try:
            found.append((root, quickstart.load(root / quickstart.MANIFEST)))
        except GenerationError:
            continue
    return found


def targets() -> set[str]:
    """Every target that can be answered: the keel's own two, and each installed target package."""
    return set(CATALOG["targets"]) | {each.name for each in TARGETS}


class ShippedQuickstartsTest(unittest.TestCase):
    """The set, as a set: that there is one, and that the index names it."""

    def test_there_is_more_than_one_and_each_has_the_three_files_a_package_has(self) -> None:
        """A quickstart package is a manifest, the reasoning and a version. The README is not decoration:
        a document whose answers are explained nowhere is a row of package names to the one reader a
        quickstart exists for."""
        found = shipped()
        self.assertGreater(len(found), 1, "docs/reference/ has stopped carrying worked quickstarts")
        for root in found:
            with self.subTest(quickstart=root.name):
                self.assertTrue((root / "README.md").is_file(), f"{root.name} has no README beside it")
                version = (root / "VERSION").read_text(encoding="utf-8").strip()
                self.assertRegex(version, f"^{VERSION.pattern}$", f"{root.name}'s VERSION is not a number")

    def test_the_index_names_every_one_of_them(self) -> None:
        """The only way anybody meets these is by reading the page above them. A directory added without a
        row on it is a worked example nobody will ever find, which is the whole of its value gone."""
        page = INDEX.read_text(encoding="utf-8")
        for root in shipped():
            with self.subTest(quickstart=root.name):
                self.assertIn(f"]({root.name}/)", page, f"{root.name} is not listed in docs/reference/README.md")

    def test_the_directory_name_is_the_quickstart_name(self) -> None:
        """`slipwai quickstart install docs/reference/<name>` then `show <name>`: the two lines every one of
        these READMEs prints. They are only the same name by this holding."""
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                self.assertEqual(one.name, root.name)


class DocumentTest(unittest.TestCase):
    """That each one reads, and reads as the thing the publisher's verbs would carry."""

    def test_each_parses_through_the_keels_own_reader(self) -> None:
        """Not a schema of this suite's own. A document this suite accepted and `quickstart find` refused
        would be a gate that proved the wrong thing in the one direction that matters."""
        for root in shipped():
            with self.subTest(quickstart=root.name):
                self.assertEqual(kind_of(root), QUICKSTART)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(check_quickstart(root), 0)

    def test_each_is_written_the_way_the_keel_writes_one(self) -> None:
        """Read, rendered and compared: a shipped document with a stray key, a different order or a field
        the reader drops is one that no longer matches what `quickstart save` would produce from the same
        answers — and these exist to be copied."""
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                held = json.loads((root / quickstart.MANIFEST).read_text(encoding="utf-8"))
                self.assertEqual(quickstart.document(one), held)

    def test_each_carries_a_sentence_about_the_product_rather_than_its_packages(self) -> None:
        """`suits` is the row the interview lists it by. The reader is somebody who does not know what an
        extension is, so a `suits` that was a name, a slug or a package list is addressed to the wrong
        person — the reader a quickstart exists for cannot choose from it."""
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                self.assertNotIn(one.name, one.suits, f"{one.name}'s `suits` names itself, not the product")
                self.assertGreaterEqual(len(one.suits.split()), 8, f"{one.name}'s `suits` is not a sentence")
                self.assertTrue(one.suits.endswith("."), f"{one.name}'s `suits` is not a finished sentence")

    def test_each_names_its_packages_by_range_and_never_by_a_pin(self) -> None:
        """The one rule a quickstart has that no other package does. A pinned one holds every team that
        installs it to the afternoon it was written, and the first thing anybody does is edit the file — at
        which point it is not a shared decision any more."""
        for root, one in loaded():
            for each in (*one.languages, *one.extensions):
                with self.subTest(quickstart=root.name, package=each.name):
                    self.assertIn(">=", each.version, f"{each.name} is named by `{each.version}`, not a range")
                    self.assertNotIn("==", each.version)

    def test_each_names_the_keel_range_this_keel_would_write(self) -> None:
        """`core` is what says a document is for this keel at all. One left behind at an older major is a
        quickstart that will be fetched out of a channel and refused by the reader that fetched it."""
        expected = core_range(CORE["schemaVersion"])
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                self.assertEqual(one.core, expected)


class AnswersTest(unittest.TestCase):
    """That every answer is one the catalogue actually offers, to the project this quickstart describes."""

    def test_the_profile_is_the_catalogues_and_the_frontend_the_keels_or_a_languages(self) -> None:
        """`none` is the keel's; every other frontend is shipped by a language (`docs/frontend-protocol.md`), so
        a quickstart answering one has to name a language to install, or it offers a browser app nobody can.
        Which language ships it is that language's to say, and no language is installed here to ask."""
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                self.assertIn(one.profile, CATALOG["profiles"])
                if one.frontend and one.frontend not in CATALOG["frontends"]:
                    self.assertTrue(one.languages, f"{one.frontend} is a language's, and this names none")

    def test_the_target_is_the_keels_own_or_a_target_package(self) -> None:
        """`none` and `existing` are the keel's; a cloud is a package. A quickstart answering a target
        neither of those knows would be offered and then refused for a name nobody can install."""
        offered = targets()
        for root, one in loaded():
            with self.subTest(quickstart=root.name):
                self.assertIn(one.target, offered, f"{one.name} answers an unknown target")

    def test_every_axis_it_answers_is_an_axis_and_every_answer_an_option(self) -> None:
        for root, one in loaded():
            for axis, answer in one.axes.items():
                with self.subTest(quickstart=root.name, axis=axis):
                    self.assertIn(axis, CATALOG["axes"], f"{one.name} answers `{axis}`, which is no axis")
                    self.assertIn(answer, CATALOG["axes"][axis]["options"],
                                  f"{one.name} answers `{axis} {answer}`, which that axis does not offer")

    def test_it_answers_no_axis_its_own_profile_is_never_asked(self) -> None:
        """The failure `internal-tool` is the worked example of. `write-model` and `persistence` are carried
        by `event-modelling` alone, and `resolve_selection` refuses either one named under `standard` rather
        than ignoring it — so a quickstart that named one would be listed in the interview, chosen, and
        refused at generation with the profile in the message."""
        for root, one in loaded():
            for axis in one.axes:
                with self.subTest(quickstart=root.name, axis=axis):
                    self.assertIn(
                        one.profile, CATALOG["axes"][axis]["profiles"],
                        f"{one.name} answers `{axis}` under the {one.profile} profile, which never asks it",
                    )

    def test_every_answer_is_offered_under_the_target_it_names(self) -> None:
        """The other dimension an option is offered along. `sqlite` and `keycloak` are reachable under
        `none` and `existing` only, `cognito` under `aws`, `entra` under `azure`; a quickstart that crossed
        those would describe a project that cannot take its own infrastructure where it is going."""
        for root, one in loaded():
            for axis, answer in one.axes.items():
                with self.subTest(quickstart=root.name, axis=axis):
                    under = CATALOG["axes"][axis]["options"][answer]["targets"]
                    self.assertIn(
                        one.target, under,
                        f"{one.name} answers `{axis} {answer}`, which the {one.target} target is not offered",
                    )

    def test_the_language_it_answers_is_a_package_it_names(self) -> None:
        """What greys a quickstart out is its `languages` list, so a language answered but not named is one
        the interview believes it can carry out and the generator cannot."""
        for root, one in loaded():
            named = {each.name for each in one.languages}
            with self.subTest(quickstart=root.name):
                self.assertIn(one.language, named,
                              f"{one.name} answers `language {one.language}` and does not name the package")
                if one.framework:
                    backend = f"{one.language}-{one.framework}"
                    self.assertIn(backend, named,
                                  f"{one.name} answers `framework {one.framework}` and names no {backend}")


class ReasoningTest(unittest.TestCase):
    """That the page beside each document says the things a reader cannot work out from the JSON."""

    def page(self, root: Path) -> str:
        return (root / "README.md").read_text(encoding="utf-8")

    def test_each_page_opens_with_its_own_name(self) -> None:
        for root in shipped():
            with self.subTest(quickstart=root.name):
                self.assertEqual(self.page(root).splitlines()[0], f"# {root.name}")

    def test_each_page_says_it_is_an_example_and_not_a_default(self) -> None:
        """The sentence 13.5 is about. A worked quickstart read as a recommendation is a default set of
        third-party answers arrived at by accident, which is the thing this repository declined to ship."""
        for root in shipped():
            with self.subTest(quickstart=root.name):
                self.assertIn("not a default", self.page(root))

    def test_each_page_says_a_typed_flag_wins(self) -> None:
        """`applied` puts every answer behind a flag a person typed. A page that did not say so leaves a
        reader believing a quickstart decides things they cannot take back."""
        for root in shipped():
            with self.subTest(quickstart=root.name):
                page = self.page(root)
                self.assertIn("flag", page)
                self.assertIn(f"--quickstart {root.name}", page)

    def test_a_page_that_answers_the_rung_says_init_can_never_change_it(self) -> None:
        """`write-model` is the one unprunable axis: `state` on a service that has kept a log is a migration
        somebody writes, not a flag `./init` offers. A quickstart hands that decision to somebody who did
        not make it, so the page it is handed with is where it has to be said."""
        for root, one in loaded():
            if "write-model" not in one.axes:
                continue
            with self.subTest(quickstart=root.name):
                page = self.page(root)
                self.assertIn("write-model", page)
                self.assertIn("./init", page)

    def test_a_page_that_answers_a_target_package_says_to_install_it_first(self) -> None:
        """The gap this is the whole mitigation for. `missing()` reads `languages` and `extensions` only, so
        a quickstart naming `target: aws` is offered on a machine without the AWS target installed and
        refused at generation instead. Until the check learns about targets, the prerequisite lives on the
        page — and this is what stops it being edited away."""
        packaged = {each.name for each in TARGETS}
        for root, one in loaded():
            if one.target not in packaged:
                continue
            with self.subTest(quickstart=root.name):
                self.assertIn(f"slipwai target install {one.target}", self.page(root))


class CarriedTest(unittest.TestCase):
    """That the keel carries them, which is the difference between a worked example and an offer.

    For six phases these were six directories nobody's copy had. They were not in any channel's index, they
    were not in anybody's `~/.slipwai/quickstarts`, and the only way to meet one was to know the path to it
    in a checkout — so `slipwai quickstart list` said "no quickstart is saved here", the interview asked no
    question at all, and the board's Quickstarts table was empty on every machine in the world. The set is
    carried now, and these are what hold it to being carried.
    """

    def empty(self) -> mock._patch_dict:
        """A quickstart directory with nothing in it: what a machine that has saved none looks like."""
        return mock.patch.dict("os.environ", {quickstart.VARIABLE: tempfile.mkdtemp()})

    def test_every_shipped_quickstart_is_one_the_keel_carries(self) -> None:
        self.assertEqual(sorted(quickstart.carried()), sorted(root.name for root in shipped()))

    def test_each_is_named_and_found_on_a_machine_that_has_saved_none(self) -> None:
        """By name and with no path, which is what `--quickstart <name>` and both interviews do."""
        with self.empty():
            self.assertEqual(quickstart.saved_names(), [])
            for root in shipped():
                with self.subTest(quickstart=root.name):
                    self.assertIn(root.name, quickstart.names())
                    self.assertEqual(quickstart.find(root.name).name, root.name)

    def test_a_saved_one_of_the_same_name_is_the_one_found(self) -> None:
        """A team who saved their own over ours meant theirs. Carried is a default, like everything else a
        quickstart is."""
        with tempfile.TemporaryDirectory() as area:
            name = sorted(quickstart.carried())[0]
            ours = quickstart.find(name)
            mine = {**quickstart.document(ours), "suits": "mine, and not the one this keel carries"}
            (Path(area) / f"{name}{quickstart.SUFFIX}").write_text(json.dumps(mine), encoding="utf-8")
            with mock.patch.dict("os.environ", {quickstart.VARIABLE: area}):
                self.assertEqual(quickstart.find(name).suits, mine["suits"])
                self.assertEqual(quickstart.names().count(name), 1)

    def test_the_keel_reads_them_from_beside_itself_rather_than_from_a_checkout(self) -> None:
        """`assets.ROOT` is the repository in a checkout and `slipwai/_bundle` in an installed copy, which
        is why `docs/reference` is in `assets.BUNDLED`. Read any other way, every case above would pass
        here and the feature would be absent from every copy anybody installs."""
        from slipwai.assets import BUNDLED, ROOT
        self.assertIn(quickstart.CARRIED, BUNDLED)
        for path in quickstart.carried().values():
            self.assertTrue(Path(path).is_relative_to(ROOT / quickstart.CARRIED), path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
