"""Every page's script parses as JavaScript.

A page's script is a Python string, and a Python escape that is not a JavaScript one — a `\\n` that became
a real newline inside a quoted string — broke the Settings tab's every button on 2026-11-06 with nothing in
the suite to say so. Node reads each script the way a browser would; where there is no Node, this is skipped.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import (
    adopt_page,
    bridge_page,
    brief_page,
    captain_page,
    chandlery_page,
    console_page,
    fleet_page,
    landing_page,
    live_page,
    settings_page,
    timeline_page,
    turn_cards,
    voyage_page,
)

SCRIPTS = {
    "adopt_page": adopt_page.SCRIPT, "bridge_page": bridge_page.SCRIPT, "brief_page": brief_page.SCRIPT,
    "captain_page": captain_page.SCRIPT, "chandlery_page": chandlery_page.SCRIPT, "console_page": console_page.SCRIPT,
    "fleet_page": fleet_page.SCRIPT, "landing_page": landing_page.SCRIPT, "live_page.strip": live_page.STRIP_SCRIPT,
    "live_page.window": live_page.WINDOW_SCRIPT, "settings_page": settings_page.SCRIPT,
    "timeline_page": timeline_page.SCRIPT, "turn_cards": turn_cards.SCRIPT, "voyage_page": voyage_page.SCRIPT,
    "voyage_page.model": voyage_page.MODEL_SCRIPT,
}


@unittest.skipUnless(shutil.which("node"), "no node on this machine to parse with")
class PageScriptsTest(unittest.TestCase):
    def test_every_page_script_parses(self) -> None:
        here = Path(tempfile.mkdtemp())
        for name, script in SCRIPTS.items():
            with self.subTest(name):
                file = here / f"{name}.js"
                file.write_text(script, encoding="utf-8")
                said = subprocess.run(["node", "--check", str(file)], capture_output=True, text=True, check=False)
                self.assertEqual(said.returncode, 0, f"{name}: {said.stderr[:400]}")


if __name__ == "__main__":
    unittest.main()
