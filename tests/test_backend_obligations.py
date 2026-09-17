"""`docs/backend-obligations.md` is the checklist the maintenance skills work from, so the code holds it.

A checklist nothing compares to the code is a checklist that is already wrong — which is how a
framework-owning backend once shipped hand-written adapters beside a framework with a first-party
extension for each. So
every list in that file is derived from something here: the axes from the catalog, the Make targets from
the generator, the per-backend tables from the modules that own them.

Adding an axis, a Make target or a per-backend table fails this suite until the document names it, and
then until every backend answers it. That failure list is the work the change created.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG, catalog_families

OBLIGATIONS = ROOT / "docs/backend-obligations.md"
FACTORY_SOURCE = ROOT / "src/slipwai"


def sections(text: str) -> dict[str, str]:
    """The document split on its `## ` headings, keyed by the leading number."""
    found = {}
    for match in re.finditer(r"^## (\d+)\..*?$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL):
        found[match.group(1)] = match.group(2)
    return found


def table_rows(section: str) -> list[list[str]]:
    """Every body row of every markdown table in a section, as stripped cells."""
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # The header row names columns rather than obligations; it is the one with no code span.
        if any("`" in cell for cell in cells):
            rows.append(cells)
    return rows


def code_spans(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def per_backend_dict(path: Path, name: str) -> dict[str, set[str]]:
    """The per-backend table assigned to `name` in `path`, as backend -> its keys.

    Read from the source rather than called, because these tables are local to the function that uses
    them, and hard-coding their contents here would assert nothing. `native = {...}[language]` is the
    common spelling — the subscript that selects one backend is unwrapped to reach the table itself.
    """
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        table = node.value.value if isinstance(node.value, ast.Subscript) else node.value
        if not isinstance(table, ast.Dict):
            continue
        found = {
            str(key.value): {str(k.value) for k in value.keys if isinstance(k, ast.Constant)}
            for key, value in zip(table.keys, table.values, strict=True)
            if isinstance(key, ast.Constant) and isinstance(value, ast.Dict)
        }
        if found:
            return found
    raise AssertionError(f"{path.name} no longer has a per-backend `{name}` table")


def backend_keyed_tables(backends: set[str]) -> dict[str, str]:
    """Every dict literal under `src/slipwai/` whose keys cover every backend, as symbol -> module path.

    The other direction of `test_every_documented_table_exists_where_it_says`: that one fails when a row
    names a table that has moved, this one fails when a table exists that no row names. A table keyed by
    every backend *is* a per-backend obligation whatever it was written for, so a new one asks the same
    question of every backend and belongs in section 3 — which is the failure `READ_SIDE_FILES` did not
    produce when the read side shipped.

    A dict literal, because that is what can be recognised without running anything; a table derived from
    others (`SERVICE_FILES = with_read_side(WRITE_SIDE_FILES)`) is not found here and is documented
    because its sources are.
    """
    found = {}
    for path in sorted((FACTORY_SOURCE).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            # `native = {...}[language]` is the common spelling: unwrap the selecting subscript.
            table = node.value.value if isinstance(node.value, ast.Subscript) else node.value
            if not isinstance(table, ast.Dict):
                continue
            keys = {key.value for key in table.keys if isinstance(key, ast.Constant)}
            if not backends <= keys:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    found[target.id] = str(path.relative_to(FACTORY_SOURCE))
    return found


def native_targets() -> set[str]:
    """Every Make target a backend declares, from any one backend's entry — they are asserted equal."""
    declared = per_backend_dict(FACTORY_SOURCE / "project/native_commands.py", "native")
    return set.union(*declared.values())


class BackendObligationsTest(FactoryTestCase):
    def setUp(self) -> None:
        self.text = OBLIGATIONS.read_text()
        self.sections = sections(self.text)
        self.backends = list(CATALOG["backends"])
        self.families = sorted(catalog_families(CATALOG))

    def test_the_documented_axes_are_the_catalog_s(self):
        """Section 1 carries one row per axis — a new axis has to state what a backend owes it."""
        documented = {name for row in table_rows(self.sections["1"]) for name in code_spans(row[0])}
        self.assertEqual(set(CATALOG["axes"]), documented)

    def test_the_documented_make_targets_are_the_generator_s(self):
        """Section 2 carries one row per `native` key, including the ones no gate runs."""
        documented = {name for row in table_rows(self.sections["2"]) for name in code_spans(row[0])}
        self.assertEqual(native_targets(), documented)

    def test_every_backend_declares_every_make_target(self):
        """A backend missing a target would otherwise surface as a `KeyError` at generation time."""
        declared = per_backend_dict(FACTORY_SOURCE / "project/native_commands.py", "native")
        self.assertEqual(set(self.backends), set(declared), "a backend has no `native` entry")
        for backend, targets in declared.items():
            with self.subTest(backend=backend):
                self.assertEqual(native_targets(), targets)

    def test_every_documented_table_exists_where_it_says(self):
        """Section 3 names a symbol and a file; a rename that leaves the row behind fails here."""
        for row in table_rows(self.sections["3"]):
            symbol, location = code_spans(row[0])[0], code_spans(row[1])[0]
            path = ROOT / location if location.startswith("assets/") else FACTORY_SOURCE / location
            with self.subTest(table=symbol, file=location):
                self.assertTrue(path.is_file(), f"{location} does not exist")
                self.assertRegex(
                    path.read_text(),
                    rf"(?m)^\s*(?:def\s+)?{re.escape(symbol)}\s*[:=(]",
                    f"{location} no longer defines {symbol}",
                )

    def test_no_per_backend_table_is_missing_from_the_document(self):
        """A table keyed by every backend that section 3 does not name is an obligation nothing asks."""
        documented = {name for row in table_rows(self.sections["3"]) for name in code_spans(row[0])}
        for symbol, module in backend_keyed_tables(set(self.backends)).items():
            with self.subTest(table=symbol, file=module):
                self.assertIn(
                    symbol,
                    documented,
                    f"{module} defines a per-backend `{symbol}` that section 3 never names",
                )

    def test_every_backend_is_named_in_every_table_it_always_owes(self):
        """The rows marked `always` have to mention every backend — or every family, where so keyed."""
        for row in table_rows(self.sections["3"]):
            if row[3] != "always":
                continue
            symbol, location, keyed_by = code_spans(row[0])[0], code_spans(row[1])[0], row[2]
            path = ROOT / location if location.startswith("assets/") else FACTORY_SOURCE / location
            source = path.read_text()
            expected = self.families if keyed_by == "family" else self.backends
            for name in expected:
                with self.subTest(table=symbol, keyed_by=keyed_by, name=name):
                    self.assertIn(
                        f'"{name}"',
                        source,
                        f"{location} never names {name}, which {symbol} owes an entry",
                    )

    def test_the_ecosystem_choices_are_confirmed_with_the_user(self):
        """Section 4 owns the decisions no document here can answer. Nor can the implementer alone.

        Every row of it is pinned into every project generated from that backend afterwards, which is the
        same permanence the framework choice has — and the framework choice was always confirmed while
        these were not. So the section has to require both: the search that finds the current options, and
        the question that lets the user pick among them.
        """
        section = self.sections["4"]
        self.assertIn("WebSearch", section, "section 4 no longer sends these choices to a search")
        self.assertIn(
            "AskUserQuestion",
            section,
            "section 4 no longer requires these choices to be confirmed with the user",
        )

    def test_the_maintenance_skills_point_at_this_document(self):
        """The checklist only holds if the procedures read it, so the link is asserted, not assumed."""
        for skill in ("add-language", "add-framework"):
            with self.subTest(skill=skill):
                text = (ROOT / f".claude/skills/{skill}/SKILL.md").read_text()
                self.assertIn("docs/backend-obligations.md", text)
