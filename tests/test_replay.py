"""`replay`: this factory's output for a project's recorded answers, as a commit that project can merge.

Three claims, each gated. The manifest is a complete record — a replay of a project by the factory that made
it is byte-identical to it. The commit is a merge base — it sits on the project's root, so a newer factory's
changes and the project's own changes meet in a three-way merge that keeps both, and conflict only where both
touched the same lines. And what the project took away stays away — a feature pruned with `./init` is not
offered back. The "newer factory" is this checkout copied aside with one skill changed and `VERSION` raised,
which is what a newer factory is.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase, commit_all

from slipwai.assets import ROOT, VERSION

SKILL = "skills/tdd/SKILL.md"
NEWER = "99.0.0"


def git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *arguments], cwd=repo, text=True, capture_output=True, check=check)


def replay(repo: Path, factory: Path = ROOT, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(factory / "slipwai"), "replay", *flags], cwd=repo, text=True, capture_output=True)


def tree(repo: Path) -> dict[str, bytes]:
    """Every file but `.git`, with its bytes: what two repositories are compared on."""
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def newer_factory(into: Path, change: str) -> Path:
    """This checkout, copied, with `change` appended to one toolkit skill and its version raised."""
    factory = into / "factory"
    factory.mkdir(parents=True)
    for name in ("src", "assets"):
        shutil.copytree(ROOT / name, factory / name, ignore=shutil.ignore_patterns("__pycache__"))
    # `CHANGELOG.md` with them: `migrate` reads the catch-up notes out of it, so a factory copy without one
    # cannot leave a project the half of an upgrade a merge does not carry.
    for name in ("catalog.json", "slipwai", "CHANGELOG.md"):
        shutil.copy2(ROOT / name, factory / name)
    (factory / "VERSION").write_text(f"{NEWER}\n")
    skill = factory / "assets/toolkit" / SKILL
    skill.write_text(skill.read_text() + change)
    return factory


class ReplayTest(FactoryTestCase):
    def test_the_factory_that_made_a_project_replays_it_byte_for_byte(self) -> None:
        """The proof that `project.json` records every answer: nothing else is needed to make the same tree.
        The replay's one commit sits on the project's root commit, and the project is not touched."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "twin", "event-modelling", "typescript", "react-vite", auth="keycloak")
            root = git(repo, "rev-parse", "HEAD").stdout.strip()

            result = replay(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            twin = Path(directory) / f"twin-at-{VERSION}"
            self.assertTrue(twin.is_dir(), result.stdout)
            self.assertEqual(tree(twin), tree(repo))
            self.assertEqual(git(twin, "rev-parse", "HEAD^").stdout.strip(), root)
            self.assertEqual(git(twin, "status", "--porcelain").stdout, "")
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), root)
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertIn(f"git fetch {twin} main", result.stdout)
            self.assertIn("git merge FETCH_HEAD", result.stdout)

    def test_a_newer_factory_merges_forward_over_what_the_project_changed(self) -> None:
        """The project edits its own code, adds a file, and edits one generated file the factory also
        changes elsewhere. The merge keeps all three, brings the factory's change, and moves `updatedWith`
        alone. Where the project changed the very lines the factory did, the merge stops and says so."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "product", "event-modelling", "typescript")
            factory = newer_factory(Path(directory), "\n## A section a newer factory added\n")
            domain = next((repo / "apps/service/src").rglob("*.ts"))
            domain.write_text(domain.read_text() + "\n// the product's own line\n")
            (repo / "docs/adr/0009-ours.md").write_text("# Ours\n")
            readme = repo / "README.md"
            readme.write_text(readme.read_text().replace("# Product\n", "# Product — the product's title\n", 1))
            # And the newer factory changes the README too, in a different place: the page no longer carries
            # a version number for a bump to move, so a factory-side hunk in this file has to be made rather
            # than assumed. The two changes are what proves a merge keeps both.
            generator = factory / "src/slipwai/project/readme.py"
            generator.write_text(generator.read_text().replace(
                "- Project: `{project_name}`", "- Project: `{project_name}`\n- Added by a newer factory"
            ))
            commit_all(repo, "The product's own work")
            before = json.loads((repo / "project.json").read_text())["generator"]

            result = replay(repo, factory, "--into", str(Path(directory) / "offered"))
            self.assertEqual(result.returncode, 0, result.stderr)
            offered = Path(directory) / "offered"
            git(repo, "fetch", str(offered), "main")
            merged = git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "merge", "--no-edit", "FETCH_HEAD")

            self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
            self.assertIn("A section a newer factory added", (repo / SKILL).read_text())
            self.assertIn("the product's own line", domain.read_text())
            self.assertTrue((repo / "docs/adr/0009-ours.md").is_file())
            self.assertIn("# Product — the product's title", readme.read_text())
            # The factory's change and the product's were in different hunks of the same file, and both are
            # in the result. The version this was written by is in `project.json` and nowhere else, which is
            # asserted next: repeated on the page it could only ever disagree with the manifest.
            self.assertIn("- Added by a newer factory", readme.read_text())
            self.assertNotIn(NEWER, readme.read_text())
            after = json.loads((repo / "project.json").read_text())["generator"]
            self.assertEqual(after, {**before, "updatedWith": NEWER})
            self.assertEqual(before["generatedWith"], VERSION)

            # Now the project has edited the same lines the factory changes: a conflict, in that file alone —
            # the README's version line and `updatedWith` moved again, but this replay measures from the
            # last one merged rather than from the scaffold, so they merge — and `--abort` leaves the project
            # as it was.
            skill = repo / SKILL
            skill.write_text(skill.read_text() + "\n## A section the product added at the same place\n")
            commit_all(repo, "The product's own section")
            factory_again = newer_factory(Path(directory) / "again", "\n## Another section from the factory\n")
            (Path(directory) / "again/factory/VERSION").write_text("99.1.0\n")
            result = replay(repo, factory_again, "--into", str(Path(directory) / "offered-again"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("the newest commit in this project's history the factory made", result.stdout)
            self.assertEqual(
                git(Path(directory) / "offered-again", "rev-parse", "HEAD^").stdout.strip(),
                git(offered, "rev-parse", "HEAD").stdout.strip(),
            )
            head = git(repo, "rev-parse", "HEAD").stdout.strip()
            git(repo, "fetch", str(Path(directory) / "offered-again"), "main")
            # With an identity, as the first merge: `git merge` asks who the committer is before it finds
            # out there is nothing to commit, and a runner has no global one.
            conflicted = git(
                repo, "-c", "user.name=t", "-c", "user.email=t@local", "merge", "--no-edit", "FETCH_HEAD", check=False
            )
            self.assertNotEqual(conflicted.returncode, 0)
            self.assertEqual(
                git(repo, "diff", "--name-only", "--diff-filter=U").stdout.split(), [SKILL],
                conflicted.stdout + conflicted.stderr,
            )
            git(repo, "merge", "--abort")
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head)
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_a_feature_the_project_pruned_is_not_offered_back(self) -> None:
        """`./init --auth none` took Keycloak away; the replay reads the project's disk, as `add-service`
        does, and the offered tree has no adapter for it either — so the merge keeps it gone.

        What it *does* offer is the rest of that answer, which the prune cannot write for itself. The prune
        removes files and marked regions; it does not regenerate the project-wide surface a selection
        decides. So a project that answered its way down to no backing container at all kept `make
        services-up`, the paragraph in `AGENTS.md` about the containers and the README section describing
        them, none of which a generation with those answers would have written. Now that `./init` records
        the new answer in `project.json`, the replay generates from it and the merge offers that surface's
        removal — which is the whole job of the command.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "settled", "event-modelling", "typescript", event_store="memory", http="fastify",
                auth="keycloak",
            )
            adapter = "apps/service/src/adapters/driving/http/auth/oidc-keycloak.ts"
            self.assertTrue((repo / adapter).is_file())
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--auth", "none"], cwd=repo, check=True,
                stdout=subprocess.DEVNULL,
            )
            self.assertFalse((repo / adapter).exists())
            commit_all(repo, "Settle on no identity provider")

            result = replay(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            offered = Path(directory) / f"settled-at-{VERSION}"
            self.assertFalse((offered / adapter).exists())
            recorded = json.loads((offered / "project.json").read_text())["deployables"]["service"]
            self.assertEqual(recorded["selection"]["auth"], "none")
            self.assertNotIn("auth-keycloak", recorded["capabilities"])
            self.assertIn("Staff authentication: `none`", (offered / "README.md").read_text())
            # Nothing containerised is left, so the surface that starts containers goes — and the pruned
            # project still had it, which is what the merge is for.
            self.assertIn("services-up", (repo / "Makefile").read_text())
            self.assertNotIn("services-up", (offered / "Makefile").read_text())
            self.assertNotIn("Local backing services", (offered / "README.md").read_text())

    def test_a_project_design_system_replaces_the_untouched_starter_styles(self) -> None:
        """A project imported its own root tokens but never edited the generated visual baseline.

        Replaying the baseline beside it used to leave two token owners in one bundle. The replay now
        offers deletion of only the untouched factory files and their imports, while the project's import
        survives the merge and the design page names what really owns the tokens.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "themed", "standard", "go", "react-vite")
            theme = repo / "apps/web/src/theme.css"
            theme.write_text(":root {\n  --border: #ddd;\n  --radius: 4px;\n}\n")
            entry = repo / "apps/web/src/main.tsx"
            entry.write_text("import './theme.css';\n" + entry.read_text())
            commit_all(repo, "Install the product design system")

            result = replay(repo, ROOT, "--into", str(Path(directory) / "offered"))

            self.assertEqual(result.returncode, 0, result.stderr)
            offered = Path(directory) / "offered"
            for relative in ("tokens.css", "base.css"):
                self.assertFalse((offered / f"apps/web/src/styles/{relative}").exists())
                self.assertNotIn(f"./styles/{relative}", (offered / "apps/web/src/main.tsx").read_text())
            design = (offered / "docs/design.md").read_text()
            self.assertIn("apps/web/src/theme.css", design)
            self.assertNotIn("apps/web/src/styles/tokens.css", design)
            self.assertNotIn("apps/web/src/styles/base.css", design)

            git(repo, "fetch", str(offered), "main")
            merged = git(
                repo, "-c", "user.name=t", "-c", "user.email=t@local",
                "merge", "--no-edit", "FETCH_HEAD", check=False,
            )
            self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
            self.assertIn("import './theme.css';", entry.read_text())
            self.assertNotIn("./styles/tokens.css", entry.read_text())
            self.assertFalse((repo / "apps/web/src/styles/tokens.css").exists())

    def test_replay_never_deletes_a_starter_stylesheet_the_project_changed(self) -> None:
        """A changed starter file is project work even after another token file appears.

        There is no safe automatic winner, so replay refuses by name instead of deleting either design
        system or silently putting both into the bundle.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "two-themes", "standard", "go", "react-vite")
            tokens = repo / "apps/web/src/styles/tokens.css"
            tokens.write_text(tokens.read_text().replace("--radius: 6px", "--radius: 8px"))
            (repo / "apps/web/src/theme.css").write_text(":root { --radius: 1rem; }\n")
            entry = repo / "apps/web/src/main.tsx"
            entry.write_text("import './theme.css';\n" + entry.read_text())
            commit_all(repo, "Change and then replace the starter tokens")

            result = replay(repo, ROOT, "--into", str(Path(directory) / "refused"))

            self.assertEqual(result.returncode, 2)
            self.assertIn("imports its own root tokens", result.stderr)
            self.assertIn("apps/web/src/styles/tokens.css", result.stderr)
            self.assertIn("Refusing to choose which design system owns the bundle", result.stderr)
            self.assertFalse((Path(directory) / "refused").exists())

    def test_replay_refuses_what_it_cannot_offer_to(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            elsewhere = Path(directory) / "elsewhere"
            elsewhere.mkdir()
            result = replay(elsewhere)
            self.assertEqual(result.returncode, 2)
            self.assertIn("there is no project.json", result.stderr)
            self.assertIn("run replay from that directory", result.stderr)

            repo = self.generate(directory, "guarded", "event-modelling", "python")
            occupied = Path(directory) / "occupied"
            occupied.mkdir()
            (occupied / "theirs.txt").write_text("not the factory's\n")
            result = replay(repo, ROOT, "--into", str(occupied))
            self.assertEqual(result.returncode, 2)
            self.assertIn("not an empty directory", result.stderr)
            self.assertEqual(sorted(p.name for p in occupied.iterdir()), ["theirs.txt"])

            result = replay(repo, ROOT, "--into", str(repo / "inside"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("inside the project being replayed", result.stderr)

            result = replay(repo, ROOT, "--base", "no-such-commit")
            self.assertEqual(result.returncode, 2)
            self.assertIn("--base no-such-commit is not a commit", result.stderr)

            # An empty directory is taken, and a project without history gets a tree and a `diff` to run.
            shutil.rmtree(repo / ".git")
            empty = Path(directory) / "empty"
            empty.mkdir()
            result = replay(repo, ROOT, "--into", str(empty))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("diff -r --exclude=.git", result.stdout)
            self.assertEqual(tree(empty), tree(repo))
            self.assertEqual(git(empty, "rev-list", "--count", "HEAD").stdout.strip(), "1")

    def test_replay_is_a_verb_with_its_own_help(self) -> None:
        shown = subprocess.run(
            [str(ROOT / "slipwai"), "replay", "--help"], check=True, text=True, stdout=subprocess.PIPE
        )
        self.assertTrue(shown.stdout.startswith("usage: slipwai replay"), shown.stdout.splitlines()[0])
        self.assertIn("--into", shown.stdout)
        self.assertIn("--base", shown.stdout)
