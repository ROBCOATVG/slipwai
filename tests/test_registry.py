"""The registry: what the protocol declares, what loading refuses, and what a backend inherits.

Every registry here is built with `load` from fakes written in `registry_fakes.py`; nothing in this file
reads the built-in one, so a red result names the rule and not a language.
"""

from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from registry_fakes import fake_language, family_answers, required_answers

from slipwai.assets import ROOT
from slipwai.registry import (
    ENTRY_STORE,
    HEALTH_BODY,
    PROTOCOL,
    READY_PATH,
    SERVICE_FILES,
    TOOLING,
    WRITE_SIDE_FILES,
    Backend,
    Family,
    Language,
    Member,
    Registry,
    RegistryError,
    check_catalog,
    load,
)

CONTRACT = ROOT / "docs/backend-protocol.md"
REQUIRED = {
    "service_files",
    "name_service",
    "repository_files",
    "ready_path",
    "health_body",
    "tooling",
    "feature_tooling",
    "compose_caches",
    "executables",
    "dev_command",
    "persistence_directory",
    "native_commands",
    "formatter",
}
REQUIRED |= {
    "image_builder", "migrations_in_production", "postgres_sslmode", "service_descriptors", "ci_toolchain_setup"
}
REQUIRED |= {
    "write_side_files", "read_side_files", "flag_reader", "entry_wiring", "flag_resource", "entry_store", "shared_code"
}
REQUIRED |= {"prune_rows"}
REQUIRED |= {"gitignore", "agent_permissions", "gate_description", "event_model_paths", "mutation_tool"}
REQUIRED |= {"procfile", "pin_files", "makefile_variables", "renovate_rules", "opt_in_flag_transports"}

def contract_rows() -> dict[str, tuple[str, bool]]:
    """The contract's member table as name -> (level, required)."""
    rows = {}
    for line in CONTRACT.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("| `") and len(cells) >= 3 and cells[1] in ("family", "backend"):
            rows[cells[0].strip("`")] = (cells[1], cells[2].startswith("required"))
    return rows



class ProtocolTest(unittest.TestCase):
    def test_4a_the_protocol_declares_every_member_and_requires_only_the_moved_ones(self) -> None:
        declared = {member.name: member for member in PROTOCOL}
        self.assertEqual(len(PROTOCOL), len(declared))
        self.assertEqual(REQUIRED, {name for name, member in declared.items() if member.required})
        for member in PROTOCOL:
            self.assertIn(member.level, {"family", "backend"}, member.name)

    def test_4b_a_backend_answering_only_the_required_members_loads(self) -> None:
        registry = load([fake_language("fake-a")])
        self.assertIn("fake-a", registry.backends)

    def test_4c_the_contract_table_and_the_protocol_list_the_same_members(self) -> None:
        in_code = {member.name: (member.level, member.required) for member in PROTOCOL}
        self.assertEqual(contract_rows(), in_code)

    def test_4d_an_answer_the_protocol_does_not_declare_is_refused_by_backend_and_member(self) -> None:
        misspelt: Member[str] = Member("ready_paths", "backend", False, str, "")
        with self.assertRaises(RegistryError) as raised:
            load([fake_language("fake-go", answers=required_answers(extra={misspelt: "/ready"}))])
        self.assertIn("backend fake-go answers ready_paths, which the protocol does not declare", str(raised.exception))

    def test_a_family_answering_an_undeclared_member_is_refused_too(self) -> None:
        misspelt: Member[str] = Member("ready_paths", "family", False, str, "")
        language = Language((Family("fake", {misspelt: "/x"}),), (Backend("fake-a", "fake", required_answers()),))
        with self.assertRaises(RegistryError) as raised:
            load([language])
        self.assertIn("family fake answers ready_paths, which the protocol does not declare", str(raised.exception))


class RequiredMembersTest(unittest.TestCase):
    def refusal(self, *languages: Language) -> str:
        with self.assertRaises(RegistryError) as raised:
            load(languages)
        return str(raised.exception)

    def test_2a_a_backend_missing_a_required_member_is_refused_by_backend_and_member(self) -> None:
        message = self.refusal(fake_language("fake-go", answers=required_answers(without=(READY_PATH,))))
        self.assertIn("backend fake-go is missing ready_path", message)

    def test_s02_2c_a_toolchain_member_is_required_like_the_skeleton_s(self) -> None:
        message = self.refusal(fake_language("fake-go", answers=required_answers(without=(TOOLING,))))
        self.assertEqual("backend fake-go is missing tooling", message)

    def test_2b_one_refusal_names_every_missing_pair(self) -> None:
        message = self.refusal(
            fake_language("fake-a", answers=required_answers(without=(HEALTH_BODY,))),
            fake_language("fake-b", family="other", answers=required_answers(without=(READY_PATH, SERVICE_FILES))),
        )
        for pair in (
            "backend fake-a is missing health_body",
            "backend fake-b is missing ready_path",
            "backend fake-b is missing service_files",
        ):
            self.assertIn(pair, message)
        self.assertNotIn("\n", message)

    def test_2c_an_answer_of_the_wrong_kind_is_refused_like_a_missing_one(self) -> None:
        message = self.refusal(fake_language("go", answers=required_answers(extra={READY_PATH: 3000})))
        self.assertIn("backend go answers ready_path with int, where the protocol wants str", message)

    def test_2b_a_backend_without_an_entry_store_is_refused_and_none_is_an_answer(self) -> None:
        message = self.refusal(fake_language("fake-go", answers=required_answers(without=(ENTRY_STORE,))))
        self.assertEqual("backend fake-go is missing entry_store", message)
        opens_its_own = load([fake_language("fake-go", answers=required_answers(extra={ENTRY_STORE: None}))])
        self.assertIsNone(opens_its_own.answer("fake-go", ENTRY_STORE))

    def test_2c_a_layout_that_is_not_a_mapping_is_refused_by_backend_member_and_kind(self) -> None:
        message = self.refusal(fake_language("go", answers=required_answers(extra={WRITE_SIDE_FILES: []})))
        self.assertIn("backend go answers write_side_files with list, where the protocol wants dict", message)


class InheritanceTest(unittest.TestCase):
    def family_of_two(self) -> Language:
        """Family `fake` answers `ready_path`; `fake-plain` leaves it to the family, `fake-framework` overrides."""
        plain = required_answers(without=(READY_PATH,))
        framework = required_answers(extra={READY_PATH: "/framework-ready"})
        return Language(
            (Family("fake", {**family_answers(), READY_PATH: "/family-ready"}),),
            (Backend("fake-plain", "fake", plain), Backend("fake-framework", "fake", framework)),
        )

    def test_3a_a_backend_inherits_its_family_s_answer(self) -> None:
        registry = load([self.family_of_two()])
        self.assertEqual("/family-ready", registry.answer("fake-plain", READY_PATH))

    def test_3b_a_backend_s_own_answer_wins_and_its_sibling_keeps_the_family_s(self) -> None:
        registry = load([self.family_of_two()])
        self.assertEqual("/framework-ready", registry.answer("fake-framework", READY_PATH))
        self.assertEqual("/family-ready", registry.answer("fake-plain", READY_PATH))

    def test_3c_a_required_member_no_one_answers_refuses_naming_the_backend(self) -> None:
        language = Language(
            (Family("fake"),), (Backend("fake-plain", "fake", required_answers(without=(READY_PATH,))),)
        )
        with self.assertRaises(RegistryError) as raised:
            load([language])
        self.assertIn("fake-plain", str(raised.exception))

    def test_3d_a_backend_of_an_undeclared_family_refuses_naming_both(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            load([Language((), (Backend("fake-orphan", "nowhere", required_answers()),))])
        self.assertIn(
            "backend fake-orphan names family nowhere, which no loaded language declares", str(raised.exception)
        )

    def test_a_backend_whose_family_is_not_loaded_refuses_with_a_key_error_naming_it(self) -> None:
        odd: Member[str] = Member("bad\nname", "backend", False, str, "")
        orphan = Registry({}, {"go\nx": Backend("go\nx", "ghost", {})})
        with self.assertRaises(KeyError) as raised:
            orphan.answer("go\nx", odd)
        self.assertEqual("backend 'go\\nx' does not answer 'bad\\nname'", raised.exception.args[0])

    def test_one_refusal_joins_every_fault_with_a_semicolon_and_a_space(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            load([fake_language("a", answers=required_answers(without=(READY_PATH, HEALTH_BODY)))])
        self.assertEqual("backend a is missing ready_path; backend a is missing health_body", str(raised.exception))

    def test_none_is_an_answer_and_absence_is_not(self) -> None:
        nothing: Member[str | None] = Member("mutation_note", "backend", False, (str, type(None)), "")
        answers = required_answers(extra={nothing: None})
        language = Language((Family("fake", family_answers()),), (Backend("fake-a", "fake", answers),))
        protocol = (*PROTOCOL, nothing)
        registry = load([language], protocol)
        self.assertIsNone(registry.answer("fake-a", nothing))
        with self.assertRaises(KeyError):
            load([fake_language("fake-b")], protocol).answer("fake-b", nothing)


class CatalogAgreementTest(unittest.TestCase):
    def registry(self) -> Registry:
        """`go` of family `fake`, and `java-spring` of family `java`."""
        return load([fake_language("go"), fake_language("java-spring", family="java")])

    def catalog(self, **backends: str) -> dict[str, dict[str, dict[str, str]]]:
        return {"backends": {key: {"family": family} for key, family in backends.items()}}

    def refusal(self, catalog: dict[str, dict[str, dict[str, str]]]) -> str:
        with self.assertRaises(RegistryError) as raised:
            check_catalog(catalog, self.registry())
        return str(raised.exception)

    def test_the_agreeing_catalog_passes(self) -> None:
        check_catalog(self.catalog(go="fake", **{"java-spring": "java"}), self.registry())

    def test_5b_a_catalog_backend_with_no_registry_object_is_named(self) -> None:
        message = self.refusal(self.catalog(go="fake", cobol="cobol", **{"java-spring": "java"}))
        self.assertIn("backend cobol is in catalog.json with no registry object", message)

    def test_5c_a_registry_backend_the_catalog_does_not_list_is_named(self) -> None:
        message = self.refusal(self.catalog(**{"java-spring": "java"}))
        self.assertIn("backend go is in the registry but not in catalog.json", message)

    def test_5d_both_directions_are_one_refusal_each_under_its_own_direction(self) -> None:
        message = self.refusal(self.catalog(cobol="cobol", **{"java-spring": "java"}))
        self.assertIn("backend cobol is in catalog.json with no registry object", message)
        self.assertIn("backend go is in the registry but not in catalog.json", message)
        self.assertNotIn("\n", message)

    def test_5e_a_family_that_differs_names_the_backend_and_both_families(self) -> None:
        message = self.refusal(self.catalog(go="fake", **{"java-spring": "kotlin"}))
        self.assertIn("backend java-spring is family kotlin in catalog.json and java in the registry", message)

    def test_a_catalog_key_with_a_line_break_is_refused_on_one_line(self) -> None:
        message = self.refusal(self.catalog(go="fake", **{"java-spring": "java", "co\nbol": "cobol"}))
        self.assertIn("backend 'co\\nbol' is in catalog.json with no registry object", message)
        self.assertNotIn("\n", message)

    def test_a_catalog_backend_with_no_family_is_refused_in_one_line(self) -> None:
        catalog = {"backends": {"go": {"family": "fake"}, "java-spring": {}}}
        self.assertEqual("backend java-spring has no family in catalog.json", self.refusal(catalog))
