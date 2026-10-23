"""Adoption from the board: what a directory holds, and what would be written in it.

Adoption's whole risk is a file changed in a repository somebody already has, which is why the terminal verb
prints its findings and why the board can do better: the list of what would be written is shown *before*
anything is, and nothing is written until somebody has pressed the button under it.

The test that matters is the one that holds the preview to the truth — a fixture repository previewed, then
really adopted, with every path the preview named a file afterwards and every file the adoption added in the
preview. A preview that is nearly right is worse than none: it is believed.

It stands up a server and shells out to git, so it is in the Makefile's `SLOW` list.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import checkout_packages  # noqa: F401

from slipwai.adopt import Answers, adopt, proposed
from slipwai.adopt_page import NOT_A_REPOSITORY, found, looked, page, run, would_write
from slipwai.assets import ADOPTION_ROOT, relaunch
from slipwai.bridge import serve
from slipwai.errors import GenerationError
from slipwai.layout import Layout
from slipwai.project import prose
from slipwai.resurvey import refresh
from slipwai.survey import survey

IDENTITY = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def repository(where: Path) -> Path:
    """A small repository that builds, committed, which is what adoption is run against."""
    where.mkdir(parents=True, exist_ok=True)
    (where / "pyproject.toml").write_text('[project]\nname = "shop"\nversion = "0.1.0"\n', encoding="utf-8")
    (where / "README.md").write_text("# shop\n", encoding="utf-8")
    env = {**os.environ, **IDENTITY}
    for command in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                    ["git", "commit", "-qm", "first"]):
        subprocess.run(command, cwd=where, check=True, env=env)
    return where


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = Path(tempfile.mkdtemp())
        self.repo = repository(self.scratch / "shop")

    def dirty(self) -> str:
        return subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, text=True,
                              capture_output=True, check=True).stdout.strip()


class LocaleEncodingTest(Fixture):
    """Force only Path's unspecified text encoding to the Windows CP1252 default.

    Actual adoption, retained source, generated pages and refresh run without replacement. Explicit
    UTF-8 calls retain their real codec, so an omitted encoding reproduces either encoding failure or
    a corrupt read even on a UTF-8 host.
    """

    def setUp(self) -> None:
        super().setUp()
        self.actor = "class 顧客:\n    pass\n"
        self.guidance = "# 顧客 → 注文\n"
        (self.repo / "actors.py").write_text(self.actor, encoding="utf-8")
        (self.repo / "AGENTS.md").write_text(self.guidance, encoding="utf-8")
        env = {**os.environ, **IDENTITY}
        subprocess.run(["git", "add", "actors.py", "AGENTS.md"], cwd=self.repo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "the actor and its guidance"],
                       cwd=self.repo, check=True, env=env)

    def legacy_default(self):
        original = io.text_encoding
        return patch("io.text_encoding", side_effect=lambda encoding, *args:
                     "cp1252" if encoding is None else original(encoding, *args))

    def adopt_for_real(self) -> None:
        found = survey(self.repo)
        adopt(self.repo, Answers("shop", applications=proposed(found, "shop")), found)

    def check_utf8(self) -> None:
        self.assertEqual((self.repo / "actors.py").read_text(encoding="utf-8"), self.actor)
        self.assertTrue((self.repo / "AGENTS.md").read_text(encoding="utf-8").startswith(self.guidance))
        page = (self.repo / "adopt/survey/structure.md").read_text(encoding="utf-8")
        self.assertIn("→", page)
        self.assertEqual(self.dirty(), "")

    def test_real_adoption_preserves_utf8_under_a_cp1252_default(self) -> None:
        with self.legacy_default():
            self.assertEqual(io.text_encoding(None), "cp1252")
            self.adopt_for_real()
        self.check_utf8()

    def test_real_refresh_reads_existing_utf8_and_leaves_it_stable(self) -> None:
        self.adopt_for_real()
        self.check_utf8()
        with self.legacy_default():
            refreshed = refresh(self.repo)
        self.assertEqual(refreshed.rewritten, [])
        self.check_utf8()


class FoundTest(Fixture):
    """What the survey read, shown as findings rather than asked about one at a time."""

    def test_a_directory_that_builds_is_named_with_the_evidence_that_found_it(self) -> None:
        seen = found(self.repo)
        self.assertEqual([row["path"] for row in seen["candidates"]], ["."])
        self.assertEqual(seen["candidates"][0]["language"], "python")
        self.assertIn("pyproject.toml", seen["candidates"][0]["evidence"])

    def test_what_the_tree_could_not_settle_is_shown_as_a_proposal(self) -> None:
        self.assertIn("CI forge", found(self.repo)["proposal"])

    def test_a_directory_that_is_no_repository_says_so_rather_than_surveying_it(self) -> None:
        """`git init` is day zero, not a step to work around, and finding that out after twelve thousand
        files were read is the refusal arriving after the work it refuses."""
        seen = found(self.scratch / "nothing-here")
        self.assertIn(NOT_A_REPOSITORY, seen["refused"])

    def test_an_unclean_tree_is_refused_before_anything_is_surveyed(self) -> None:
        (self.repo / "scratch.txt").write_text("in flight\n", encoding="utf-8")
        self.assertIn("uncommitted", found(self.repo)["refused"])

    def test_looking_writes_nothing(self) -> None:
        """The whole promise of the tab: a look is a read."""
        looked({"root": str(self.repo)}, self.scratch)
        self.assertEqual(self.dirty(), "")

    def test_a_fault_in_the_keel_s_own_material_reaches_the_page_as_a_refusal(self) -> None:
        """`would_write` assembles what adoption would write, and anything that refuses the assembly is
        said where the list would have been rather than becoming a traceback in a server thread."""
        with patch("slipwai.toolkit.resolve_canonical_examples", side_effect=GenerationError("missing guidance")):
            said = looked({"root": str(self.repo)}, self.scratch)
        self.assertIn("card", said)
        self.assertIn("missing guidance", said)


class PreviewTest(Fixture):
    """The list, held to what the adoption then does. A preview that is nearly right is believed."""

    def adopt_for_real(self) -> dict[str, list[str]]:
        env = {**os.environ, **IDENTITY, "SLIPWAI_LANGUAGES": str(self.scratch / "no-packages")}
        done = subprocess.run([*relaunch(), "adopt", "--yes", "--no-init"], cwd=self.repo,
                              capture_output=True, text=True, env=env)
        if done.returncode != 0:
            raise AssertionError(done.stdout + done.stderr)
        changed = subprocess.run(["git", "diff", "--name-status", "HEAD^", "HEAD"], cwd=self.repo,
                                 text=True, capture_output=True, check=True).stdout
        landed: dict[str, list[str]] = {"A": [], "M": []}
        for line in changed.splitlines():
            how, _, path = line.partition("\t")
            landed.setdefault(how[:1], []).append(path)
        return landed

    def test_the_preview_is_not_empty(self) -> None:
        """Two empty lists agree with anything."""
        self.assertGreater(len(would_write(self.repo)["written"]), 20)

    def test_every_path_the_preview_named_is_written_and_no_other(self) -> None:
        plan = would_write(self.repo)
        landed = self.adopt_for_real()
        self.assertEqual(sorted(plan["written"]), sorted(landed["A"]))

    def test_every_file_of_theirs_the_preview_said_would_be_added_to_was(self) -> None:
        plan = would_write(self.repo)
        landed = self.adopt_for_real()
        self.assertEqual(sorted(plan["appended"]), sorted(landed["M"]))

    def test_existing_managed_files_are_appended_and_the_rest_are_added(self) -> None:
        for name in ("AGENTS.md", ".gitignore"):
            (self.repo / name).write_text("# theirs\n", encoding="utf-8")
        env = {**os.environ, **IDENTITY}
        subprocess.run(["git", "add", "AGENTS.md", ".gitignore"], cwd=self.repo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "their guidance"], cwd=self.repo, check=True, env=env)
        plan = would_write(self.repo)
        landed = self.adopt_for_real()
        self.assertEqual(sorted(plan["written"]), sorted(landed["A"]))
        self.assertEqual(sorted(plan["appended"]), sorted(landed["M"]))
        self.assertEqual(plan["appended"], [".gitignore", "AGENTS.md"])
        for name in plan["appended"]:
            self.assertTrue((self.repo / name).read_text(encoding="utf-8").startswith("# theirs\n"))


class ServedTest(Fixture):
    """Over the board's own server: a directory picked, looked at, and only then adopted."""

    def setUp(self) -> None:
        super().setUp()
        self.server = serve(self.scratch, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def get(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as answer:
            return answer.read().decode("utf-8")

    def post(self, path: str, body: dict) -> tuple[int, str]:
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as answer:
                return answer.status, answer.read().decode("utf-8")
        except urllib.error.HTTPError as answer:
            with answer:
                return answer.code, answer.read().decode("utf-8")

    def test_the_board_asks_for_a_directory_rather_than_assuming_this_one(self) -> None:
        said = self.get("/adopt")
        self.assertIn("Adopt a repository", said)
        self.assertIn('name="root"', said)

    def test_the_board_links_to_it_rather_than_naming_a_command(self) -> None:
        self.assertIn('href="/adopt"', self.get("/"))

    def test_looking_shows_what_was_found_and_leaves_the_repository_alone(self) -> None:
        code, said = self.post("/adopt/look", {"root": str(self.repo)})
        self.assertEqual(code, 200)
        self.assertIn("pyproject.toml", said)
        self.assertEqual(self.dirty(), "", "looking at a repository changed it")

    def test_a_directory_that_is_no_repository_is_a_refusal_and_not_a_traceback(self) -> None:
        code, said = self.post("/adopt/look", {"root": str(self.scratch / "nowhere")})
        self.assertEqual(code, 200)
        self.assertIn(NOT_A_REPOSITORY, said)

    def test_running_against_a_directory_it_refused_never_reaches_the_verb(self) -> None:
        code, said = self.post("/adopt/run", {"root": str(self.scratch / "nowhere")})
        self.assertEqual(code, 400)
        self.assertIn(NOT_A_REPOSITORY, said)

    def test_adopting_from_the_page_is_the_verb_and_leaves_its_one_commit(self) -> None:
        code, said = self.post("/adopt/run", {"root": str(self.repo)})
        self.assertEqual(code, 200, said)
        self.assertTrue((self.repo / "project.json").is_file())
        self.assertEqual(self.dirty(), "")


class RefusalTest(Fixture):
    def test_running_against_a_directory_it_refused_does_not_run_the_verb(self) -> None:
        worked, said = run({"root": str(self.scratch / "nowhere")}, self.scratch)
        self.assertFalse(worked)
        self.assertIn(NOT_A_REPOSITORY, said)

    def test_the_tab_is_a_page(self) -> None:
        self.assertIn("<!doctype html>", page({}))

    def test_the_assembly_refuses_rather_than_half_listing(self) -> None:
        """Where the keel cannot assemble what it would write, the preview says so. A partial list is the
        failure this slice exists to prevent."""
        with (
            patch("slipwai.toolkit.resolve_canonical_examples", side_effect=GenerationError("missing guidance")),
            self.assertRaisesRegex(GenerationError, "missing guidance"),
        ):
            would_write(self.repo)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class PlaceholderTest(Fixture):
    """The third rule of `docs/generated-prose.md`, for the trees only an adopted repository receives.

    A token can be provided, named, and still reach somebody unresolved if a page is copied by a path that
    does not render it — the one failure the other two rules cannot make. `test_generated.py` reads it over
    a generated project and skips the trees under `assets/adoption/`, because a generated project has no
    `docs/adoption.md` to read. This is where those are read: a repository really adopted, every landing the
    rows name, and no marker left in any of them.
    """

    def test_nothing_an_adoption_renders_still_carries_a_placeholder(self) -> None:
        from test_generated_prose import TEMPLATED

        found = survey(self.repo)
        adopt(self.repo, Answers("shop", applications=proposed(found, "shop")), found)
        layout = Layout(json.loads(
            (self.repo / "project.json").read_text(encoding="utf-8"))["layout"]["delivery"])
        carried: dict[str, list[str]] = {}
        for directory, lands, _provider in TEMPLATED:
            if not directory.is_relative_to(ADOPTION_ROOT):
                continue
            for landing in lands:
                where = self.repo / layout.place(landing)
                self.assertTrue(where.exists(), f"{landing} is not in an adopted repository")
                for path in (sorted(where.rglob("*")) if where.is_dir() else [where]):
                    if path.is_file() and (left := prose.unresolved(path.read_text(encoding="utf-8"))):
                        carried[str(path.relative_to(self.repo))] = left
        self.assertEqual(carried, {}, f"rendered files still carrying a placeholder: {carried}")
