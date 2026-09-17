"""A backend's walking skeleton is an asset, not a string literal in the generator.

`assets/` is the single source for everything generated — the claim the README opens with. A skeleton file
inlined in code is that claim being false in the one place hardest to notice, because the file still
appears in the output and only the *editing* of it moved somewhere else. These tests read the asset tree
and require the generated project to match it, so a skeleton that stops coming from disk stops passing.
"""
from __future__ import annotations

import re
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import LANGUAGE_ROOT, asset_tree
from slipwai.catalog import CATALOG
from slipwai.project.languages import BACKENDS, language_files
from slipwai.project.languages.go import go_language_version
from slipwai.selection import Selection
from slipwai.services import default_apps

# The skeleton files that carry a name derived from the project, and so cannot be compared byte for byte.
# Everything else in a language's `app/` tree must arrive exactly as committed.
RENAMED = {
    "typescript": {"package.json"},
    "python": {"pyproject.toml", "src/delivery_starter/__init__.py", "tests/test_health.py"},
    "go": set(),
    # Every Java file names its package, so all of them are rewritten; the pom carries the artifact id and
    # the analysed package, and `application.properties` is cut down by the pruner on the way out. The
    # family's own tree — the wrapper, the analyser configurations — carries no project name and so is
    # compared byte for byte, which is the point of it being shared.
    "java-quarkus": {
        "pom.xml",
        "src/main/resources/application.properties",
        "src/main/java/com/example/deliverystarter/health/HealthStatus.java",
        "src/test/java/com/example/deliverystarter/health/HealthStatusTest.java",
    },
    "java-spring": {
        "pom.xml",
        "src/main/resources/application.properties",
        "src/main/java/com/example/deliverystarter/ServiceApplication.java",
        "src/main/java/com/example/deliverystarter/health/HealthStatus.java",
        "src/test/java/com/example/deliverystarter/health/HealthStatusTest.java",
    },
}

# Trees a backend's skeleton is assembled from, beyond its own `<backend>/app`. A framework-owning backend
# reads its language family's shared build material too — the Maven wrapper and the three analyser
# configurations are the same files whichever framework owns startup — and those files have to arrive in
# the generated project exactly as committed just as much as the backend's own do. Without this the test
# would silently stop checking the wrapper the moment it moved out of `<backend>/app`, which is precisely
# when a lost `chmod +x` or a flattened `mvnw.cmd` would go unnoticed.
SHARED_SKELETONS = {
    "java-quarkus": ("java/build",),
    "java-spring": ("java/build",),
}


def landed_at(relative: str, project_name: str) -> str:
    """Where a committed skeleton file ends up once the project has been named.

    A backend may move the *path* and not only the contents — a Python package directory is named after
    the project. Spelled here rather than inline in one test, so a backend whose layout does the same is
    covered by stating its rename instead of being quietly skipped by a loop that only knows Python's.

    Java does the same thing with a different spelling, and that difference is the reason this function
    exists rather than one `replace` inline: the ecosystem drops the separators in a package segment
    (`delivery-starter` is `deliverystarter`) where Python replaces them with underscores.
    """
    return relative.replace(
        "delivery_starter", re.sub(r"[^a-z0-9_]", "_", project_name)
    ).replace("deliverystarter", re.sub(r"[^a-z0-9]", "", project_name))


class LanguageSkeletonsTest(FactoryTestCase):
    def test_every_skeleton_asset_reaches_the_generated_project_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for language in CATALOG["backends"]:
                skeleton = asset_tree(LANGUAGE_ROOT / f"{language}/app")
                self.assertTrue(skeleton, f"{language} has no committed skeleton")
                for shared in SHARED_SKELETONS.get(language, ()):
                    tree = asset_tree(LANGUAGE_ROOT / shared)
                    self.assertTrue(tree, f"{shared} has no committed files")
                    # The backend's own tree wins on a clash, exactly as `service_files` merges them.
                    skeleton = {**tree, **skeleton}
                name = f"skeleton-{language}"
                repo = self.generate(directory, name, language=language)
                for relative, content in skeleton.items():
                    expected = landed_at(relative, name)
                    landed = repo / "apps/service" / expected
                    self.assertTrue(landed.is_file(), f"{language}: {expected} never reached the project")
                    if relative not in RENAMED[language]:
                        # Bytes, not `read_text()`. Universal-newline translation on either side of this
                        # comparison would hide the one difference it cannot afford to hide: `mvnw.cmd` is
                        # CRLF throughout and is a batch/PowerShell polyglot that re-reads itself with
                        # `Get-Content -Raw`, so a pipeline that flattened it would still pass a
                        # character-level check and ship a script Windows cannot run.
                        self.assertEqual(
                            landed.read_bytes(),
                            content.encode(),
                            f"{language}: {relative} was rewritten on the way out; it should be copied",
                        )

    def test_a_renamed_skeleton_file_still_comes_from_its_asset(self) -> None:
        """The files that do get rewritten are rewritten *from* the asset, not written afresh.

        Python's manifest is rewritten twice over: the two names, and the two dependency arrays the
        selection fills in. Empty those arrays again and what is left has to be the committed asset,
        line for line — including every word of prose above the settings, which is the half that would
        quietly stop being editable if the file were assembled in code instead.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "renamed-skeleton", language="python")
            committed = (LANGUAGE_ROOT / "python/app/pyproject.toml").read_text()
            generated = (repo / "apps/service/pyproject.toml").read_text()
            emptied = re.sub(r'\[\n(?:  "[^"]+",\n)+\]', "[]", generated)
            self.assertEqual(
                emptied,
                committed.replace('name = "delivery-starter"', 'name = "renamed-skeleton-service"').replace(
                    "delivery_starter", "renamed_skeleton"
                ),
            )

    def test_the_event_port_arrives_only_where_no_event_store_adapter_does(self) -> None:
        """The port with nothing behind it is for a backend whose event-store axis offers nothing yet.

        Unreachable from the command line while every language has the in-memory adapter, so it is asked
        for directly — and it has to stay unreachable, because the port arriving *beside* a real adapter
        would define it twice.
        """
        for language in ("python", "go"):
            port = asset_tree(LANGUAGE_ROOT / f"{language}/event-port")
            self.assertTrue(port, f"{language} has no committed event port")
            unoffered = language_files("probe", True, default_apps(language, "none", Selection({})))
            answered = language_files(
                "probe", True, default_apps(language, "none", Selection({"event-store": "memory"}))
            )
            for relative, content in port.items():
                expected = f"apps/service/{landed_at(relative, 'probe')}"
                self.assertIn(expected, unoffered, f"{language}: {relative} is not emitted as the fallback")
                self.assertEqual(
                    unoffered[expected],
                    content.replace("delivery_starter", "probe"),
                    f"{language}: {relative} does not match its asset",
                )
            store = {
                path
                for path in answered
                if path.endswith(("events.py", "events.go")) and "adapters" not in path
            }
            for path in store:
                self.assertNotEqual(
                    answered[path],
                    unoffered.get(path),
                    f"{language}: {path} is the placeholder even though an adapter was selected",
                )

    def test_each_language_reads_its_skeleton_rather_than_listing_it(self) -> None:
        """The tree is read, so adding a file to a starter is an edit under `assets/` and nothing else.

        Asserted against the source because that is where the property lives: a module that enumerated its
        skeleton would still produce a correct project today and quietly require a code change tomorrow.

        The module is found through the `BACKENDS` dispatch rather than by spelling
        `languages/<backend>.py`, because a backend key is not always a module name. The naming rule this
        factory adopted for a framework-owning backend produces keys like `java-quarkus`, and a hyphen
        cannot appear in a Python module name — so a guessed filename would fail here for a reason that has
        nothing to do with the skeleton, on the very first backend named for its framework. The dispatch
        already holds the mapping; asking it is both correct and one fewer thing to keep in step.
        """
        for language in CATALOG["backends"]:
            module_file = BACKENDS[language].__file__
            assert module_file is not None
            module_path = Path(module_file)
            self.assertTrue(
                module_path.is_file(), f"{language} dispatches to a module with no file on disk"
            )
            self.assertIn(
                f'asset_tree(LANGUAGE_ROOT / "{language}/app")',
                module_path.read_text(),
                f"{module_path.name} no longer reads its skeleton from the asset tree",
            )

    def test_every_committed_go_module_asks_for_one_language_version(self) -> None:
        """One `go` directive across every committed module, because `go.work` can only pin one.

        `repository_files` writes the workspace from the *first* service's `go.mod`
        (`go_language_version`). A project with two Go services whose event-store answers differ therefore
        pinned the workspace at whatever the first one happened to say — and the base module said `go 1.22`
        while the sqlite and postgres modules, raised by `go mod tidy` for their dependencies, said
        `go 1.25.0`. A workspace pinned below a module it uses is a workspace that refuses to build, and
        nothing in the gate generated that combination.
        """
        modules = sorted(LANGUAGE_ROOT.rglob("go.mod"))
        self.assertTrue(modules, "no committed Go module found under assets/languages/")
        versions = {
            module.relative_to(LANGUAGE_ROOT).as_posix(): go_language_version(module.read_text())
            for module in modules
        }
        self.assertEqual(
            1,
            len(set(versions.values())),
            "every committed go.mod must ask for the same language version, or `go.work` pins one of "
            f"them below a module it uses: {versions}",
        )

    def test_every_committed_go_module_pins_the_gate_s_third_analyser(self) -> None:
        """staticcheck is a `tool` dependency of every variant, not a binary somebody installs.

        `go vet` is deliberately narrow, which leaves a large class of real findings to a second analyser;
        a `tool` directive is how this ecosystem pins one, so `go mod download` fetches it with everything
        else and `go tool staticcheck ./...` runs it offline from the module cache. Per variant rather than
        once, because each committed module is a whole dependency set and `go build` refuses a `go.sum`
        that disagrees with its `go.mod`.
        """
        modules = sorted(LANGUAGE_ROOT.rglob("go.mod"))
        for module in modules:
            text = module.read_text()
            self.assertIn(
                "tool honnef.co/go/tools/cmd/staticcheck", text, module.relative_to(LANGUAGE_ROOT)
            )
            self.assertIn("honnef.co/go/tools v", text, module.relative_to(LANGUAGE_ROOT))
            checksums = module.with_name("go.sum")
            self.assertTrue(checksums.is_file(), f"{module.relative_to(LANGUAGE_ROOT)} has no go.sum")
            self.assertIn("honnef.co/go/tools", checksums.read_text())

    def test_every_committed_manifest_is_well_formed(self) -> None:
        """A manifest the build tool cannot parse fails a generated project before its first compile.

        Asserted here rather than left to `make verify`, because the failure this catches is one prose
        causes: XML forbids `--` anywhere inside a comment, so a perfectly reasonable sentence mentioning a
        `--flag` in an explanatory comment makes Maven refuse the whole POM. The message it gives names a
        column rather than the rule, and nothing else in this repository would notice.
        """
        for manifest in sorted(LANGUAGE_ROOT.rglob("*.xml")):
            with self.subTest(manifest=str(manifest.relative_to(LANGUAGE_ROOT))):
                try:
                    ElementTree.fromstring(manifest.read_text())
                except ElementTree.ParseError as failure:
                    self.fail(f"{manifest.relative_to(LANGUAGE_ROOT)} is not well-formed XML: {failure}")
