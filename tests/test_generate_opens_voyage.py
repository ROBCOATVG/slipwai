"""Where the run is watched after a generate, when the browser will not open the tab for it.

What is proved, of the page's script: the way to the voyage is put on the page whether or not the tab
opened, and says which; and the tab is opened so that the page can tell.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import interview_form


class GenerateOpensVoyageTest(unittest.TestCase):
    def test_the_way_to_the_voyage_is_on_the_page_when_the_tab_was_refused(self) -> None:
        """A browser lets a page open a tab for a few seconds after the click that asked. A generate takes
        longer, so the voyage's tab was refused without a word and the run went on where nobody looked."""
        script = interview_form.SCRIPT
        self.assertIn("const opened = window.open(where, '_blank');", script,
                      "not `noopener`: that answers nothing, and the page could not tell a refusal from a tab")
        self.assertIn("'Open the voyage: the project is being finished there'", script)
        self.assertIn("'The voyage is open in another tab: open it again'", script)
        self.assertIn("said.after(link);", script)
        self.assertIn("const where = '/voyage?look=' + encodeURIComponent(receipt.root);", script)


if __name__ == "__main__":
    unittest.main()
