"""The picture the Windows app shows while it opens, and the line of words under it.

The Windows app is one file, and one file unpacks itself before any of the keel runs: some seconds, more
while a virus scanner reads an executable it has not met, and twice on a first launch — the download, then
the copy it placed. All of that happened with nothing on the screen, and the board's page came a good while
after the double-click. So the build gives the program that does the unpacking a picture to show the moment
it starts (`slipwai.spec`), and this module is how the keel changes the words on it and takes it down.

Only a double-click should show it. The same file is also the command: the board at sign-in, and every
`slipwai` an agent runs. `QUIET` is the variable the unpacking program reads before it draws anything, so
`quiet_children` sets it for everything this process starts, the wrappers and the sign-in file set it for
themselves, and `shown` takes it out again for the one child that is the app being opened: the placed copy.

On a Mac and on Linux there is no picture — PyInstaller cannot draw one on macOS — and every function here
does nothing.
"""
from __future__ import annotations

import contextlib
import importlib
import os
import sys
from collections.abc import Mapping, MutableMapping
from types import ModuleType

#: Read by the program that unpacks the app, before the keel runs: set, it draws no picture.
QUIET = "PYINSTALLER_SUPPRESS_SPLASH_SCREEN"
#: Set by that program where the build carries a picture: the port its words are sent to, or 0 where quiet.
PORT = "_PYI_SPLASH_IPC"
MODULE = "pyi_splash"


def screen() -> ModuleType | None:
    """PyInstaller's own module for the picture, or None in a build without one. It is imported only where
    the unpacking program left its port: without that the import itself writes a warning, on every launch
    of every build that has no picture. The import takes the port out of the environment, so a second ask
    finds the module rather than the variable."""
    if MODULE not in sys.modules and PORT not in os.environ:
        return None
    try:
        return importlib.import_module(MODULE)
    except ImportError:
        return None


def say(words: str) -> None:
    """Put `words` under the picture. Nothing where there is none, or it has gone."""
    held = screen()
    if held is None:
        return
    with contextlib.suppress(RuntimeError, OSError):
        held.update_text(words)


def close() -> None:
    """Take the picture down. It is over every other window until this, so it goes before the page opens."""
    held = screen()
    if held is None:
        return
    with contextlib.suppress(RuntimeError, OSError):
        held.close()


def quiet_children(environ: MutableMapping[str, str] | None = None) -> None:
    """Everything this process starts from here on opens without the picture."""
    (os.environ if environ is None else environ)[QUIET] = "1"


def shown(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment for a child that is the app itself, opened as a double-click opens it."""
    return {name: value for name, value in (os.environ if environ is None else environ).items() if name != QUIET}
