"""Where trunk's CI is read: a remote, or a person's word that there is none, settled before the fleet sails.

The harbourmaster grants no merge it cannot check. Before each one it asks the forge whether trunk is green,
and a repository with no remote has no forge to ask, so every merge is refused until it has one or
`harbour.json` says `"ci": "off"`. game-club-manager found that out with three slices built and none merged:
the repository its person typed on the board had gone nowhere, because only a target that deploys was ever
handed it. So the board gives every project the remote it was told, and where it was told none it asks at
Cast off and Continue the build, once, rather than at the first merge after a day of work.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from .cli_telegraph import read, write
from .errors import GenerationError
from .init_run import Step
from .page_shell import esc
from .project.harbour import CONFIG
from .shell_environment import login_environment

#: What Cast off and Continue the build say while the question stands, and what the card says above them.
#: A remote on GitHub, as `owner/name`, in either spelling git takes: `git@github.com:o/n.git` or `https://...`.
GITHUB = re.compile(r"github\.com[:/](?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?/?$")

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


def add_remote(root: Path, url: str, now: bool = True) -> str:
    """`origin`, set to the URL a person gave; what to do next, or a refusal saying why not.

    Then published — created on GitHub where it is missing, and main pushed — so the forge has a trunk whose
    CI the harbourmaster can read before the first merge. Not `now` when the project is still being made:
    `publishing` does it once `./init`'s work is committed."""
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
    lines: list[str] = []
    if now:
        publish(root, lines.append)
    return " ".join([f"origin is {url}.", *lines])


def publish(root: Path, say: Callable[[str], None]) -> None:
    """`main` pushed to `origin`, the repository created on GitHub first where it is not there: what the cloud
    targets' `bootstrap.py push` has always done at the end of `./init`, for a target that deploys nothing.

    game-club-manager-new was given a remote on the board and nothing ever created it: a remote that does not
    exist is one the harbourmaster cannot read trunk's CI on, so its first merge would have been refused.
    Private, as the cloud targets make it. Anything that goes wrong is said, never raised — the project is
    made either way, and pushing is one command a person can run afterwards."""
    url = remote_url(root)
    if not url:
        return
    env = login_environment(root=root)

    def run(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(argv), cwd=root, env=env, capture_output=True, text=True, check=False)

    found = GITHUB.search(url)
    if found and shutil.which("gh", path=env.get("PATH")) and run("gh", "repo", "view", found["repository"]).returncode:
        made = run("gh", "repo", "create", found["repository"], "--private")
        if made.returncode:
            say(f"{found['repository']} is not on GitHub and could not be created ({last_line(made)}). Create it, "
                "empty, then `git push -u origin main`; until then the fleet's first merge is refused.")
            return
        say(f"Created {found['repository']} on GitHub, private.")
    pushed = run("git", "push", "-u", "origin", "HEAD")
    if pushed.returncode:
        say(f"main was not pushed to {url} ({last_line(pushed)}). Once the repository exists and you can push to "
            "it, `git push -u origin main`; until then the fleet's first merge is refused.")
        return
    say(f"Pushed main to {url}. Each merge the fleet makes is pushed there, and trunk's CI is read there.")


def publishing(root: Path) -> tuple[Step, ...]:
    """The step that publishes, for after `./init`'s commit; none where there is no `origin` to publish to —
    a target that deploys is given its remote by `./init` itself, and its bootstrap pushes."""
    if not has_remote(root):
        return ()
    return (Step([], "", lambda code: "", "init", stops=False,
                 session=lambda fitting: published(root, fitting.say)),)


def published(root: Path, say: Callable[[str], None]) -> int:
    """`publish` as a step: always 0, because what went wrong is said and the project is made either way."""
    publish(root, say)
    return 0


def remote_url(root: Path) -> str:
    """`origin` as it was given, not as `insteadOf` rewrites it: the forge is named by what the person typed."""
    done = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=root, capture_output=True,
                          text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def last_line(done: subprocess.CompletedProcess[str]) -> str:
    said = (done.stderr or done.stdout).strip().splitlines()
    return said[-1] if said else f"exit {done.returncode}"


def given(root: Path, url: str) -> str:
    """The remote typed when the project was made, added for a target that deploys nothing, or `""`.

    A target that deploys is handed it by `./init`, which pushes there as its last step. Every other target
    was handed nothing, and its fleet refused every merge for want of the remote the person had typed."""
    if not url.strip():
        return ""
    try:
        return add_remote(root, url, now=False)
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
