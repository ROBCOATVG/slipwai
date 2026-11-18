"""A capability's film: one recording of the whole walk, its marks, and the card that plays it."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import TOOLKIT_ROOT
from slipwai.film import films_card, films_of, ranged
from slipwai.logs import run_dir
from slipwai.try_card import walk_file, walks_of


class FilmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = run_dir(self.root) / "walks/001-demo/bring-it"
        self.home.mkdir(parents=True)
        (self.home / "film.webm").write_bytes(b"0123456789")
        (self.home / "film.json").write_text(json.dumps({"length": 125, "chapters": [
            {"at": 48.0, "slice": "GN3", "example": "1", "says": "Amara says she will bring Catan."},
            {"at": 0.0, "slice": "GN1", "example": "1", "says": "Dev puts Friday on the calendar."},
            {"at": 20.0, "slice": "GN1", "example": "2", "says": "Dev changes the time."}]}), encoding="utf-8")

    def test_a_film_is_read_with_its_marks_in_order_and_is_not_a_clip(self) -> None:
        found = films_of(self.root, "seat1")
        self.assertEqual([(one["capability"], one["id"]) for one in found], [("bring-it", "film-bring-it")])
        self.assertEqual([one["at"] for one in found[0]["chapters"]], [0.0, 20.0, 48.0])
        self.assertIn("/walks/001-demo/bring-it/film.webm?seat=seat1&v=", found[0]["href"])
        self.assertEqual(walks_of(self.root), [], "the old list of clips does not show the film as one")
        self.assertIsNotNone(walk_file(self.root, "001-demo/bring-it/film.webm"))

    def test_the_card_is_a_chapter_a_slice_and_says_what_is_on_screen(self) -> None:
        card = films_card(films_of(self.root), [{"slice": "GN1", "title": "Put a night on the calendar"}],
                          {"bring-it": "nights"})
        self.assertIn("On film · 1 capability filmed", card)
        self.assertIn("Ready for you", card)
        self.assertEqual(card.count("<li><button"), 2, "three marks, two slices")
        self.assertIn("<span>1 · GN1 · Put a night on the calendar</span><span class=\"at\">0:00</span>", card)
        self.assertIn('data-film-at="48.0" data-slice="GN3"', card)
        self.assertIn('<p class="says">Dev puts Friday on the calendar.</p>', card)
        self.assertEqual(films_card([], []), "")

    def test_a_film_with_no_marks_is_still_a_film(self) -> None:
        (self.home / "film.json").unlink()
        self.assertIn("Filmed without chapter marks.", films_card(films_of(self.root), []))

    def test_a_player_is_given_the_range_it_asked_for(self) -> None:
        data = b"0123456789"
        self.assertEqual(ranged(data, "")[:2], (200, data))
        code, part, more = ranged(data, "bytes=2-5")
        self.assertEqual((code, part, dict(more)["Content-Range"]), (206, b"2345", "bytes 2-5/10"))
        self.assertEqual(ranged(data, "bytes=7-")[1], b"789")
        self.assertEqual(ranged(data, "bytes=-3")[1], b"789")
        self.assertEqual(ranged(data, "bytes=20-")[0], 416)


class FilmVerbTest(unittest.TestCase):
    """`try_it.py film`, run as the hand runs it, in a repository of its own."""

    def test_start_says_where_to_record_and_each_chapter_is_marked_from_then(self) -> None:
        root = Path(tempfile.mkdtemp())
        agents = root / "scripts/agents"
        agents.mkdir(parents=True)
        source = TOOLKIT_ROOT / "scripts/agents"
        for name in ("try_it.py", "logs.py"):
            (agents / name).write_bytes((source / name).read_bytes())
        (root / "project.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True)

        def film(*argv: str) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, str(agents / "try_it.py"), "film", *argv], cwd=root,
                                  capture_output=True, text=True, check=False)

        started = film("start", "001-demo", "bring-it")
        self.assertEqual(started.returncode, 0, started.stderr)
        # A real path the recorder writes to: the platform's own, so compared as a path.
        self.assertTrue(Path(started.stdout.strip()).as_posix().endswith("walks/001-demo/bring-it/film.webm"))
        self.assertNotEqual(film("chapter", "001-demo", "bring-it", "--slice", "GN1").returncode, 0,
                            "a chapter with nothing to say is refused")
        said = film("chapter", "001-demo", "bring-it", "--slice", "GN1", "--example", "2", "--says", "Dev signs in.")
        self.assertEqual(said.returncode, 0, said.stderr)
        self.assertEqual(film("stop", "001-demo", "bring-it").returncode, 0)
        held = json.loads((Path(started.stdout.strip()).parent / "film.json").read_text(encoding="utf-8"))
        self.assertEqual([(one["slice"], one["example"], one["says"]) for one in held["chapters"]],
                         [("GN1", "2", "Dev signs in.")])
        self.assertIn("length", held)
        self.assertNotEqual(film("chapter", "001-demo", "never-started", "--slice", "GN1", "--says", "x").returncode, 0)


if __name__ == "__main__":
    unittest.main()
