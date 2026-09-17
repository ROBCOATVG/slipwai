"""The factory-maintenance skills are documentation the code can drift away from.

`.claude/skills/add-language/`, `.claude/skills/add-backing-service/` and `.claude/skills/add-framework/`
are the checklists somebody follows to extend this factory, and every item is a claim about code: this
module owns that table, this test asserts that rule, the generated gate runs these targets. A claim that
quietly stopped being true is worse than a missing one — it is followed, and it fails somewhere else.

Nothing gated them before, and the drift showed: a per-language table `KeyError`s for a new backend while
being documented nowhere, a cross-reference pointing at a renumbered item, a list of the generated gate's
targets missing one that had been added since. These tests pin the claims that can be checked mechanically.

One test here pins a different kind of claim. A skill also names *products* — frameworks, stores, image
tags — and those cannot be checked against this repository at all, because their truth lives outside it and
changes without any commit here. What is checkable is that each skill says so, and sends the reader to a
search before it offers anybody a choice.
"""
from __future__ import annotations

import ast
import re
import unittest

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG

SKILLS = ROOT / ".claude/skills"
PACKAGE = ROOT / "src/slipwai"
NAMES = ("add-language", "add-backing-service", "add-framework")
# The two skills that have to name every table keyed by backend: `add-language` because a new backend
# meets each one as a `KeyError`, and `add-framework` because a promotion has to visit each one to decide
# whether the framework changes its answer or the family still owns it.
TABLE_SKILLS = ("add-language", "add-framework")

# A backticked token that looks like a path this repository should contain, rather than a path inside a
# *generated* project — which these skills also quote, and which does not exist here.
CITED_PATH = re.compile(r"`((?:src/|tests/|scripts/|assets/|\.claude/)[\w./<>-]+|project/[\w./]+\.py|[\w]+\.py)`")
# `tests/test_axes.py::test_something` — a named test that has to still be there under that name.
CITED_TEST = re.compile(r"`(tests/\w+\.py)::(\w+)`")
GENERATED_ONLY = re.compile(r"^(apps|specs|docs|skills|commands)/")
# Paths that exist only inside a *generated* project. `scripts/backing-services.py` is the name
# `assets/backing-services/prune.py` is emitted under, which is the whole point of that asset.
GENERATED_NAMES = {"scripts/backing-services.py", "scripts/verify", "scripts/check-imports.py"}
# Where a citation may resolve. A bare `go.py` means the language module; `prune.py` means the asset.
SEARCH_ROOTS = (
    "",
    "src/slipwai",
    "src/slipwai/project",
    "src/slipwai/project/languages",
    "assets/backing-services",
)


def skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


class MaintenanceSkillsTest(unittest.TestCase):
    def test_every_language_keyed_table_is_documented(self) -> None:
        """A table indexed by language raises `KeyError` for a new backend, so it has to be on the list.

        This is the check that was missing: `dev_command`, `event_store_directory` and `COMPOSE_CACHES`
        were all mandatory for a language answering an axis, and all three were documented nowhere.
        """
        skills = {name: skill_text(name) for name in TABLE_SKILLS}
        languages = set(CATALOG["backends"])
        undocumented: list[str] = []

        for path in sorted(PACKAGE.rglob("*.py")):
            relative = path.relative_to(PACKAGE).as_posix()
            tree = ast.parse(path.read_text())

            # Module-level tables with one entry per language: cited by their own name.
            for node in tree.body:
                if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                    continue
                keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
                if keys != languages:
                    continue
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    for name, skill in skills.items():
                        if target.id not in skill:
                            undocumented.append(
                                f"{name}: {relative}: the per-language table `{target.id}`"
                            )

            # Functions that index anything with `[backend]` or `[language]` — a backend key or a language
            # family, the two things a per-backend table is keyed by: cited by name, or by their module.
            for function in ast.walk(tree):
                if not isinstance(function, ast.FunctionDef):
                    continue
                indexes_backend = any(
                    isinstance(inner, ast.Subscript)
                    and isinstance(inner.slice, ast.Name)
                    and inner.slice.id in {"backend", "language"}
                    for inner in ast.walk(function)
                )
                if not indexes_backend:
                    continue
                for name, skill in skills.items():
                    if function.name not in skill and relative not in skill:
                        undocumented.append(f"{name}: {relative}: `{function.name}` is keyed by backend")

        self.assertEqual(
            [],
            undocumented,
            "these skills do not mention these tables, and both have to: a new backend meets each one "
            "as a KeyError, and a promoted family has to decide which of them the framework changes:\n  "
            + "\n  ".join(undocumented),
        )

    def test_every_repository_path_a_skill_cites_exists(self) -> None:
        missing: list[str] = []
        for name in NAMES:
            for cited in sorted(set(CITED_PATH.findall(skill_text(name)))):
                if "<" in cited or GENERATED_ONLY.match(cited) or cited in GENERATED_NAMES:
                    continue  # a placeholder, or a path inside a generated project
                if not any((ROOT / root / cited).exists() for root in SEARCH_ROOTS):
                    missing.append(f"{name}: `{cited}`")
        self.assertEqual([], missing, "these skills cite paths that do not exist:\n  " + "\n  ".join(missing))

    def test_every_test_a_skill_names_still_exists_under_that_name(self) -> None:
        missing: list[str] = []
        for name in NAMES:
            for module, test in sorted(set(CITED_TEST.findall(skill_text(name)))):
                path = ROOT / module
                if not path.is_file():
                    missing.append(f"{name}: {module} (no such suite)")
                elif f"def {test}(" not in path.read_text():
                    missing.append(f"{name}: {module}::{test}")
        self.assertEqual(
            [], missing, "these skills name tests that have moved or been renamed:\n  " + "\n  ".join(missing)
        )

    def test_every_skill_sends_the_reader_to_a_search_before_it_offers_an_option(self) -> None:
        """An option list recalled from a skill is a stale option list, and it does not read as one.

        These documents name products to illustrate their rules — "Spring Boot owns startup", "Postgres
        needs a container" — and the rules outlive the names. Whoever answers an `AskUserQuestion` cannot
        tell an example that has aged out from a current recommendation, and whatever they pick is pinned
        into every project generated afterwards. So each skill has to say that ecosystem facts come from a
        search, and no section may ask the user to choose without saying so where they will read it.
        """
        missing: list[str] = []
        for name in NAMES:
            text = skill_text(name)
            if "WebSearch" not in text:
                missing.append(f"{name}: never tells the reader to search for the ecosystem's own facts")
            # Per section, because a reader follows the section they are in: a search instruction four
            # sections earlier is not one they will see before answering.
            for section in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
                if "AskUserQuestion" in section and "WebSearch" not in section:
                    heading = section.splitlines()[0].strip()
                    missing.append(f"{name}: section '{heading}' asks the user to choose without searching")
        self.assertEqual(
            [],
            missing,
            "the option lists in these skills are illustrative, and each one has to say so:\n  "
            + "\n  ".join(missing),
        )

    def test_the_toolchain_choices_are_confirmed_with_the_user_not_only_searched(self) -> None:
        """Searching a per-backend tool choice is half the job; the other half is asking.

        The sibling of the test above, and the gap it closes was found by running `add-language` for real.
        That skill sends the reader to a search for nine decisions — formatter, linter, static analysis,
        test runner, coverage, mutation tool, audit, migrations, health probe, OIDC client — and then never
        says to confirm any of them. So they were searched faithfully, decided alone, and reported
        afterwards, while the framework and the axis coverage went to `AskUserQuestion` as the skill
        requires. The asymmetry is not defensible: a generated project has no update relationship with this
        factory, so a linter or a mutation plugin chosen for a backend is chosen for every project generated
        from it, exactly as permanently as the framework, and nobody is asked about it a second time.

        The passage that lists those decisions is found by the decisions it lists rather than by a heading
        or a table shape, so rewording it does not slip past this. It has to send the reader to a search
        *and* to the user.
        """
        decisions = ("formatter", "test runner", "mutation", "audit")
        missing: list[str] = []
        for name in TABLE_SKILLS:
            sections = re.split(r"^#{2,3} ", skill_text(name), flags=re.MULTILINE)
            deciding = [
                section
                for section in sections
                if sum(decision in section.lower() for decision in decisions) >= 3
            ]
            if not deciding:
                missing.append(f"{name}: no passage lists the per-backend tool choices at all")
                continue
            for section in deciding:
                heading = section.splitlines()[0].strip()
                if "WebSearch" not in section:
                    missing.append(f"{name}: '{heading}' lists tool choices without sending them to a search")
                if "AskUserQuestion" not in section:
                    missing.append(f"{name}: '{heading}' lists tool choices without confirming them")
        self.assertEqual(
            [],
            missing,
            "a per-backend tool choice is as permanent as the framework choice, so each skill has to "
            "both search it and confirm it:\n  " + "\n  ".join(missing),
        )

    def test_the_generated_gate_a_skill_quotes_is_the_one_the_makefile_builds(self) -> None:
        """add-language tells the reader which targets the generated `make verify` runs. It has to be true.

        The list had fallen a target behind, which matters: item 3 asks for a `native` entry that makes
        every one of them work, so a reader who trusts a short list writes an incomplete entry.
        """
        makefile = (PACKAGE / "project/makefile.py").read_text()
        tree = ast.parse(makefile)
        assignment = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "verify_dependencies" for target in node.targets)
        )
        value = ast.literal_eval(assignment.value)
        targets = value.split()
        skill = skill_text("add-language")
        # The quoted list wraps across lines in the skill; join it back before reading it.
        quoted = re.search(r"runs `([^`]*check-imports[^`]*)`", re.sub(r"\n\s+", " ", skill))
        self.assertIsNotNone(quoted, "add-language no longer quotes the generated verify target list")
        assert quoted is not None
        # `[check-model]` is bracketed because the event profile adds it; the rest are unconditional.
        listed = [token for token in quoted.group(1).split() if not token.startswith("[")]
        self.assertEqual(
            targets,
            listed,
            "add-language quotes a different set of generated verify targets than makefile.py builds",
        )
