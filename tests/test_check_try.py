"""`scripts/check-try.py`: a slice's story held to what it would need to seed, with no app running.

Run against `tests/fixtures/recap-try/`, which is recap's second day as the files stood when 22 of 22
stories failed: sixteen stories, two people nobody declared, a realm with one user, and a browser app whose
route table two unbuilt hubs were missing from. The gate is run the way a project runs it — a subprocess,
from a tree laid out like a project — because that is what `make verify` calls.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

FIXTURE = Path(__file__).resolve().parent / "fixtures/recap-try"
FEATURE = "specs/001-audiobook-recap"


class CheckTryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "recap"
        shutil.copytree(FIXTURE, self.root)
        (self.root / "scripts/agents").mkdir(parents=True)
        for name in ("check-try.py",):
            shutil.copy(TOOLKIT_ROOT / "scripts" / name, self.root / "scripts" / name)
        shutil.copy(TOOLKIT_ROOT / "scripts/agents/try_it.py", self.root / "scripts/agents/try_it.py")

    def run_gate(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", "scripts/check-try.py"], cwd=self.root, capture_output=True,
                              text=True, check=False)

    def person(self, username: str, name: str = "Someone", realm: str = "customers", **extra: object) -> None:
        place = self.root / FEATURE / "people"
        place.mkdir(exist_ok=True)
        (place / f"{username}.json").write_text(json.dumps(
            {"username": username, "name": name, "password": username, "realm": realm, **extra}), encoding="utf-8")

    def story(self, slice_id: str, body: dict) -> None:
        place = self.root / FEATURE / "slices" / slice_id
        place.mkdir(parents=True, exist_ok=True)
        (place / "try-it.json").write_text(json.dumps(body), encoding="utf-8")

    def test_recap_s_day_is_refused_naming_the_two_people_nobody_declared(self) -> None:
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("LB1: `as` names ines, whom no realm or people file declares", done.stderr)
        self.assertIn("LB6: `as` names ada, whom no realm or people file declares", done.stderr)
        named = {line.split("`as` names ")[1].split(",")[0] for line in done.stderr.splitlines()
                 if "`as` names" in line}
        self.assertEqual(named, {"ada", "ines"})
        self.assertIn("declare the person under specs/<feature>/people/", done.stderr)

    def test_declaring_the_two_people_passes_every_story_and_counts_them(self) -> None:
        self.person("ada", "Ada Okoye")
        self.person("ines", "Ines Ferreira")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("16 stories seedable on paper", done.stdout)
        self.assertIn("3 people to sign in as", done.stdout)

    def test_an_open_under_a_parameterised_route_passes_and_one_nothing_mounts_is_refused(self) -> None:
        self.person("ada")
        self.person("ines")
        self.story("LB13", {"as": "ada", "open": [{"label": "Now playing", "path": "/books/nw-1/player?at=3"},
                                                   {"label": "The library", "path": "/library"}],
                            "steps": [{"method": "GET", "path": "/api/books"}]})
        done = self.run_gate()
        self.assertEqual(done.returncode, 1)
        self.assertIn("LB13: open 2 is at /library, which no browser route mounts", done.stderr)
        self.assertNotIn("open 1", done.stderr)

    def test_a_person_file_missing_a_field_or_doubling_a_realm_user_is_refused_by_file(self) -> None:
        self.person("ada")
        self.person("ines")
        self.person("customer@example.invalid", "Casey Twice")
        place = self.root / FEATURE / "people"
        (place / "half.json").write_text(json.dumps({"username": "half", "name": "Half"}), encoding="utf-8")
        done = self.run_gate()
        self.assertIn(f"{FEATURE}/people/customer@example.invalid.json: customer@example.invalid is already a user "
                      "of the realm", done.stderr)
        self.assertIn(f"{FEATURE}/people/half.json: says no password, realm", done.stderr)

    def test_a_malformed_story_and_a_stray_key_are_named(self) -> None:
        self.person("ada")
        self.person("ines")
        (self.root / FEATURE / "slices/CU1/try-it.json").write_text("{not json", encoding="utf-8")
        self.story("CU3", {"as": "ada", "steps": [{"method": "FETCH", "path": "api/x"}], "opens": []})
        done = self.run_gate()
        self.assertIn("001-audiobook-recap/CU1: try-it.json is not JSON", done.stderr)
        self.assertIn("CU3: says `opens`, which a story has no use for", done.stderr)
        self.assertIn("CU3: step 1 names no `path` starting with /", done.stderr)

    def test_a_given_is_held_to_the_model_s_event_and_its_attributes(self) -> None:
        self.person("ada")
        self.person("ines")
        self.story("CU5", {"as": "ada", "steps": [{"method": "GET", "path": "/api/books/cs-1/recap"}],
                           "given": [{"stream": "book-cs-1", "event": "BookImported", "data": {"bookId": "cs-1"}},
                                     {"stream": "listening-cs-1", "event": "ListeningResumed",
                                      "data": {"bookId": "cs-1", "position": 10, "resumedAtt": "x"}},
                                     {"stream": "x", "event": "RecapGenerated", "data": {}},
                                     {"stream": "x", "event": "Nothing", "data": {}}]})
        done = self.run_gate()
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("given 1", done.stderr, "a frame with prose data alone types nothing to refuse")
        self.assertIn("given 2: ListeningResumed has no attribute `resumedAtt` "
                      "(docs/event-model/model.yaml#ListeningResumed)", done.stderr)
        self.assertIn("given 2: ListeningResumed identifies a resumption by `resumptionId`, which the data leaves "
                      "out", done.stderr)
        self.assertIn("given 3 is a RecapGenerated, which this slice itself sets", done.stderr)
        self.assertIn("given 4 is a Nothing, which the model has no event of", done.stderr)

    def test_the_standard_profile_has_no_given(self) -> None:
        self.person("ada")
        self.person("ines")
        (self.root / "docs/event-model/model.yaml").unlink()
        self.story("CU5", {"as": "ada", "steps": [{"method": "GET", "path": "/api/x"}],
                           "given": [{"stream": "s", "event": "BookImported", "data": {}}]})
        done = self.run_gate()
        self.assertIn("CU5: given 1: the standard profile has no `given`", done.stderr)

    def test_a_project_with_no_browser_app_skips_the_screen_check(self) -> None:
        self.person("ada")
        self.person("ines")
        manifest = json.loads((self.root / "project.json").read_text(encoding="utf-8"))
        del manifest["deployables"]["recap-web"]
        (self.root / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.story("LB13", {"as": "ada", "open": [{"label": "x", "path": "/library"}], "steps": []})
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no browser app, so no screen check", done.stdout)


if __name__ == "__main__":
    unittest.main()
