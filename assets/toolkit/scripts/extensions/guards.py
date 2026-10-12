#!/usr/bin/env python3
"""Running an extension's guard before a tool call, and carrying a refusal back to the agent.

The sibling of `hooks.py`, and the differences are the point.

A hook runs around a rung and **is never fatal to it**: it is reported and the rung completes, because an
extension that could fail a stage can stop a delivery loop it was added to help. A guard runs in front of
one tool call and **may refuse that call**, by exiting 2 — and what it printed goes back to the agent, which
then does something else. The rung completes either way. No guard can end one.

    python3 scripts/extensions/guards.py before-search --query "def place_order" --stage implement

Exit 0: nothing refused, the call goes ahead. Exit 2: refused, and stderr is the reason the agent is given.
Anything a guard does other than exit 2 — a crash, a timeout, a non-zero code that is not 2 — is a hook's
behaviour: said on stderr, and the call goes ahead. A guard that cannot run is not a reason a delegate
cannot search.

`--elect <key>...` writes `.slipwai/guards.json`, and takes only the keys a person agreed to. An extension
is *elected* by being installed and *agreed to* by answering a question, because a guard refuses things a
person asked for. An extension that declares a guard nobody agreed to fires none.

`--offer <key>...` is that question, asked once by `./init` over the elected extensions: it says what each
one would be able to refuse and in whose words, then allows the ones agreed to. It reads and writes
`/dev/tty` rather than stdin and stdout, so a scripted or CI `./init` is not asked and agrees to nothing —
silence is *no*, which is the only safe direction for a question about refusing somebody's tool calls.

**Once per quickstart, not once per project.** A project generated from a quickstart carries
`.slipwai/quickstart.json`, and the guards it already records a yes for are allowed without being asked
about again: a person who said yes when they wrote that quickstart has said yes. What an extension has
*gained* since is asked about on its own, naming the new point and nothing else — so the question a person
reads is always a question they have not answered.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AVAILABLE = HERE / "available-guards.json"
#: Shorter than a hook's 30s: this is in front of a tool call somebody is waiting on.
DEFAULT_BUDGET = "5s"
#: The exit code that refuses. Every other one is a hook's behaviour.
REFUSE = 2


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
REGISTRY = ROOT / ".slipwai/guards.json"
#: What the quickstart this project came from already carries a person's agreement for, where it came from
#: one at all. Written by `slipwai generate`, read here and nowhere else.
RECORD = ROOT / ".slipwai/quickstart.json"


def seconds(budget: str) -> float:
    """A budget as seconds. A budget nobody can parse is not a reason a guard does not run."""
    text = str(budget).strip().lower()
    scale = {"s": 1.0, "m": 60.0, "h": 3600.0}.get(text[-1:], 1.0)
    try:
        return float(text.rstrip("smh")) * scale
    except ValueError:
        return 5.0


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}


def elect(keys: list[str]) -> int:
    """Write `.slipwai/guards.json` for the extensions `keys` names — the ones a person agreed to."""
    available = read(AVAILABLE)
    return write_registry({key: list(available.get(key, {})) for key in set(keys)}, available)


def write_registry(allowed: dict[str, list[str]], available: dict) -> int:
    """`.slipwai/guards.json` from exactly what is allowed: per extension, which of its guards may fire.

    Per guard rather than per extension, because an agreement is per guard from 13.4 on. An extension that
    was agreed to when a quickstart was written and has *gained* a point since fires the one it was agreed
    for and not the new one, until somebody is asked about that one — which is a sentence that cannot be
    written if the registry is a list of extension keys.
    """
    guards: dict[str, list[dict]] = {}
    for key in sorted(allowed):
        for name, body in sorted(available.get(key, {}).items()):
            if name in allowed[key]:
                guards.setdefault(name, []).append({"extension": key, **body})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({"v": 1, "guards": guards}, indent=2) + "\n", encoding="utf-8")
    attached = ", ".join(sorted(guards)) or "no guard"
    firing = sum(1 for key, names in allowed.items() if names and key in available)
    print(f"guards: {firing} extension(s) may refuse at {attached}")
    return 0


def agreed_already() -> dict[str, list[str]]:
    """Which guards this project's quickstart already carries a person's yes for.

    A quickstart is a set of answers somebody settled once, and one of those answers is *this extension may
    refuse a tool call*. Asking it again in every project generated from that quickstart is how a person
    learns to answer a question without reading it, which is the opposite of what the question is for.
    """
    document = read(RECORD)
    found = document.get("guards")
    if not isinstance(found, dict):
        return {}
    return {key: [name for name in names if isinstance(name, str)]
            for key, names in found.items() if isinstance(key, str) and isinstance(names, list)}


def newly(offered: dict[str, dict], already: dict[str, list[str]]) -> dict[str, dict]:
    """Each extension's guards nobody has agreed to yet: what a person is actually asked about.

    An extension with nothing new drops out of the question entirely rather than appearing with an empty
    list, because the question names what it asks and a row with nothing in it is a row that reads as a
    second request for the same permission.
    """
    found: dict[str, dict] = {}
    for key, declared in offered.items():
        new = {name: body for name, body in declared.items() if name not in already.get(key, ())}
        if new:
            found[key] = new
    return found


#: What each guard can stop, in the words a person deciding needs. The keel's `guards.py` is where these
#: are written; this is the copy a project reads, because there is no keel in a project to ask.
REFUSING = {
    "session": "stop a delegate's session before its first tool call",
    "before-search": "stop a search of the tree and tell the agent what to ask instead",
    "before-write": "stop a file being written and tell the agent why",
    "before-command": "stop a shell command running and tell the agent why",
    "before-fetch": "stop a URL being read and tell the agent where to look instead",
    "after-delegate": "reject a delegate's answer and have it asked again",
    "before-stop": "stop a session ending, and carry the turn on with the reason",
}


def offer(keys: list[str]) -> int:
    """Ask once whether the elected extensions may refuse tool calls, then allow the ones agreed to.

    Once per *quickstart*, not once per project (13.4): what the quickstart this project came from already
    carries a yes for is allowed without being asked about, and what an extension has gained since is asked
    about on its own. A project that came from no quickstart is asked about everything, as it always was.

    Over `/dev/tty`, so a scripted or CI `./init` is never asked — and agrees to nothing new. A question
    about whether software may refuse what a person told it to do has one safe answer when nobody is there.
    """
    available = read(AVAILABLE)
    offered = {key: available.get(key, {}) for key in sorted(set(keys)) if available.get(key)}
    if not offered:
        return elect([])
    already = agreed_already()
    # Only what this project actually has: a quickstart that agreed to an extension whose guards have gone
    # away carries a yes for nothing, and an entry for it would write a registry naming a guard nobody has.
    carried = {key: [name for name in already.get(key, []) if name in offered[key]] for key in offered}
    asked = newly(offered, carried)
    if not asked:
        print("guards: carried from this project's quickstart — "
              f"{sum(len(names) for names in carried.values())} already agreed to, nothing asked")
        return write_registry(carried, available)
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            if any(carried.values()):
                tty.write("\nYour quickstart already allows some of these to refuse a tool call. "
                          "This is what is new:\n")
            else:
                tty.write("\nThese extensions can refuse a tool call:\n")
            for key, declared in asked.items():
                for name in sorted(declared):
                    tty.write(f"  {key}: {REFUSING.get(name, name)}\n")
            tty.write("A guard never ends a stage — it stops one call and tells the agent why.\n")
            tty.write("Allow them? [y/N]: ")
            tty.flush()
            answer = tty.readline().strip().lower()
    except OSError:
        print("guards: nothing new asked and nothing new allowed — `./init` was not run from a terminal; "
              "`python3 scripts/extensions/guards.py --elect <keys>` allows them later", file=sys.stderr)
        return write_registry(carried, available)
    if answer in ("y", "yes"):
        for key, declared in asked.items():
            carried[key] = [*carried[key], *declared]
    return write_registry(carried, available)


def applies(body: dict, given: dict[str, str]) -> bool:
    """Whether this guard wants this rung. One that names no `stages` wants all of them."""
    stages = body.get("stages")
    return not isinstance(stages, list) or given.get("stage") in stages


def reason(run: subprocess.CompletedProcess) -> str:
    """What the agent is told. Everything the guard wrote, not just its last line — a refusal that says
    *ask the index instead, like this* is only useful whole, and this is the one place an extension gets to
    say something to the model rather than to a log."""
    said = ((run.stderr or "") + (run.stdout or "")).strip()
    return said or "refused, and said nothing about why"


def fire(name: str, given: dict[str, str]) -> int:
    """Run every guard on `name`. 2 as soon as one refuses; 0 otherwise.

    In extension-name order and stopping at the first refusal, because the call is already not happening and
    a second opinion about a call nobody is making is noise a person has to read.
    """
    for body in read(REGISTRY).get("guards", {}).get(name, []):
        key, script = body.get("extension", "?"), body.get("run", "")
        if not applies(body, given):
            continue
        path = ROOT / "scripts/extensions" / key / script
        if not path.is_file():
            print(f"guard {key} {name}: {path} is not in this project", file=sys.stderr)
            continue
        environment = {**os.environ, **{f"SLIPWAI_{word.upper()}": value for word, value in given.items()}}
        try:
            run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=ROOT,
                                 timeout=seconds(body.get("budget", DEFAULT_BUDGET)), env=environment)
        except subprocess.TimeoutExpired:
            # Not a refusal. A guard that ran out of time has said nothing, and a tool call stopped by
            # silence is a delegate blocked by a bug in something it was never told about.
            print(f"guard {key} {name}: over its {body.get('budget', DEFAULT_BUDGET)} budget, ended; the "
                  f"call goes ahead", file=sys.stderr)
            continue
        except OSError as error:
            print(f"guard {key} {name}: could not run ({type(error).__name__}); the call goes ahead",
                  file=sys.stderr)
            continue
        if run.returncode == REFUSE:
            print(reason(run), file=sys.stderr)
            return REFUSE
        if run.returncode != 0:
            print(f"guard {key} {name}: exited {run.returncode}, which is not a refusal; the call goes "
                  f"ahead", file=sys.stderr)
            continue
        if run.stdout.strip():
            print(run.stdout.strip())
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    if argv[0] == "--elect":
        return elect(argv[1:])
    if argv[0] == "--offer":
        return offer(argv[1:])
    given: dict[str, str] = {}
    rest = argv[1:]
    for index in range(0, len(rest) - 1, 2):
        if rest[index].startswith("--"):
            given[rest[index][2:]] = rest[index + 1]
    return fire(argv[0], given)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
