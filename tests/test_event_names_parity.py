"""`validate.ts` and `check.py` read the held event names one way: the same names, the same refusals.

The two checkers are a mirror kept by hand — `make check-model` runs the Python one, the render pipeline
the TypeScript one — and issue 95's exemption has to mean the same in both, or a name passes one gate and
fails the other. The TypeScript reader is its own dependency-free module, `held-names.ts`, so this can run
it with Node alone: the keel's suite never does an `npm install`. It shells out, so it is in the
`Makefile`'s `SLOW` list.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_rung_gate import CHECK, GATE


class HeldNamesParityTest(unittest.TestCase):
    """Skipped where there is no Node that runs TypeScript; the source reading below runs everywhere."""

    CASES: tuple[object, ...] = (
        None, {"events": []}, {"events": ["WorkspaceCreated", "DocumentNotReceived"], "why": "kept"},
        {"events": ["A", "A"]}, "{", "[]", "{}", "null", '"x"', {"events": "A"}, {"events": ["A", 3]},
        {"events": ["A", ""]}, {"events": None}, {"events": {"A": True}},
    )

    def typescript(self, root: Path) -> object:
        program = ("import { heldEventNames } from " + json.dumps((GATE / "held-names.ts").as_uri()) + ";"
                   "try { console.log(JSON.stringify([...heldEventNames(process.argv[1])].sort())); }"
                   "catch (error) { console.log(JSON.stringify('refused')); }")
        done = subprocess.run(["node", "--input-type=module", "-e", program, str(root)],
                              capture_output=True, text=True, encoding="utf-8", check=False)
        if done.returncode != 0:
            self.fail(done.stderr)
        return json.loads(done.stdout)

    def python(self, root: Path) -> object:
        with mock.patch.object(CHECK, "ROOT", root):
            try:
                return sorted(CHECK.held_event_names())
            except OSError:
                return "refused"

    def test_the_two_readers_agree_on_every_file(self) -> None:
        node = shutil.which("node")
        if node is None or subprocess.run([node, "-e", "process.exit(process.features.typescript ? 0 : 1)"],
                                          capture_output=True, check=False).returncode != 0:
            self.skipTest("no Node here that runs TypeScript")
        for body in self.CASES:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                if body is not None:
                    (root / ".specify").mkdir()
                    (root / CHECK.NAMES_FROM).write_text(body if isinstance(body, str) else json.dumps(body),
                                                         encoding="utf-8")
                self.assertEqual(self.typescript(root), self.python(root))

    def test_both_checkers_skip_a_held_name_before_either_naming_rule(self) -> None:
        """Read from the source, as `ChartTest` does: nothing here installs `zod` to run `validate.ts`."""
        source = (GATE / "validate.ts").read_text(encoding="utf-8")
        body = source[source.index("function namingViolations("):source.index("function streamInvariants(")]
        self.assertLess(body.index("held.has(frame.name)"), body.index("CRUD_VERBS.find"))
        self.assertLess(body.index("held.has(frame.name)"), body.index("NEGATIVE_NAME.test"))
        self.assertIn("const heldNames = workspace.heldEventNames();", source)
        self.assertIn("namingViolations(slice, heldNames)", source)
        self.assertIn("return heldEventNames(ROOT);", (GATE / "workspace.ts").read_text(encoding="utf-8"))
        self.assertIn(f"'{CHECK.NAMES_FROM}'", (GATE / "held-names.ts").read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
