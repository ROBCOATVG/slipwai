"""Whether the folder the board reads is level with the forge's trunk, and what of the person's is only here.

The board draws the project from one checkout — the folder it was pointed at, which is usually the person's
own — and the harbourmaster merges onto the forge. On manda the two came apart for a whole day: the forge's
`main` took 493 commits while the checkout sat where it was last pulled, so the board drew a project with
none of the day's slices as if it were the current one, and three commits made on that checkout's `main`
were never pushed and never mentioned while the fleet reused their decision numbers on trunk (slipwai#166).

This is the reading both of those want, from git and nothing else, against `origin/<trunk>` as the last
fetch left it — the harbourmaster fetches before every merge and its push moves it too, so on a running
harbour that is the forge's trunk give or take one pass:

- **behind**: how many of the forge's trunk commits this folder's `HEAD` does not hold, which is how old the
  project the board is drawing is;
- **stranded**: the commits on the local trunk branch the forge's trunk does not have, each as its short id
  and subject. Nothing here moves them; the board names them so a person lands them before anything that
  tidies a checkout throws them away.

Nothing where there is no repository, no local trunk or no `origin/<trunk>`: a harbour with no forge has
nothing to be behind.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .need_check import git, trunk_name


def level(root: Path, configured: object = None) -> dict[str, Any]:
    """`{"trunk", "behind", "stranded"}` for this folder against the forge's trunk, or `{}` where there is none."""
    name = trunk_name(root, configured)
    remote = f"refs/remotes/origin/{name}"
    if git(root, "rev-parse", "--verify", "--quiet", remote).returncode != 0:
        return {}
    counted = git(root, "rev-list", "--count", f"HEAD..{remote}")
    behind = int(counted.stdout.strip()) if counted.returncode == 0 and counted.stdout.strip().isdigit() else 0
    stranded: list[str] = []
    if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
        found = git(root, "log", "--format=%h %s", f"{remote}..refs/heads/{name}")
        stranded = [line.strip() for line in found.stdout.splitlines() if line.strip()] if found.returncode == 0 else []
    return {"trunk": name, "behind": behind, "stranded": stranded}
