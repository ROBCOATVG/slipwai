"""`LICENSE`, `SECURITY.md` and the pull-request template.

Each of them states something a scaffolder only half knows, so what is asserted here is that the half it
does know is right — this project's name, this project's gates, this project's paths — and that the half it
does not is left as the owner's rather than guessed. The licence assertions are the ones that matter most: a
generator that wrote a permissive licence into somebody's repository would have made a grant nobody made.
"""
from __future__ import annotations

import datetime
import re
import tempfile

from support import FactoryTestCase

from slipwai.catalog import axis_default
from slipwai.project.adopted import OWN
from slipwai.project.repository import repository_files
from slipwai.services import default_apps

# Words that would mean this file had granted something. None of them belongs in a default nobody chose.
GRANTS = (
    "Permission is hereby granted", "MIT License", "Apache License", "GNU GENERAL PUBLIC",
    "redistribute", "free of charge",
)
# What a checklist line points at: a Make target, or a path in the repository.
TARGETS = re.compile(r"`make ([a-z][a-z0-9-]*)`")
PATHS = re.compile(r"`([a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]*)`")


class RepositoryFilesTest(FactoryTestCase):
    def test_the_licence_is_the_default_nobody_chose_and_grants_nothing(self) -> None:
        """There is no licence axis and this does not invent one. `All rights reserved` is where a
        repository with no licence file already stands, said clearly — and it is the one default that
        cannot be wrong in the direction that matters, because it gives nothing away."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "owned", "standard", "typescript", "none")
            text = (repo / "LICENSE").read_text()
            self.assertIn("All rights reserved", text)
            self.assertIn("owned", text)
            self.assertIn(str(datetime.date.today().year), text)
            for grant in GRANTS:
                self.assertNotIn(grant, text, f"the default licence grants something: {grant}")
            # And it says what to do instead, so the default is a step rather than a dead end.
            self.assertIn("spdx.org/licenses/", text)
            self.assertIn("docs/adr/", text)

    def test_the_security_policy_is_this_project_s_and_asks_for_the_one_thing_only_it_knows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "guarded", "standard", "python", "none")
            text = (repo / "SECURITY.md").read_text()
            self.assertIn("guarded", text)
            self.assertIn("Do not open an issue", text)
            # The contact is the one thing the factory cannot know, and a placeholder that does not
            # announce itself is worse than none: somebody will file the issue instead.
            self.assertIn("replace this line", text)

    def test_every_gate_and_path_the_template_names_is_one_this_project_has(self) -> None:
        """A checklist item pointing at a target this project does not run, or a directory it does not
        have, is how a template becomes something people tick without reading."""
        with tempfile.TemporaryDirectory() as directory:
            # The store is the event profile's, so the standard row answers nothing but its transport.
            for name, profile, backend, target, store in (
                ("templated", "event-modelling", "typescript", "none", "postgres"),
                ("deployed", "event-modelling", "go", "aws", "postgres"),
                ("plain", "standard", "python", "none", None),
            ):
                with self.subTest(profile=profile, backend=backend, target=target):
                    axes = {"http": axis_default("http", backend, target)}
                    if store:
                        axes["event_store"] = store
                    repo = self.generate(directory, name, profile, backend, "none", target=target, **axes)
                    template = (repo / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
                    self.assertIn("`make verify`", template)
                    makefile = (repo / "Makefile").read_text()
                    for gate in TARGETS.findall(template):
                        self.assertRegex(makefile, rf"(?m)^{gate}:", f"the template names `make {gate}`")
                    for path in set(PATHS.findall(template)) - {"specs/"}:
                        self.assertTrue((repo / path).exists(), f"the template names {path}, which is absent")

    def test_the_checklist_is_this_project_s_answers_and_not_a_fixed_list(self) -> None:
        """The event model, the expand/contract rule and the flag gate are asked for where the project has
        them and nowhere else."""
        with tempfile.TemporaryDirectory() as directory:
            event = self.generate(
                directory, "asked", "event-modelling", "typescript", "none", event_store="postgres",
                http=axis_default("http", "typescript", "none"),
            )
            plain = self.generate(directory, "unasked", "standard", "go", "none")
            self.assertIn("check-model", (event / ".github/PULL_REQUEST_TEMPLATE.md").read_text())
            self.assertIn("check-migrations", (event / ".github/PULL_REQUEST_TEMPLATE.md").read_text())
            self.assertNotIn("check-model", (plain / ".github/PULL_REQUEST_TEMPLATE.md").read_text())
            self.assertNotIn("check-migrations", (plain / ".github/PULL_REQUEST_TEMPLATE.md").read_text())

    def test_the_template_says_there_is_no_changelog_rather_than_pointing_at_one(self) -> None:
        """The project has none, and the honest line is the one that says so and says where the record of a
        change actually is — an unfollowable checklist item is worse than a missing one."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "recorded", "standard", "typescript", "none")
            template = (repo / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
            self.assertIn("keeps no CHANGELOG.md of its own", template)
            self.assertFalse((repo / "CHANGELOG.md").exists())

    def test_an_adopted_repository_keeps_its_own(self) -> None:
        """Its licence is real, its security policy is somebody's commitment, and its template is its
        team's. A placeholder written over any of the three would be worse than nothing."""
        for path in repository_files("adopted", "standard", default_apps("python", "none"), "none"):
            self.assertIn(path, OWN, f"an adoption would write {path} over the repository's own")

    def test_the_licence_year_is_the_year_it_was_generated(self) -> None:
        """Read through the one seam rather than by waiting for January."""
        from slipwai.project.repository import licence

        self.assertIn("Copyright (c) 1999", licence("old", datetime.date(1999, 6, 1)))
