"""Where the factory's delivery material lives in a project — `project.json`'s `layout.delivery` — and what
follows from putting it somewhere other than the root.

Every generated project records `.`, and the property worth gating first is that this changes nothing for
it: the assembled files are the same mapping, byte for byte, with `delivery` recorded and nothing else. The
rest is for the repository the factory did not make, where the method is installed beside an existing
codebase (experimental, as `AGENTS.md` defines the word): the delivery paths land under the
directory, root-relative pointers in the text are respelled and everything else is left alone, the scripts
find the root by the manifest rather than by counting parents, and a project laid out that way passes its own
`make -f delivery/Makefile verify`, is pruned in its new place, and replays byte for byte — the proof that the
manifest records the layout as an answer and not as an accident of where the files were written.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_replay import replay, tree

from slipwai.assets import VERSION
from slipwai.errors import GenerationError
from slipwai.layout import AT_ROOT, POINTER, Layout, is_delivery, layout_of
from slipwai.scaffold import project_files, write_project
from slipwai.selection import Selection
from slipwai.services import default_apps

DELIVERY = Layout("delivery")


def gate(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, cwd=cwd, text=True, capture_output=True)


class LayoutTest(FactoryTestCase):
    def test_the_root_layout_changes_nothing_but_records_itself(self) -> None:
        """The gate on every existing project: a layout of `.` is the identity, and the manifest says so."""
        apps = default_apps("typescript", "react-vite", Selection({"http": "fastify"}))
        files = project_files("same", "event-modelling", "none", apps)
        self.assertIs(AT_ROOT.relocate(files), files)
        self.assertEqual(project_files("same", "event-modelling", "none", apps, Layout(".")), files)
        document = json.loads(files["project.json"])
        self.assertEqual(document["layout"], {"applications": "apps", "packages": "packages", "delivery": "."})
        # A manifest written before the key, and one that records the root, both read as the root.
        self.assertEqual(layout_of({"layout": {"applications": "apps"}}), AT_ROOT)
        self.assertEqual(layout_of(document), AT_ROOT)
        self.assertFalse(AT_ROOT.moved)
        self.assertEqual(AT_ROOT.make, "make")
        self.assertEqual(AT_ROOT.place("Makefile"), "Makefile")
        pointer = "see `skills/tdd/SKILL.md` and ./init"
        self.assertEqual(AT_ROOT.repoint("AGENTS.md", pointer), pointer)

    def test_delivery_paths_move_and_root_relative_pointers_are_respelled(self) -> None:
        """What moves is the factory's own material and nothing of the project's; what is respelled is a
        pointer read from the root and nothing that already sits inside a path, a URL or a relative climb."""
        moved = ("Makefile", "init", "scripts/verify", "skills/tdd/SKILL.md", "commands/drive.md", "docs/README.md")
        for path in moved:
            self.assertTrue(is_delivery(path), path)
            self.assertEqual(DELIVERY.place(path), f"delivery/{path}")
        for path in ("project.json", "AGENTS.md", "README.md", ".gitignore", ".github/workflows/verify.yml",
                     ".claude/settings.json", "apps/service/scripts/x", "packages/.gitkeep", "docker-compose.yml",
                     "initial.md", "documents/x"):
            self.assertFalse(is_delivery(path), path)
            self.assertEqual(DELIVERY.place(path), path)
        respelled = {
            "read `skills/tdd/SKILL.md`": "read `delivery/skills/tdd/SKILL.md`",
            "python3 scripts/check-imports.py": "python3 delivery/scripts/check-imports.py",
            "- `/drive` — `commands/drive.md`": "- `/drive` — `delivery/commands/drive.md`",
            "[x](docs/workflow.md)": "[x](delivery/docs/workflow.md)",
            "      - 'docs/event-model/**'": "      - 'delivery/docs/event-model/**'",
            "scripts/event-model/node_modules/\n": "delivery/scripts/event-model/node_modules/\n",
            "scripts/event-model/.mermaid-cli/\n": "delivery/scripts/event-model/.mermaid-cli/\n",
            "rerun ./init --extension codegraph": "rerun ./delivery/init --extension codegraph",
        }
        for before, after in respelled.items():
            self.assertEqual(DELIVERY.repoint("AGENTS.md", before), after)
        untouched = (
            "apps/web/scripts/build.ts",
            "https://github.com/github/spec-kit/blob/main/docs/installation.md",
            "see ../docs/workflow.md and ../../scripts/verify",
            "the docs, the scripts and the commands",
            "the Makefile, and `make verify`",
            "a file named init.py, and ./initial",
            '"scripts": {"dev": "tsx watch"}',
        )
        for text in untouched:
            self.assertEqual(DELIVERY.repoint("AGENTS.md", text), text)
        # Code finds its own way, so a literal in a script is left exactly as written.
        code = 'MODEL = ROOT / "docs/event-model/model.yaml"'
        self.assertEqual(DELIVERY.repoint("scripts/event-model/check.py", code), code)
        self.assertEqual(DELIVERY.make, "make -f delivery/Makefile")
        self.assertEqual(DELIVERY.to_root, "..")
        self.assertEqual(Layout("tools/delivery").to_root, "../..")
        self.assertEqual(Layout("tools/delivery").place("docs/x.md"), "tools/delivery/docs/x.md")

    def test_a_manifest_names_the_layout_or_is_refused(self) -> None:
        self.assertEqual(layout_of({"layout": {"delivery": "delivery"}}), DELIVERY)
        self.assertEqual(layout_of({"layout": {"delivery": "tools/delivery"}}), Layout("tools/delivery"))
        for bad in ("/delivery", "../delivery", "delivery/./x", "delivery/", "", 3, ["delivery"]):
            with self.assertRaises(GenerationError, msg=repr(bad)):
                layout_of({"layout": {"delivery": bad}})

    def test_a_project_laid_out_under_a_directory_replays_and_passes_its_own_gate_from_there(self) -> None:
        """The whole path, end to end, for the layout an adopted repository will have. Nothing asked of the
        toolchain that the matrix does not already ask: one TypeScript service, and its own `make verify`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "wrapped"
            apps = default_apps("typescript", "none", Selection({"http": "fastify"}))
            write_project(repo, "wrapped", "event-modelling", "none", apps, layout=DELIVERY)
            placed = tree(repo)

            # The delivery material is under `delivery/`, the project's own files are where they were, and
            # nothing of the factory's is left at the root.
            for path in ("delivery/Makefile", "delivery/init", "delivery/scripts/verify",
                         "delivery/scripts/agents/project.py", "delivery/scripts/backing-services.py",
                         "delivery/skills/tdd/SKILL.md", "delivery/commands/drive.md", "delivery/docs/README.md",
                         "delivery/docs/event-model/model.yaml"):
                self.assertIn(path, placed)
            for path in ("Makefile", "init", "scripts/verify", "skills/tdd/SKILL.md", "commands/drive.md",
                         "docs/README.md"):
                self.assertNotIn(path, placed)
            for path in ("project.json", "AGENTS.md", "README.md", ".gitignore", ".claude/settings.json",
                         ".github/workflows/verify.yml", ".github/workflows/event-model.yml",
                         "apps/service/package.json"):
                self.assertIn(path, placed)
            for executable in ("delivery/init", "delivery/scripts/verify", "delivery/scripts/backing-services.py"):
                self.assertTrue(os.access(repo / executable, os.X_OK), executable)
            self.assertEqual(json.loads(placed["project.json"])["layout"]["delivery"], "delivery")

            # Everything run or read from the root reaches the material where it now is.
            text = {path: content.decode() for path, content in placed.items() if not path.endswith((".png", ".ico"))}
            self.assertIn("run: make -f delivery/Makefile verify", text[".github/workflows/verify.yml"])
            self.assertIn("run: make -f delivery/Makefile model", text[".github/workflows/event-model.yml"])
            self.assertIn("'delivery/docs/event-model/**'", text[".github/workflows/event-model.yml"])
            self.assertIn("python3 delivery/scripts/event-model/check.py", text[".github/workflows/event-model.yml"])
            self.assertIn("python3 delivery/scripts/agents/project.py", text["delivery/Makefile"])
            self.assertIn("$(MAKE) -f delivery/Makefile --no-print-directory agents", text["delivery/Makefile"])
            self.assertIn('cd "$(dirname "$0")/.."', text["delivery/init"])
            self.assertIn("python3 delivery/scripts/backing-services.py", text["delivery/init"])
            self.assertIn("delivery/scripts/event-model/node_modules/", text[".gitignore"])
            self.assertIn("delivery/scripts/event-model/.mermaid-cli/", text[".gitignore"])
            self.assertIn("`delivery/skills/", text["AGENTS.md"])
            # Not one root-relative pointer to the old place survives outside the scripts, which find their
            # own way and are left as written.
            for path, content in text.items():
                if not path.startswith("delivery/scripts/"):
                    self.assertIsNone(POINTER.search(content), f"{path}: {POINTER.search(content)}")

            # The manifest records the layout as an answer: the same factory replays the same tree.
            result = replay(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tree(Path(directory) / f"wrapped-at-{VERSION}"), placed)

            # The scripts find the root wherever they are run from, and the gate holds from its new home.
            checked = gate("python3", str(repo / "delivery/scripts/check-imports.py"), cwd=Path(directory))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            verified = gate("make", "-f", "delivery/Makefile", "verify", cwd=repo)
            self.assertEqual(verified.returncode, 0, verified.stdout[-4000:] + verified.stderr[-4000:])
            self.assertIn("verify: all gates passed", verified.stdout)
            # The one line an existing Makefile adds to offer the same targets as its own.
            (repo / "Makefile").write_text("-include delivery/Makefile\n")
            listed = gate("make", "-s", "help", cwd=repo)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("verify", listed.stdout)
            (repo / "Makefile").unlink()

            # A later prune reaches the marked regions where the layout put them.
            self.assertIn("# backing-service:fastify:begin", text["delivery/Makefile"])
            pruned = gate("python3", "delivery/scripts/backing-services.py", "--http", "none", cwd=repo)
            self.assertEqual(pruned.returncode, 0, pruned.stdout + pruned.stderr)
            self.assertNotIn("# backing-service:fastify:begin", (repo / "delivery/Makefile").read_text())
