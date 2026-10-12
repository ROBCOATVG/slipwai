"""Real adoption and refresh keep the evidenced big picture and respect catalogue ownership."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
import yaml  # type: ignore[import-untyped]

from slipwai.adopt import Answers, adopt, proposed
from slipwai.project.big_picture_page import ACTORS, BIG_PICTURE
from slipwai.resurvey import refresh
from slipwai.survey import survey

IDENTITY = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com"}
ROUTES = """app.get('/orders/:id', requireRole('clerk'), listOrders);
app.post('/refunds', requireRole('manager'), refund);
const payment = 'https://api.stripe.com/v1/charges';
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, env={**os.environ, **IDENTITY}, check=True, capture_output=True)


class AdoptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / "package.json").write_text('{"name":"shop","scripts":{"start":"node routes.js"}}')
        (self.root / "routes.js").write_text(ROUTES)
        git(self.root, "init", "-q", "-b", "main")
        self.commit()

    def commit(self) -> None:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fixture")

    def adopt(self, profile: str = "standard", candidates: bool = False) -> None:
        found = survey(self.root)
        answers = Answers("shop", profile=profile, applications=[] if candidates else proposed(found, "shop"),
                          candidates=[{"name": "shop", "path": "."}] if candidates else [])
        adopt(self.root, answers, found)

    def path(self, relative: str) -> Path:
        return self.root / "delivery" / relative

    def test_both_profiles_write_evidenced_actors_without_model_events(self) -> None:
        for profile in ("standard", "event-modelling"):
            with self.subTest(profile=profile):
                self.adopt(profile)
                page = self.path(BIG_PICTURE).read_text()
                self.assertIn("api.stripe.com", page)
                self.assertIn("routes.js:1", page)
                catalogue = yaml.safe_load(self.path(ACTORS).read_text())
                clerk = next(actor for actor in catalogue["actors"] if actor["name"] == "clerk")
                self.assertEqual(clerk["does"], ["GET /orders/:id (routes.js:1)"])
                self.assertEqual(clerk["cannot"], ["POST /refunds (routes.js:2)"])
                listing = self.path(".written").read_text()
                self.assertIn("delivery/" + BIG_PICTURE, listing)
                self.assertIn("delivery/" + ACTORS, listing)
                self.assertNotIn("`evt`", page)
                model = self.path("docs/event-model/model.yaml")
                if model.exists():
                    self.assertNotIn("observed", model.read_text())
                git(self.root, "reset", "--hard", "HEAD^")
                git(self.root, "clean", "-fd")

    def test_refresh_follows_source_and_removes_empty_catalogue(self) -> None:
        self.adopt()
        (self.root / "routes.js").write_text("app.get('/orders', requireRole('auditor'), listOrders);\n")
        self.commit()
        done = refresh(self.root)
        self.assertIn("delivery/" + ACTORS, done.rewritten)
        self.assertIn("auditor", self.path(ACTORS).read_text())
        self.commit()
        (self.root / "routes.js").write_text("app.get('/health', health);\n")
        self.commit()
        done = refresh(self.root)
        self.assertFalse(self.path(ACTORS).exists())
        self.assertTrue(any(ACTORS in removed for removed in done.removed))
        self.assertNotIn("delivery/" + ACTORS, self.path(".written").read_text())

    def test_catalogue_taken_over_by_person_survives_refresh_and_disappearing_roles(self) -> None:
        self.adopt()
        listing = self.path(".written")
        listing.write_text(listing.read_text().replace("delivery/" + ACTORS + "\n", ""))
        self.path(ACTORS).write_text("version: 1\nactors: []\n# confirmed by person\n")
        (self.root / "routes.js").write_text("app.get('/health', health);\n")
        self.commit()
        self.path(ACTORS).write_text("version: 1\nactors: []\n# confirmed by person, edited again\n")
        done = refresh(self.root)
        self.assertIn("delivery/" + ACTORS, done.owned)
        self.assertIn("confirmed by person", self.path(ACTORS).read_text())

    def test_adoption_before_candidate_confirmation_still_writes_an_honest_page(self) -> None:
        self.adopt(candidates=True)
        self.assertIn("nothing in the code names a role", self.path(BIG_PICTURE).read_text())
        self.assertFalse(self.path(ACTORS).exists())
        document = json.loads((self.root / "project.json").read_text())
        self.assertEqual(document["deployables"], {})
