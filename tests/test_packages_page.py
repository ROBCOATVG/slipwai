"""The chandlery as a tab of the board: what is here, what is offered, and one press to have one.

The page is `slipwai search` and the install verbs with a document around them, so what is worth proving is
that it stays that — the rows are the index's, the installed half is the package directory's, and the button
reaches the same function the verb calls rather than a second path that stages a package its own way.

Every test here runs against an index written in this file and a package directory, a quickstart directory
and a trust store in a temporary `SLIPWAI_HOME`: a suite that asked the network would go red for somebody
else's reasons, and one that read the developer's own trust store would pass or fail by what they had
happened to accept.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import chandlery_page
from slipwai.bridge import serve
from slipwai.chandlery_page import page, put, sections
from slipwai.errors import GenerationError
from slipwai.index_schema import EXTENSION, LANGUAGE, QUICKSTART, TARGET
from slipwai.language_index import Release
from slipwai.page_shell import TABS


def release(name: str, version: str = "1.0.0", kind: str = LANGUAGE, publisher: str = "ROBCOATVG",
            **fragment: object) -> Release:
    """One release as a channel lists it, carrying the whole manifest the way a published entry does."""
    whole: dict[str, object] = {"name": name, "core": ">=9.0,<10", "family": name, **fragment}
    if kind == EXTENSION:
        whole = {"key": name, "name": name.title(), "core": ">=9.0,<10", **fragment}
    return Release(name, version, f"https://example.invalid/{name}-{version}.tar.gz", "0" * 64, whole,
                   kind=kind, publisher=publisher, description=str(fragment.get("description", "")))


OFFERED = {
    "python": release("python", "1.2.0", description="Python, with FastAPI or nothing"),
    "go": release("go", "2.0.0", description="Go — modules, gofmt"),
    "codegraph": release("codegraph", kind=EXTENSION, description="A local code index"),
    "stranger": release("stranger", kind=EXTENSION, publisher="somebody-else", description="Unaccepted"),
    "aws": release("aws", kind=TARGET, description="AWS, with CDK"),
}


class Fixture(unittest.TestCase):
    """A machine of our own: a package directory, a quickstart directory and a trust store, all temporary."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.packages = self.home / "packages"
        self.packages.mkdir()
        self.quickstarts = self.home / "quickstarts"
        self.quickstarts.mkdir()
        self.patch = mock.patch.dict(os.environ, {
            "SLIPWAI_HOME": str(self.home), "SLIPWAI_LANGUAGES": str(self.packages),
            "SLIPWAI_QUICKSTARTS": str(self.quickstarts)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def install(self, name: str, manifest: str = "language.json", version: str = "1.0.0",
                **held: object) -> Path:
        place = self.packages / name
        place.mkdir()
        (place / "VERSION").write_text(version + "\n", encoding="utf-8")
        (place / manifest).write_text(json.dumps({"name": name, "key": name, "core": ">=9.0,<10",
                                                  "family": name, "order": 10, **held}), encoding="utf-8")
        return place

    def rows(self, kind: str) -> list:
        return sections(OFFERED)[kind]

    def named(self, kind: str) -> list[str]:
        return [row.name for row in self.rows(kind)]


class SectionsTest(Fixture):
    def test_what_is_here_comes_before_what_is_offered(self) -> None:
        """A reader's first question about a search result is whether they already have it, so the page
        answers it by where the row is before they have read a word of it."""
        self.install("python")
        self.assertEqual(self.named(LANGUAGE), ["python", "go"])
        self.assertTrue(self.rows(LANGUAGE)[0].here)
        self.assertFalse(self.rows(LANGUAGE)[1].here)

    def test_a_package_no_channel_lists_is_shown_all_the_same(self) -> None:
        """A local install is an install. A listing that dropped it would be a page disagreeing with the
        directory it is about."""
        self.install("ours", description="installed from a path")
        self.assertIn("ours", self.named(LANGUAGE))
        self.assertEqual(self.rows(LANGUAGE)[0].what, "installed from a path")

    def test_a_newer_release_is_said_on_the_installed_row(self) -> None:
        self.install("python", version="1.0.0")
        self.assertEqual(self.rows(LANGUAGE)[0].newer, "1.2.0")

    def test_an_installed_package_at_the_newest_release_says_nothing_about_versions(self) -> None:
        self.install("python", version="1.2.0")
        self.assertEqual(self.rows(LANGUAGE)[0].newer, "")

    def test_each_kind_is_read_by_the_manifest_its_own_walk_reads(self) -> None:
        """Three kinds share the package directory and are told apart by the file each carries, which is
        how the loader tells them apart too."""
        self.install("python")
        self.install("codegraph", manifest="extension.json")
        self.install("aws", manifest="target.json")
        (self.quickstarts / "browser-app.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.named(LANGUAGE)[0], "python")
        self.assertEqual(self.named(EXTENSION)[0], "codegraph")
        self.assertEqual(self.named(TARGET)[0], "aws")
        self.assertEqual(self.named(QUICKSTART), ["browser-app"])

    def test_an_extension_is_not_listed_as_a_language_it_happens_to_sit_beside(self) -> None:
        self.install("codegraph", manifest="extension.json")
        self.assertNotIn("codegraph", self.named(LANGUAGE))


class PublisherTest(Fixture):
    """The one question the terminal makes a person say out loud, asked where the person is."""

    def test_an_unaccepted_publisher_is_asked_about_on_the_row(self) -> None:
        row = next(row for row in self.rows(EXTENSION) if row.name == "stranger")
        self.assertTrue(row.asked)
        self.assertIn("accept somebody-else", page(OFFERED))

    def test_an_accepted_publisher_is_not_asked_about_again(self) -> None:
        row = next(row for row in self.rows(EXTENSION) if row.name == "codegraph")
        self.assertFalse(row.asked)

    def test_a_language_is_never_asked_about_because_its_install_does_not_ask(self) -> None:
        """Nothing on the language path calls `trust.admitted`. A box that did nothing would be the page
        claiming to have put a question it never put."""
        stranger = release("stranger-lang", publisher="somebody-else")
        row = next(row for row in sections({"stranger-lang": stranger})[LANGUAGE] if not row.here)
        self.assertEqual(row.publisher, "somebody-else")
        self.assertFalse(row.asked)


class PageTest(Fixture):
    def test_it_is_a_tab_of_the_board_and_the_bar_says_which(self) -> None:
        self.assertIn(("/packages", "Packages"), TABS)
        self.assertIn('<a href="/packages" aria-current="page">', page(OFFERED))

    def test_every_offered_package_has_a_button_naming_its_kind(self) -> None:
        said = page(OFFERED)
        self.assertIn('data-install="go" data-kind="language"', said)
        self.assertIn('data-install="codegraph" data-kind="extension"', said)
        self.assertIn('data-install="aws" data-kind="target"', said)

    def test_an_installed_package_has_nothing_to_press(self) -> None:
        self.install("go", version="2.0.0")
        self.assertNotIn('data-install="go"', page(OFFERED))

    def test_a_channel_that_could_not_be_read_is_said_above_what_is_here(self) -> None:
        """A short listing that does not say it is short is how a person concludes a package does not
        exist when a channel was down."""
        said = page({}, "", ["the index at https://example.invalid could not be read"])
        self.assertIn("could not be read", said)
        self.assertIn("A channel could not be read", said)

    def test_a_publisher_s_own_words_are_escaped(self) -> None:
        held = {"x": release("x", kind=EXTENSION, description="<script>alert(1)</script>")}
        self.assertNotIn("<script>alert(1)</script>", page(held))


class PutTest(Fixture):
    def test_a_kind_this_board_does_not_install_is_a_refusal_and_not_a_traceback(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            put("spaceship", "go", False)
        self.assertIn("not a kind of package", str(refused.exception))

    def test_an_install_with_no_package_says_so(self) -> None:
        with self.assertRaises(GenerationError):
            put(LANGUAGE, "", False)


class ServerTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        self.server = serve(self.root, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, path: str, body: dict) -> tuple[int, str]:
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                return answer.status, answer.read().decode("utf-8")
        except urllib.error.HTTPError as answer:
            with answer:
                return answer.code, answer.read().decode("utf-8")

    def test_the_tab_is_served(self) -> None:
        with mock.patch.object(chandlery_page, "chandlery", return_value=(OFFERED, "a channel", [])), \
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/packages", timeout=5) as answer:
            said = answer.read().decode("utf-8")
        self.assertIn("Languages", said)
        self.assertIn('data-install="go"', said)

    def test_the_button_reaches_the_function_the_verb_calls(self) -> None:
        with mock.patch.object(chandlery_page, "put_language", return_value=["go installed"]) as called:
            code, said = self.post("/packages/install", {"kind": LANGUAGE, "name": "go"})
        self.assertEqual((code, said), (200, "go installed"))
        self.assertEqual(called.call_args.args[0], ["go"])

    def test_the_tick_box_is_what_accepts_the_publisher(self) -> None:
        with mock.patch.object(chandlery_page, "put_extension", return_value=["in"]) as called:
            self.post("/packages/install", {"kind": EXTENSION, "name": "stranger", "accept": True})
        self.assertIs(called.call_args.args[2], True)

    def test_a_refusal_is_the_line_it_is_and_not_a_traceback(self) -> None:
        code, said = self.post("/packages/install", {"kind": "spaceship", "name": "go"})
        self.assertEqual(code, 400)
        self.assertIn("not a kind of package", said)
        self.assertNotIn("Traceback", said)

    def test_the_read_only_copy_has_no_such_tab_and_no_such_control(self) -> None:
        """The published copy is one file on somebody's Pages site. A page that offered to install
        something onto the machine serving it would be the two copies disagreeing about what they are."""
        server = serve(self.root, "127.0.0.1", 0, controls=False)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/packages", timeout=5).close()
            self.fail("a read-only copy served the packages tab")
        except urllib.error.HTTPError as answer:
            with answer:
                self.assertEqual(answer.code, 404)


if __name__ == "__main__":
    unittest.main()
