"""A cloud refuses its own brand inside the names it is asked to create, and not always the same way.

Everything a target's stack creates is named after the project, so a word the cloud reserves is a project
name that cannot be applied — and the apply is where it would surface, three minutes in, with half a stack
already in somebody's account. The name is checked the moment the target is known, where it is still a
choice. What is checked here is the shape of that declaration: a target says *how* each word is refused
(`anywhere`, `word`, `prefix`) because `aws` needs one class and `azure` publishes all three, and reading
either one as the other refuses names the cloud takes or admits names it does not.
"""
from __future__ import annotations

import unittest

from test_targets import pruner_matching, with_cloud

from slipwai.catalog import validate_catalog
from slipwai.errors import GenerationError
from slipwai.targets import check_project_name, reserved_words

CLOUD = {
    "targets": {
        "cloud": {
            "label": "a stand-in",
            "managed": True,
            "reserved": {
                "anywhere": ["microsoft"],
                "word": ["access", "web.config", "app_code"],
                "prefix": ["login"],
            },
        }
    }
}


class ReservedNamesTest(unittest.TestCase):
    def test_the_catalog_refuses_a_reserved_declaration_it_cannot_honour(self) -> None:
        """A word arrives with the way it is refused, and only a target that provisions something has any."""
        for edit, message in (
            (
                lambda c: c["targets"]["cloud"].update(reserved=["cloud"]),
                "reserved words must be a mapping from how a word is refused",
            ),
            (
                lambda c: c["targets"]["cloud"].update(reserved={"inside": ["cloud"]}),
                "reserved words must be a mapping from how a word is refused",
            ),
            (
                lambda c: c["targets"]["cloud"].update(reserved={"anywhere": []}),
                "reserved anywhere words must be a non-empty list",
            ),
            (
                lambda c: c["targets"]["cloud"].update(reserved={"word": ["Cloud"]}),
                "reserved word words must be lowercase",
            ),
            (
                lambda c: c["targets"]["cloud"].update(reserved={"prefix": ["cloud-"]}),
                "reserved prefix words must be lowercase",
            ),
            (
                lambda c: c["targets"]["existing"].update(reserved={"anywhere": ["x"]}),
                "existing provisions nothing, so it",
            ),
        ):
            catalog = with_cloud()
            edit(catalog)
            with (
                self.subTest(message=message),
                pruner_matching(with_cloud()),
                self.assertRaisesRegex(ValueError, message),
            ):
                validate_catalog(catalog)

    def test_a_cloud_refuses_a_reserved_word_three_different_ways(self) -> None:
        """Azure publishes three classes at once and a flat list of substrings expresses only one of them.

        `microsoft` and `windows` are refused anywhere inside a name; about forty more only as whole words,
        which is why `access-log` is refused and `preaccess` is not; and `login` only at the start. The
        separators a word stands between are the ones a project name may carry — `.`, `_` and `-` — so a
        reserved word may hold one itself, as `web.config` and `app_code` do.
        """
        self.assertEqual(
            reserved_words(CLOUD, "cloud"), ["microsoft", "access", "web.config", "app_code", "login"]
        )
        for name, expected in (
            ("themicrosoftshop", "contains 'microsoft', which the cloud target reserves anywhere in a name"),
            ("access-log", "uses 'access' as a word, which the cloud target reserves"),
            ("log.access", "uses 'access' as a word, which the cloud target reserves"),
            ("api_web.config_store", "uses 'web.config' as a word, which the cloud target reserves"),
            ("app_code", "uses 'app_code' as a word, which the cloud target reserves"),
            ("login-service", "starts with 'login', which the cloud target reserves at the start of a name"),
        ):
            with self.subTest(name=name), self.assertRaises(GenerationError) as refused:
                check_project_name(CLOUD, "cloud", name)
            message = str(refused.exception)
            self.assertIn(expected, message)
            self.assertIn("--target none", message)
            self.assertIn("reserves 5 words in all, listed in docs/cloud-target.md", message)

    def test_a_class_admits_the_names_the_other_two_would_refuse(self) -> None:
        """The whole-word words pass inside a longer word and the prefix word passes anywhere but the front.

        This is the half a flat substring list got wrong: Azure takes `preaccess` and `relogin`, and would
        have been told it does not."""
        for name in ("preaccess", "accessible", "webconfig", "appcode", "api-login", "relogin"):
            with self.subTest(name=name):
                check_project_name(CLOUD, "cloud", name)
