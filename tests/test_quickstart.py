"""A quickstart: the answers somebody gave once, under a name, given again without remembering them.

Generating a project is a language, a foundation, a target, an answer per axis and a set of extensions, and
every repository after the first is that decision re-made from recollection. A quickstart is the decision
written down — and the thing it is written down *for* is the person who does not know what `uipro` is, which
is why every one of these tests is about what the file says in words rather than about its keys.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from support import command

from slipwai import cli_quickstart, quickstart
from slipwai.errors import GenerationError

ANSWERS: dict[str, object] = {
    "profile": "event-modelling",
    "target": "none",
    "language": "toy",
    "framework": "plain",
    "frontend": "react-vite",
    "axes": {"persistence": "postgres", "http": "toy-serve"},
}
DOCUMENT: dict[str, object] = {
    "quickstart": 1,
    "name": "toy-ui",
    "suits": "A product whose browser app is the product, with the review gates already on.",
    "core": ">=9.0,<10",
    "answers": ANSWERS,
    "languages": [{"name": "toy", "version": ">=1.0,<2"}],
    "extensions": [{"name": "codegraph", "version": ">=0.1,<1", "guards": ["before-search"]}],
}


def saved(into: Path, document: dict | None = None) -> Path:
    """One quickstart written where `SLIPWAI_QUICKSTARTS` points, as `save` writes it."""
    body = DOCUMENT if document is None else document
    into.mkdir(parents=True, exist_ok=True)
    path = into / f"{body['name']}.json"
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


class DocumentTest(unittest.TestCase):
    def test_a_quickstart_is_read_back_as_what_it_was_written_from(self) -> None:
        """The round trip is the whole of the promise: a second project from one name and no remembering."""
        self.assertEqual(quickstart.document(quickstart.read(DOCUMENT)), DOCUMENT)

    def test_the_sentence_is_about_the_product_and_a_quickstart_without_one_is_refused(self) -> None:
        """What the interview lists is this sentence (13.2). A quickstart with no sentence about the
        product it suits would be listed by its package names, to the one reader it exists for."""
        with self.assertRaises(GenerationError) as refused:
            quickstart.read({**DOCUMENT, "suits": ""})
        self.assertIn("suits", str(refused.exception))
        self.assertIn("sentence", str(refused.exception))

    def test_a_name_that_could_not_be_a_file_or_a_flag_is_refused(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            quickstart.read({**DOCUMENT, "name": "../../etc/passwd"})
        self.assertIn("name", str(refused.exception))

    def test_an_answer_that_is_not_an_answer_is_refused_rather_than_carried(self) -> None:
        answers = dict(ANSWERS, axes={"persistence": ["postgres"]})
        document = {**DOCUMENT, "answers": answers}
        with self.assertRaises(GenerationError) as refused:
            quickstart.read(document)
        self.assertIn("persistence", str(refused.exception))

    def test_a_package_named_with_no_version_range_at_all_is_carried(self) -> None:
        """A range is how a quickstart avoids pinning a team to the day it was written; absent is not a
        pin either, and is the honest thing a `save` with nothing to read writes."""
        document = {**DOCUMENT, "languages": [{"name": "toy"}]}
        self.assertEqual(quickstart.read(document).languages[0].version, "")

    def test_a_package_that_is_not_a_package_name_is_refused(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            quickstart.read({**DOCUMENT, "languages": [{"name": "Toy Language"}]})
        self.assertIn("Toy Language", str(refused.exception))


class DirectoryTest(unittest.TestCase):
    def test_one_is_found_by_name_in_the_directory_and_by_the_path_it_lives_at(self) -> None:
        """Both, because a team's own quickstart lives beside their repository rather than in a home
        directory nobody shares."""
        with tempfile.TemporaryDirectory() as area:
            path = saved(Path(area) / "quickstarts")
            with mock.patch.dict("os.environ", {quickstart.VARIABLE: str(path.parent)}):
                self.assertEqual(quickstart.find("toy-ui").name, "toy-ui")
            self.assertEqual(quickstart.find(str(path)).name, "toy-ui")

    def test_a_name_nothing_is_saved_under_is_refused_with_what_is(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            saved(Path(area))
            with mock.patch.dict("os.environ", {quickstart.VARIABLE: area}):
                with self.assertRaises(GenerationError) as refused:
                    quickstart.find("toy-io")
                self.assertIn("toy-ui", str(refused.exception))
                self.assertEqual(quickstart.saved_names(), ["toy-ui"])


class WordsTest(unittest.TestCase):
    """`quickstart show` says in plain words what it would do before it does any of it."""

    def setUp(self) -> None:
        self.said = "\n".join(quickstart.in_words(quickstart.read(DOCUMENT)))

    def test_it_says_what_it_would_install_elect_and_answer(self) -> None:
        for expected in ("toy >=1.0,<2", "codegraph", "event-modelling", "persistence", "postgres",
                         "react-vite"):
            with self.subTest(said=expected):
                self.assertIn(expected, self.said)

    def test_it_says_what_the_extension_would_be_allowed_to_refuse(self) -> None:
        """A guard refuses a tool call, and `show` is where somebody reads that before it ever fires."""
        self.assertIn("before-search", self.said)

    def test_it_ends_with_the_command_that_carries_it_out(self) -> None:
        self.assertIn("--quickstart toy-ui", self.said)


class AnswersTest(unittest.TestCase):
    def test_what_it_answers_is_named_as_the_flags_generate_already_takes(self) -> None:
        """Not a second vocabulary: every answer is a flag a person could have typed, which is what makes
        the transcript able to show them what was chosen on their behalf."""
        self.assertEqual(
            quickstart.answered(quickstart.read(DOCUMENT)),
            {"profile": "event-modelling", "target": "none", "language": "toy", "framework": "plain",
             "frontend": "react-vite", "persistence": "postgres", "http": "toy-serve"},
        )

    def test_a_flag_typed_on_the_command_line_wins_over_the_quickstart(self) -> None:
        """Every question it answers stays changeable: a quickstart is a default, never an override."""
        taken = quickstart.applied(quickstart.read(DOCUMENT), {"profile": "standard", "target": None})
        self.assertEqual(taken["profile"], "standard")
        self.assertEqual(taken["target"], "none")


class RecordTest(unittest.TestCase):
    """What a project generated from a quickstart carries, so `./init` elects without asking again."""

    def test_the_record_names_the_quickstart_its_extensions_and_the_guards_agreed(self) -> None:
        document = json.loads(quickstart.record(quickstart.read(DOCUMENT)))
        self.assertEqual(document["name"], "toy-ui")
        self.assertEqual(document["extensions"], ["codegraph"])
        self.assertEqual(document["guards"], {"codegraph": ["before-search"]})


class FromProjectTest(unittest.TestCase):
    """`quickstart save` writes what this project actually has, rather than what somebody remembers."""

    MANIFEST = {
        "name": "bookings",
        "profile": "event-modelling",
        "target": "none",
        "frontend": "react-vite",
        "generator": {"languages": {"toy": "1.2.0"}},
        "deployables": {
            "web": {"kind": "web", "path": "apps/web", "language": "react-vite"},
            "service": {"kind": "service", "path": "apps/service", "language": "toy",
                        "framework": "plain", "selection": {"persistence": "postgres"}},
        },
    }

    def test_it_reads_the_answers_off_the_project_and_the_versions_off_what_is_installed(self) -> None:
        one = cli_quickstart.from_project("toy-ui", "A sentence about the product.", self.MANIFEST,
                                      elected={"codegraph": ("before-search",)})
        self.assertEqual(one.profile, "event-modelling")
        self.assertEqual(one.language, "toy")
        self.assertEqual(one.framework, "plain")
        self.assertEqual(dict(one.axes), {"persistence": "postgres"})
        self.assertEqual(one.extensions[0].guards, ("before-search",))

    def test_a_language_is_named_by_range_rather_than_by_the_version_installed_today(self) -> None:
        """A snapshot would pin a team to the day the quickstart was written."""
        one = cli_quickstart.from_project("toy-ui", "A sentence.", self.MANIFEST, elected={})
        self.assertEqual(one.languages, (quickstart.Wanted("toy", ">=1.2,<2"),))


class VerbTest(unittest.TestCase):
    """`slipwai quickstart list|show|save`, run as a person runs it."""

    #: `cwd` moves, so the path this checkout is imported by cannot be the relative one `make` exports.
    SOURCE = str(Path(__file__).resolve().parents[1] / "src")

    def run_it(self, *arguments: str, where: Path, cwd: Path | None = None) -> subprocess.CompletedProcess:
        environment = {**os.environ, quickstart.VARIABLE: str(where), "PYTHONPATH": self.SOURCE}
        return subprocess.run(command("quickstart", *arguments), text=True, capture_output=True,
                              env=environment, cwd=cwd)

    def test_list_says_what_each_one_suits_rather_than_what_it_installs(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            saved(Path(area))
            done = self.run_it("list", where=Path(area))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("toy-ui", done.stdout)
            self.assertIn("browser app is the product", done.stdout)

    def test_show_says_what_it_would_do_and_does_none_of_it(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            saved(Path(area))
            before = sorted(Path(area).iterdir())
            done = self.run_it("show", "toy-ui", where=Path(area))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("install", done.stdout)
            self.assertEqual(sorted(Path(area).iterdir()), before)

    def test_save_writes_what_this_project_has_and_find_reads_it_back(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            project, into = Path(area) / "bookings", Path(area) / "quickstarts"
            project.mkdir()
            (project / "project.json").write_text(json.dumps(FromProjectTest.MANIFEST), encoding="utf-8")
            done = self.run_it("save", "ours", "--suits", "The way we start one here.",
                               where=into, cwd=project)
            self.assertEqual(done.returncode, 0, done.stderr)
            with mock.patch.dict("os.environ", {quickstart.VARIABLE: str(into)}):
                self.assertEqual(quickstart.find("ours").language, "toy")

    def test_saving_without_the_sentence_is_refused_by_the_flag_that_gives_it(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            project = Path(area) / "bookings"
            project.mkdir()
            (project / "project.json").write_text(json.dumps(FromProjectTest.MANIFEST), encoding="utf-8")
            done = self.run_it("save", "ours", where=Path(area) / "q", cwd=project)
            self.assertEqual(done.returncode, 2)
            self.assertIn("--suits", done.stderr)


class ElectedTest(unittest.TestCase):
    """`scripts/extensions/elected.py`, the copy a generated project reads its own record with."""

    RUNNER = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/extensions/elected.py"

    def project(self, area: str, record: dict | None) -> Path:
        root = Path(area)
        (root / "project.json").write_text("{}", encoding="utf-8")
        scripts = root / "scripts/extensions"
        scripts.mkdir(parents=True)
        (scripts / "elected.py").write_text(self.RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
        if record is not None:
            (root / ".slipwai").mkdir()
            (root / quickstart.RECORD).write_text(json.dumps(record), encoding="utf-8")
        return root

    def run_in(self, root: Path) -> str:
        done = subprocess.run([sys.executable, "scripts/extensions/elected.py"], cwd=root,
                              text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def test_the_record_s_extensions_are_what_init_elects(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            root = self.project(area, {"v": 1, "name": "toy-ui", "extensions": ["codegraph", "uipro"]})
            self.assertEqual(self.run_in(root), "codegraph uipro")

    def test_a_project_that_came_from_no_quickstart_elects_nothing_and_says_nothing(self) -> None:
        """Which is most projects: the menu then appears exactly as it always has."""
        with tempfile.TemporaryDirectory() as area:
            self.assertEqual(self.run_in(self.project(area, None)), "")

    def test_a_record_nobody_can_read_elects_nothing_rather_than_stopping_the_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            root = self.project(area, {"v": 1, "extensions": "codegraph"})
            self.assertEqual(self.run_in(root), "")


class GenerateTest(unittest.TestCase):
    """What `generate --quickstart` does with one, short of writing a project (that is the slow suite)."""

    def test_a_quickstart_naming_a_language_nobody_has_is_refused_with_the_install(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            path = saved(Path(area), {**DOCUMENT, "languages": [{"name": "absent", "version": ">=1,<2"}]})
            done = subprocess.run(
                command("generate", "bookings", "--quickstart", str(path), "--output", area),
                text=True, capture_output=True,
            )
            self.assertEqual(done.returncode, 2)
            self.assertIn("absent", done.stderr)
            self.assertIn("install absent", done.stderr)
            self.assertFalse((Path(area) / "bookings").exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
