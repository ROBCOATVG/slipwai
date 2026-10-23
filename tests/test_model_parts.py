"""The parts that write the model, the frontend and the ladder's own table of stages.

`stage_models` is the one worth reading twice: it declares every rung of `/sail` and, per rung, the
role whose model runs it and what a delegate at that rung may write. It is how a project puts a bigger
model on deciding than on typing, and how a read-only stage is kept read-only.

Their suites generate a project and come back in 3.3z.
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
import frontend_entry

from slipwai.project import biome, event_model, frontend, gitignore, stage_models


def setUpModule() -> None:  # noqa: N802 - unittest's name
    """A browser app here is `react-vite`, whose catalogue entry is the TypeScript family's (`frontend_entry`)."""
    frontend_entry.install()


def tearDownModule() -> None:  # noqa: N802 - unittest's name
    frontend_entry.remove()

#: The toolkit's own copy of the ladder's stage names, which runs inside a generated project where
#: there is no slipwai to import. Read as text rather than imported: it sits outside the keel's
#: package and importing it would make the keel's gate depend on a project runtime's imports.
CHECKER = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/agents/models.py"
BENCHMARK = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/agents/benchmark.py"


class StagesTest(unittest.TestCase):
    def test_every_stage_is_named_once(self) -> None:
        names = [stage.key for stage in stage_models.STAGES]
        self.assertEqual(len(names), len(set(names)))

    def test_the_ladder_still_has_the_rungs_the_plan_draws(self) -> None:
        """Section 5's figures are drawn from these names. A rung renamed here and not there is a
        picture that lies.

        Held as a prefix rather than equality since the delegable stages took the name of the crew member
        who runs them: the purpose leads, so the word the plan uses is still the start of the key. That is
        the whole reason the compound reads `implement-shipwright` and not the other way round.
        """
        names = {stage.key for stage in stage_models.STAGES}
        for rung in ("example-map", "gaps", "plan", "tasks", "implement", "converge", "demo",
                     "adversary", "mutation"):
            with self.subTest(rung=rung):
                self.assertTrue(any(name == rung or name.startswith(f"{rung}-") for name in names),
                                f"no stage is named for the {rung} rung")

    def test_the_two_cruise_seats_and_the_bosun_are_stages_without_being_rungs(self) -> None:
        """They are stages so the model table names their model and the benchmark records their cost."""
        names = {stage.key for stage in stage_models.STAGES}
        self.assertLessEqual({"decide-skipper", "demo-hand", "unblock-bosun"}, names)

    def test_a_read_only_stage_writes_nothing(self) -> None:
        """The lookout and the privateer report; a reporting stage that can write is a reviewer that edits."""
        for stage in stage_models.STAGES:
            if stage.key in ("gaps-lookout", "adversary-privateer"):
                with self.subTest(stage=stage.key):
                    self.assertEqual(stage.writes, stage_models.NONE)

    def test_every_stage_has_a_role_the_table_can_resolve(self) -> None:
        for stage in stage_models.STAGES:
            with self.subTest(stage=stage.key):
                self.assertTrue(stage.role)

    def test_the_toolkit_knows_every_stage_the_factory_writes(self) -> None:
        """`.specify/models.json` is written from `STAGES` here and checked against `KNOWN_STAGES` there.

        The two were separate lists and drifted: `mockups`, `chart`, `review` and `merge` were stages the
        factory wrote and the project's own checker then called typos, so `make verify` was red on a
        generated repository nobody had touched — the one state `docs/guide/start-here.md` promises. Held
        as an equality rather than a subset, because the checker prints this tuple as "known" and a list
        in a different order is a worse message, not a correct one.
        """
        source = CHECKER.read_text(encoding="utf-8")
        found = re.search(r"KNOWN_STAGES = \((.*?)\n\)", source, re.S)
        if found is None:
            self.fail(f"{CHECKER} no longer declares KNOWN_STAGES as a literal tuple")
        known = tuple(re.findall(r'"([^"]+)"', found.group(1)))
        self.assertEqual(known, tuple(stage.key for stage in stage_models.STAGES))

    def test_deciding_has_a_role_of_its_own(self) -> None:
        """So a project can put a bigger model on deciding than on driving, without moving every
        judgement stage with it."""
        seats = {stage.key: stage.role for stage in stage_models.STAGES}
        self.assertEqual(seats["decide-skipper"], stage_models.DECIDE)
        self.assertNotEqual(seats["decide-skipper"], stage_models.DEFAULT_ROLE)

    def test_a_stage_with_a_delegate_is_named_for_the_crew_member_who_runs_it(self) -> None:
        """The rule the keys encode: `purpose-crew` where the stage is sent away, the work alone where it
        stays on the host. It is the only part of the table a person editing `models.json` can see."""
        crew = {"lookout", "quartermaster", "shipwright", "navigator", "mate", "privateer", "shipworm",
                "skipper", "hand", "bosun"}
        for stage in stage_models.STAGES:
            with self.subTest(stage=stage.key):
                named = stage.key.rsplit("-", 1)[-1] in crew
                self.assertEqual(named, stage.delegable,
                                 "a crew-named stage has a delegate and a work-named one does not")

    def test_every_copy_of_the_rename_table_says_the_same_thing(self) -> None:
        """Three copies: the keel's, and one in each project-side script, which run where no keel is
        installed and so cannot import it. A drift here reads a migrated project's table as a typo."""
        for path in (CHECKER, BENCHMARK):
            with self.subTest(script=path.name):
                found = re.search(r"RENAMED = \{(.*?)\n\}", path.read_text(encoding="utf-8"), re.S)
                if found is None:
                    self.fail(f"{path} no longer declares RENAMED as a literal dict")
                pairs = dict(re.findall(r'"([^"]+)": "([^"]+)"', found.group(1)))
                self.assertEqual(pairs, stage_models.RENAMED)


class GitignoreTest(unittest.TestCase):
    def test_the_canonical_slots_are_the_spec_kit_files_a_slice_fills(self) -> None:
        self.assertIn("plan.md", gitignore.CANONICAL_SLOTS)
        self.assertIn("tasks.md", gitignore.CANONICAL_SLOTS)

    def test_every_harness_directory_is_projected_from_the_registry_and_not_a_fixed_list(self) -> None:
        """A harness added to the registry must not need an edit here to have its directory ignored."""
        self.assertEqual(gitignore.harness_directories({}), [])
        self.assertTrue(gitignore.projection_artifacts().strip())


class FrontendTest(unittest.TestCase):
    def test_a_browser_app_with_no_feature_still_gets_a_manifest(self) -> None:
        written = frontend.web_package_json('{"name": "web", "dependencies": {}}', set(), "react-vite")
        self.assertIn("web", written)

    def test_a_feature_adds_to_the_manifest_and_to_the_lock_suffix(self) -> None:
        """The two move together: a dependency in one and not the other is an install that drifts. Both are the
        frontend's own rows (`frontends.<name>.features`), so they cannot be written down apart."""
        features = set(frontend.web_lock_features("react-vite")[:1])
        self.assertTrue(features)
        self.assertNotEqual(frontend.web_lock_suffix(features, "react-vite"),
                            frontend.web_lock_suffix(set(), "react-vite"))
        written = frontend.web_package_json('{"name": "web", "dependencies": {}}', features, "react-vite")
        self.assertIn("react-oidc-context", written)


class BiomeTest(unittest.TestCase):
    def test_the_version_is_a_placeholder_the_workspace_answer_fills_in(self) -> None:
        """The keel does not pin the formatter; the language package that answers the workspace does."""
        self.assertTrue(biome.VERSION.startswith("__") and biome.VERSION.endswith("__"))

    def test_a_project_with_no_application_gets_no_formatter_files(self) -> None:
        self.assertEqual(biome.biome_files([]), {})


class EventModelTest(unittest.TestCase):
    def test_the_model_page_url_is_built_from_the_project_name(self) -> None:
        self.assertIn("demo", event_model.event_model_page_url("demo"))

    def test_the_workflow_calls_the_make_it_is_given(self) -> None:
        """An adopted repository may drive its gate with something other than `make`."""
        self.assertIn("just", event_model.event_model_workflow("just"))

class RenameReadingTest(unittest.TestCase):
    """A table and a benchmark record written before a stage's name said who runs it.

    The rename is ours and the files are theirs: `.specify/models.json` is hand-edited and versioned with
    the project, and `benchmark.json` is a record of runs that already happened. Neither may be made wrong
    by a word we changed, so both are read under either name and say which one answered.
    """

    def script(self, path: Path):  # noqa: ANN201 - a module loaded from a path, by design
        spec = importlib.util.spec_from_file_location(f"probe_{path.stem}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_a_table_still_keyed_by_the_old_name_is_read_and_says_so(self) -> None:
        models = self.script(CHECKER)
        role, said = models.role_of("implement-shipwright", {"stages": {"default": "strong", "implement": "fast"}})
        self.assertEqual(role, "fast")
        self.assertIn("`implement` row", said)

    def test_the_old_name_typed_from_memory_finds_the_row_that_is_there(self) -> None:
        models = self.script(CHECKER)
        role, said = models.role_of("implement", {"stages": {"default": "strong", "implement-shipwright": "fast"}})
        self.assertEqual(role, "fast")
        self.assertIn("before the rename", said)

    def test_setting_a_stage_by_its_old_name_leaves_one_row_and_not_two(self) -> None:
        """Two rows for one stage is a table whose next reader has to know which of them wins."""
        models = self.script(CHECKER)
        table = {"stages": {"default": "strong", "implement": "fast"}}
        models.assign(table, {}, "implement=strong")
        self.assertEqual(table["stages"], {"default": "strong", "implement-shipwright": "strong"})

    def test_a_record_written_before_the_rename_counts_as_the_stage_it_was(self) -> None:
        benchmark = self.script(BENCHMARK)
        self.assertEqual(benchmark.canonical("converge"), "converge-navigator")
        self.assertEqual(benchmark.order("converge"), benchmark.order("converge-navigator"))
        self.assertLess(benchmark.order("implement"), benchmark.order("mutation-shipworm"))

if __name__ == "__main__":  # pragma: no cover
    unittest.main()
