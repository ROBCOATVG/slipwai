"""The catalog is the keel's file with every loaded language's fragment folded in, in the order the fragments declare.

Fakes only: a fragment is a dict the test writes, a package a `Package` at a path that need not exist. What the
merge refuses it refuses per package, one line each, and everything else still merges.
"""
from __future__ import annotations

import copy
import json
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT
from slipwai.catalog_checks import validate_backends
from slipwai.catalog_merge import merge, reachable, retract
from slipwai.language_directory import Package, read
from slipwai.registry import RegistryError, check_catalog, registry

# Every package this checkout pins, in the order the directory reads them. None until slice 3.8.
PINNED = sorted(
    path for path in checkout_packages.PACKAGES.iterdir()
    if path.is_dir() and not path.name.startswith(".")
) if checkout_packages.PACKAGES.is_dir() else []

CORE = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def with_keel_rows(catalog: Mapping[str, Any], *rows: tuple[str, int]) -> dict[str, Any]:
    """A copy of `catalog` as it would read if the keel carried a backend of its own per `(key, order)`.

    Version 2's keel carries none — every language is a package — but `catalog_merge` still has to order
    a keel row against a fragment's, because that is what decides a tie, and the only way to test that is
    to write one here. A fixture, never a shape the keel ships.
    """
    built = json.loads(json.dumps(catalog))
    for key, order in rows:
        built["backends"][key] = {"family": key, "label": f"{key} label",
                                  "targets": ["none", "existing"], "order": order}
        built["axes"]["persistence"]["options"]["memory"]["backends"].append(key)
        built["axes"]["http"]["options"]["none"]["backends"].append(key)
        built["default"]["http"][key] = "none"
    return built


# The keel as it would be with two backends of its own, at the orders TypeScript and Python had.
BUILT = with_keel_rows(CORE, ("core-a", 10), ("core-b", 20))


def fragment(name: str = "bad", order: int = 50, **row: Any) -> dict[str, Any]:
    backend = {
        "label": f"{name} label",
        "targets": ["none", "existing"],
        "options": {"persistence": ["memory"], "http": ["none"]},
        **row,
    }
    return {"name": name, "core": ">=9.0,<10", "order": order, "family": name, "backends": {name: backend}}


def package(name: str = "bad", order: int = 50, **row: Any) -> Package:
    return Package(name, at(name), fragment(name, order, **row))


def at(name: str) -> Path:
    """Where a fake package sits. A refusal names it, and what a path reads as is the platform's to say:
    `/languages/a` on POSIX and `\\languages\\a` on Windows. Tests ask this rather than spelling one."""
    return Path(f"/languages/{name}")


class MergeOrderTest(unittest.TestCase):
    def test_a_merge_of_nothing_is_core_with_the_order_key_stripped(self) -> None:
        merged, refused, _ = merge(copy.deepcopy(CORE), [])
        self.assertEqual(refused, {})
        self.assertEqual(merged["schemaVersion"], CORE["schemaVersion"])
        self.assertTrue(all("order" not in row for row in merged["backends"].values()))
        expected = copy.deepcopy(CORE)
        for row in expected["backends"].values():
            del row["order"]
        self.assertEqual(json.dumps(merged, indent=2), json.dumps(expected, indent=2))

    def test_every_core_row_declares_its_order(self) -> None:
        self.assertEqual(
            {key: row["order"] for key, row in CORE["backends"].items()},
            {},  # S09 and S10 moved every row into its package's fragment; the keel is built with no language
        )

    def test_a_fragment_takes_the_place_its_order_declares_and_every_list_follows(self) -> None:
        merged, refused, _ = merge(copy.deepcopy(BUILT), [package("zed", 15, defaults={"http": "none"})])
        self.assertEqual(refused, {})
        expected = ["core-a", "zed", "core-b"]
        self.assertEqual(list(merged["backends"]), expected)
        for axis in ("persistence", "http"):
            for name, option in merged["axes"][axis]["options"].items():
                self.assertEqual(option["backends"], [key for key in expected if key in option["backends"]], name)
        self.assertIn("zed", merged["axes"]["persistence"]["options"]["memory"]["backends"])
        self.assertNotIn("zed", merged["axes"]["persistence"]["options"]["postgres"]["backends"])
        self.assertEqual(list(merged["default"]["http"]), expected)
        self.assertEqual(merged["default"]["http"]["zed"], "none")

    def test_at_a_tie_core_comes_first_and_a_fragment_keeps_its_own_listing_order(self) -> None:
        one = package("one", 20)
        one.fragment["backends"]["two"] = dict(one.fragment["backends"]["one"], label="two")
        one.fragment["backends"]["one"]["defaults"] = {"http": "none"}
        one.fragment["backends"]["two"]["defaults"] = {"http": "none"}
        merged, _, _ = merge(copy.deepcopy(BUILT), [one])
        self.assertEqual(list(merged["backends"])[-3:], ["core-b", "one", "two"])

    def test_a_merged_row_reads_as_a_catalog_row_does(self) -> None:
        merged, _, _ = merge(copy.deepcopy(CORE), [package("zed", 25, framework="zfw")])
        self.assertEqual(
            merged["backends"]["zed"],
            {"family": "zed", "framework": "zfw", "label": "zed label", "targets": ["none", "existing"]},
        )

    def test_the_cores_own_dict_is_left_as_it_was(self) -> None:
        core = copy.deepcopy(CORE)
        merge(core, [package("zed", 25)])
        self.assertEqual(core, CORE)


@unittest.skipUnless(all(checkout_packages.installed(n) for n in ("go",)),
                     "needs the first-party packages, which the keel never installs")
class MovesTest(unittest.TestCase):
    """The merge reproduces the catalog as it was when every language was a row of the keel's own file:
    the six pinned packages fold back into the same bytes."""

    def test_6a_core_and_the_pinned_packages_merge_into_the_catalog_before_the_moves(self) -> None:
        packages, refusals = read(checkout_packages.PACKAGES, CORE["schemaVersion"])
        self.assertEqual(refusals, [])
        self.assertEqual([package.name for package in packages], [root.name for root in PINNED])
        self.assertEqual([package.name for package in packages],
                         ["go", "java", "java-quarkus", "java-spring", "python", "typescript"])
        merged, refused, _ = merge(copy.deepcopy(CORE), packages)
        self.assertEqual(refused, {})
        before = json.loads((ROOT / "tests/catalog-before-s08.json").read_text(encoding="utf-8"))
        # Less the default backend, which is the merge's first backend now and no key of the keel's.
        default = {key: value for key, value in before["default"].items() if key != "backend"}
        expected = {**before, "schemaVersion": "9.0", "default": default}
        self.assertEqual(json.dumps(merged, indent=2), json.dumps(expected, indent=2))

    def test_6b_cores_file_has_no_go_anywhere(self) -> None:
        def strings(value: Any) -> Iterator[str]:
            if isinstance(value, dict):
                for key, inner in value.items():
                    yield key
                    yield from strings(inner)
            elif isinstance(value, list):
                for inner in value:
                    yield from strings(inner)
            elif isinstance(value, str):
                yield value

        self.assertNotIn("go", set(strings(CORE)))
        self.assertEqual(CORE["axes"]["http"]["options"]["net-http"]["backends"], [])


class ClaimTest(unittest.TestCase):
    def test_two_claims_on_a_key_refuse_both_and_each_names_the_other(self) -> None:
        one, two = package("a"), package("b")
        one.fragment["backends"] = {"dup": one.fragment["backends"]["a"]}
        two.fragment["backends"] = {"dup": two.fragment["backends"]["b"]}
        merged, refused, _ = merge(copy.deepcopy(CORE), [one, two])
        self.assertEqual(
            refused,
            {
                "a": f"language a ({at('a')}): declares backend dup, which language b ({at('b')}) also declares",
                "b": f"language b ({at('b')}): declares backend dup, which language a ({at('a')}) also declares",
            },
        )
        self.assertNotIn("dup", merged["backends"])

    def test_a_claim_on_a_built_in_key_is_refused_and_the_built_in_is_untouched(self) -> None:
        built_in = next(iter(BUILT["backends"]))
        clash = package("py2")
        clash.fragment["backends"] = {built_in: clash.fragment["backends"]["py2"]}
        merged, refused, _ = merge(copy.deepcopy(BUILT), [clash, package("fine")])
        self.assertEqual(
            refused, {"py2": f"language py2 ({at('py2')}): declares backend {built_in}, which core already has"}
        )
        self.assertEqual(merged["backends"][built_in]["label"], BUILT["backends"][built_in]["label"])
        self.assertIn("fine", merged["backends"])


class UndeclaredTest(unittest.TestCase):
    def refusal(self, **row: Any) -> str:
        merged, refused, _ = merge(copy.deepcopy(CORE), [package("bad", **row)])
        self.assertNotIn("bad", merged["backends"])
        return refused["bad"]

    def test_an_axis_core_does_not_have(self) -> None:
        self.assertEqual(
            self.refusal(options={"cache": ["memory"]}),
            f"language bad ({at('bad')}): backend bad answers axis cache, which core does not declare",
        )



class UnreachableAnswersTest(unittest.TestCase):
    """A cloud nobody installed is a fact about this machine, not a fault in the package.

    Every published language names every cloud it has deployment answers for, and a person installs the
    clouds they deploy to — usually none of them. Refusing the package for the gap left that person with
    no language at all: `--language {}` with a language installed, and `generate --target none` refused
    outright. So an answer the catalogue cannot reach is pruned from the row and the rest of the package
    merges, which is what the keel already does to an option no installed target offers.
    """

    def merged_row(self, **row: Any) -> dict[str, Any]:
        merged, refused, _ = merge(copy.deepcopy(CORE), [package("good", **row)])
        self.assertEqual(refused, {})
        return merged["backends"]["good"]

    def test_a_target_nothing_installed_declares_is_pruned_and_the_backend_stays(self) -> None:
        self.assertEqual(self.merged_row(targets=["none", "existing", "gcp"])["targets"],
                         ["none", "existing"])

    def test_a_backend_whose_every_cloud_is_absent_still_generates_locally(self) -> None:
        """The case that was wholly broken: two clouds named, neither installed, `--target none` wanted."""
        self.assertEqual(self.merged_row(targets=["none", "existing", "aws", "azure"])["targets"],
                         ["none", "existing"])

    def test_an_option_no_installed_target_offers_is_pruned_from_the_backend(self) -> None:
        merged, refused, _ = merge(copy.deepcopy(CORE), [package("good", options={"auth": ["none", "cognito"]})])
        self.assertEqual(refused, {})
        self.assertNotIn("good", merged["axes"]["auth"]["options"].get("cognito", {}).get("backends", []))
        self.assertIn("good", merged["axes"]["auth"]["options"]["none"]["backends"])

    def test_a_default_whose_option_was_pruned_is_dropped_rather_than_left_dangling(self) -> None:
        """Asked of `reachable` directly: core takes a per-backend default on `framework` and `http` only,
        and neither axis is gated on a target, so no merge of today's catalogue can reach this. The rule
        still holds — a default is a pointer into the options beside it, and the pruner must not leave one
        aimed at an answer it has just taken away."""
        row, gone = reachable(
            copy.deepcopy(CORE),
            {"label": "x", "targets": ["none"], "options": {"auth": ["none", "cognito"]},
             "defaults": {"auth": "cognito"}},
        )
        self.assertEqual(row["options"]["auth"], ["none"])
        self.assertEqual(row["defaults"], {})
        self.assertEqual(gone, ["auth option cognito"])

    def test_an_option_nothing_declares_is_pruned_and_named_rather_than_refused(self) -> None:
        """`gin` could be a Go package's own framework option or a misspelling, and nothing on this machine
        can tell the two apart — the package's own CI can, because it installs the siblings it names. So the
        backend keeps the answers that work and `slipwai list` says which one went."""
        merged, refused, unreachable = merge(copy.deepcopy(CORE), [package("good", options={"http": ["none", "gin"]})])
        self.assertEqual(refused, {})
        self.assertIn("good", merged["backends"])
        self.assertEqual(unreachable["good"], ["http option gin"])

    def test_an_axis_core_does_not_declare_is_still_a_fault(self) -> None:
        """Pruning is for an answer that could exist. An axis that does not is a mistake in the package."""
        _, refused, _ = merge(copy.deepcopy(CORE), [package("bad", options={"cache": ["memory"]})])
        self.assertIn("answers axis cache, which core does not declare", refused["bad"])


class DefaultsTest(unittest.TestCase):
    def refusal(self, **row: Any) -> str:
        _, refused, _ = merge(copy.deepcopy(CORE), [package("bad", **row)])
        return refused["bad"]

    def test_a_default_the_backends_own_options_cannot_take_names_both(self) -> None:
        line = self.refusal(defaults={"http": "fastify"})
        self.assertIn("backend bad defaults http to fastify", line)
        self.assertIn("none", line)

    def test_a_per_backend_default_for_an_axis_core_answers_once_is_refused(self) -> None:
        self.assertEqual(
            self.refusal(options={"auth": ["none"]}, defaults={"auth": "none"}),
            f"language bad ({at('bad')}): backend bad defaults auth, and core's auth default is one answer, "
            "not one per backend",
        )


class OverTheMergeTest(unittest.TestCase):
    def test_the_naming_rule_holds_the_merged_catalog(self) -> None:
        packages = [package("zed", 25, defaults={"http": "none"}), package("zed-two", 26, defaults={"http": "none"})]
        merged, refused, _ = merge(copy.deepcopy(CORE), packages)
        self.assertEqual(refused, {})
        merged["backends"]["zed-two"]["family"] = "zed"
        with self.assertRaisesRegex(ValueError, "zed has more than one backend"):
            validate_backends(merged)

    def test_the_registry_check_sees_a_merged_row_no_registry_object_answers(self) -> None:
        merged, _, _ = merge(copy.deepcopy(CORE), [package("zed", 25, defaults={"http": "none"})])
        with self.assertRaisesRegex(RegistryError, "backend zed is in catalog.json with no registry object"):
            check_catalog(merged, registry())


class RetractTest(unittest.TestCase):
    def test_a_retracted_package_leaves_no_row_no_list_entry_and_no_default(self) -> None:
        core = copy.deepcopy(CORE)
        for row in core["backends"].values():
            del row["order"]
        zed = package("zed", 25, defaults={"http": "none"})
        merged, _, _ = merge(copy.deepcopy(CORE), [zed])
        retract(merged, zed)
        self.assertEqual(json.dumps(merged, indent=2), json.dumps(core, indent=2))


if __name__ == "__main__":
    unittest.main()
