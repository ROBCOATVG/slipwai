"""Every script the board serves, parsed.

Nothing else in this suite would notice a broken one. A browser reports a SyntaxError to its own console
and to nobody else: the page still renders, every test still passes, and the half of the board that moves
simply stops moving. That is exactly how it went — `'\\n'` written in a Python string that is not raw is a
real newline by the time a browser sees it, so one `join` closed no quote, the whole script was a syntax
error, and the first person to find out was the one watching a card that never updated.

A string literal that runs off the end of its line is the whole of that class of fault, and counting quotes
catches it without asking this suite to carry a JavaScript engine.
"""
from __future__ import annotations

import re
import unittest

import checkout_packages  # noqa: F401

from slipwai.bridge_page import SCRIPT
from slipwai.interview_page import SCRIPT as ASK
from slipwai.page_shell import REGISTER, WORKER_SOURCE

SCRIPTS = {"bridge_page": SCRIPT, "interview_page": ASK,
           "page_shell.REGISTER": REGISTER, "page_shell.WORKER": WORKER_SOURCE}


class ScriptTest(unittest.TestCase):
    def test_no_line_of_any_script_leaves_a_string_open(self) -> None:
        for name, script in SCRIPTS.items():
            for number, line in enumerate(script.splitlines(), 1):
                for quote in ("'", '"'):
                    with self.subTest(script=name, line=number, quote=quote):
                        bare = re.sub(r"\\.", "", line.partition("//")[0])
                        self.assertEqual(bare.count(quote) % 2, 0, line)

    def test_a_newline_in_a_script_is_an_escape_and_never_the_character(self) -> None:
        """The same fault said the other way round, which is the way it will come back."""
        for name, script in SCRIPTS.items():
            with self.subTest(script=name):
                self.assertNotIn("join('\n", script)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
