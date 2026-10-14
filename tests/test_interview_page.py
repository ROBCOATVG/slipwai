"""One interview, two faces: the questions of 3.x asked on a page, and the project that comes out.

The plan's rule for this slice is that the questions, their order and their refusals are read from the
catalogue and never written twice, and the gate it names is the two trees being identical. So two tests here
matter and the rest are about them:

* **In step.** The terminal interview is driven with a recording `input`, and the questions the page would
  ask are found in what it printed, in that order. A page asking the same things in a different order would
  be a second interview wearing the first one's name.
* **Byte-identical.** A project generated from the board, and the same answers given in the terminal, are
  one tree file for file. That is the only check prose cannot satisfy.

It generates projects, so it is in the Makefile's `SLOW` list.
"""
from __future__ import annotations

import contextlib
import filecmp
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import checkout_packages

from slipwai.bridge import serve
from slipwai.catalog import CATALOG, axis_applies
from slipwai.interview_page import asked, destination, flags, form, run, settled
from slipwai.targets import offered_backends

#: Where in the terminal's transcript each question of the page is. Both faces read the catalogue; this is
#: the seam that holds the two readings in step, and it lives here rather than in the module because it is a
#: fact about the *other* face.
IN_THE_TERMINAL = {
    "name": "Project name",
    "profile": "Use Event Modeling?",
    "target": "Production target",
    "language": "Language",
    "framework": "Application framework",
    "service-name": "Service name",
    "purpose": "What does",
    "context": "Bounded contexts",
    "frontend": "Frontend",
    "frontend-name": "Browser app name",
    "output": "Output parent",
    "prd": "Product requirements document",
}


def in_the_terminal(name: str) -> str:
    """What the terminal prints when it asks the question the page calls `name`."""
    return str(CATALOG["axes"][name]["prompt"]) if name in CATALOG["axes"] else IN_THE_TERMINAL[name]


def terminal_interview(answer: Callable[[str], str]) -> str:
    """The interview of 3.x, run, with `answer` deciding what is typed at each prompt. What it printed."""
    from slipwai.cli import generate_main

    said = io.StringIO()

    def typed(prompt: str = "") -> str:
        said.write(prompt)
        return answer(prompt)

    with (contextlib.redirect_stdout(said),
          mock.patch("builtins.input", typed),
          mock.patch("slipwai.cli_prompts.terminal_can_select", lambda: False)):
        # `--no-init` rather than nothing: the interview's own default is to run `./init` in what it made,
        # which reaches the network and is the one thing a test of the questions must not do. It is still the
        # interactive form — the flags that have nothing to prompt about do not make it a scripted one.
        generate_main(["--no-init"])
    return said.getvalue()


def every_default(name: str, output: Path) -> Callable[[str], str]:
    """Enter at every question but the two a default cannot answer: the project's name and where it goes."""
    def answer(prompt: str) -> str:
        if IN_THE_TERMINAL["name"] in prompt:
            return name
        return str(output) if IN_THE_TERMINAL["output"] in prompt else ""
    return answer


class QuestionsTest(unittest.TestCase):
    """What is asked, before anything is generated."""

    def test_the_first_question_is_the_project_s_name(self) -> None:
        self.assertEqual(asked({})[0].name, "name")

    def test_a_question_with_one_answer_is_not_asked(self) -> None:
        """The terminal's own rule: something with one answer is not a choice, and offering it teaches the
        reader that it is."""
        declared = [name for name in CATALOG["targets"] if offered_backends(CATALOG, name)]
        asked_now = [question.name for question in asked({})]
        self.assertEqual("target" in asked_now, len(declared) > 1)

    def test_every_axis_the_answers_make_applicable_is_asked_and_no_other(self) -> None:
        """Read from the catalogue, so an axis added to `catalog.json` is asked here with no edit."""
        answers = settled({"name": "demo"})
        applicable = [axis for axis in CATALOG["axes"]
                      if axis_applies(axis, answers["profile"], answers["backend"], answers["target"])]
        self.assertEqual([q.name for q in asked({"name": "demo"}) if q.name in CATALOG["axes"]], applicable)

    def test_the_form_asks_every_question_by_its_label(self) -> None:
        said = form({"name": "demo"})
        for question in asked({"name": "demo"}):
            with self.subTest(question=question.name):
                self.assertIn(question.label, said)

    def test_the_output_parent_proposed_is_where_the_board_is_looking(self) -> None:
        """Not the process's own directory: a board started by a login service holds `/`, and a project
        staged beside `/` was a traceback on a read-only filesystem rather than a project."""
        with tempfile.TemporaryDirectory() as scratch:
            harbour = Path(scratch).resolve()
            proposed = {q.name: q.default for q in asked({"name": "demo"}, harbour)}["output"]
            self.assertEqual(proposed, str(harbour))
            self.assertIn(f'value="{harbour}"', form({"name": "demo"}, harbour))
            self.assertEqual(destination({"name": "demo"}, harbour), harbour / "demo")
            said = flags({"name": "demo"}, harbour)
            self.assertEqual(said[said.index("--output") + 1], str(harbour))
            typed = {"name": "demo", "output": "/elsewhere"}
            self.assertEqual(destination(typed, harbour), Path("/elsewhere/demo").resolve(),
                             "an answer somebody typed still wins over the proposal")

    def test_the_last_question_is_the_document_and_it_is_a_file(self) -> None:
        """A PRD is the one answer that is a document rather than a word: the board asks for it with a file
        picker, the terminal with a path, and `--prd` is the flag both become."""
        last = asked({"name": "demo"})[-1]
        self.assertEqual((last.name, last.kind, last.optional), ("prd", "file", True))
        said = form({"name": "demo"})
        self.assertIn('id="prd"', said)
        self.assertIn('type="file"', said)
        self.assertNotIn("--prd", flags({"name": "demo", "prd": "# A document\n"}),
                         "the text is not a flag; `run` writes it to a file and names that")

    def test_an_answer_a_person_typed_is_escaped_and_never_rendered_as_markup(self) -> None:
        self.assertNotIn("<script>alert(1)</script>", form({"name": "<script>alert(1)</script>"}))

    def test_a_refusal_the_catalogue_makes_is_the_page_s_refusal_too(self) -> None:
        """A name the generator will not take is said here rather than after every other question."""
        ok, said = run({"name": "Not A Name"}, Path(tempfile.gettempdir()))
        self.assertFalse(ok)
        self.assertIn("project name", said.lower())


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class InStepTest(unittest.TestCase):
    """The terminal interview, driven, with the page's questions looked for in what it printed."""

    def test_the_page_asks_the_same_questions_in_the_same_order(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            said = terminal_interview(every_default("demo", Path(scratch)))
        at = -1
        for question in asked({"name": "demo"}):
            marker = in_the_terminal(question.name)
            with self.subTest(question=question.name):
                found = said.find(marker, at + 1)
                self.assertNotEqual(found, -1, f"the terminal never asked {question.name}: {marker!r}")
                at = found


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class ByteIdenticalTest(unittest.TestCase):
    """The gate the plan names: the same answers, two faces, one tree."""

    def test_a_project_from_the_board_is_the_project_from_the_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            terminal, board = Path(one), Path(two)
            terminal_interview(every_default("demo", terminal))
            ok, said = run({"name": "demo", "output": str(board)}, board)
            self.assertTrue(ok, said)
            # Guarded, because two empty trees are identical and prove nothing.
            self.assertGreater(len(list((terminal / "demo").rglob("*"))), 100)
            self.assertEqual(differences(terminal / "demo", board / "demo"), [])

    @unittest.skipIf(sys.platform == "win32", "a login shell is asked with `-ilc`, which Windows has no shell for")
    def test_the_child_is_given_the_login_shells_path_and_keeps_its_own_variables(self) -> None:
        """A board started from a launcher has `PATH=/usr/bin:/bin` and no tokens, and `generate` then refuses
        a target on a machine that has every tool. The login shell is what the person's terminal has."""
        from slipwai.shell_environment import login_environment
        with tempfile.TemporaryDirectory() as scratch:
            shell = Path(scratch) / "shell"
            shell.write_text("#!/bin/sh\nprintf 'PATH=/opt/tools/bin:/usr/bin\\0TOKEN=from-login\\0KEPT=login\\0'\n",
                             encoding="utf-8")
            shell.chmod(0o755)
            found = login_environment({"PATH": "/usr/bin:/bin", "KEPT": "mine"}, shell=str(shell))
        self.assertEqual(found["PATH"], "/opt/tools/bin:/usr/bin:/bin")
        self.assertEqual(found["TOKEN"], "from-login")
        self.assertEqual(found["KEPT"], "mine", "this process's own variable wins where both have one")
        self.assertEqual(login_environment({"PATH": "/bin"}, shell="/nonexistent/shell"), {"PATH": "/bin"})

    def test_a_document_given_on_the_board_lands_in_the_project_as_the_prd(self) -> None:
        """What the picker is for: the text arrives with the answers, and the project is made with it under
        `docs/`, listed in the docs index, before its first commit."""
        with tempfile.TemporaryDirectory() as scratch:
            board = Path(scratch)
            ok, said = run({"name": "demo", "output": scratch, "prd": "# Demo\n\nSell more demos.\n",
                            "prd-name": "demo-prd.md"}, board)
            self.assertTrue(ok, said)
            self.assertEqual((board / "demo/docs/prd.md").read_text(encoding="utf-8"), "# Demo\n\nSell more demos.\n")
            self.assertIn("prd.md", (board / "demo/docs/README.md").read_text(encoding="utf-8"))
            self.assertIn("commands/draft.md", (board / "demo/docs/skills-and-commands.md").read_text(encoding="utf-8"))
            self.assertTrue((board / "demo/commands/launch.md").is_file())
            self.assertTrue((board / "demo/scripts/agents/draft.py").is_file())
            self.assertIn("docs/prd.md", subprocess.run(["git", "show", "--stat", "HEAD"], cwd=board / "demo",
                                                        capture_output=True, text=True).stdout)

    def test_the_board_says_where_it_put_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            ok, said = run({"name": "demo", "output": scratch}, Path(scratch))
            self.assertTrue(ok, said)
            self.assertIn("demo", said)


class ServedTest(unittest.TestCase):
    """The interview, over the one server the board already is."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.server = serve(self.root, "127.0.0.1", 0)
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
            with urllib.request.urlopen(request, timeout=120) as answer:
                return answer.status, answer.read().decode("utf-8")
        except urllib.error.HTTPError as answer:
            with answer:
                return answer.code, answer.read().decode("utf-8")

    def test_the_interview_is_a_page_on_the_board_s_own_server(self) -> None:
        self.assertIn("Start a new project", self.get("/generate"))

    def test_the_served_interview_proposes_the_board_s_own_root_as_the_output_parent(self) -> None:
        self.assertIn(f'value="{self.root.resolve()}"', self.get("/generate"))
        code, said = self.post("/generate/ask", {"name": "demo"})
        self.assertEqual(code, 200)
        self.assertIn(f'value="{self.root.resolve()}"', said)

    def test_the_board_links_to_it_rather_than_naming_a_command(self) -> None:
        self.assertIn('href="/generate"', self.get("/"))

    def test_an_answer_that_decides_a_later_question_asks_the_rest_again(self) -> None:
        """The catalogue decides which questions follow which answers, and it is read on this side of the
        wire. A browser working that out for itself would be the second reading this slice exists to avoid."""
        code, said = self.post("/generate/ask", {"name": "demo", "profile": "standard"})
        self.assertEqual(code, 200)
        self.assertIn('value="standard" selected', said)

    def test_a_refusal_comes_back_as_a_refusal_and_not_as_a_traceback(self) -> None:
        code, said = self.post("/generate/run", {"name": "Not A Name"})
        self.assertEqual(code, 400)
        self.assertIn("project name", said.lower())


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class HandoverTest(unittest.TestCase):
    """What the terminal does after `created:`.

    `./init` is the step that installs Spec Kit and projects the skills and commands, and nothing in a new
    tree works until it has run. It used to be a sentence in the guide, which is the state this closes: the
    interview ends by running it, and a scripted run is given the flag or left with the next step — the same
    rule `adopt` has, and for the same reason. The run itself is stubbed here: the real one needs the
    network, and what is under test is who it is run for.
    """

    def ran(self, argv: list[str], answer: Callable[[str], str] | None = None) -> list[Path]:
        """Where `generate` handed the new project over, for this way of asking it."""
        from slipwai import cli

        handed: list[Path] = []

        def instead_of_init(where: Path, harness: str | None = None) -> int:
            handed.append(where)
            return 0

        def typed(prompt: str = "") -> str:
            return answer(prompt) if answer else ""

        with (contextlib.redirect_stdout(io.StringIO()),
              mock.patch.object(cli, "run_init", instead_of_init),
              mock.patch("builtins.input", typed),
              mock.patch("slipwai.cli_prompts.terminal_can_select", lambda: False)):
            cli.generate_main(argv)
        return handed

    def scripted(self, scratch: Path, *extra: str) -> list[str]:
        held = settled({"name": "demo"})
        return ["demo", "--backend", held["backend"], "--frontend", "none",
                "--output", str(scratch), "--skip-checks", *extra]

    def test_the_interview_hands_the_project_over_when_it_is_done(self) -> None:
        """Somebody is sitting there, and `./init` has a question of its own to ask them."""
        with tempfile.TemporaryDirectory() as scratch:
            # Resolved, because `generate` resolves the output parent before it writes: on macOS the
            # scratch directory is reached through a symlink and the two spellings are the same directory.
            self.assertEqual(self.ran([], every_default("demo", Path(scratch))),
                             [(Path(scratch) / "demo").resolve()])

    def test_a_scripted_run_is_left_with_the_next_step(self) -> None:
        """It reaches the network, and a build that did that without being asked would be the surprise."""
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(self.ran(self.scripted(Path(scratch))), [])

    def test_a_scripted_run_that_asks_for_it_gets_it(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(self.ran(self.scripted(Path(scratch), "--init")),
                             [(Path(scratch) / "demo").resolve()])

    def test_the_interview_can_decline_it_and_still_be_the_interview(self) -> None:
        """`--no-init` says what happens after the last question; it does not make the run a scripted one."""
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(self.ran(["--no-init"], every_default("demo", Path(scratch))), [])


def differences(one: Path, two: Path) -> list[str]:
    """Every path the two trees disagree about, `.git` left out: two commits are two timestamps, and the
    question here is what was written, not when."""
    def files(root: Path) -> set[str]:
        return {path.relative_to(root).as_posix() for path in root.rglob("*")
                if path.is_file() and ".git" not in path.relative_to(root).parts}

    here, there = files(one), files(two)
    return ([f"only in the terminal's tree: {name}" for name in sorted(here - there)]
            + [f"only in the board's tree: {name}" for name in sorted(there - here)]
            + [f"different bytes: {name}" for name in sorted(here & there)
               if not filecmp.cmp(one / name, two / name, shallow=False)])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
