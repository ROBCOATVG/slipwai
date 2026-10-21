#!/usr/bin/env python3
"""The harness's own moments, answered by the captain: the guards it refuses at and the hooks it fires.

Every coding harness has a handful of places it will run a command of yours and read what comes back —
before a tool call, before it compacts, when a turn tries to end. Version 1 reached three of them by having
the keel write `scripts/agents/cruise.py <verb>` straight into `.claude/settings.json`, which is how the
control-file refusal came to work on Claude Code and silently nowhere else.

This script is the one place those moments arrive, and it does two things with each: **the keel's own
answer**, and then **whatever an extension declared there**. The second half is the point — the moments are
`guards.py`'s and `hooks.py`'s closed sets, so an extension says `before-write` once and gets it on every
harness that has such an event, rather than learning each harness's spelling.

    python3 scripts/agents/session.py before-write   < the harness's event on stdin
    python3 scripts/agents/session.py before-stop    < the harness's event on stdin

**A guard moment may refuse; a hook moment may not.** `before-write`, `before-command`, `before-fetch`,
`before-search`, `session` and `before-stop` are guards, and this script exits 2 to refuse — the spelling
every harness reads, with the reason on stderr for the model. `before-compact` and `after-compact` are
hooks: they are reported and nothing is refused, because a context is compacted whether an extension liked
it or not.

**The captain depends on none of this.** Its controls are the deck log's own lines, the controlled-files
diff it takes around every stage, the bounded waits and the inbox receipt. Delete this file and the loop
still runs; what is lost is the cheap recovery, not the control. That is the same rule `hooks.py` opens
with, and it is why every failure here is said and shrugged off rather than raised.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
GUARDS = ROOT / "scripts/extensions/guards.py"
HOOKS = ROOT / "scripts/extensions/hooks.py"
#: How the captain says which fairway, slice and stage a session it dispatched is running. A session a
#: person typed carries none of them, which is how this script tells the two apart — and most of what it
#: does, it does only for the captain's.
FAIRWAY_VARIABLE, SLICE_VARIABLE, STAGE_VARIABLE = "SLIPWAI_FAIRWAY", "SLIPWAI_SLICE", "SLIPWAI_STAGE"
#: The exit code every harness reads as *this call does not happen, and stderr is why*.
REFUSE = 2
#: How many turns running this script will hold before it lets one end. Below every harness's own cap on
#: consecutive holds (Cursor 5, Claude Code and Copilot 8), so it is this file that decides when to let go
#: and says so, rather than a cap somewhere else deciding silently.
HOLD_LIMIT = 3
HOLDS = ROOT / ".slipwai/holds.json"
#: Where a harness whose stop event carries no text keeps its last assistant message, for the stop
#: hook that runs a moment later to read.
KEPT = ROOT / ".slipwai/last-response.txt"
#: How many of the deck log's last lines go back into a compacted context. Enough to see the stage
#: and what it has written; not so many that the summary is replaced by the thing it summarised.
RESUME_LINES = 20

# What a stage may never change to get itself past a gate: the gates that judge it, the Makefile that runs
# them, the tools they run, CI, and the registries that say what may hook or guard this project. A gate is
# satisfied in the tree it measures; a stage that edited one instead is a stage that moved the finish line.
# `tools/` is installed by `./init --extension`, so a file added there is an install and a file changed or
# removed is an edit.
CONTROL_PATHS = ("Makefile", "scripts", "tools", ".github/workflows", ".gitea/workflows",
                 ".claude/settings.json", ".cursor/hooks.json", ".gemini/settings.json",
                 ".slipwai/hooks.json", ".slipwai/guards.json")
INSTALLED = "tools"
REFUSAL = (
    "slipwai: `{path}` is a gate or a control of this run, and a stage never edits one. A gate is satisfied "
    "in the tree it measures, or the slice parks with the gate's own output as the reason. If the gate is "
    "wrong, say so in the deck log and park — changing the thing that judges you is not a way past it."
)
#: The shell is judged by the same list, by the words a command would have to contain to reach a control.
#: Deliberately crude: this is a second belt over the captain's controlled-files diff, which is what
#: actually catches a shell write, and a clever parser here would buy false refusals rather than safety.
WRITING = ("sed -i", "tee ", ">", ">>", "truncate", "rm ", "mv ", "cp ", "chmod", "patch ")


#: The event, once. stdin is a pipe and a pipe is read once, so a verb that asked twice got `{}` the second
#: time — which reads as *no evidence* and is therefore silent, which is the worst way for this to break.
EVENT: dict | None = None


def event() -> dict:
    """The harness's event, off stdin. A harness that sent nothing readable sent nothing: every caller
    treats an empty event as *no evidence*, which is never a reason to refuse."""
    global EVENT
    if EVENT is None:
        try:
            read = json.loads(sys.stdin.read() or "{}")
        except (ValueError, OSError):
            read = {}
        EVENT = read if isinstance(read, dict) else {}
    return EVENT


def event_cwd() -> Path:
    """Where the harness says the session is. A hook runs in whatever directory the session wandered into,
    so a relative `file_path` means nothing without it."""
    where = event().get("cwd")
    return Path(str(where)) if isinstance(where, str) and where else ROOT


def dispatched() -> bool:
    """Whether the captain started this session. A person's own `/sail` edits what it likes."""
    return bool(os.environ.get(FAIRWAY_VARIABLE))


def about() -> dict[str, str]:
    """What this session is, as the captain named it: what every guard and hook is handed."""
    named = {"fairway": os.environ.get(FAIRWAY_VARIABLE, ""),
             "slice": os.environ.get(SLICE_VARIABLE, ""),
             "stage": os.environ.get(STAGE_VARIABLE, "")}
    return {word: value for word, value in named.items() if value}


#: Where every slice's activity log is kept: the main checkout's, which the board reads, whichever worktree
#: the session runs in. One file per slice, so two slices never append to one file.
ACTIVITY = ".slipwai/activity"
#: A slice's log is cut back to its newest lines past this size, so a poll reading its tail stays cheap.
ACTIVITY_LIMIT, ACTIVITY_KEEP = 1_000_000, 2000
#: How long a line may be: a sentence for a person, never a command's whole text or a file's contents.
SAID = 240


def main_checkout() -> Path:
    """The main checkout this session's worktree belongs to, by Git's shared directory."""
    try:
        done = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return ROOT
    common = done.stdout.strip()
    return Path(common).parent if done.returncode == 0 and common else ROOT


def record(kind: str, what: str, agent: str = "", **fields: object) -> None:
    """One line in this slice's activity log: what happened, in words a person reads, and who did it.

    Only in a session the captain dispatched, which is the one that has a slice to file it under. Never
    raised: a hook that could not write a line has cost nothing but the line."""
    fairway, slice_id = os.environ.get(FAIRWAY_VARIABLE, ""), os.environ.get(SLICE_VARIABLE, "")
    if not fairway or not slice_id or not what.strip():
        return
    from datetime import datetime, timezone
    line = {"t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "fairway": fairway, "slice": slice_id,
            "stage": os.environ.get(STAGE_VARIABLE, ""), "agent": agent or "session", "kind": kind,
            "what": " ".join(what.split())[:SAID],
            **{key: value for key, value in fields.items() if value not in (None, "")}}
    path = main_checkout() / ACTIVITY / fairway / f"{slice_id}.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(line, ensure_ascii=False) + "\n")
        if path.stat().st_size > ACTIVITY_LIMIT:
            kept = path.read_text(encoding="utf-8").splitlines()[-ACTIVITY_KEEP:]
            path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    except OSError:
        return


def acting() -> tuple[str, str]:
    """Which agent a tool call came from — a sub-agent the harness names, or the session — and its type."""
    given = event()
    return str(given.get("agent_id") or ""), str(given.get("agent_type") or "")


def described(given: dict) -> str:
    """A command as a person would say it: the description its agent gave it, else its first words."""
    tool_input = given.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    words = str(tool_input.get("description") or "").strip()
    if words:
        return words
    command = str(tool_input.get("command") or "").strip().splitlines()
    return " ".join(command[0].split()[:6]) if command else ""


def extensions(script: Path, point: str, given: dict[str, str]) -> int:
    """Run the extensions attached at `point`, and hand back what they said.

    A runner that is not in this project, cannot be started, or dies is said on stderr and treated as having
    refused nothing. An extension registry is a convenience; a stage that could not run because one of them
    was missing would be the control plane both closed sets are written to prevent.
    """
    if not script.is_file():
        return 0
    arguments = [part for word, value in sorted(given.items()) for part in (f"--{word}", value)]
    try:
        run = subprocess.run([sys.executable, str(script), point, *arguments], cwd=ROOT, text=True)
    except OSError as error:
        print(f"slipwai: {script.name} {point} could not run ({type(error).__name__}); carrying on",
              file=sys.stderr)
        return 0
    return REFUSE if run.returncode == REFUSE else 0


def controls() -> list[Path]:
    return [ROOT / where for where in CONTROL_PATHS]


def controlled(target: str, cwd: str | None = None) -> str | None:
    """The path, relative to the root, where `target` is a gate or a control. None where it is ordinary.

    A file *added* under `tools/` is an install rather than an edit, and installs are `./init --extension`'s
    to make, so it is not refused here — an edit to one that exists is.
    """
    if not target:
        return None
    path = Path(target)
    if not path.is_absolute():
        path = Path(cwd or ROOT) / path
    try:
        path = path.resolve()
        shown = path.relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return None
    for control in controls():
        if path == control or control in path.parents:
            if shown.startswith(INSTALLED + "/") and not path.exists():
                return None
            return shown
    return None


def written(given: dict) -> str:
    """The path an editing tool is about to write, under whichever key this harness calls it."""
    for key in ("file_path", "filePath", "notebook_path", "path", "target_file"):
        value = given.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def deck(fairway: str) -> list[dict]:
    """This fairway's deck log, oldest first. Unreadable reads as empty: a log nobody can parse is not
    evidence that a stage wrote nothing, and this file never refuses on an absence of evidence."""
    directory = ROOT / logs.LOGS
    found: list[dict] = []
    for path in sorted(directory.glob(f"*/{fairway}.jsonl")) if directory.is_dir() else []:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                found.append(entry)
    return found


def holds(fairway: str, bump: bool = False) -> int:
    """How many turns this script has held in a row for this fairway, and optionally one more.

    Version 1 counted the holds on the checkpoint it was holding against, so a rewritten checkpoint reset
    the count — which was the point. There is no checkpoint now: a stage that writes a line has made
    progress, and `before-stop` clears the count when it sees one, which is the same rule folded from the
    log instead of stamped on a file.
    """
    try:
        table = json.loads(HOLDS.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        table = {}
    if not isinstance(table, dict):
        table = {}
    count = int(table.get(fairway) or 0) if str(table.get(fairway) or 0).isdigit() else 0
    if not bump:
        return count
    table[fairway] = count + 1
    HOLDS.parent.mkdir(parents=True, exist_ok=True)
    HOLDS.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    return count + 1


def released(fairway: str) -> None:
    """Forget this fairway's holds. Called the moment a stage writes a line, which is what a hold was for."""
    try:
        table = json.loads(HOLDS.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return
    if isinstance(table, dict) and table.pop(fairway, None) is not None:
        HOLDS.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")


def before_write() -> int:
    """A file is about to be written. Refuse a gate or a control, then ask the extensions.

    The keel's own half runs only in a session the captain dispatched: a person's `/sail` edits the
    Makefile if they want to, and a tool that refused them would be a tool they turn off. The extensions'
    half runs in every session, because an extension was agreed to by the person, not by the run.
    """
    given = event().get("tool_input")
    path = written(given if isinstance(given, dict) else {})
    cwd = str(event_cwd())
    agent, role = acting()
    record("edit", Path(path).name if path else "", agent, role=role)
    if dispatched():
        shown = controlled(path, cwd)
        if shown:
            print(REFUSAL.format(path=shown), file=sys.stderr)
            return REFUSE
    return extensions(GUARDS, "before-write", {**about(), "path": path})


def before_command(command: str = "") -> int:
    """A shell command is about to run. The same refusal through the door `before-write` cannot see.

    A command's text is judged crudely — does it name a control, and does it contain something that writes
    — because the real control is the captain's controlled-files diff around every stage, and this is a
    cheap belt in front of it. A crude judgement costs a false refusal the agent is told the reason for; a
    clever one costs a parse of shell nobody can get right.
    """
    given = event().get("tool_input")
    text = command or (given.get("command") if isinstance(given, dict) else "") or ""
    # The session's own sentences for the board are words, not a write to `scripts/`, whatever they contain.
    narrating = re.match(r"\s*python3\s+\S*scripts/agents/session\.py\s+(say|waiting)\b", text) is not None
    if not narrating:
        agent, role = acting()
        record("ran", described(event()), agent, role=role)
    if dispatched() and not narrating and any(word in text for word in WRITING):
        for control in CONTROL_PATHS:
            if control in text:
                print(REFUSAL.format(path=control), file=sys.stderr)
                return REFUSE
    return extensions(GUARDS, "before-command", {**about(), "command": text})


def before_fetch() -> int:
    """A URL is about to be read. The keel holds no opinion; an extension may."""
    given = event().get("tool_input")
    url = (given.get("url") if isinstance(given, dict) else "") or ""
    host = str(url).split("//", 1)[-1].split("/", 1)[0]
    return extensions(GUARDS, "before-fetch", {**about(), "url": str(url), "host": host})


def before_search() -> int:
    """The tree is about to be searched. The keel holds no opinion; a code index is why this point exists.

    A shell command reaches here as well as the search tools, because a `grep` or an `rg` typed into Bash is
    the same search by another door, and a guard that saw only the search tools would be a rule with a gap
    in it the size of the shell.
    """
    given = event().get("tool_input")
    given = given if isinstance(given, dict) else {}
    query = str(given.get("pattern") or given.get("query") or given.get("command") or "")
    return extensions(GUARDS, "before-search", {**about(), "query": query})


def session() -> int:
    """A session has opened, before its first tool call."""
    return extensions(GUARDS, "session", about())


#: The delegate type whose return is a commit. A shipwright commits each green increment locally and hands
#: back the hash, and the session integrates that commit and nothing else — never files copied out of a
#: working tree, which is how a host once took a sibling's files while its next rule was still RED.
COMMITTING = ("sail-implement-shipwright",)
#: A commit named in a return: the word, then a hash of seven to forty hex digits somewhere after it.
NAMED_COMMIT = re.compile(r"\bcommit\b[^\n]{0,80}?\b[0-9a-f]{7,40}\b", re.IGNORECASE)
#: The honest empty return — nothing was committed, and the return says so and why.
NO_COMMIT = re.compile(r"\bno commit\b", re.IGNORECASE)


def delegate_type(given: dict) -> str:
    """Which agent type the delegate was, as the harness's tool input names it, or nothing."""
    tool_input = given.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    for field in ("subagent_type", "agent", "agent_type", "type"):
        named = tool_input.get(field)
        if isinstance(named, str) and named:
            return named
    return ""


def response_text(given: dict) -> str:
    """What the delegate said, flattened: a string, or whatever structure the harness wrapped it in."""
    answer = given.get("tool_response", given.get("tool_result", ""))
    if isinstance(answer, str):
        return answer
    try:
        return json.dumps(answer)
    except (TypeError, ValueError):
        return str(answer)


def uncommitted_return(given: dict) -> str | None:
    """Why a committing delegate's return is refused, or None: it named neither a commit nor `no commit`."""
    if delegate_type(given) not in COMMITTING:
        return None
    text = response_text(given)
    if not text.strip():
        return None  # no evidence of what was said is never a reason to refuse
    if NAMED_COMMIT.search(text) or NO_COMMIT.search(text):
        return None
    return (f"slipwai: {delegate_type(given)} returned without naming a commit. A boundary returns a committed "
            "candidate — `commit <hash>` in the report — and the session integrates that commit, never files "
            "copied out of a working tree; or it says `no commit` and why. Ask the delegate to commit its green "
            "increment and return the hash (commands/sail.md, *Who runs each stage*).")


def after_delegate() -> int:
    """A delegate has answered, before its answer is used. The one guard that fires *after* a tool call.

    It is a guard and not a hook because of what refusing it does: the answer is not used and the agent is
    told why and asks again, which is a thing that stops happening — one tool call — rather than a stage
    that fails. The same test every other guard passes.

    A delegate came back having edited whatever it edited, so this is also where an extension that keeps an
    index of the tree gets to notice; refusing is the rarer half of what it is for. The keel's own refusal
    here is the committed return: an implementing delegate that names no commit and does not say `no commit`
    is sent back for the hash, because what the session integrates is a commit and not a working tree.
    """
    given = event()
    answer = given.get("tool_response")
    answer = answer if isinstance(answer, dict) else {}
    named = NAMED_COMMIT.search(response_text(given))
    record("done", str((given.get("tool_input") or {}).get("description") or delegate_type(given))
           if isinstance(given.get("tool_input"), dict) else delegate_type(given),
           str(given.get("tool_use_id") or ""), role=delegate_type(given), id=str(answer.get("agentId") or ""),
           commit=named.group(0).split()[-1] if named else "", tokens=answer.get("totalTokens"))
    refused = uncommitted_return(given)
    if refused is not None:
        print(refused, file=sys.stderr)
        return REFUSE
    return extensions(GUARDS, "after-delegate", {**about(), "tool": str(given.get("tool_name") or "")})



def ending_message(given: dict) -> str:
    """The message the turn ends on: the event's own copy, under whichever name this harness gives it, then
    what the after-response hook kept for a harness whose stop event carries no text at all."""
    for field in ("last_assistant_message", "lastAssistantMessage", "prompt_response", "text"):
        text = given.get(field)
        if isinstance(text, str) and text.strip():
            return text
    if KEPT.is_file():
        try:
            return KEPT.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def hold(given: dict, reason: str) -> int:
    """Print the hold the way this harness reads it, and say nothing else.

    Claude Code's `Stop` takes `{"decision": "block", "reason"}` and so do the harnesses that copied it;
    Cursor's `stop` takes `{"followup_message"}`, which it submits as the next user message. The event says
    which — Cursor's carries `loop_count`, and names its event in lower case.
    """
    cursor = "loop_count" in given or str(given.get("hook_event_name", "")) == "stop"
    print(json.dumps({"followup_message": reason} if cursor else {"decision": "block", "reason": reason}))
    return 0


def before_stop() -> int:
    """A turn is about to end. Hold it where the stage it was dispatched for wrote no line.

    *A stage that wrote no line made no progress* is the loop's whole rule, and this is the cheap half of
    enforcing it: a session that is about to end having written nothing is told so and carries on, which
    costs a turn. The dear half is the captain's, which reads the same log after the session has gone and
    parks the slice. Both are needed — prose in a command file is not a control, and the first attempt
    proved it by ending iterations on a report that said "continuing now".

    Only in a session the captain dispatched, and only while the log stays empty: the moment a line is
    written the count is forgotten, so a long stage is never held for being long. After HOLD_LIMIT holds
    with nothing written in between it lets go and says why, because a turn held for ever is the same
    silence the hold was there to break.
    """
    if not dispatched():
        return 0
    given = event()
    fairway = os.environ.get(FAIRWAY_VARIABLE, "")
    started = os.environ.get("SLIPWAI_SINCE", "")
    wrote = [line for line in deck(fairway) if not started or str(line.get("t", "")) > started]
    if wrote:
        released(fairway)
        return extensions(GUARDS, "before-stop", about())
    text = ending_message(given).strip()
    if not text:
        # No message, no transcript, no after-response hook: nothing says what the turn ended on, and a
        # hold on no evidence is a hold on every turn.
        print("slipwai: the stop event carries no last message and no hook kept one; not holding",
              file=sys.stderr)
        return extensions(GUARDS, "before-stop", about())
    if holds(fairway) >= HOLD_LIMIT:
        print(f"slipwai: held {HOLD_LIMIT} times for {fairway} with no line written; letting the turn end "
              f"and leaving the slice to the captain's gate", file=sys.stderr)
        return extensions(GUARDS, "before-stop", about())
    holds(fairway, bump=True)
    stage = os.environ.get(STAGE_VARIABLE) or "this stage"
    return hold(given, f"slipwai: {stage} has written no line to the deck log of {fairway}, and a stage "
                       f"that wrote no line made no progress — whatever this turn says it did. Write the "
                       f"stage's own lines now (`python3 scripts/agents/telegraph.py` is how), or, if the "
                       f"stage genuinely cannot be done, write the line that says so. The captain reads the "
                       f"log and nothing else.")


def before_compact() -> int:
    """A context is about to be compacted. Reported, never refused: it is going to happen regardless."""
    extensions(HOOKS, "before-compact", about())
    return 0


def after_compact() -> int:
    """A compacted context has resumed. What the summary lost is in the log, so the log goes back in.

    Version 1 kept a checkpoint file for this and rewrote it at every stage boundary, which made the
    resumed context depend on something being remembered to be written. The deck log is written anyway —
    it is what the captain reads — so the last lines of it are both cheaper and truer.
    """
    extensions(HOOKS, "after-compact", about())
    fairway = os.environ.get(FAIRWAY_VARIABLE, "")
    if not fairway:
        return 0
    recent = deck(fairway)[-RESUME_LINES:]
    if not recent:
        return 0
    print(f"slipwai: this session is {os.environ.get(STAGE_VARIABLE) or 'a stage'} of "
          f"{os.environ.get(SLICE_VARIABLE) or 'a slice'} on fairway {fairway}, and its context was "
          f"compacted. The summary lost what is below, which is the deck log and not a retelling of it. "
          f"Carry on from the last line; the captain reads this log and nothing else.")
    for line in recent:
        print("  " + json.dumps(line, ensure_ascii=False))
    return 0


def responded() -> int:
    """Keep the last assistant message, for a harness whose stop event does not carry one.

    Not a point of either closed set: it is plumbing for `before-stop` on Cursor, whose `stop` event hands
    over no text at all. An extension has nothing to attach here, and a point nothing could use would be a
    promise with no caller.
    """
    if not dispatched():
        return 0
    text = event().get("text") or event().get("last_assistant_message")
    if isinstance(text, str) and text.strip():
        KEPT.parent.mkdir(parents=True, exist_ok=True)
        KEPT.write_text(text, encoding="utf-8")
    return 0


def before_delegate() -> int:
    """A sub-agent is about to be given its brief. Recorded, never refused: the start of its lane."""
    given = event()
    tool_input = given.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    record("start", str(tool_input.get("description") or ""), str(given.get("tool_use_id") or ""),
           role=delegate_type(given), model=str(tool_input.get("model") or ""))
    return 0


def agent_started() -> int:
    """The harness has started a sub-agent and named it: which start line its own tool calls belong to."""
    agent, role = acting()
    record("link", role or "sub-agent", agent, role=role)
    return 0


def after_failure() -> int:
    """A tool call failed. A command's failure is a line of its own: the same one three times running is
    an agent going round in circles, which is what the board warns of."""
    given = event()
    if str(given.get("tool_name") or "") not in ("Bash", "PowerShell", "Shell", "run_shell_command"):
        return 0
    agent, role = acting()
    error = str(given.get("error") or "").strip().splitlines()
    record("failed", described(given), agent, role=role, said=error[0] if error else "")
    return 0


def said_aloud(kind: str) -> int:
    """`session.py say <sentence>` and `session.py waiting <on what>`: what only the session can say, on
    every harness alike, because it is a command the session runs and not an event a harness may not have."""
    words = " ".join(sys.argv[2:]).strip()
    if not words:
        print(f"session: {kind} needs the words to record", file=sys.stderr)
        return 1
    record("said" if kind == "say" else "wait", words, os.environ.get("SLIPWAI_AGENT", ""))
    return 0


VERBS = {
    "before-delegate": before_delegate,
    "agent-started": agent_started,
    "after-failure": after_failure,
    "say": lambda: said_aloud("say"),
    "waiting": lambda: said_aloud("waiting"),
    "session": session,
    "before-search": before_search,
    "before-write": before_write,
    "before-command": before_command,
    "before-fetch": before_fetch,
    "after-delegate": after_delegate,
    "before-stop": before_stop,
    "before-compact": before_compact,
    "after-compact": after_compact,
    "responded": responded,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in VERBS:
        print(f"session: one of {', '.join(VERBS)}, with the harness's event on stdin", file=sys.stderr)
        return 0 if not argv else 1
    try:
        return VERBS[argv[0]]()
    except Exception as error:  # noqa: BLE001 - a broken hook never stops a stage; see the module docstring
        print(f"slipwai: session.py {argv[0]} failed ({type(error).__name__}: {error}); carrying on",
              file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
