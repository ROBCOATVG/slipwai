#!/usr/bin/env python3
"""Saying that an elected extension has a guard nobody agreed to — and never agreeing to it for anybody.

A guard is agreed to at `./init`, by a person, on a terminal. A project that elected an extension *before*
the extension had a guard was never asked: `slipwai migrate` brings the guard's files and its declaration,
and until this script nothing said that a refusal was waiting for somebody's yes. The extension cannot
write `.slipwai/guards.json` itself, and must not — that file is the agreement, and software that writes it
has agreed with itself.

    python3 scripts/extensions/guard_offer.py          # say what is owed, one line each; change nothing
    python3 scripts/extensions/guard_offer.py --ask    # and ask, where somebody is at a terminal

`make agents` runs the second and `slipwai migrate` the first, for its report and its catch-up page. Both
exit 0 whatever they found: an agreement nobody has given is not a failure of a projection.

**The only thing here that writes the registry is a person typing `y`.** With no terminal — a pipe, CI, an
agent's shell, `migrate` reading the output — it says the line and the command and moves on. The question is
asked on stdin and stdout and only where both are a terminal, so there is no device to open and a scripted
run cannot be asked by accident.

Two things are said and only one is asked. A guard an extension **gained** is asked about. A guard that
**changed** since it was agreed to — another script, something new it sees — is said with its command and
never folded into a yes about something else: the registry holds a guard as it was when a person agreed,
and goes on holding it until they agree again.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
AVAILABLE = HERE / "available-guards.json"
RUNNER = HERE / "guards.py"


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
REGISTRY = ROOT / ".slipwai/guards.json"
ELECTED = ROOT / ".slipwai/extensions.json"
#: The command a person types, by the path this project keeps its scripts at.
COMMAND = f"python3 {RUNNER.relative_to(ROOT).as_posix()}"
#: What each guard can stop, in the words a person deciding needs: `guards.py`'s, which are the keel's.
REFUSING = {
    "session": "stop a delegate's session before its first tool call",
    "before-search": "stop a search of the tree and tell the agent what to ask instead",
    "before-write": "stop a file being written and tell the agent why",
    "before-command": "stop a shell command running and tell the agent why",
    "before-fetch": "stop a URL being read and tell the agent where to look instead",
    "after-delegate": "reject a delegate's answer and have it asked again",
    "before-stop": "stop a session ending, and carry the turn on with the reason",
}


def read(path: Path) -> dict:
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return found if isinstance(found, dict) else {}


def elected() -> list[str]:
    """The extensions this project elected. One it did not elect is offered nothing: its files are here
    because every installed extension's are, and nobody chose it."""
    recorded = read(ELECTED).get("extensions")
    return sorted({key for key in recorded if isinstance(key, str)}) if isinstance(recorded, list) else []


def agreed() -> dict[str, dict[str, dict]]:
    """Per extension, each guard the registry holds for it, as it was agreed to."""
    found: dict[str, dict[str, dict]] = {}
    guards = read(REGISTRY).get("guards")
    for name, bodies in (guards.items() if isinstance(guards, dict) else ()):
        for body in (bodies if isinstance(bodies, list) else ()):
            if isinstance(body, dict) and isinstance(body.get("extension"), str):
                found.setdefault(body["extension"], {})[name] = {
                    word: value for word, value in body.items() if word != "extension"}
    return found


def owed() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Per elected extension: the guards it has gained that nobody agreed to, and the agreed ones that are
    no longer what was agreed to."""
    available, held = read(AVAILABLE), agreed()
    gained: dict[str, list[str]] = {}
    changed: dict[str, list[str]] = {}
    for key in elected():
        declared = available.get(key)
        for name, body in sorted(declared.items() if isinstance(declared, dict) else ()):
            if name not in held.get(key, {}):
                gained.setdefault(key, []).append(name)
            elif held[key][name] != body:
                changed.setdefault(key, []).append(name)
    return gained, changed


def lines() -> list[str]:
    """What is owed, a line an extension, each ending with the command that settles it."""
    gained, changed = owed()
    said = []
    for key, names in gained.items():
        what = "; ".join(REFUSING.get(name, name) for name in names)
        said.append(f"guards: {key} can refuse a tool call here, and nobody has agreed to it: it would {what}. "
                    f"It refuses nothing until a person agrees: {COMMAND} --elect {key}")
    for key, names in changed.items():
        said.append(f"guards: {key}'s {', '.join(names)} guard has changed since somebody agreed to it, and "
                    f"the one agreed to is the one that fires. To agree to it as it is now: "
                    f"{COMMAND} --elect {key}")
    return said


def announce(terminal: bool, ask: Callable[[str], str] = input, say: Callable[[str], object] = print) -> int:
    """Say what is owed; where somebody is there, ask about what was gained and agree only on a yes."""
    gained, _ = owed()
    if not terminal or not gained:
        for line in lines():
            say(line)
        return 0
    say("These extensions can refuse a tool call, and nobody has agreed to it:")
    for key, names in gained.items():
        for name in names:
            say(f"  {key}: {REFUSING.get(name, name)}")
    say("A guard never ends a stage — it stops one call and tells the agent why.")
    try:
        answer = ask("Allow them? [y/N]: ").strip().lower()
    except (EOFError, OSError, KeyboardInterrupt):
        answer = ""
    if answer in ("y", "yes"):
        done = subprocess.run([sys.executable, str(RUNNER), "--elect", *sorted(gained)], cwd=ROOT,
                              capture_output=True, text=True, check=False)
        say((done.stdout or done.stderr).strip() or "guards: the registry was not written")
    for line in lines():  # whatever is still owed: everything on a no, a changed guard either way
        say(line)
    return 0


def main(argv: list[str]) -> int:
    asking = "--ask" in argv and sys.stdin.isatty() and sys.stdout.isatty()
    try:
        return announce(asking)
    except Exception as error:  # noqa: BLE001 — a sentence that could not be said is not a failed projection
        print(f"guards: could not say what is agreed to here ({type(error).__name__}); "
              f"`{COMMAND} --elect <key>` agrees to an extension's guards", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
