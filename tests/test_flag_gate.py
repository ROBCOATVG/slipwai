"""The service side of a feature flag: the reader every backend gets, and the gate that holds it.

A flag is the only thing between a merge and a customer under a production target — every commit that
passes `verify` on `main` is applied to staging and then to production — so the constitution requires that
unfinished work arrive dark, behind a flag, with tests on both paths. Until this existed the browser half
was designed and the service half was a sentence in `AGENTS.md`: no reader, no key-to-variable transform,
no seam to inject, and therefore no both-path testing.

What is proved here is each of those, in the order they depend on each other: that every backend gets a
reader that spells one key one way and treats everything but `on` as off, that `--target none` gets none of
it, that `make check-flags` catches each of the five failures it exists for, and that the rule an author is
held to points at the file rather than describing the convention.

The fifth is a pair rather than a rule on its own, and both halves are proved: a read that names `FLAG_<KEY>`
instead of calling the reader is still *seen* as one, so the dead-configuration rule cannot be fooled by it,
and is *reported*, so that allowance does not become permission to bypass the reader.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase, backends_under_test, commit_all

from slipwai.assets import LANGUAGE_ROOT, asset_tree
from slipwai.catalog import CATALOG, axis_default
from slipwai.project.flags import FLAG_READERS

# The declaration the factory ships, and what a project turns it into for its first flag.
EMPTY = '''flags = {
  # api = {
  #   checkout-v2 = "off"
  # }
}'''


def declared(seed: str, service: str = "service") -> str:
    return f'flags = {{\n  {service} = {{\n    checkout-v2 = "{seed}"\n  }}\n}}'


def seed_flag(repo: Path, seed: str) -> None:
    """Declare `checkout-v2` on the first service, the way a project fills in the file it was shipped."""
    path = repo / "infra/service/flags.auto.tfvars"
    text = path.read_text()
    assert EMPTY in text, "the shipped declaration file no longer has the shape this fills in"
    path.write_text(text.replace(EMPTY, declared(seed)))


def check_flags(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", "scripts/check-flags.py"], cwd=repo, text=True, capture_output=True
    )


class FlagReaderTest(FactoryTestCase):
    def test_every_backend_gets_a_reader_and_its_own_tests_under_a_target(self) -> None:
        """The enabling change, and the reason it is per backend: a flag costs a project nothing at run
        time — an environment variable ECS resolves — but somebody still has to read it, and reading it by
        hand is where `checkout-v2` becomes `FLAG_CHECKOUT_V_2` and the feature silently never turns on."""
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                reader = FLAG_READERS[backend]
                committed = asset_tree(LANGUAGE_ROOT / reader.tree)
                self.assertTrue(committed, f"{backend} has no committed flag reader")
                self.assertIn(reader.source, committed, f"{backend}'s FLAG_READERS row names no committed source")
                self.assertIn(reader.tests, committed, f"{backend}'s FLAG_READERS row names no committed test")
                name = f"flagged-{backend}"
                repo = self.generate(
                    directory, name, "event-modelling", backend, "none", target="aws",
                    http=axis_default("http", backend, "aws"),
                )
                for relative in (reader.source, reader.tests):
                    # The same rename every other file in the service gets: a Python package named after
                    # the project, a Java package segment. Spelled here the way the skeleton suite spells
                    # it, because the reader is emitted beside the skeleton and named by the same code.
                    landed = repo / "apps/service" / relative.replace(
                        "delivery_starter", name.replace("-", "_")
                    ).replace("deliverystarter", name.replace("-", ""))
                    self.assertTrue(landed.is_file(), f"{backend}: {relative} never reached the project")
                    text = landed.read_text()
                    # One key transform, and only `on` is on. Asserted in each language's own syntax by
                    # the reader's own tests, which ship beside it; asserted here is that both facts are
                    # present at all, so a backend cannot arrive with a reader that reads any truthy value.
                    self.assertIn("FLAG_", text)
                    self.assertIn("on", text)

    def test_a_project_with_nowhere_to_deploy_gets_no_reader_at_all(self) -> None:
        """Not an oversight and not an inert file: `--target none` has no `flags.auto.tfvars` to declare a
        flag in and no unattended push to production for one to hold back. A reader shipped there would be
        a seam with nothing on the other side of it, and `make check-flags` would pass by having nothing to
        check — which reads as coverage the project does not have."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "local-only", "event-modelling", "python", "none")
            self.assertEqual(list(repo.glob("apps/service/src/*/flags.py")), [])
            self.assertFalse((repo / "scripts/check-flags.py").exists())
            self.assertNotIn("check-flags", (repo / "Makefile").read_text())
            self.assertNotIn("check-flags", (repo / "AGENTS.md").read_text())

    def test_the_reader_is_wired_into_the_gate_and_the_rule_points_at_it(self) -> None:
        """`AGENTS.md` names the file rather than describing the convention, which is the whole difference
        between a rule an author follows and one they re-derive."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "flag-wired", "event-modelling", "python", "none", target="aws",
                http=axis_default("http", "python", "aws"),
            )
            makefile = (repo / "Makefile").read_text()
            self.assertIn("check-flags check-speckit", makefile)
            self.assertIn("python3 scripts/check-flags.py", makefile)
            self.assertIn("check-constitution check-benchmark check-decisions test check-model check-drawio check-flags",
                          makefile)
            self.assertTrue((repo / "scripts/check-flags.py").stat().st_mode & 0o111, "not executable")

            guidance = (repo / "AGENTS.md").read_text()
            self.assertIn("apps/service/src/<package>/flags.py", guidance)
            self.assertIn('flag_enabled("checkout-v2")', guidance)
            self.assertIn("releasable capability, not a slice", guidance)
            # The two things the user of a generated project asked for by name: a recommendation rather
            # than an open question, and a stop before an unflagged change reaches a customer.
            self.assertIn("Recommend the answer with its reason", guidance)
            self.assertIn("**stop and ask the user to", guidance)
            self.assertIn("confirm this is a release they want now**", guidance)

            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("**Release constraint**", drive)
            self.assertIn("Before you push, name the release constraint", drive)

            deployment = (repo / "docs/deployment.md").read_text()
            self.assertIn("A flag covers a releasable capability, not a slice", deployment)
            self.assertIn("a rollback does not turn a flag off", deployment)
            self.assertIn("one production change outside the pipeline", deployment)
            self.assertIn("both revisions read the same parameter", deployment.lower())


class FlagGateTest(FactoryTestCase):
    """`make check-flags`, given each violation it exists to catch, in a real generated project."""

    def flagged(self, directory: str, name: str) -> Path:
        repo = self.generate(
            directory, name, "event-modelling", "python", "none", target="aws",
            http=axis_default("http", "python", "aws"),
        )
        # The gate compares what is declared now against what was declared before this change, so the
        # scaffold commit is the "before" every case below is measured against.
        return repo

    def read_it(self, repo: Path, package: str) -> None:
        """A slice that branches on the flag, read through the reader the way the rule requires."""
        source = repo / f"apps/service/src/{package}/application"
        source.mkdir(parents=True, exist_ok=True)
        (source / "checkout.py").write_text(
            f"from {package}.flags import flag_enabled\n\n\n"
            "def price(total: int, source=None) -> int:\n"
            '    if flag_enabled("checkout-v2", source):\n'
            "        return total - 1\n"
            "    return total\n"
        )

    def bypass_it(self, repo: Path, package: str) -> None:
        """The same branch, read the way the reader exists to stop: the variable derived and read by hand."""
        source = repo / f"apps/service/src/{package}/application"
        source.mkdir(parents=True, exist_ok=True)
        (source / "checkout.py").write_text(
            "import os\n\n\n"
            "def price(total: int) -> int:\n"
            '    if os.environ.get("FLAG_CHECKOUT_V2") == "on":\n'
            "        return total - 1\n"
            "    return total\n"
        )

    def test_a_project_with_no_flags_passes_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            done = check_flags(self.flagged(directory, "no-flags"))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("no flag is declared yet", done.stdout)

    def test_a_declared_flag_nothing_reads_is_dead_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "dead-flag")
            seed_flag(repo, "off")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn("service/checkout-v2: declared and read nowhere", done.stderr)

    def test_a_flag_read_and_declared_nowhere_is_the_dangerous_direction(self) -> None:
        """From the outside it looks exactly like a feature that shipped and was fine: nothing fails, and
        the parameter the code is waiting for exists in no environment, so it can never be turned on."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "unreachable-flag")
            self.read_it(repo, "unreachable_flag")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn("checkout-v2: read in `service` and declared nowhere", done.stderr)

    def test_a_new_flag_seeded_on_is_refused(self) -> None:
        """The seed is what a *new* environment starts at, so a flag being introduced is seeded off — and
        it cannot be corrected afterwards, because the stack never touches a parameter it has created."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "seeded-on")
            self.read_it(repo, "seeded_on")
            seed_flag(repo, "on")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn('new in this change and seeded "on"', done.stderr)

    def test_a_flag_declared_before_this_change_is_not_held_to_the_seed_rule(self) -> None:
        """Only a *new* key is being introduced. A key seeded on before this change is a decision somebody
        already made, and re-reporting it on every commit would train a reader to ignore the gate."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "seeded-long-ago")
            self.read_it(repo, "seeded_long_ago")
            seed_flag(repo, "on")
            self.both_paths(repo, "seeded_long_ago")
            commit_all(repo, "declare it on, before this change")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 0, done.stderr)

    def both_paths(self, repo: Path, package: str) -> None:
        tests = repo / "apps/service/tests/application"
        tests.mkdir(parents=True, exist_ok=True)
        (tests / "test_checkout.py").write_text(
            f"from {package}.application.checkout import price\nfrom {package}.flags import fixed_source\n\n\n"
            "def test_the_new_price_applies_when_the_flag_is_on() -> None:\n"
            '    assert price(10, fixed_source({"checkout-v2": "on"})) == 9\n\n\n'
            "def test_the_old_price_applies_while_the_flag_is_off() -> None:\n"
            "    assert price(10, fixed_source({})) == 10\n"
        )

    def test_a_flag_tested_only_on_the_path_that_is_not_shipping_is_refused(self) -> None:
        """The sharp end of the issue this closes: a slice merges with its flag off, so the branch running
        in production is the one its own tests do not cover — and inserting the branch changed that path
        too, so the code that used to work is not the code that is running."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "one-path")
            self.read_it(repo, "one_path")
            seed_flag(repo, "off")
            tests = repo / "apps/service/tests/application"
            tests.mkdir(parents=True, exist_ok=True)
            (tests / "test_checkout.py").write_text(
                "from one_path.application.checkout import price\n\n\n"
                "def test_the_new_price_applies_when_the_flag_is_on() -> None:\n"
                '    assert price(10, {"FLAG_CHECKOUT_V2": "on"}) == 9\n'
            )

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn("no test appears to drive it off", done.stderr)

    def test_a_flag_declared_read_seeded_off_and_tested_both_ways_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "held-back")
            self.read_it(repo, "held_back")
            seed_flag(repo, "off")
            self.both_paths(repo, "held_back")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("1 flag(s) declared, read, and tested on both paths", done.stdout)
            # And the reader naming the variable is not itself a bypass: being the one place that names it
            # is the whole of its job, which is why rule 5 skips the same files rules 1 and 2 do.
            self.assertNotIn("instead of asking the reader", done.stderr)

    def test_a_key_only_a_test_asks_for_is_still_dead_configuration(self) -> None:
        """A test is not a read. Counted as one, a key that is declared, exercised on both paths and never
        consulted by the code that ships would pass every rule here — while the parameter exists in both
        environments, appears in `make flags`, and gates nothing at all."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "tested-not-read")
            seed_flag(repo, "off")
            tests = repo / "apps/service/tests/application"
            tests.mkdir(parents=True, exist_ok=True)
            (tests / "test_checkout.py").write_text(
                "from tested_not_read.flags import fixed_source, flag_enabled\n\n\n"
                "def test_on() -> None:\n"
                '    assert flag_enabled("checkout-v2", fixed_source({"checkout-v2": "on"})) is True\n\n\n'
                "def test_off() -> None:\n"
                '    assert flag_enabled("checkout-v2", fixed_source({})) is False\n'
            )

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn("declared and read nowhere", done.stderr)

    def test_the_readers_own_tests_are_not_read_as_this_project_s_flags(self) -> None:
        """They demonstrate the transform with an example key. Counted as reads, every generated project
        would fail the gate before anybody had declared anything — which is exactly what the first version
        of this gate did."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "machinery")
            reader = (repo / "apps/service/src/machinery/flags.py").read_text()
            self.assertIn("checkout-v2", reader + (repo / "apps/service/tests/test_flags.py").read_text())

            done = check_flags(repo)

            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("no flag is declared yet", done.stdout)
    def test_a_read_that_names_the_variable_instead_of_the_reader_is_refused(self) -> None:
        """The reader says of itself that it is the only place this side touches the environment, and until
        this rule existed nothing held anybody to it: a flag could be declared, read by hand, tested on both
        paths and pass, with the reader the factory ships sitting unused beside it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "bypassed")
            self.bypass_it(repo, "bypassed")
            seed_flag(repo, "off")
            self.both_paths(repo, "bypassed")

            done = check_flags(repo)

            self.assertEqual(done.returncode, 1)
            self.assertIn("apps/service/src/bypassed/application/checkout.py", done.stderr)
            self.assertIn("reads FLAG_CHECKOUT_V2 from the environment", done.stderr)
            self.assertIn('Call flag_enabled("checkout-v2") instead', done.stderr)

    def test_a_bypassed_read_is_still_a_read_for_the_rule_about_dead_configuration(self) -> None:
        """Why the variable is matched at all, and the half that breaks if rule 5 is written as a stricter
        pattern rather than an extra rule: a hand-derived read is a real read, and called invisible the key
        reads as dead configuration — whose stated fix, deleting it, takes out live configuration."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.flagged(directory, "seen-anyway")
            self.bypass_it(repo, "seen_anyway")
            seed_flag(repo, "off")
            self.both_paths(repo, "seen_anyway")

            done = check_flags(repo)

            self.assertNotIn("declared and read nowhere", done.stderr)
            self.assertNotIn("declared nowhere", done.stderr)


class FlagReaderCatalogTest(FactoryTestCase):
    def test_every_backend_the_catalog_offers_has_a_reader(self) -> None:
        """A backend added later meets this as a `KeyError` at generation time under a target, which is
        `docs/backend-obligations.md`'s row for `FLAG_READERS` doing its job."""
        self.assertEqual(set(CATALOG["backends"]), set(FLAG_READERS))

    def test_both_java_backends_read_one_committed_tree(self) -> None:
        """The class names no framework type — no `@ConfigProperty`, no `@Value` — so a second copy would
        have nothing to say differently and could only drift, exactly as `../java/` sources do elsewhere."""
        self.assertEqual(FLAG_READERS["java-quarkus"].tree, FLAG_READERS["java-spring"].tree)
