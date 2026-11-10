"""Where trunk's CI is read: a remote, or a person's word that there is none, settled before the fleet sails.

The harbourmaster grants no merge it cannot check. Before each one it asks the forge whether trunk is green,
and a repository with no remote has no forge to ask, so every merge is refused until it has one or
`harbour.json` says `"ci": "off"`. game-club-manager found that out with three slices built and none merged:
the repository its person typed on the board had gone nowhere, because only a target that deploys was ever
handed it. So the board gives every project the remote it was told, and where it was told none it asks at
Cast off and Continue the build, once, rather than at the first merge after a day of work.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .cli_telegraph import read, write
from .errors import GenerationError
from .page_shell import esc
from .project.harbour import CONFIG

#: What Cast off and Continue the build say while the question stands, and what the card says above them.
ASK = ("This repository has no remote, so the harbourmaster can read no CI before a merge and would refuse "
       "every one the fleet asks for. Add the remote trunk's CI runs on, or say this project has no CI.")


def has_remote(root: Path) -> bool:
    return subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True,
                          check=False).returncode == 0


def ci_off(root: Path) -> bool:
    try:
        return read(root / CONFIG).get("ci") == "off"
    except GenerationError:
        return False


def unasked(root: Path) -> bool:
    """Whether a fleet cast off here would build slices it can never merge: a harbour with no `origin` and no
    `"ci": "off"`. Not a harbour at all — no git, no `harbour.json` — is nothing this can settle."""
    if not (root / ".git").exists() or not (root / CONFIG).is_file():
        return False
    return not has_remote(root) and not ci_off(root)


def add_remote(root: Path, url: str) -> str:
    """`origin`, set to the URL a person gave; what to do next, or a refusal saying why not.

    Added and not pushed: the repository may not exist on the forge yet, and the harbourmaster pushes trunk
    there with its first merge. Until it does, a forge it cannot read refuses that merge and says so."""
    url = url.strip()
    if not url:
        raise ValueError("a remote is a URL: git@github.com:you/name.git, or https://github.com/you/name.git")
    if has_remote(root):
        raise ValueError("this repository has an `origin` already; `git remote -v` says where")
    done = subprocess.run(["git", "remote", "add", "origin", url], cwd=root, capture_output=True, text=True,
                          check=False)
    if done.returncode != 0:
        said = (done.stderr or done.stdout).strip().splitlines()
        raise ValueError(f"git would not add it: {said[-1] if said else 'it gave no reason'}")
    return (f"origin is {url}. The harbourmaster reads trunk's CI there before every merge; push main to it "
            "(`git push -u origin main`) once the repository exists.")


def given(root: Path, url: str) -> str:
    """The remote typed when the project was made, added for a target that deploys nothing, or `""`.

    A target that deploys is handed it by `./init`, which pushes there as its last step. Every other target
    was handed nothing, and its fleet refused every merge for want of the remote the person had typed."""
    if not url.strip():
        return ""
    try:
        return add_remote(root, url)
    except ValueError as refused:
        return f"The remote was not added ({refused}); the board asks for it again before the fleet sails."


def no_ci(root: Path) -> str:
    """`"ci": "off"` in `harbour.json`, a person's word that this project has no CI to read."""
    held = read(root / CONFIG)
    held["ci"] = "off"
    write(root / CONFIG, held)
    return ("harbour.json says `\"ci\": \"off\"`: each merge is granted unverified, and the board says so rather "
            "than calling trunk green.")


def card(root: Path) -> str:
    """The question, above the strip, while it stands; nothing once it is answered."""
    if not unasked(root):
        return ""
    return ('<div class="card" id="remote-card"><h2>Before the fleet sails: where is trunk&#8217;s CI?</h2>'
            f'<p>{esc(ASK)}</p><div class="ask"><input id="remote-url" placeholder="git@github.com:you/name.git">'
            '<button class="go" id="remote-add">Add the remote</button>'
            '<button class="install" id="ci-off">This project has no CI</button></div></div>')
