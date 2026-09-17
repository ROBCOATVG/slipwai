"""What a backend may be called, and how a language plus a framework resolves to one.

Split from `test_catalog.py` for the reason the structure gate applies to source: two concerns in one
module, and the naming rules are self-contained. They are about `validate_backends` and `resolve_backend`
— the flattening of "which language" and "which framework" into the single key every per-backend table is
keyed by, and the directory-name rule that falls out of it.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from support import FactoryTestCase

from slipwai import catalog as catalog_module
from slipwai.catalog import (
    CATALOG,
    families,
    family_of,
    framework_of,
    resolve_backend,
    validate_backends,
)
from slipwai.errors import GenerationError


def without_java() -> dict:
    """The catalog with its Java family removed, so the naming rules can be tested against arrangements
    the validator *refuses* — the real Java family is already a valid one.

    The family's `default.framework` entry goes with it. That entry only exists because the family has
    two members, so leaving it behind would make every arrangement built on top of this one fail as
    "one backend, so it has no framework to default to" instead of on the rule under test."""
    catalog = json.loads(json.dumps(CATALOG))
    for name in [n for n, backend in catalog["backends"].items() if backend["family"] == "java"]:
        del catalog["backends"][name]
        catalog["default"]["http"].pop(name, None)
    catalog["default"]["framework"].pop("java", None)
    return catalog


class BackendNamingTest(FactoryTestCase):
    def test_a_language_with_two_frameworks_becomes_two_backends(self) -> None:
        """A framework that owns startup multiplies with its language rather than crossing it.

        So it is flattened into the backend key, and the *prompt* is what splits it back into two
        questions.

        The real catalog's Java family is now exactly this shape, so it is checked first and directly —
        this used to be synthetic-only, on the grounds that the mechanism had to be right before a
        backend depended on it. A synthetic catalog is still used afterwards for the arrangements the real
        one does not have: a member whose framework is `none`, and a family whose default names the
        other member.
        """
        # The real thing first. `families()` groups by family, so a two-member family appears as one key
        # with both backends under it, and each is reachable by naming its framework.
        self.assertEqual(families()["java"], ["java-quarkus", "java-spring"])
        self.assertEqual(resolve_backend("java", "quarkus"), "java-quarkus")
        self.assertEqual(resolve_backend("java", "spring-boot"), "java-spring")
        # Unanswered, the catalog's recommendation applies rather than the first member in file order.
        self.assertEqual(resolve_backend("java", None), "java-quarkus")
        self.assertEqual(framework_of("java-quarkus"), "quarkus")
        self.assertEqual(framework_of("java-spring"), "spring-boot")
        self.assertEqual(family_of("java-quarkus"), family_of("java-spring"))
        # A framework no member has is refused by name rather than silently defaulted.
        with self.assertRaisesRegex(GenerationError, "not implemented for java"):
            resolve_backend("java", "micronaut")
        # And the family name is not itself a backend, which is what keeps
        # `assets/languages/java/` free to mean "what the two share".
        self.assertNotIn("java", CATALOG["backends"])

        backends = {
            "go": {"family": "go", "label": "Go"},
            "java-plain": {"family": "java", "framework": "none", "label": "Framework-free"},
            "java-spring": {"family": "java", "framework": "spring-boot", "label": "Spring Boot"},
        }
        default = dict(CATALOG["default"], backend="go", framework={"java": "spring-boot"})

        with patch.dict(catalog_module.CATALOG, {"backends": backends, "default": default}):
            self.assertEqual(
                families(), {"go": ["go"], "java": ["java-plain", "java-spring"]}
            )
            # Two questions, resolving to one key.
            self.assertEqual(resolve_backend("java", "spring-boot"), "java-spring")
            self.assertEqual(resolve_backend("java", "none"), "java-plain")
            # Unanswered, the family's default framework applies.
            self.assertEqual(resolve_backend("java", None), "java-spring")
            # A single-member family is never asked, and refuses to be answered.
            self.assertEqual(resolve_backend("go", None), "go")
            with self.assertRaisesRegex(GenerationError, "nothing owns startup there"):
                resolve_backend("go", "spring-boot")
            with self.assertRaisesRegex(GenerationError, "not implemented for java"):
                resolve_backend("java", "quarkus")
            self.assertEqual(family_of("java-spring"), "java")
            self.assertEqual(framework_of("java-spring"), "spring-boot")
            self.assertIsNone(framework_of("go"))

    def test_a_backend_is_named_for_its_language_only_when_nothing_owns_its_startup(self) -> None:
        """`assets/languages/<family>/` holds what a family's backends share, so it cannot also be one.

        The rule is about the framework, not the member count: a backend that has one is suffixed with it
        whether or not it has a sibling. Enforced in both directions, because either mistake produces a
        directory name that means two things.
        """
        catalog = without_java()
        catalog["backends"]["java"] = {"family": "java", "label": "Java"}
        catalog["backends"]["java-spring"] = {
            "family": "java", "framework": "spring-boot", "label": "Spring Boot",
        }
        catalog["default"]["framework"]["java"] = "spring-boot"
        with self.assertRaisesRegex(ValueError, "none of them may be named java"):
            validate_backends(catalog)

        # Renaming the bare one fixes it, but only if every member then declares its own framework.
        catalog["backends"]["java-plain"] = catalog["backends"].pop("java")
        with self.assertRaisesRegex(ValueError, "must name its own distinct framework"):
            validate_backends(catalog)
        catalog["backends"]["java-plain"]["framework"] = "none"
        validate_backends(catalog)

        # A lone backend with nothing owning its startup must be named for the language itself.
        lone = json.loads(json.dumps(CATALOG))
        lone["backends"]["go-plain"] = lone["backends"].pop("go")
        with self.assertRaisesRegex(ValueError, "must be named for the language itself"):
            validate_backends(lone)

        # But a lone backend that *does* have a framework is suffixed from the start: that is what a new
        # Java or C# backend looks like on the day it arrives, before any sibling exists. The catalog no
        # longer has one of those — Java has two members now — so this is the only place the shape is
        # covered, which is why it asserts rather than relying on the real catalog to be it.
        first = without_java()
        first["backends"]["java-spring"] = {
            "family": "java", "framework": "spring-boot", "label": "Spring Boot owns startup",
        }
        validate_backends(first)

        # One member is still one answer, so there is nothing to recommend between.
        first["default"]["framework"]["java"] = "spring-boot"
        with self.assertRaisesRegex(ValueError, "no framework to default to"):
            validate_backends(first)

        # And the other direction of the rule: it may not fall back to the bare language name.
        del first["default"]["framework"]["java"]
        first["backends"]["java"] = first["backends"].pop("java-spring")
        with self.assertRaisesRegex(ValueError, "must be named for that too"):
            validate_backends(first)

    def test_a_lone_framework_backend_is_reachable_and_refuses_the_others_honestly(self) -> None:
        """A single-member family is now two situations, and the refusal has to tell them apart.

        `--framework quarkus` against a Java family that only has Spring Boot is "not implemented yet";
        the same flag against Go is "nothing owns startup there". Reporting the second for the first
        would tell the caller their language has no frameworks, which is the opposite of true.
        """
        backends = {
            "go": {"family": "go", "label": "Go"},
            "java-spring": {"family": "java", "framework": "spring-boot", "label": "Spring Boot"},
        }
        default = dict(CATALOG["default"], backend="go", framework={})

        with patch.dict(catalog_module.CATALOG, {"backends": backends, "default": default}):
            self.assertEqual(families(), {"go": ["go"], "java": ["java-spring"]})
            # Reachable both ways round, and the framework question is never asked: one answer.
            self.assertEqual(resolve_backend("java", None), "java-spring")
            self.assertEqual(resolve_backend("java", "spring-boot"), "java-spring")
            self.assertEqual(family_of("java-spring"), "java")

            with self.assertRaisesRegex(GenerationError, "offers with spring-boot only"):
                resolve_backend("java", "quarkus")
            with self.assertRaisesRegex(GenerationError, "nothing owns startup there"):
                resolve_backend("go", "spring-boot")

    def test_a_multi_framework_family_must_recommend_one(self) -> None:
        """Two frameworks and no default is a question with no recommended answer behind it."""
        catalog = without_java()
        catalog["backends"]["java-plain"] = {"family": "java", "framework": "none", "label": "Plain"}
        catalog["backends"]["java-spring"] = {
            "family": "java", "framework": "spring-boot", "label": "Spring",
        }
        with self.assertRaisesRegex(ValueError, "default framework for java"):
            validate_backends(catalog)
        catalog["default"]["framework"]["java"] = "micronaut"   # a framework no member declares
        with self.assertRaisesRegex(ValueError, "default framework for java"):
            validate_backends(catalog)
        catalog["default"]["framework"]["java"] = "none"
        validate_backends(catalog)

