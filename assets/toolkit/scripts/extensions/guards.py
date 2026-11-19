#!/usr/bin/env python3
"""Running an extension's guard before a tool call, and carrying a refusal back to the agent.

The sibling of `hooks.py`, and the differences are the point.

A hook runs around a rung and **is never fatal to it**: it is reported and the rung completes, because an
extension that could fail a stage can stop a delivery loop it was added to help. A guard runs in front of
one tool call and **may refuse that call**, by exiting 2 — and what it printed goes back to the agent, which
then does something else. The rung completes either way. No guard can end one.

    python3 scripts/extensions/guards.py before-search --query "def place_order" --stage implement

`scripts/agents/session.py` is what fires it for real, from a harness's own event, and where the point has
an event it adds `--event stdin` and writes the event there: one JSON object, which each guard is handed on
its own stdin. Fired by hand as above there is none, and a guard reads the `SLIPWAI_<WORD>` variables.

Exit 0: nothing refused, the call goes ahead. Exit 2: refused, and stderr is the reason the agent is given.
Anything a guard does other than exit 2 — a crash, a timeout, a non-zero code that is not 2 — is a hook's
behaviour: said on stderr, and the call goes ahead. A guard that cannot run is not a reason a delegate
cannot search.

`--elect <key>...` agrees to the guards of the extensions it names, in `.slipwai/guards.json`, and keeps
every agreement already there; `--remove <key>...` takes one back and keeps the rest. An extension is
*elected* by being installed and *agreed to* by answering a question, because a guard refuses things a
person asked for. An extension that declares a guard nobody agreed to fires none.

A guard may also be **told** that a tool was used, where its declaration `sees` that tool: `guards.py
tool-use --tool <name>` runs it with the event on stdin and discards what it exits with. That is how an
extension knows its own MCP tool was called, and it cannot refuse the call by it.

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
import re
import subprocess
import sys
import tempfile
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


def agreed_now() -> dict[str, dict[str, dict]]:
    """What the registry records: per extension, each guard a person agreed to, as it was agreed to.

    Read from the file every time and kept whole, down to a field this script does not know, because it is
    the only record there is of somebody's answer — and it is read in the shape `--elect` has always
    written, so a registry from before agreeing was additive is still one.
    """
    found: dict[str, dict[str, dict]] = {}
    guards = read(REGISTRY).get("guards")
    for name, bodies in (guards.items() if isinstance(guards, dict) else ()):
        for body in (bodies if isinstance(bodies, list) else ()):
            if isinstance(body, dict) and isinstance(body.get("extension"), str):
                found.setdefault(body["extension"], {})[name] = {
                    word: value for word, value in body.items() if word != "extension"}
    return found


def offered_by(available: dict, key: str) -> dict[str, dict]:
    declared = available.get(key)
    return {name: body for name, body in declared.items() if isinstance(body, dict)} \
        if isinstance(declared, dict) else {}


def elect(keys: list[str]) -> int:
    """Agree to the guards of the extensions `keys` names, and keep every agreement already made.

    It used to write the registry from `keys` alone, so agreeing to one extension's guard withdrew every
    other's without a word (#121). An answer to *may this one refuse* is not an answer about the rest;
    `--remove` is how one is taken back. An extension named here is agreed to as it is offered now.
    """
    available, agreed = read(AVAILABLE), agreed_now()
    for key in sorted(set(keys)):
        declared = offered_by(available, key)
        if declared:
            agreed[key] = declared
        else:
            agreed.pop(key, None)
            print(f"guards: {key} offers no guard in this project, so there is nothing of its to agree to")
    return write_registry(agreed)


def remove(keys: list[str]) -> int:
    """Take back the agreement to the guards of the extensions `keys` names, and keep every other."""
    if not keys:
        print("guards: name the extension whose guards may no longer refuse a tool call: "
              "python3 scripts/extensions/guards.py --remove <key>", file=sys.stderr)
        return 1
    agreed = agreed_now()
    gone = [key for key in sorted(set(keys)) if agreed.pop(key, None) is not None]
    for key in sorted(set(keys) - set(gone)):
        print(f"guards: {key} has no guard agreed to here, so nothing was removed")
    return write_registry(agreed) if gone else 0


def write_registry(agreed: dict[str, dict[str, dict]]) -> int:
    """`.slipwai/guards.json` from exactly what is agreed: per extension, each of its guards that may fire.

    Per guard rather than per extension, because an agreement is per guard from 13.4 on. An extension that
    was agreed to when a quickstart was written and has *gained* a point since fires the one it was agreed
    for and not the new one, until somebody is asked about that one — which is a sentence that cannot be
    written if the registry is a list of extension keys.
    """
    guards: dict[str, list[dict]] = {}
    for key in sorted(agreed):
        for name, body in sorted(agreed[key].items()):
            guards.setdefault(name, []).append({"extension": key, **body})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({"v": 1, "guards": guards}, indent=2) + "\n", encoding="utf-8")
    attached = ", ".join(sorted(guards)) or "no guard"
    firing = sum(1 for names in agreed.values() if names)
    print(f"guards: {firing} extension(s) may refuse at {attached}")
    matched()
    return 0


def matched() -> None:
    """Have the harness run `tool-use` for exactly the tools the agreed guards see. Never a reason an
    agreement is not recorded: the registry is written, and `make agents` writes the row again."""
    script = HERE / "guard_harness.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=False)
    except OSError:
        return


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


def newly(offered: dict[str, dict], already: dict[str, dict]) -> dict[str, dict]:
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
    available, agreed = read(AVAILABLE), agreed_now()
    offered = {key: offered_by(available, key) for key in sorted(set(keys)) if offered_by(available, key)}
    if not offered:
        return elect([])
    already = agreed_already()
    # Only what this project actually has: a quickstart that agreed to an extension whose guards have gone
    # away carries a yes for nothing, and an entry for it would write a registry naming a guard nobody has.
    # And what was agreed to here already stays as it was agreed to: this is asked about the extensions one
    # `./init` named, and an extension it did not name was not asked about, so it is not withdrawn either.
    carried = {key: {name: agreed.get(key, {}).get(name, body) for name, body in offered[key].items()
                     if name in already.get(key, []) or name in agreed.get(key, {})} for key in offered}
    asked = newly(offered, carried)
    if not asked:
        print("guards: carried from this project's quickstart — "
              f"{sum(len(names) for names in carried.values())} already agreed to, nothing asked")
        return write_registry({**agreed, **carried})
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            if any(carried.values()):
                tty.write("\nYour quickstart already allows some of these to refuse a tool call. "
                          "This is what is new:\n")
            else:
                tty.write("\nThese extensions can refuse a tool call:\n")
            for key, declared in asked.items():
                for name in sorted(declared):
                    told = ", ".join(sees(declared[name]))
                    tty.write(f"  {key}: {REFUSING.get(name, name)}"
                              + (f" (and be told when {told} is used)\n" if told else "\n"))
            tty.write("A guard never ends a stage — it stops one call and tells the agent why.\n")
            tty.write("Allow them? [y/N]: ")
            tty.flush()
            answer = tty.readline().strip().lower()
    except OSError:
        print("guards: nothing new asked and nothing new allowed — `./init` was not run from a terminal; "
              "`python3 scripts/extensions/guards.py --elect <keys>` allows them later", file=sys.stderr)
        return write_registry({**agreed, **carried})
    if answer in ("y", "yes"):
        for key, declared in asked.items():
            carried[key] = {**carried[key], **declared}
    return write_registry({**agreed, **carried})


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


def ran(script: Path, environment: dict[str, str], budget: float, told: str = "") -> subprocess.CompletedProcess:
    """One guard, run with `told` on its stdin. Raises `TimeoutExpired` once it is over `budget` and ended.

    **The budget is the longest a call can wait, whatever the guard did** — so nothing here is a pipe. A
    pipe has a far end somebody has to service: an event longer than a pipe holds blocks its writer until a
    guard that never reads it exits, and output is not finished until every process holding it open has
    gone, so a guard that started something and was then ended at its budget could leave this waiting on a
    process nobody had a budget for. The event is a file the guard may read, and what it prints goes to two
    more. Its streams are UTF-8 unless it asked for something else, so the reason it printed reaches the
    agent as it was written, and not as the machine's code page read it.
    """
    command = [sys.executable, str(script)]
    with tempfile.TemporaryFile() as given, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        given.write(told.encode("utf-8"))
        given.seek(0)
        process = subprocess.Popen(command, stdin=given, stdout=out, stderr=err, cwd=ROOT,
                                   env={"PYTHONIOENCODING": "utf-8", **environment})
        try:
            code = process.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            process.kill()  # it, and only it: what it started is its own, and is not waited for
            process.wait()
            raise
        out.seek(0)
        err.seek(0)
        return subprocess.CompletedProcess(command, code, out.read().decode("utf-8", "replace"),
                                           err.read().decode("utf-8", "replace"))


#: The moment a guard is *told* a tool was used, which is not a guard point and refuses nothing.
TOOL_USE = "tool-use"
#: What a guard may declare under `sees`, held here over the registry as the keel holds it over a manifest:
#: one MCP server's tools, by name or all of them. Nothing that could match any other kind of call.
SEES = re.compile(r"mcp__[A-Za-z0-9_-]+__(?:[A-Za-z0-9_-]+|\.\*)")
SEES_LIMIT = 8


def sees(body: dict) -> list[str]:
    """The tool patterns this guard may be told about: its `sees`, less anything it may not declare."""
    declared = body.get("sees")
    return [pattern for pattern in (declared if isinstance(declared, list) else [])[:SEES_LIMIT]
            if isinstance(pattern, str) and SEES.fullmatch(pattern)]


def saw(given: dict[str, str], told: dict | None = None) -> int:
    """Tell every agreed guard that `sees` this tool that it is being used. Always 0: seeing is not judging.

    A guard's own tool reaches it this way — `codegraph`'s guard learns that a session asked the index —
    and the one thing it must never be able to do with that is stop the tool. So the code it exits with is
    discarded, a 2 included, and said where it was one: a guard written to refuse wherever it is run has
    refused nothing here.
    """
    tool = given.get("tool", "")
    event = json.dumps(told) if told is not None else ""
    for point, bodies in sorted(read(REGISTRY).get("guards", {}).items()):
        for body in bodies if isinstance(bodies, list) else []:
            if not isinstance(body, dict) or not applies(body, given):
                continue
            if not any(re.fullmatch(pattern, tool) for pattern in sees(body)):
                continue
            key = body.get("extension", "?")
            path = ROOT / "scripts/extensions" / key / str(body.get("run", ""))
            if not path.is_file():
                continue
            environment = {**os.environ, "SLIPWAI_POINT": TOOL_USE, "SLIPWAI_GUARD": point,
                           **{f"SLIPWAI_{word.upper()}": value for word, value in given.items()}}
            try:
                run = ran(path, environment, seconds(body.get("budget", DEFAULT_BUDGET)), event)
            except (subprocess.TimeoutExpired, OSError) as error:
                print(f"guard {key} {TOOL_USE}: {type(error).__name__}; the call goes ahead", file=sys.stderr)
                continue
            if run.returncode == REFUSE:
                print(f"guard {key} {TOOL_USE}: exited {REFUSE}, and a guard cannot refuse a tool it is only "
                      f"told about; the call goes ahead", file=sys.stderr)
    return 0


def fire(name: str, given: dict[str, str], told: dict | None = None) -> int:
    """Run every guard on `name`. 2 as soon as one refuses; 0 otherwise.

    In extension-name order and stopping at the first refusal, because the call is already not happening and
    a second opinion about a call nobody is making is noise a person has to read.

    `given` reaches a guard as `SLIPWAI_<WORD>` variables, and `told` — the event, where the point has one —
    as one JSON object on its stdin. A guard that reads only the variables is handed what it always was.
    """
    event = json.dumps(told) if told is not None else ""
    for body in read(REGISTRY).get("guards", {}).get(name, []):
        key, script = body.get("extension", "?"), body.get("run", "")
        if not applies(body, given):
            continue
        path = ROOT / "scripts/extensions" / key / script
        if not path.is_file():
            print(f"guard {key} {name}: {path} is not in this project", file=sys.stderr)
            continue
        environment = {**os.environ, "SLIPWAI_POINT": name,
                       **{f"SLIPWAI_{word.upper()}": value for word, value in given.items()}}
        try:
            run = ran(path, environment, seconds(body.get("budget", DEFAULT_BUDGET)), event)
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
    if argv[0] == "--remove":
        return remove(argv[1:])
    given: dict[str, str] = {}
    rest = argv[1:]
    for index in range(0, len(rest) - 1, 2):
        if rest[index].startswith("--"):
            given[rest[index][2:]] = rest[index + 1]
    # Only when told one is there: fired by hand, stdin is a keyboard, and nobody is going to type an event.
    told = sent() if given.pop("event", "") == "stdin" else None
    return saw(given, told) if argv[0] == TOOL_USE else fire(argv[0], given, told)


def sent() -> dict | None:
    """The event `session.py` wrote to this script's stdin, or nothing where it is not one."""
    try:
        read = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "null")
    except (OSError, ValueError):
        return None
    return read if isinstance(read, dict) else None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
