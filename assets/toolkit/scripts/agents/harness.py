#!/usr/bin/env python3
"""Which coding agent a headless session runs through, and the command that starts one.

Two things in this directory need to start a fresh harness session and ask it one thing: `cruise.py`, which
asks `/cruise` once an iteration, and `captain.py`, which asks `/sail` once a slice. They had one copy
between them and it was `cruise.py`'s — so the captain, which is the thing that will outlive the runner,
fell back to `scripts/agents/sail.py`. That script is the *settings reader* for `/sail`: handed a slice
and a fairway it prints its table and exits 0. A whole real run was reported through on the strength of it.

So the knowledge is here, and both callers read it:

**Which harness.** The first harness `.specify/integration.json` records as installed that has a verified
`headless` row in `registry.json` and whose binary is on PATH. Not the first one on PATH: a harness `./init`
never initialised here has no projected commands, no delegate types and no hook files, so the command being
asked for is unknown to it and the session ends having done nothing. One that is on PATH but uninitialised
is *named in the refusal*, with the `./init` that would add it, rather than driven.

**What to ask it.** A harness whose row says its print mode resolves this project's slash commands
(`prompt: "slash"`) is asked `/<command>`; every other is asked to read the command file and follow it,
which needs nothing of a harness beyond reading a file and is the same words whatever the harness.

**What the session must not inherit.** A harness session started from inside another's reads the parent's
identity out of the environment and either takes the parent's transcript for its own or refuses to start as
a nested copy. Every harness's session variable comes out, and the row's own `env` goes in.

**When it is finished.** A Claude Code print session can write its last `result` line, with every background
task it started reported back, and then not exit: the MCP servers it started (`npm exec chrome-devtools-mcp`,
`codegraph serve --mcp`) stay attached, and the script waiting on it waits for ever. `run_session` and
`Session` read the stream as it passes through and end a session that has said it is finished and is still
there a grace period later — it and everything it started — and report what the session itself said.

Nothing here decides anything about a run. It answers *how to start a session*, and the caller says what the
session is for. Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import contextlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO, Any

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "registry.json"


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
INTEGRATION = ROOT / ".specify/integration.json"
#: What `scripts/extensions/hooks.py --elect` wrote: the extensions this project elected, and the tool names
#: they need a session allowed to call. Read here rather than carried in `registry.json` because the tool
#: belongs to whoever brings it — the registry is the keel's catalogue of coding agents, and a tool name in
#: it is handed to every project whether it elected that extension or not (6.1c).
ELECTED = ROOT / ".slipwai/hooks.json"
#: The environment a harness session started from inside another's must not inherit: the parent's own
#: identity, or the child reads the parent's transcript as its own and refuses to start as a nested copy.
PARENT_SESSION_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


class NoHarness(RuntimeError):
    """No harness here can be asked anything, said as the one line a person reads and acts on."""


def registry() -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]}


def installed_keys() -> list[str]:
    """The harnesses Spec Kit recorded as installed here, in the order it recorded them; none where it never ran."""
    if not INTEGRATION.is_file():
        return []
    try:
        state = json.loads(INTEGRATION.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    keys = state.get("installed_integrations") or [state.get("default_integration")]
    return [key for key in keys if isinstance(key, str)]


def headless_row(harness: dict[str, Any] | None) -> dict[str, Any] | None:
    row = harness.get("headless") if harness is not None else None
    return row if isinstance(row, dict) else None


def binary_of(harness: dict[str, Any]) -> str:
    """The executable a harness's headless command starts with: what is looked for on PATH."""
    row = headless_row(harness)
    assert row is not None
    return shlex.split(str(row["command"]))[0]


def choose() -> tuple[dict[str, Any], str]:
    """The harness a session runs through, and a sentence saying why that one, or `NoHarness` saying why none.

    The refusal is the whole value of this function. "No harness" has three different causes and three
    different things a person does about them — one is installed and its binary is missing, one is installed
    and the registry records no way to run it headless, or one is on PATH and was never initialised here —
    and a run that said only "no harness" would send them to read source to tell which.
    """
    rows = registry()
    installed = [key for key in installed_keys() if key in rows]
    for key in installed:
        harness = rows[key]
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            return harness, f"harness: {harness['name']}"
    on_path = [harness for key, harness in rows.items()
               if key not in installed and headless_row(harness) is not None and shutil.which(binary_of(harness))]
    able = ", ".join(f"{harness['name']} (`{binary_of(harness)}`)" for harness in rows.values()
                     if headless_row(harness) is not None)
    named = ", ".join(rows[key]["name"] for key in installed) or "no harness is initialised here"
    words = " is installed" if len(installed) == 1 else " are installed" if installed else ""
    if installed and headless_row(rows[installed[0]]) is None:
        words += ", and the registry records no way to run it headless"
    elif installed:
        words += f", and `{binary_of(rows[installed[0]])}` is not on PATH"
    if on_path:
        found = ", ".join(f"{harness['name']} (`./init --integration {harness['key']}`)" for harness in on_path)
        raise NoHarness(f"no initialised harness a session can run through is on PATH: {named}{words}. On "
                        f"PATH but never initialised here, so its commands, delegate types and hooks are "
                        f"not projected: {found} — that init adds it beside what is installed; then run "
                        f"again")
    raise NoHarness(f"no harness a session can run through is on PATH: {named}{words}, and none of the "
                    f"harnesses the registry records a headless command for is on PATH — {able} "
                    f"(scripts/agents/registry.json, `headless`)")


def elected_tools(separator: str = ",") -> str:
    """The tool names this project's elected extensions declared, as one allow-list fragment.

    Empty — not the separator, not a stray comma — where nothing was elected or the election has not been
    run, which is the common case and the one a plain generated project is in. The leading separator is
    part of the fragment so that a row can write `'Bash,Skill{tools}'` and read correctly either way.
    """
    try:
        record = json.loads(ELECTED.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    names = [name for name in record.get("tools", []) if isinstance(name, str) and name.strip()]
    return "".join(f"{separator}{name.strip()}" for name in names)


def template(harness: dict[str, Any], sandbox: bool = False) -> tuple[str, str]:
    """The shell template a session runs, and the sentence saying which permissions it runs under."""
    headless = headless_row(harness)
    assert headless is not None
    permissions = str(headless.get("sandboxPermissions" if sandbox else "permissions", ""))
    # `{tools}` is where an elected extension's tool names join this harness's allow-list, in the spelling
    # the row around it already uses. A row with no placeholder gets nothing added: a harness whose allow
    # list this project has not been taught to extend is left exactly as the registry records it, rather
    # than handed a flag nobody checked it accepts.
    permissions = permissions.replace("{tools}", elected_tools())
    why = ("--sandbox: every permission check is bypassed, which is only for a container with nothing to lose"
           if sandbox else
           "edits are accepted and every other permission is the harness's own to grant or refuse; pass "
           "--sandbox inside a disposable container to bypass them all")
    said = str(headless["command"]).replace("{permissions}", permissions)
    # A headless session in a checkout nobody has trusted ignores the project's own MCP file on some
    # harnesses, so the row's `headlessFlags` make it honoured — passed only when the file exists, since a
    # flag naming a missing file refuses to start, and `{root}` is this checkout for a harness that trusts
    # by path. `{mcp}` is the file itself, by absolute path: a slice's session starts in its own worktree,
    # where a relative `.mcp.json` names a file that is not there when the branch was cut before the file
    # was committed — and the session exits 1 before its first line, every attempt.
    project = harness.get("projectMcp")
    if isinstance(project, dict) and project.get("headlessFlags") and (ROOT / str(project["file"])).is_file():
        flags = str(project["headlessFlags"]).replace("{mcp}", shlex.quote(str(ROOT / str(project["file"]))))
        said = f"{said} {flags.replace('{root}', str(ROOT))}"
    # The ladder's concurrent slices work in worktrees beside the checkout, which a print session under
    # `acceptEdits` is refused every edit in; the row's `worktreeFlags` name the directory the checkout sits
    # in as a second working directory, so a delegate's first edit is not its last.
    worktrees = headless.get("worktreeFlags")
    if worktrees:
        said = f"{said} {str(worktrees).replace('{parent}', shlex.quote(str(ROOT.parent)))}"
    return said, why


def model_flags(harness: dict[str, Any] | None, model: str | None) -> str:
    """What puts a session on a named model: the row's `modelFlag` with the identifier in it. Nothing where
    no model is named or where the row records no flag — the caller says which, because "the harness's own
    default ran" is a thing a reader has to be told rather than infer from a transcript."""
    headless = headless_row(harness)
    flag = headless.get("modelFlag") if headless is not None else None
    if not model or not flag:
        return ""
    return " " + str(flag).replace("{model}", shlex.quote(model))


def prompt_for(harness: dict[str, Any] | None, command: str, file: Path, argument: str | None = None) -> str:
    """What a session is asked: the slash command, or the words that make any harness read the file."""
    headless = headless_row(harness)
    if headless is not None and headless.get("prompt") == "slash":
        return f"/{command} {argument}" if argument else f"/{command}"
    where = file.relative_to(ROOT).as_posix() if file.is_relative_to(ROOT) else str(file)
    tail = f", with `{argument}` as its argument" if argument else "; it is given no argument"
    return f"Run the /{command} command: read {where} and follow it exactly as written{tail}."


def child_environment(harness: dict[str, Any] | None) -> dict[str, str]:
    """What a session runs under: this environment, plus what the row's `headless.env` sets — Claude Code's
    wait ceiling, which otherwise ends a print session while its delegates still run — and minus every
    harness's own session variables."""
    environment = dict(os.environ)
    for variable in PARENT_SESSION_VARIABLES:
        environment.pop(variable, None)
    for row in registry().values():
        session_variable = (row.get("usage") or {}).get("env")
        if session_variable:
            environment.pop(str(session_variable), None)
    headless = headless_row(harness)
    if headless is not None and isinstance(headless.get("env"), dict):
        environment.update({str(key): str(value) for key, value in headless["env"].items()})
    return environment


#: How long a session that has said it is finished is given to exit by itself before it is ended. Long
#: enough for a harness to flush its transcript and shut its own servers down, which takes a second or two
#: when it works at all; short against the failure this exists for, which was a `result` line followed by
#: seven minutes of nothing and a person reaching for `kill`.
END_GRACE = 30.0
#: How long a session asked to stop is given before it, and whatever it started, is killed outright.
STOP_GRACE = 5.0
#: How long the last of a session's output is waited for once it has exited. A server it started can hold
#: the pipe open after it has gone, and its output is over either way.
DRAIN = 2.0
#: A `task_updated` status that means the task is over even where its `task_notification` never comes.
TASK_OVER = frozenset({"completed", "failed", "killed", "stopped", "cancelled"})


def streams_events(argv: list[str]) -> bool:
    """Whether a session writes one JSON event per line (`--output-format stream-json`), which is the only
    shape whose end can be read. Every other harness's output is prose, and is left exactly as it was."""
    return any(arg == "stream-json" or arg.endswith("=stream-json") for arg in argv)


class Ending:
    """What a stream-json session has said so far about whether it is finished.

    Finished is two facts together, and the transcript that cost seven minutes had both: a `result` line,
    and no background task outstanding — every `task_started` answered by its `task_notification` (or a
    `task_updated` whose status says it is over), and the last `background_tasks_changed` naming nothing
    still open. A `result` alone is not the end: a session woken by a delegate's notification starts another
    turn after it, and an `init`, `assistant` or `user` line is that turn starting, so the `result` before it
    stops counting. What the session reported is the last `result`'s, because that is the turn it ended on.
    """

    def __init__(self) -> None:
        self.outcome: str | None = None
        self.erred = False
        self.started: set[str] = set()
        self.background: set[str] = set()
        self.over: set[str] = set()

    def read(self, line: bytes | str) -> None:
        try:
            event = json.loads(line)
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "result":
            self.outcome, self.erred = str(subtype), bool(event.get("is_error"))
        elif kind in ("assistant", "user") or (kind == "system" and subtype == "init"):
            self.outcome = None
        elif kind == "system" and subtype == "task_started":
            self.started.add(str(event.get("task_id")))
        elif kind == "system" and subtype == "task_notification":
            self.over.add(str(event.get("task_id")))
        elif kind == "system" and subtype == "task_updated":
            patch = event.get("patch")
            if isinstance(patch, dict) and patch.get("status") in TASK_OVER:
                self.over.add(str(event.get("task_id")))
        elif kind == "system" and subtype == "background_tasks_changed":
            tasks = event.get("tasks")
            tasks = tasks if isinstance(tasks, list) else []
            self.background = {str(task.get("task_id")) for task in tasks if isinstance(task, dict)}

    @property
    def outstanding(self) -> set[str]:
        return (self.started | self.background) - self.over

    @property
    def ended(self) -> bool:
        return self.outcome is not None and not self.outstanding

    @property
    def succeeded(self) -> bool:
        return self.outcome == "success" and not self.erred


class Session(subprocess.Popen[bytes]):
    """A headless session, started so that one which has said it is finished cannot keep its caller waiting.

    A `Popen`, so that the captain's watch on its deck log — which polls, terminates and kills — needs no
    change to drive one. For a stream-json session three things differ from a plain `Popen`:

    **Its output passes through here.** Line by line and flushed, unchanged, so a person watching sees what
    they saw before; each line is also read by an `Ending`.

    **It runs in a process group of its own,** so that ending it ends the servers it started too. Those are
    what kept the observed session alive, and signalling the session alone leaves them behind. `terminate`
    and `kill` signal the whole group for the same reason.

    **It is ended once finished.** When the `Ending` says so and the session is still there `END_GRACE`
    seconds after its last line, its group is sent SIGTERM, then SIGKILL after `STOP_GRACE`. The return code
    is then what the session *said*, 0 for a `success` result and 1 for anything else, rather than the 143 of
    a signal: a person killing it by hand is what used to turn finished work into a failed stage.

    Any other harness gets a plain `Popen` with nothing piped and nothing watched.
    """

    def __init__(self, argv: list[str], cwd: Path | str, env: dict[str, str]) -> None:
        # Set before `Popen.__init__`, which assigns `returncode` and so reaches the property below.
        self.streamed = streams_events(argv)
        self.ending = Ending()
        self.closed = False
        self.raw: int | None = None
        self.quiet_since: float | None = None
        self.lock = threading.Lock()
        # A process group of its own whatever the harness, so that ending it reaches what it started: the
        # captain's `end` signals the group by the session's pid, and a group that was never made is one
        # that signal misses without a word, leaving the session running.
        super().__init__(argv, cwd=cwd, env=env, stdout=subprocess.PIPE if self.streamed else None,
                         start_new_session=True)
        self.relay = threading.Thread(target=self.pass_through, daemon=True)
        if self.streamed:
            self.relay.start()
            threading.Thread(target=self.watch, daemon=True).start()

    @property
    def returncode(self) -> int | None:
        if self.raw is None or not self.closed:
            return self.raw
        return 0 if self.ending.succeeded else 1

    @returncode.setter
    def returncode(self, value: int | None) -> None:
        self.raw = value

    def pass_through(self) -> None:
        stdout: IO[bytes] | None = self.stdout
        assert stdout is not None
        sink = getattr(sys.stdout, "buffer", None)
        for line in iter(stdout.readline, b""):
            if sink is not None:
                sink.write(line)
            else:
                sys.stdout.write(line.decode("utf-8", errors="replace"))
            sys.stdout.flush()
            with self.lock:
                self.ending.read(line)
                self.quiet_since = time.monotonic() if self.ending.ended else None

    def watch(self) -> None:
        while subprocess.Popen.poll(self) is None:
            time.sleep(0.25)
            with self.lock:
                since = self.quiet_since
            if since is None or time.monotonic() - since < END_GRACE:
                continue
            self.closed = True
            print(f"session: it said it was finished ({self.ending.outcome}) and was still running "
                  f"{END_GRACE:.0f}s later, so it and the servers it started were stopped", file=sys.stderr,
                  flush=True)
            self.group(hard=False)
            with contextlib.suppress(subprocess.TimeoutExpired):
                subprocess.Popen.wait(self, timeout=STOP_GRACE)
            # Killed whether or not the session went: a server that ignored SIGTERM outlives its parent.
            self.group(hard=True)
            return

    def group(self, hard: bool) -> None:
        """SIGKILL (hard) or SIGTERM to the session's whole process group. Windows has no process groups to
        signal, so there the tree is ended through `taskkill /T` — the session and every process it started,
        which is the point: ending the session alone left its dev servers running on Windows."""
        if os.name == "nt":  # pragma: no cover - the other platform's branch
            with contextlib.suppress(OSError):
                subprocess.run(["taskkill", "/T", *(["/F"] if hard else []), "/PID", str(self.pid)],
                               capture_output=True, check=False)
            return
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.pid, signal.SIGKILL if hard else signal.SIGTERM)

    def terminate(self) -> None:
        self.group(hard=False)

    def kill(self) -> None:
        self.group(hard=True)

    def wait(self, timeout: float | None = None) -> int:
        code = super().wait(timeout)
        if self.streamed:
            self.relay.join(DRAIN)
        return code


def run_session(argv: list[str], cwd: Path | str, env: dict[str, str]) -> int:
    """Run one headless session to its end and return its exit status, or what it said where it was ended.

    A harness whose output is not stream-json runs exactly as `subprocess.run` ran it. A stream-json one
    runs as a `Session`, in a process group of its own — which a terminal's Ctrl-C does not reach, so an
    interrupt here ends the group itself before it is passed on.
    """
    if not streams_events(argv):
        return subprocess.run(argv, cwd=cwd, env=env, check=False).returncode
    return run_bounded(argv, cwd, env, None)[0]


def run_bounded(argv: list[str], cwd: Path | str, env: dict[str, str],
                seconds: float | None) -> tuple[int, bool]:
    """`run_session` with a wall-clock budget: the exit status, and whether the budget is what ended it.

    Any harness runs as a `Session` here, stream-json or not, because a budget has to be able to end the
    session *and everything it started* — the delegates a drawing fans out to are in its process group, and
    a budget that ended the parent alone would leave them drawing into a directory nobody is waiting on.
    At the budget the group is sent SIGTERM, then SIGKILL `STOP_GRACE` seconds later, which is the same
    pair the session's own end uses. Nothing it wrote is touched: what a session left is the caller's to
    count, and a stage that was ended at its budget usually left most of what it was asked for.

    `None` is no budget, and is `run_session` for a stream-json harness exactly.
    """
    session = Session(argv, cwd, env)
    try:
        try:
            return session.wait(seconds), False
        except subprocess.TimeoutExpired:
            pass
        session.terminate()
        try:
            session.wait(STOP_GRACE)
        except subprocess.TimeoutExpired:
            session.kill()
            session.wait()
        # Killed whether or not the session went: a delegate that ignored SIGTERM outlives its parent.
        session.group(hard=True)
        return session.raw if session.raw is not None else 1, True
    except BaseException:
        session.kill()
        session.wait()
        raise


#: Where the project declares its delegate types, which every harness's own directory is projected from.
TYPES = ROOT / "agents"


def current_key() -> str:
    """Which harness this session is running inside, from its own session variable, or `""`.

    Asked of the environment rather than of `.specify/integration.json`, because what is *installed* and
    what is *running right now* are different questions and only the second decides whether this session
    can delegate. Two rows declare the variable; where none is set the caller falls back to what is
    installed and says that it did, because a guess reported as a reading is the expensive kind.
    """
    for key, row in registry().items():
        variable = (row.get("usage") or {}).get("env")
        if variable and os.environ.get(str(variable)):
            return key
    return ""


def declared_types() -> list[str]:
    """The delegate types this project declares: one `agents/<name>.md` each, at the root and committed."""
    return sorted(path.stem for path in TYPES.glob("*.md")) if TYPES.is_dir() else []


def projected_types(harness: dict[str, Any]) -> tuple[str, list[str]]:
    """Where this harness reads its delegate types, and which of them are actually in this checkout."""
    row = harness.get("agentFile")
    if not isinstance(row, dict) or not row.get("dir"):
        return "", []
    where = str(row["dir"])
    extension = str(row.get("extension") or ".md")
    place = ROOT / where
    found = sorted(path.name[: -len(extension)] for path in place.glob(f"*{extension}")) if place.is_dir() else []
    return where, found


def delegation(key: str) -> dict[str, Any]:
    """Whether a session in this harness may delegate here, and the sentence that says why not.

    Three different noes, and a run told only *cannot delegate* would have to read source to tell which:
    the harness has no sub-agents at all, the types are declared and this checkout has none of them
    projected, or some are missing.

    The middle one is what this exists for. A cloud checkout has `agents/` from git and nothing under
    `.claude/agents/`, because the projections are derived and git ignores them — so a session there reads
    a method built on delegates and has none to call. That was the sentence nothing was in a position to
    write, and writing it is the whole of this.
    """
    harness = registry().get(key)
    if harness is None:
        return {"harness": key, "name": key, "able": False, "where": "", "declared": [], "projected": [],
                "why": f"no harness row is recorded for {key or 'this session'}, so nothing says whether "
                       f"it delegates"}
    name = str(harness.get("name") or key)
    declared = declared_types()
    where, found = projected_types(harness)
    answer = {"harness": key, "name": name, "where": where, "declared": declared, "projected": found}
    if not where:
        return {**answer, "able": False,
                "why": f"{name} has no delegate types: the registry records no directory it reads them "
                       f"from, so every slice a session here takes runs in that session"}
    if not declared:
        return {**answer, "able": False,
                "why": f"this project declares no delegate types in agents/, so there is nothing for "
                       f"{name} to delegate to"}
    missing = [one for one in declared if one not in found]
    if not found:
        return {**answer, "able": False,
                "why": f"{where}/ holds none of this project's {len(declared)} delegate types. They are "
                       f"derived from agents/ and git ignores them, so a fresh clone — a cloud runner, a "
                       f"new machine — has none. Run `make agents`, then start a new session: a harness "
                       f"reads its delegate types once, at session start"}
    if missing:
        return {**answer, "able": False,
                "why": f"{where}/ is missing {len(missing)} of {len(declared)} delegate types "
                       f"({', '.join(missing[:3])}{'…' if len(missing) > 3 else ''}). Run `make agents`, "
                       f"then start a new session"}
    return {**answer, "able": True,
            "why": f"{name} reads {len(found)} delegate type(s) from {where}/, so the ready set may fan out"}


def can_delegate() -> dict[str, Any]:
    """The answer for this session: its own harness where it says which, else what is installed here.

    How it was decided travels with the answer. *This session's own variable* and *the first of three
    installed* are different grades of evidence, and a ledger that recorded only the verdict would lose
    which one it rests on.
    """
    key = current_key()
    if key:
        return {**delegation(key), "how": "this session's own harness variable"}
    installed = [one for one in installed_keys() if one in registry()]
    if len(installed) == 1:
        return {**delegation(installed[0]), "how": "the one harness installed here; no session variable was set"}
    for one in installed:
        answer = delegation(one)
        if answer["able"]:
            return {**answer, "how": "an installed harness that can; no session variable said which is running"}
    if installed:
        return {**delegation(installed[0]),
                "how": "the first installed harness; no session variable said which is running"}
    return {"harness": "", "name": "", "able": False, "where": "", "declared": declared_types(),
            "projected": [], "how": "nothing is installed here",
            "why": "no harness is initialised in this checkout, so nothing projects delegate types and "
                   "there is nothing to delegate to. Run `./init`"}


def main(argv: list[str]) -> int:
    """`--can-delegate`: whether this session may fan out, as a sentence or as a record.

    Exit 1 where it may not, so a run that takes one slice at a time has a recorded reason rather than a
    judgement. `commands/sail.md` carries the prose; this carries the answer it was asserting.
    """
    if "--can-delegate" not in argv:
        print("harness: run `python3 scripts/agents/harness.py --can-delegate [--json]`", file=sys.stderr)
        return 2
    answer = can_delegate()
    if "--json" in argv:
        print(json.dumps({"v": 1, **answer}))
    else:
        print(f"harness: {'can delegate' if answer['able'] else 'cannot delegate'} — {answer['why']}")
        print(f"  decided by {answer['how']}")
    return 0 if answer["able"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
