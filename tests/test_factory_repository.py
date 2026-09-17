"""The factory's own repository: the shape its source has to keep, what it publishes, what it won't commit.

The factory is held to the rules it writes into every project it generates, so the gate that enforces its
own structure is proved here the same way the generated gates are: by handing it the violation it exists to
catch and checking it says which one it found.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG
from slipwai.features import known_features


class FactoryRepositoryTest(FactoryTestCase):
    def structure_gate(self, edit) -> tuple[int, str]:
        """Run `check-structure.py` over a copy of the source, after `edit` has had its way with it.

        A copy rather than the checkout, because the whole point is to introduce a violation, and a gate
        proved by breaking the repository it guards is a gate that leaves the repository broken.
        """
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            shutil.copytree(ROOT / "src", copy / "src")
            (copy / "scripts").mkdir()
            shutil.copy(ROOT / "scripts/check-structure.py", copy / "scripts/check-structure.py")
            edit(copy / "src/slipwai")
            result = subprocess.run(
                ["python3", "scripts/check-structure.py"],
                cwd=copy,
                text=True,
                capture_output=True,
            )
            return result.returncode, result.stdout + result.stderr

    def test_the_factorys_own_source_keeps_the_shape_it_claims(self) -> None:
        code, output = self.structure_gate(lambda _package: None)
        self.assertEqual(code, 0, output)
        self.assertIn("no upward imports and no cycles", output)

    def test_the_structure_gate_rejects_an_import_against_the_direction(self) -> None:
        # `selection` is what almost every part of a generated repository reads. The day it reads one of
        # them back, the thing everything depends on depends on everything, and the tiers mean nothing.
        def add_upward_import(package: Path) -> None:
            path = package / "selection.py"
            path.write_text(
                path.read_text().replace(
                    "from .errors import GenerationError",
                    "from .errors import GenerationError\nfrom .project.makefile import makefile",
                )
            )

        code, output = self.structure_gate(add_upward_import)
        self.assertEqual(code, 1, output)
        self.assertIn("answers imports parts", output)
        self.assertIn("selection -> project.makefile", output)

    def test_the_structure_gate_rejects_an_import_cycle(self) -> None:
        def close_a_cycle(package: Path) -> None:
            path = package / "project/compose.py"
            path.write_text(
                "from .backing_services import backing_service_files  # noqa: F401\n" + path.read_text()
            )

        code, output = self.structure_gate(close_a_cycle)
        self.assertEqual(code, 1, output)
        self.assertIn("import cycle:", output)
        self.assertIn("project.compose", output)

    def test_the_structure_gate_rejects_a_module_that_outgrew_its_budget(self) -> None:
        # The state this package was split out of: one file too long for anybody to read end to end.
        def grow_a_module(package: Path) -> None:
            path = package / "project/compose.py"
            path.write_text(path.read_text() + "\n# padding\n" * 400)

        code, output = self.structure_gate(grow_a_module)
        self.assertEqual(code, 1, output)
        self.assertIn("over the 350-line budget", output)

    def test_the_structure_gate_rejects_logic_hidden_in_a_package_facade(self) -> None:
        def fatten_the_facade(package: Path) -> None:
            path = package / "project/languages/__init__.py"
            path.write_text(path.read_text() + "\n\n" + "\n".join(f"# line {n}" for n in range(60)))

        code, output = self.structure_gate(fatten_the_facade)
        self.assertEqual(code, 1, output)
        self.assertIn("package facade", output)

    def test_the_structure_gate_rejects_a_module_that_does_not_say_what_it_is(self) -> None:
        def drop_the_docstring(package: Path) -> None:
            path = package / "project/gitignore.py"
            body = path.read_text()
            path.write_text(body[body.index('"""', body.index('"""') + 3) + 3 :].lstrip("\n"))

        code, output = self.structure_gate(drop_the_docstring)
        self.assertEqual(code, 1, output)
        self.assertIn("no module docstring", output)

    def test_a_family_question_is_never_asked_of_a_backend_key(self) -> None:
        """`language` throughout this package is a *backend* key, and families are what have properties.

        The two coincide only while every family has one member — a backend is named for its language right
        up until a sibling framework arrives — so `language == "typescript"` reads correctly today and
        silently means the wrong thing the moment `typescript-nest` exists beside `typescript`. The failure
        is quiet, which is what makes it worth a gate: a generated project would install and audit the same
        npm workspace twice, or lose the Go mutation note, with every test still green.

        So a comparison against a family name has to go through `family_of`. This is the rule
        `frontend.py`, `readme.py` and `toolkit.py` already follow; the gate is what stops the next call
        site from being written the other way.
        """
        families = set(CATALOG["backends"]) | {backend["family"] for backend in CATALOG["backends"].values()}
        offenders: list[str] = []
        for path in sorted((ROOT / "src/slipwai").rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name):
                    continue
                if node.left.id not in {"language", "backend", "backend_language"}:
                    continue
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and comparator.value in families:
                        relative = path.relative_to(ROOT).as_posix()
                        offenders.append(
                            f"{relative}:{node.lineno}: {node.left.id} == {comparator.value!r}"
                        )
        self.assertEqual(
            [],
            offenders,
            "these compare a backend key against a language family name, which stops being the same "
            "question when a family gains a second framework — ask `family_of(...)` instead:\n  "
            + "\n  ".join(offenders),
        )

    def test_an_option_s_feature_is_never_branched_on_by_name(self) -> None:
        """"Needs a container, migrations, a suite outside the gate" is a *trait*, not the string `postgres`.

        It used to be the string. `selection.has("postgres")` was tested in twelve places across nine
        modules — the Makefile's variables and its migrate target, the CI job, the README, the gates page,
        AGENTS.md, the agent permissions, the vitest exclusion, the npm and pip dependency sets — so a
        second container-backed store meant writing a twin of every one of them, and a third meant a
        triplet. Worse, a half-written twin generates a project whose `make test-integration` silently
        tests nothing. `keycloak`, `sqlite` and `fastify` were the same defect one axis over, three
        branches each.

        So the options declare their traits in `catalog.json`, every site reads them through `Selection`,
        and what is genuinely per-feature — prose about a product, the pins it adds, the files it owns — is
        a table keyed by the feature and looked up with `feature_of(axis)`. An option's feature may still
        be a *key*; that is exactly the right shape. What it may never be again is the thing a branch tests
        for, because that is the shape that has to be copied.
        """
        declaring = known_features(CATALOG)
        self.assertTrue(declaring, "no option owns a feature, so this gate would prove nothing")
        offenders: list[str] = []
        for path in sorted((ROOT / "src/slipwai").rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            for node in ast.walk(ast.parse(path.read_text())):
                # An option name reaching a call — `selection.has("postgres")` — or either side of a
                # comparison. A name in a dict key, a tuple of feature names or a comment is data.
                if isinstance(node, ast.Call):
                    named = [*node.args, *(keyword.value for keyword in node.keywords)]
                elif isinstance(node, ast.Compare):
                    named = [node.left, *node.comparators]
                else:
                    continue
                for argument in named:
                    if isinstance(argument, ast.Constant) and argument.value in declaring:
                        offenders.append(f"{relative}:{node.lineno}: {argument.value!r}")
        self.assertEqual(
            [],
            offenders,
            "these branch on the name of an option's feature, which is the defect that made adding a "
            "second option a twin of every one of them — read a trait off the selection, or look the "
            "feature up in a table keyed by it:\n  " + "\n  ".join(offenders),
        )

    def test_every_asset_is_text_because_the_pipeline_can_carry_nothing_else(self) -> None:
        """`asset_tree` reads with `read_text` and `write_project` writes with `write_text`.

        So the whole of `assets/` has to be decodable text, and that is a property worth a gate rather than
        a habit: a committed binary would not fail at review, it would fail at `./slipwai generate` with a
        `UnicodeDecodeError` naming a file nobody was thinking about.

        It is also a real constraint on what a backend can ship, and one that reads as an option until you
        try it. A build wrapper is the case that matters — `gradlew` and `mvnw` are shell scripts that
        cannot run without a `.jar` beside them — so an ecosystem whose convention is "commit the wrapper"
        cannot have that convention honoured here, and its generated projects have to take the build tool
        from the PATH and the CI image instead. `.claude/skills/add-language/` says so where it asks about
        executables, and this is what keeps that true; `adopt`'s Gradle Wrapper jar is base64 text for it.
        """
        binaries: list[str] = []
        for path in sorted((ROOT / "assets").rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                path.read_text()
            except UnicodeDecodeError:
                binaries.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(
            [],
            binaries,
            "these assets are not decodable text, so `./slipwai generate` cannot emit them at all:\n  "
            + "\n  ".join(binaries),
        )

    def test_the_factorys_own_gate_runs_the_same_checks_ci_does(self) -> None:
        """`make verify` locally and CI run the same targets, which is the rule the factory generates.

        A gate that exists only in the Makefile passes locally and never runs; one that exists only in the
        workflow cannot be run before pushing. Both read the same targets — CI as slices, in parallel jobs.
        """
        makefile = (ROOT / "Makefile").read_text()
        verify = next(
            line for line in makefile.splitlines() if line.startswith("verify:")
        )
        for gate in ("lint", "typecheck", "check-structure", "test"):
            self.assertIn(gate, verify, f"`make verify` no longer runs {gate}")
            self.assertRegex(makefile, rf"(?m)^{gate}:.*##", f"{gate} is not a documented target")
        # CI runs the same four targets, as parallel slices of `make test` — every suite named once across
        # the jobs, and the ones that generate whole projects kept out of `checks`.
        workflow = (ROOT / ".github/workflows/verify.yml").read_text()
        for gate in ("make lint", "make typecheck", "make check-structure", "make test"):
            self.assertIn(gate, workflow, f"CI no longer runs {gate}")
        whole = ("test_matrix test_add_service test_aws_target test_aws_stack test_azure_target "
                 "test_azure_stack test_auth0_identity test_images test_launcher")
        self.assertIn(f'SKIP="{whole}"', workflow)
        for suite in whole.split():
            self.assertRegex(workflow, rf'TESTS="?[^"\n]*\b{suite}\b', f"{suite} runs in no job")
        # The image suite rides in the matrix jobs, sliced by the same variable: five builds beside each other.
        self.assertIn('TESTS="test_matrix test_images"', workflow)
        # And both suites there read their backends from that slice alone; `test_monorepos` holds them to it.

    def test_the_snapshot_is_published_only_when_every_gate_is_green(self) -> None:
        """The `snapshot` job packages `main` and publishes it — after every other job, on a push to `main`
        alone, and through the two scripts the suite gates. A job that ran beside the gates would publish a
        red main; one triggered from another workflow would depend on an event this forge may never send."""
        workflow = (ROOT / ".github/workflows/verify.yml").read_text()
        jobs = re.findall(r"(?m)^  ([a-z0-9-]+):$", workflow[workflow.index("\njobs:"):])
        self.assertIn("snapshot", jobs)
        # Dispatched in file order, so the longest job is written first and the run is not its wait plus it.
        self.assertEqual(jobs[0], "aws", "the longest job is no longer dispatched first")
        # And nothing queues behind a warm-up job: the toolchains are in the job image, so there is nothing
        # to warm and every job but `snapshot` starts at once.
        self.assertNotIn("needs: toolchains", workflow)
        snapshot = workflow[workflow.index("\n  snapshot:"):workflow.index("\n  release:")]
        needs = re.search(r"needs: \[([^\]]*)\]", snapshot)
        assert needs is not None, "the snapshot job needs nothing, so it would publish a red main"
        self.assertEqual(
            sorted(name.strip() for name in needs.group(1).split(",")),
            sorted(job for job in jobs if job not in ("snapshot", "release")),
        )
        publishing = "github.server_url == 'https://git.treyco.dev' && github.event_name == 'push'"
        self.assertIn(f"if: {publishing} && github.ref == 'refs/heads/main'", snapshot)
        self.assertIn("fetch-depth: 0", snapshot)
        for step in ("scripts/snapshot-version.py --write", "make package-executable", "make publish-wheel",
                     "scripts/publish-release.py", "--snapshot", "--commit"):
            self.assertIn(step, snapshot, f"the snapshot job no longer runs {step}")

    def test_the_ci_matrix_names_every_backend_the_catalog_has(self) -> None:
        """The matrix suite runs one CI job per backend, sliced with `FACTORY_BACKENDS`. The list of backends
        in the workflow is a copy of the catalog's, and a backend missing from it is a backend CI never gates
        — silently, because every other job stays green. Adding a language is one word here."""
        workflow = (ROOT / ".github/workflows/verify.yml").read_text()
        match = re.search(r"^\s+backend: \[([^\]]*)\]", workflow, re.MULTILINE)
        assert match is not None, "verify.yml has no `backend: [...]` matrix"
        listed = [name.strip() for name in match.group(1).split(",")]
        self.assertEqual(listed, list(CATALOG["backends"]))
        self.assertIn("FACTORY_BACKENDS: ${{ matrix.backend }}", workflow)
        # Every job checks its toolchains through the one composite action; what that action may contain,
        # and what the job image has to provide, is `tests/test_ci_image.py`.
        self.assertEqual(workflow.count("uses: ./.github/actions/toolchains"), workflow.count("runs-on:"))

    def test_the_wheel_bundles_exactly_what_the_package_reads_from_the_root(self) -> None:
        """`assets.py` resolves `assets/`, `catalog.json` and `VERSION` from the checkout root — and
        `catch_up.py` resolves `CHANGELOG.md` and `changelog.d/` from it — or from `slipwai/_bundle/` when
        installed. pyproject's `force-include` is what puts them there, so the two lists are one fact in two
        files: a sixth root path the package started reading would install fine and fail on the first project,
        which is the failure `make test-wheel` exists to catch before a release."""
        import tomllib

        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        bundled = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
        self.assertEqual(
            bundled,
            {
                "assets": "slipwai/_bundle/assets",
                "catalog.json": "slipwai/_bundle/catalog.json",
                "VERSION": "slipwai/_bundle/VERSION",
                "CHANGELOG.md": "slipwai/_bundle/CHANGELOG.md",
                "changelog.d": "slipwai/_bundle/changelog.d",
            },
        )
        self.assertEqual(pyproject["project"]["scripts"], {"slipwai": "slipwai.cli:main"})
        self.assertEqual(pyproject["tool"]["hatch"]["version"]["path"], "VERSION")
        # The build backend is pinned twice — for `pip install .` and for `make wheel` — to the same version.
        (backend,) = pyproject["build-system"]["requires"]
        self.assertIn(backend, (ROOT / "requirements-publish.txt").read_text().splitlines())
        # The tag is verify.yml's trigger now, and these two are dispatch-only retries behind it; the gate
        # that keeps them that way is `tests/test_publish_release.py`.
        publish = (ROOT / ".github/workflows/publish-package.yml").read_text()
        self.assertIn("make test-wheel", publish)
        self.assertIn("make publish-wheel", publish)

    def test_the_pinned_tooling_matches_what_a_generated_project_is_given(self) -> None:
        """The factory is not checked by a looser tool than the one it hands its own output."""
        from slipwai.project.languages.python import requirements
        from slipwai.selection import Selection

        runtime, development = requirements(Selection({}))
        generated = dict(
            pin.split("==", 1) for pin in runtime + development if "==" in pin
        )
        factory = dict(
            line.split("==", 1)
            for line in (ROOT / "requirements-dev.txt").read_text().splitlines()
            if "==" in line
        )
        self.assertEqual(
            factory.get("ruff"),
            generated.get("ruff"),
            "the factory and the projects it generates must be linted by the same ruff",
        )

    def test_gitea_publisher_has_the_exact_canonical_scope(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/publish-to-gitea.py", "--list"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        self.assertEqual(result.stdout.splitlines(), ["slipwai"])

    def test_no_derived_starter_copies_are_committed(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "starters"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout
        self.assertEqual(tracked, "", "starters are derived artifacts; materialize them with `make starters`")
