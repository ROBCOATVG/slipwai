"""The machine's own folder chooser, opened by the board for the one answer that is a path.

A browser cannot hand a page a path. It never could and never will: `<input type="file">` gives a file's
*contents*, `webkitdirectory` gives names relative to the folder picked, and the File System Access API
gives a handle — three ways of saying the same thing, which is that a web page may not learn where
anything is on the disk. So a board that wants a folder has two choices: carry every byte of it up through
the browser and write it back down, or ask the machine.

**This board is on the machine.** It binds this host only and generates here, so the folder is already
where the verb can read it and the only thing missing is its name. Asking the operating system for that is
one dialog — the same one every other program on this computer opens — and the answer is a path.

Nothing here is required. Where no chooser can be run — a board reached from another machine's browser, a
host with no desktop, a platform this has no command for — the field is still a path somebody can type,
which is what it was before this and what the terminal has always taken.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .shell_environment import login_environment

#: How long a dialog may stand open. Long, because a person choosing a folder is reading their own disk
#: and that is not a thing to hurry; bounded, because a dialog nobody ever answers would hold the thread
#: it was asked on for as long as the board runs.
PATIENCE = 300.0
#: What the dialog says it is for, in the words the page beside it uses.
PROMPT = "Choose the folder your brief is in"
#: The same, for each field of the form that is a folder. Looked up by the field's name, never taken from
#: the request: the words go into a script the dialog runs, so only these words can.
PROMPTS = {"brief": PROMPT, "output": "Choose the folder the project is made in",
           "root": "Choose the repository to adopt", "prd": "Choose the PRD to draft from"}
#: The fields whose answer is a file rather than a folder: the same dialog, asked for a file.
FILES = frozenset({"prd"})


def asking(start: Path, prompt: str = PROMPT, file: bool = False) -> list[str]:
    """The command that opens this machine's folder chooser at `start` — its file chooser, for a `file` —
    or `[]` where there is none.

    One per platform and each the one that platform already has: AppleScript's own `choose folder` on
    macOS, `zenity` or `kdialog` on a Linux desktop, and the folder browser in .NET's forms on Windows,
    which every Windows install carries.
    """
    where = str(start)
    if sys.platform == "darwin":
        return ["osascript", "-e", 'tell application "System Events" to activate',
                "-e", f'POSIX path of (choose {"file" if file else "folder"} with prompt "{prompt}" '
                      f'default location POSIX file "{where}")']
    if sys.platform == "win32":  # pragma: no cover — read on the platform it is for
        dialog = (f"$one = New-Object System.Windows.Forms.OpenFileDialog; $one.Title = '{prompt}'; "
                  f"$one.InitialDirectory = '{where}'; if ($one.ShowDialog() -eq 'OK') {{ $one.FileName }}"
                  if file else
                  "$one = New-Object System.Windows.Forms.FolderBrowserDialog; "
                  f"$one.Description = '{prompt}'; $one.SelectedPath = '{where}'; "
                  "if ($one.ShowDialog() -eq 'OK') { $one.SelectedPath }")
        return ["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Windows.Forms; " + dialog]
    zenity = ["zenity", "--file-selection", *([] if file else ["--directory"]), f"--title={prompt}",
              f"--filename={where}/"]
    for chooser in (zenity, ["kdialog", "--getopenfilename" if file else "--getexistingdirectory", where]):
        if which(chooser[0]):
            return chooser
    return []


def which(command: str) -> str | None:
    """Here rather than imported at the top so the one platform that needs it pays for it."""
    import shutil
    return shutil.which(command)


def chosen(start: Path, field: str = "brief") -> str:
    """The folder a person picked, or `""` where they cancelled or there was nothing to ask with.

    Cancelling is not a fault and neither is a machine with no chooser on it: both mean *no folder*, and
    the field keeps whatever it already held. The exit status is not read for that reason — every chooser
    here spells cancellation as a non-zero exit, and so does a chooser that could not start.
    """
    file = field in FILES
    start = start.parent if file and start.is_file() else start
    command = asking(start if start.is_dir() else Path.home(), PROMPTS.get(field, PROMPT), file)
    if not command:
        return ""
    try:
        done = subprocess.run(command, capture_output=True, text=True,  # noqa: S603 — a fixed command
                              timeout=PATIENCE, env=login_environment(), check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    picked = done.stdout.strip()
    return picked if picked and (Path(picked).is_file() if file else Path(picked).is_dir()) else ""
