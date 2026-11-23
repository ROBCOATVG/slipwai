#!/usr/bin/env python3
"""The captain's own session: one per stream, held open over the Agent Client Protocol, acting only through
`orders.py`.

**Only over the protocol.** A stream's captain is an agent only where the program can hold its session over
the protocol, because only there is it confined: the session's policy (`permit`) allows reading and running
this project's own `orders.py`, and refuses every other tool call. A captain run as a process with a shell of
its own — a harness's print mode — could reach anything in the project, and nothing checked afterwards can
tell every change from the fleet's own, so there is no such captain: where this harness has no proven
launch over the protocol, the stream runs on the program alone, exactly as it did before there was an agent,
and says so once (`STATUS`, beside its events, which the board's reader shows).

Its launch is the first of: a command named in `SLIPWAI_CAPTAIN` that starts an agent speaking the protocol
(the suite's stand-in is one); `SLIPWAI_CAPTAIN=1`, the initialised harness's launch row as `SLIPWAI_ACP=1`
reads it; otherwise the protocol launch of the harness this project runs (the row `harness.choose` names),
where the registry marks that launch proven and this machine can make it. Nothing is ever run in print mode. The session is started in the project's root, its conversation
`talk/<fairway>/_captain/`. Each wake-up hands it the event and the stream's state as the log says it now
(`events/<fairway>/state.json`), never what it remembers, so a cold start answers as a warm one would; each is
bounded by `captain.bound`, from when the session is ready.

**So its history is worth nothing, and it is never carried.** One session was held for a whole run and loaded
again at the next fleet start: manda's intake captain reached 655k tokens a call after 634 calls, every one of
them paying for a history the brief says not to believe. A captain program starts its session fresh, never
the one saved beside its conversation, and closes it at an event boundary once its context passes
`captain.context_ceiling` tokens (`CONTEXT_CEILING`), as the agent reports it in a `usage_update`. Where the
agent never reports it, `captain.wake_ceiling` wake-ups (`WAKE_CEILING`) stand in for the size.

**For the evals, and only for them**: `python3 scripts/agents/captain_agent.py decide <event file> [--bound
N]` wakes a captain once with a recorded event in a throwaway project the evals laid out, and prints
`{"exit", "timed_out", "tokens", "seconds", "orders"}`. It is not how a fleet runs a captain: it refuses to run
unless `SLIPWAI_EVAL=1` is set and the project carries the evals' marker (`EVAL_MARKER`), so it can never be
pointed at a real checkout.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
# budget: 550 — the captain session's whole policy in one place: the command parsed as a shell would, its reads, the
# launch only over the protocol, and the evals' one door, each beside the reasons it is confined so
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import drive  # noqa: E402
import harness  # noqa: E402
import logs  # noqa: E402
import captain_orders  # noqa: E402
import orders as order_door  # noqa: E402
import talk  # noqa: E402

COMMAND = "SLIPWAI_CAPTAIN"
#: Seconds a decision may take from when the captain's session is ready.
BOUND = 60.0
#: Events a stream's captain may be woken for in an hour before the stream runs on its rules alone.
PER_HOUR = 30
#: Tokens of context past which the captain's session is closed at the next event and a fresh one started.
CONTEXT_CEILING = 150_000
#: Wake-ups one captain session answers before a fresh one, where the agent never says how large its context is:
#: about a thousand tokens each, measured on manda, so near the same size as the token ceiling.
WAKE_CEILING = 100
BRIEF = "agents/drive-captain.md"
#: Beside a stream's events: whether its captain is an agent, and why not where it is not.
STATUS = "captain.json"
#: What the evals write at the root of a throwaway project they lay out; `decide` runs nowhere else.
EVAL_MARKER = order_door.EVAL_MARKER
NO_LAUNCH = "no captain agent: this harness has no proven protocol launch"


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
#: The one script a captain runs: this project's own, beside this file, never a copy in a berth.
ORDERS = HERE / "orders.py"


def settings(held: dict[str, Any]) -> dict[str, Any]:
    """`harbour.json`'s `captain`: whether the stream's captain is an agent (`agent`), how long a decision may
    take (`bound`), how many times an hour it may be woken (`per_hour`), how large its session's context may
    grow before a fresh one is started (`context_ceiling`, tokens) and, where the agent never reports that,
    how many wake-ups one session answers (`wake_ceiling`), and whether it may answer a slice's
    mid-turn question (`answers`, off unless true: the program cannot tell an operational question from a
    product one, and under `/cruise` nothing bounds the answers it gives, so by default a question is declined
    as it always was and goes down the deck log's `question` path). Absent, or anything but `agent: true`, is
    the program alone. `SLIPWAI_CAPTAIN` says first, as `SLIPWAI_ACP` does: `off` is the program alone
    whatever the file says; `1` (`true`, `yes`, `on`) turns the agent on through the project's own harness;
    any other value is the command that starts the captain's agent over the protocol."""
    said = held.get("captain") if isinstance(held.get("captain"), dict) else {}

    def number(name: str, fallback: float) -> float:
        value = said.get(name)
        return float(value) if isinstance(value, int | float) and not isinstance(value, bool) and value > 0 else fallback
    named = os.environ.get(COMMAND, "").strip()
    agent = named.lower() != "off" and (said.get("agent") is True or bool(named))
    return {"agent": agent, "bound": number("bound", BOUND), "answers": said.get("answers") is True,
            "per_hour": int(number("per_hour", PER_HOUR)),
            "context_ceiling": int(number("context_ceiling", CONTEXT_CEILING)),
            "wake_ceiling": int(number("wake_ceiling", WAKE_CEILING))}


def overridden(held: dict[str, Any]) -> str:
    """Where `SLIPWAI_CAPTAIN` in the environment, not `harbour.json`, is what turned the captain agent on or
    off, that said as one sentence; `''` where the two agree or the variable is unset."""
    named = os.environ.get(COMMAND, "").strip()
    said = held.get("captain") if isinstance(held.get("captain"), dict) else {}
    if not named or (named.lower() != "off") == (said.get("agent") is True):
        return ""
    return (f"SLIPWAI_CAPTAIN={'off' if named.lower() == 'off' else named[:60]} in the environment turns this "
            f"stream's captain agent {'off' if named.lower() == 'off' else 'on'}, whatever harbour.json says")


def command() -> str:
    """The command named in `SLIPWAI_CAPTAIN` to start the captain's agent, or `''` where it names none."""
    named = os.environ.get(COMMAND, "").strip()
    return "" if named.lower() in (*drive.ON, "off") else named


def launch() -> tuple[list[str], dict[str, Any] | None] | str:
    """How this stream's captain is started over the protocol: (argv, the harness row or None for a named
    command) — or why it cannot be, in which case the stream has no captain agent."""
    named = command()
    if named:
        return drive.words(named), None
    try:
        if os.environ.get(COMMAND, "").strip().lower() in drive.ON:
            rows = harness.registry()
            for key in harness.installed_keys():
                argv = drive.acp_launch(rows.get(key))
                if argv:
                    return argv, rows[key]
            return NO_LAUNCH
        row, _said = harness.choose()
    except harness.NoHarness:
        return NO_LAUNCH
    found = row.get("acp") if isinstance(row, dict) else None
    argv = drive.acp_launch(row) if isinstance(found, dict) and found.get("proven") is True else []
    return (argv, row) if argv else NO_LAUNCH


def order_command() -> str:
    """The command the captain runs to give an order: this program's own interpreter and this project's own
    `orders.py`, both by their paths, each quoted as one word. Handed to it in its prompt, and only there, so a
    shim on its PATH (pyenv, asdf, mise) is never what it runs and a project path with a space is still one."""
    return shlex.join([sys.executable, str(ORDERS)])


#: The commands the captain session was refused since the captain program last asked: how many, and the first —
#: kept to that, so what the deck log says of them is bounded however many it tries.
REFUSED: dict[str, Any] = {"count": 0, "first": "", "why": "", "shapes": []}
#: How much of a refused command is said: enough to recognise it, never the agent's words at length.
SAID = 80


def say_status(events: Path, agent: bool, why: str = "") -> None:
    """Write whether this stream's captain is an agent, why not, and since when, for the board's reader."""
    events.mkdir(parents=True, exist_ok=True)
    held = {"v": 1, "agent": agent, "t": logs.now(), **({"why": why} if why else {})}
    (events / STATUS).write_text(json.dumps(held) + "\n", encoding="utf-8")


def prompt(fairway: str, event: Path, state: Path, held: dict[str, Any]) -> str:
    """What the captain's session is asked at each wake-up: the brief, the event, the state, the one door."""
    return (f"You are the captain of the `{fairway}` stream of the project at {ROOT}. Read {ROOT / BRIEF} for what "
            f"you are asked and what you may do. Event {held['id']} ({held['kind']}) needs you: read {event}. The "
            f"stream's state, as its log says it now, is {state} — believe it over anything you remember. Act only "
            f"by running `{order_command()} <verb> … --event {held['id']}` — that command exactly, as written, with "
            f"every prose value in single quotes (`--why 'the third run failed; read the demo log'`, an apostrophe "
            f"written '\\''), since any other quoting of `;`, `$` or a backtick is refused — and "
            f"change nothing else anywhere; this "
            f"event takes {', '.join(held.get('may') or [])}. Say what you did in one sentence a person can read, "
            f"with `say`, where it is worth saying, and end your turn.")


# -- a turn, over the protocol ----------------------------------------------------------------------------------


class Held:
    """One event put to the captain's held session, whose policy (`permit`) holds it to reading and `orders.py`."""

    kind = "protocol"

    def __init__(self, driver: drive.Drive) -> None:
        self.driver = driver
        self.launched = time.monotonic()
        self.began: float | None = None

    def finished(self) -> bool:
        return self.driver.poll() is not None

    def started(self) -> float:
        return self.launched

    def ready(self) -> float | None:
        # Ready once its turn has begun: the agent is up, its session open, and the prompt with it. A session
        # that is not ready within the bound has its event closed by the rule (`captain_events.Helm.watch`).
        if self.began is None and (self.driver.turning or self.driver.poll() is not None):
            self.began = time.monotonic()
        return self.began

    def end(self) -> None:
        self.driver.terminate()  # the turn is cancelled; the session stays for the next event


def permit(tool_call: Any, options: Any) -> str | None:
    """The captain session's policy: running this project's own `orders.py` alone, and reading its own brief,
    events and deck and the project's files; nothing else, wherever it is. Its hands are the orders, which the
    program checks. Decided on the whole request: a request carrying a command is judged as a command whatever
    its `kind` says, one with no `kind` that carries a command is an execute, and a shape this does not expect
    is refused and counted with its keys named, so a supervised run shows at once what its harness sent."""
    if not isinstance(tool_call, dict) or not isinstance(options, list):
        return refuse(None, "", f"a request that is not a tool call and its options ({type(tool_call).__name__}, "
                                f"{type(options).__name__})", shape=True)
    offered = [one for one in options if isinstance(one, dict)]
    allowed = next((str(one["optionId"]) for one in offered if one.get("kind") == "allow_once" and "optionId" in one), None)
    refused = next((str(one["optionId"]) for one in offered if one.get("kind") == "reject_once" and "optionId" in one), None)
    kind = str(tool_call.get("kind") or "")
    raw = tool_call.get("rawInput")
    if raw is not None and not isinstance(raw, dict):
        return refuse(refused, "", f"rawInput that is not an object ({shape_of(tool_call)})", shape=True)
    if kind == "execute" or "command" in (raw or {}):
        why = refusal(tool_call)
        if allowed and not why:
            return allowed
        return refuse(refused, str((raw or {}).get("command") or tool_call.get("title") or "a command"),
                      why or "no way to allow it was offered")
    if kind == "think" and not tool_call.get("locations") and not paths(raw or {}):
        return allowed or refuse(refused, "", "no way to allow it was offered")
    if kind == "read":
        why = own_read(tool_call)
        if allowed and not why:
            return allowed
        return refuse(refused, f"read {', '.join(places_of(tool_call))[:SAID]}", why or "no way to allow it was offered")
    return refuse(refused, "", f"a request of a shape not expected ({shape_of(tool_call)})", shape=True)


def refuse(refused: str | None, said: str, why: str, shape: bool = False) -> str | None:
    """Count one refusal for the event's `noted` line, the first said with its reason, and every unexpected
    shape by its keys alone; then refuse."""
    REFUSED["count"] += 1
    if shape and why not in REFUSED["shapes"] and len(REFUSED["shapes"]) < 3:
        REFUSED["shapes"].append(why)
    if not REFUSED["first"]:
        # The order command's two long paths said once, at the end, so what is cut short is what it added.
        shown = said.replace(order_command(), "<order command>", 1) if said else "a request"
        REFUSED["first"] = " ".join(shown.split())[:SAID]
        REFUSED["why"] = why
    return refused


def shape_of(tool_call: dict[str, Any]) -> str:
    """A request's shape by its keys alone, never their values: what a supervised run needs to see."""
    raw = tool_call.get("rawInput")
    inner = f"; rawInput keys {', '.join(sorted(map(str, raw))) or 'none'}" if isinstance(raw, dict) else ""
    return f"kind {tool_call.get('kind') or 'none'}; keys {', '.join(sorted(map(str, tool_call))) or 'none'}{inner}"


#: The `rawInput` fields a harness names a file to read by.
PATHS = ("path", "filePath", "file_path", "abs_path", "absolute_path", "file", "filename", "target_file")


def paths(raw: dict[str, Any]) -> list[str]:
    return [str(raw[name]) for name in PATHS if raw.get(name) not in (None, "")]


def places_of(tool_call: dict[str, Any]) -> list[str]:
    found = [str(one.get("path") if isinstance(one, dict) else one) for one in tool_call.get("locations") or []]
    raw = tool_call.get("rawInput")
    return found + (paths(raw) if isinstance(raw, dict) else [])


def own_read(tool_call: dict[str, Any]) -> str:
    """Why the captain session may not read what a read names, or `''`: each place one plain file of this
    project, no secret by name, nothing under `.slipwai/` or `.git/` but its own stream's events and the deck
    logs (`captain_orders.unreadable`, the rule a slice's read through its captain is held to), and nothing
    outside the project, which it never needs."""
    places = places_of(tool_call)
    if not places:
        return "a read that names no file"
    run = logs.run_dir(ROOT)
    for place in places:
        why = captain_orders.unreadable(place, ROOT, ROOT, (run / "events", logs.logs_dir(ROOT)))
        if why:
            return why
    return ""


def keyed(tool_call: dict[str, Any]) -> bool:
    """Whether a tool call reads something the captain may not (`own_read`): the old name, kept for its readers."""
    return bool(own_read(tool_call))


#: Outside any quotes, what a shell would read as more than words: a second command, a redirection, a
#: substitution, a subshell, a glob, a comment. Each refuses the command; inside single quotes each is a letter.
BARE = {";": "a `;`", "&": "an `&`", "|": "a `|`", ">": "a `>`", "<": "a `<`", "`": "a backtick", "$": "a `$`",
        "(": "a `(`", ")": "a `)`", "*": "a `*`", "?": "a `?`", "[": "a `[`", "\n": "a new line", "~": "a `~`",
        "{": "a `{`", "}": "a `}`"}


def tokens(command: str) -> list[str] | str:
    """A command split as a POSIX shell splits it, or why it is refused. Parsed, never scanned: text in single
    quotes is inert and may hold anything a sentence holds — `;`, a backtick, `$0.01`, `draft -> sent` — which
    is where the brief tells the captain to put every prose value. Inside double quotes a `$`, a backtick or a
    line continued is refused, since there the shell would still expand it; outside quotes anything a shell
    reads as more than words (`BARE`) is refused, as is a `#` that begins a word, which would hide the rest."""
    words: list[str] = []
    word: list[str] = []
    started = False
    index, size = 0, len(command)
    while index < size:
        char = command[index]
        if char == "'":
            end = command.find("'", index + 1)
            if end < 0:
                return "a single quote that is never closed"
            word.append(command[index + 1:end])
            started, index = True, end + 1
            continue
        if char == '"':
            index += 1
            while index < size and command[index] != '"':
                char = command[index]
                if char in "$`":
                    return f"{BARE[char]} inside double quotes, where the shell expands it: single-quote prose"
                if char == "\\" and index + 1 < size:
                    if command[index + 1] == "\n":
                        return "a line continued inside double quotes"
                    if command[index + 1] in '"\\':
                        index += 1
                word.append(command[index])
                index += 1
            if index >= size:
                return "a double quote that is never closed"
            started, index = True, index + 1
            continue
        if char == "\\":
            if index + 1 >= size or command[index + 1] == "\n":
                return "a line continued outside quotes"
            word.append(command[index + 1])  # `'it'\''s'`: the brief's way to write an apostrophe
            started, index = True, index + 2
            continue
        if char in " \t":
            if started:
                words.append("".join(word))
            word, started, index = [], False, index + 1
            continue
        if char in BARE:
            return f"{BARE[char]} outside quotes"
        if char == "#" and not started:
            return "a `#` outside quotes, which begins a comment"
        if char == "=" and not started:
            return "a word that begins with `=` outside quotes, which a shell may expand"
        word.append(char)
        started, index = True, index + 1
    if started:
        words.append("".join(word))
    return words


def ordering(tool_call: dict[str, Any]) -> bool:
    """Whether a command is one run of this project's own `orders.py`, and nothing beside it (`refusal`)."""
    return not refusal(tool_call)


def refusal(tool_call: dict[str, Any]) -> str:
    """Why a command is not one run of this project's own `orders.py` under the very interpreter this program
    runs under, or `''` where it is: its first two words exactly the two the prompt handed the captain — no
    shell, no name looked up on PATH (a shim answers that), no copy of the script in a berth a slice could have
    edited — and nothing where the command itself cannot be read: the display title is never taken for it."""
    raw = tool_call.get("rawInput") if isinstance(tool_call, dict) else None
    command = raw.get("command") if isinstance(raw, dict) else None
    if not isinstance(command, str) or not command:
        return "no command could be read"
    # What the tokenizer does not see is not run: its own environment, words beside the command, another folder.
    if raw.get("env"):
        return "it sets an environment of its own"
    if raw.get("args"):
        return "it carries words beside its command line"
    try:
        if raw.get("cwd") and not Path(str(raw["cwd"])).resolve().is_relative_to(ROOT.resolve()):
            return "it runs from a folder outside the project"
        words = tokens(command)
        if isinstance(words, str):
            return words
        if len(words) < 2 or words[0] != sys.executable or not Path(words[1]).is_absolute():
            return "not the order command as it was handed"
        return "" if Path(words[1]).resolve() == ORDERS.resolve() else "it runs another copy of `orders.py`"
    except (OSError, ValueError, RuntimeError):
        return "its paths cannot be read (a NUL, or a loop of links)"


class Runner:
    """The stream's captain session, held open across events; one that will not start closes each event by the
    rule, and is tried again at the next."""

    def __init__(self, fairway: str, run: Path, bounds: dict[str, Any], started: tuple[list[str], dict[str, Any] | None]) -> None:
        self.fairway, self.run, self.bounds = fairway, Path(run), bounds
        self.argv, self.row = started
        self.driver: drive.Drive | None = None
        #: Wake-ups the held session has answered: the stand-in for its size where the agent never says it.
        self.wakes = 0

    def bound(self, turn: Any) -> float:
        return float(self.bounds["bound"])

    def refusals(self) -> str:
        """What the session was refused since this was last asked — once an event — as one sentence for the deck
        log: how many commands, and the first, cut short. `''` where it was refused nothing."""
        count, first, why = int(REFUSED["count"]), str(REFUSED["first"]), str(REFUSED["why"])
        shapes = list(REFUSED["shapes"])
        REFUSED.update(count=0, first="", why="", shapes=[])
        if not count:
            return ""
        return (f"the captain session was refused {count} command{'s' if count > 1 else ''} in one event, the first "
                f"`{first}` for {why}: it may run only `{order_command()} …`, prose in single quotes"
                + (f"; refused as shapes not expected: {' | '.join(shapes)}" if shapes else ""))

    def holds_session(self) -> bool:
        return self.driver is not None and self.driver.alive

    def reset(self) -> None:
        """Close the held session, so the next wake-up starts one with the key as it now is."""
        self.close()
        self.driver = None

    def outgrown(self) -> str:
        """Why the held session is past its ceiling and is to be closed before this event, or `''`.

        Asked at an event boundary — before a prompt, never during a turn — so nothing the captain is doing is
        cut short. The context the agent last reported, where it reports one; otherwise the wake-ups answered."""
        driver = self.driver
        if driver is None:
            return ""
        used = getattr(driver, "context", None)
        ceiling = int(self.bounds.get("context_ceiling") or CONTEXT_CEILING)
        if isinstance(used, int):
            return f"its context holds {used} tokens, past the ceiling of {ceiling}" if used > ceiling else ""
        wakes = int(self.bounds.get("wake_ceiling") or WAKE_CEILING)
        return (f"it has answered {self.wakes} wake-ups, the ceiling where the agent never says how large its "
                f"context is" if self.wakes >= wakes else "")

    def wake(self, event: Path, state: Path, held: dict[str, Any], env: dict[str, str]) -> Any:
        text = prompt(self.fairway, event, state, held)
        if self.driver is not None and self.driver.unlaunched:
            why = self.driver.unlaunched
            self.driver = None
            return f"its session would not start over the protocol ({why})"
        if self.driver is not None and self.driver.alive:
            grown = self.outgrown()
            if not grown:
                self.wakes += 1
                self.driver.prompt(text)
                return Held(self.driver)
            drive.say(f"captain: {self.fairway}'s captain session is closed for a fresh one: {grown}")
            self.reset()
        home = talk.place(self.run, self.fairway, talk.CAPTAIN)
        environment = {**harness.child_environment(self.row), **drive.acp_environment(self.row), **env}
        # Fresh, always: never the session saved beside the conversation, which a fleet start would otherwise
        # load with every wake-up of the run before it in its context.
        self.driver = drive.Drive(self.argv, ROOT, environment, text, kept=self.run / "acp" / f"_captain-{self.fairway}",
                                  conversation=home, activity=self.run / "activity" / self.fairway / "_captain.jsonl",
                                  fresh=True, harness_key=str((self.row or {}).get("key") or ""), inbox=False,
                                  permit=permit)
        self.wakes = 1
        return Held(self.driver)

    def close(self) -> None:
        if self.driver is not None:
            self.driver.end()


# -- the evals' door, and nothing else's ---------------------------------------------------------------------------


def evaluate(event: Path, bound: float) -> dict[str, Any]:
    """Wake a captain once with a recorded event, in a project the evals laid out, and say how it ended. The
    captain is the command named in `SLIPWAI_CAPTAIN`, run with the event's path; the orders are files."""
    import secrets
    if os.environ.get("SLIPWAI_EVAL") != "1" or not (ROOT / EVAL_MARKER).is_file():
        raise SystemExit(f"captain_agent: `decide` is the evals' door alone: it runs only with SLIPWAI_EVAL=1 in a "
                         f"project the evals laid out ({EVAL_MARKER} at its root). A fleet runs its captain over "
                         f"the protocol, never this way")
    named = command()
    if not named:
        raise SystemExit("captain_agent: name the captain under test in SLIPWAI_CAPTAIN")
    fairway = event.parent.name
    # The run folder the event is in, as the contract lays it out (`<run>/events/<fairway>/<id>.json`).
    run = event.parents[2] if event.parent.parent.name == "events" else logs.run_dir(ROOT)
    orders = run / "orders" / fairway
    before = {path.name for path in orders.glob("*.json")} if orders.is_dir() else set()
    env = {**os.environ, order_door.KEY: secrets.token_hex(32), order_door.FAIRWAY: fairway,
           order_door.EVENTS: str(event.parent), order_door.ORDERS: str(orders), "SLIPWAI_STAGE": "captain",
           "SLIPWAI_CAPTAIN_ORDERS_PY": str(ORDERS), "SLIPWAI_CAPTAIN_WAIT": "0"}
    began = time.monotonic()
    child = subprocess.Popen([*drive.words(named), str(event)], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name != "nt")
    timed_out = False
    try:
        child.wait(timeout=bound)
    except subprocess.TimeoutExpired:
        timed_out = True
        drive.end_group(child.pid, hard=True)  # the command and all it started, on every platform
        child.kill()
        child.wait()
    after = sorted(path.stem for path in orders.glob("*.json")
                   if path.name not in before and not path.name.endswith(".result.json")) if orders.is_dir() else []
    return {"exit": child.returncode, "timed_out": timed_out, "tokens": None,
            "seconds": round(time.monotonic() - began, 3), "orders": after}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="captain_agent", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="what", required=True)
    decide = sub.add_parser("decide", help="the evals' door: wake a captain once with an event, in their project")
    decide.add_argument("event", type=Path)
    decide.add_argument("--bound", type=float, default=BOUND, help="seconds")
    parsed = parser.parse_args(argv)
    print(json.dumps(evaluate(parsed.event.resolve(), parsed.bound)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
