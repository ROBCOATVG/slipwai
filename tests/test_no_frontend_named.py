"""The keel names no browser app — and the two lines where a frontend's word is the name of a skill.

Phase 17 moved the last answer the keel carried, `react-vite`, into the TypeScript family that ships its files
and the lock that resolves them, and made a frontend something a package declares (`language.json`'s
`frontends` block) and answers (`browser_apps`). That is only true while nothing in `src/slipwai/` knows a
frontend by name: a dict keyed by `"react-vite"`, a manifest edit naming `react-oidc-context`, a comment about
what Vite does. None of those imports anything, and every one of them is the keel knowing a framework a second
frontend would then have to be edited around.

**A gate rather than a grep somebody remembers to run**, in the shape `test_no_cloud_named.py` has: the search
is here, and the only way past it is a line in `ALLOWED` with a reason, which a reviewer sees.

**What is allowed.** Two lines, each the name of a skill the keel's own toolkit ships — `react-testing` — in
the table that says which skills are written in TypeScript and on the page that says where one went. A skill
is toolkit material, not a frontend, and taking its name out would make both lines lie about which skill they
mean. What a second frontend in another bundler still has to move is listed in `docs/frontend-protocol.md`.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

KEEL = Path(__file__).resolve().parents[1] / "src/slipwai"
#: Every word that would mean the keel knew a frontend: the one that shipped here, its framework, its bundler and
#: the bundler's environment prefix, and the login library its feature adds. Word-bounded where English or a
#: neighbouring tool would otherwise match — `Vitest` is a test runner a language names, not this.
NAMES = re.compile(r"react-vite|\breact\b|\bvite\b|\bVITE_|oidc-client|react-oidc", re.IGNORECASE)

#: Module → the lines in it a frontend's word may appear on, each with why it is not the keel knowing a frontend.
ALLOWED: dict[str, list[tuple[str, str]]] = {
    "examples.py": [
        ('"react-testing"', "a skill the keel's toolkit ships, in the table of skills whose examples are "
                            "TypeScript by nature"),
    ],
    "project/skills_page.py": [
        ("`react-testing` went", "the same skill, named on the page that says where it went"),
    ],
}


def modules() -> list[Path]:
    return sorted(KEEL.rglob("*.py"))


class NoFrontendNamedTest(unittest.TestCase):
    def test_no_module_names_a_frontend_but_the_lines_allowed_with_a_reason(self) -> None:
        found = []
        for path in modules():
            relative = path.relative_to(KEEL).as_posix()
            allowed = [fragment for fragment, _why in ALLOWED.get(relative, [])]
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if NAMES.search(line) and not any(fragment in line for fragment in allowed):
                    found.append(f"{relative}:{number}: {line.strip()}")
        self.assertEqual(found, [], "a frontend is its family's to name; say it through the catalogue's "
                                    "`frontends` entry, or add the line to ALLOWED with why it is not one")

    def test_every_allowed_line_is_still_there(self) -> None:
        """An allowance for a line that has gone is an allowance for whatever is written there next."""
        for relative, lines in ALLOWED.items():
            text = (KEEL / relative).read_text(encoding="utf-8")
            for fragment, _why in lines:
                with self.subTest(module=relative, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_the_keel_ships_no_frontend_material(self) -> None:
        self.assertFalse((KEEL.parents[1] / "assets/frontends").exists())


if __name__ == "__main__":
    unittest.main()
