"""The picture the Windows app shows while it opens: its words, its going, and who goes without it.

The picture itself is drawn by the program that unpacks the app, before the keel runs, and only a Windows
build has one. What is held here is the keel's half: that a build with no picture is left alone — the
module behind it is not even imported, because importing it without one writes a warning — that the words
reach it where there is one, that a picture already gone is not a fault, and that the variable which keeps
the picture off the command is set for children and taken out for the app itself.
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from slipwai import splash


class SplashTest(unittest.TestCase):
    def picture(self, **said: object) -> mock._patch_dict:
        """A build with a picture: PyInstaller's module, already imported, as it is after the first ask."""
        return mock.patch.dict(sys.modules, {splash.MODULE: types.SimpleNamespace(**said)})

    def test_a_build_with_no_picture_imports_nothing(self) -> None:
        with mock.patch.dict(splash.os.environ), mock.patch.dict(sys.modules), \
                mock.patch.object(splash.importlib, "import_module") as imported:
            splash.os.environ.pop(splash.PORT, None)
            sys.modules.pop(splash.MODULE, None)
            self.assertIsNone(splash.screen())
            splash.say("Starting the board...")
            splash.close()
        imported.assert_not_called()

    def test_where_the_port_was_left_the_module_is_asked_for(self) -> None:
        with mock.patch.dict(splash.os.environ, {splash.PORT: "0"}), mock.patch.dict(sys.modules), \
                mock.patch.object(splash.importlib, "import_module", side_effect=ImportError) as imported:
            sys.modules.pop(splash.MODULE, None)
            self.assertIsNone(splash.screen())
        imported.assert_called_once_with(splash.MODULE)

    def test_the_words_reach_the_picture_and_it_is_taken_down(self) -> None:
        went: list[str] = []
        with self.picture(update_text=went.append, close=lambda: went.append("closed")):
            splash.say("Installing slipwai...")
            splash.close()
        self.assertEqual(went, ["Installing slipwai...", "closed"])

    def test_a_picture_already_gone_is_not_a_fault(self) -> None:
        def gone(*_: object) -> None:
            raise RuntimeError("the connection to the splash screen is closed")

        with self.picture(update_text=gone, close=gone):
            splash.say("Starting the board...")
            splash.close()

    def test_children_go_without_it_and_the_app_itself_does_not(self) -> None:
        held = {"PATH": "/bin"}
        splash.quiet_children(held)
        self.assertEqual(held, {"PATH": "/bin", splash.QUIET: "1"})
        self.assertEqual(splash.shown(held), {"PATH": "/bin"})


if __name__ == "__main__":
    unittest.main()
