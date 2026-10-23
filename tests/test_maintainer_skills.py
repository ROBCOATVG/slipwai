"""The five maintainer skills: that they exist, that they are about version 2, and that they repeat no verb.

A skill that describes a file this factory does not have sends a contributor to look for it. A skill that
repeats what `slipwai package new` writes is a second copy of the scaffold, and the second copy is the one
that goes stale.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT

SKILLS = ROOT / "maintainer/skills"
FIVE = ("add-module", "add-framework", "add-extension", "add-target", "add-backing-service")
#: Things version 1 had and version 2 has not. A skill naming one is a skill written for the old factory.
GONE = (
    "src/slipwai/project/languages/",   # a language is a package now
    "assets/toolkit/scripts/extensions/codegraph",  # the three left the keel in 6.1b
    "scripts/add-language.py",          # there was never such a script in version 2
    "LANGUAGES = (",                    # the built-in list
)
#: The verbs that do the work. A skill about publishing has to name the ones that publish.
VERBS = ("slipwai package new", "slipwai package check", "make register")


def body(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class PresenceTest(unittest.TestCase):
    def test_all_five_are_there(self) -> None:
        for name in FIVE:
            with self.subTest(name=name):
                self.assertTrue((SKILLS / name / "SKILL.md").is_file(), name)

    def test_each_declares_a_name_and_a_description_a_session_can_match_on(self) -> None:
        for name in FIVE:
            with self.subTest(name=name):
                head = body(name).split("---")[1]
                self.assertIn(f"name: {name}", head)
                self.assertRegex(head, r"description: \S.{40,}")

    def test_each_description_says_when_to_use_it(self) -> None:
        """Five skills whose descriptions all say "add a thing" is five skills nothing can choose between."""
        for name in FIVE:
            with self.subTest(name=name):
                self.assertIn("Use when", body(name).split("---")[1])


class ContentTest(unittest.TestCase):
    def test_none_names_a_file_version_2_does_not_have(self) -> None:
        for name in FIVE:
            for absent in GONE:
                with self.subTest(name=name, absent=absent):
                    self.assertNotIn(absent, body(name))

    def test_the_three_package_skills_name_the_verbs_that_do_the_work(self) -> None:
        for name in ("add-module", "add-framework", "add-extension"):
            with self.subTest(name=name):
                said = body(name)
                self.assertTrue(any(verb in said for verb in VERBS), name)

    def test_the_extension_skill_names_all_six_obligations(self) -> None:
        said = body("add-extension")
        from slipwai.extension_shape import obligations
        for one in obligations():
            with self.subTest(obligation=one):
                self.assertIn(one.split("-")[0].capitalize(), said)

    def test_the_backing_service_skill_names_the_axes_the_catalogue_actually_has(self) -> None:
        """A skill naming a fifth axis would send somebody to add an option to a question nobody asks."""
        from slipwai.catalog import CORE
        said = body("add-backing-service")
        for axis in CORE["axes"]:
            with self.subTest(axis=axis):
                self.assertIn(f"`{axis}`", said)

    def test_the_target_skill_names_both_shapes(self) -> None:
        said = body("add-target")
        self.assertIn("Skiff", said)
        self.assertIn("Liner", said)

    def test_each_ends_on_a_mistake_rather_than_a_summary(self) -> None:
        """A summary of what was just read is the part nobody reads; the thing people get wrong is not."""
        for name in FIVE:
            with self.subTest(name=name):
                self.assertRegex(body(name), r"mistakes? worth naming")


class CopyTest(unittest.TestCase):
    def test_make_skills_carries_them_beside_the_toolkit_s(self) -> None:
        """`.claude/skills` is generated and ignored, so the source has to be the thing that is edited."""
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("maintainer/skills", makefile)
        self.assertIn("assets/toolkit/skills", makefile)

    def test_they_are_not_in_the_toolkit_a_project_gets(self) -> None:
        """A generated project is not extending slipwai, and five skills about doing so are five wrong turns."""
        for name in FIVE:
            with self.subTest(name=name):
                self.assertFalse((ROOT / "assets/toolkit/skills" / name).exists(), name)

    def test_every_directory_under_maintainer_skills_is_one_of_the_five(self) -> None:
        found = sorted(one.name for one in SKILLS.iterdir() if one.is_dir())
        self.assertEqual(found, sorted(FIVE))


if __name__ == "__main__":
    unittest.main()
