"""A stand-in agent that speaks the Agent Client Protocol from a script, for `tests/test_acp.py`.

One JSON object per line on stdin and stdout, as the protocol says. It answers `initialize`, `session/new`
and `session/load`; on a prompt it streams a message chunk, asks permission to write a file in its working
directory and writes it, and does more by the words in the prompt: `outside` asks permission for a path
beyond the directory, `ask` puts a question, `slow` waits on a permission until it is answered or cancelled,
`die` exits mid-turn. Nothing here is clever; it is the other end of the wire, held still.

For a driver held open (`tests/test_drive_held.py`): `count` says how many prompts its session has had,
`linger` waits for a cancel, `dawdle` waits for a `.go` file before it goes on, and a delivered message is
answered `Reply: <text>` — or not at all where it says `quiet`. A captain's drive does the same where a
`.linger` or `.dawdle` file is in the berth, once each, and asks what `asked_once` says, once each.
"""
import hashlib
import json
import os
import select
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.cwd()
#: How many prompts each session has had, for `count`: the proof a second prompt reached the same one.
PROMPTS: dict = {}
#: The head of a message a driver delivers (`drive.message_prompt`).
MESSAGE = "A message for this slice from "
#: The sessions minted for this working directory, kept outside it: each `session/new` is `s-<n>`, numbered on
#: from the last, and a `session/load` of an id not minted here is refused, as a real agent refuses one.
MINTED = Path(tempfile.gettempdir()) / f"acp-stand-in-{hashlib.sha256(str(HOME).encode()).hexdigest()[:16]}"
#: Seconds a cancel takes to land, where the suite asks for a slow one.
CANCEL_DELAY = float(os.environ.get("STAND_IN_CANCEL_DELAY") or 0)


def minted():
    try:
        return MINTED.read_text(encoding="utf-8").split()
    except OSError:
        return []


def mint():
    ident = f"s-{len(minted()) + 1}"
    with MINTED.open("a", encoding="utf-8") as out:
        out.write(ident + "\n")
    return ident
#: How this agent says it can be signed in to: through itself, or by a command run in a terminal.
METHODS = [{"id": "login", "name": "Sign in", "description": "Opens the browser", "type": "agent"},
           {"id": "setup", "name": "Set up", "description": "Interactive setup", "type": "terminal",
            "args": ["--setup"]}]


def send(**message):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
    sys.stdout.flush()


def update(session, **body):
    send(method="session/update", params={"sessionId": session, "update": body})


def text(session, words):
    update(session, sessionUpdate="agent_message_chunk", content={"type": "text", "text": words})


def ask(number, method, params):
    """A request to the client, and the next thing it says back: the reply, or a cancel notification
    ahead of it (the client answers every open permission `cancelled` on a cancel)."""
    send(id=number, method=method, params=params)
    cancelled = False
    while True:
        line = sys.stdin.readline()
        if not line:
            return None, cancelled
        message = json.loads(line)
        if message.get("method") == "session/cancel":
            cancelled = True
            continue
        if message.get("id") == number:
            return message.get("result"), cancelled


def permission(number, session, path):
    # Forward slashes whatever the platform: the stub's wire form is what the tests read back, and a Windows
    # `Path` would have put backslashes in the card the keel showed.
    path = Path(path).as_posix()
    call = {"toolCallId": f"call-{number}", "title": f"Write {path}", "kind": "edit", "status": "pending",
            "locations": [{"path": path}], "rawInput": {"filePath": path, "content": "<title>"}}
    update(session, sessionUpdate="tool_call", **call)
    result, cancelled = ask(number, "session/request_permission", {
        "sessionId": session, "toolCall": call,
        "options": [{"optionId": "yes-once", "name": "Allow once", "kind": "allow_once"},
                    {"optionId": "no-once", "name": "Reject", "kind": "reject_once"}]})
    outcome = ((result or {}).get("outcome") or {})
    allowed = outcome.get("outcome") == "selected" and outcome.get("optionId") == "yes-once"
    update(session, sessionUpdate="tool_call_update", toolCallId=call["toolCallId"],
           status="completed" if allowed else "failed")
    return allowed, cancelled or outcome.get("outcome") == "cancelled"


def linger(session):
    """Wait, saying so, until the client cancels the turn: the turn an interrupt or a stop lands in."""
    text(session, "Lingering.")
    (HOME / ".lingering").write_text("", encoding="utf-8")
    while True:
        line = sys.stdin.readline()
        if not line:
            os._exit(0)
        if json.loads(line).get("method") == "session/cancel":
            time.sleep(CANCEL_DELAY)
            return "cancelled"


def busy(session):
    """Call tools, one finished every fifth of a second, and write nothing else, until the turn is cancelled:
    an agent going round in circles, which the captain must still end."""
    count = 0
    while True:
        count += 1
        update(session, sessionUpdate="tool_call", toolCallId=f"busy-{count}", title="Read a file", kind="read",
               status="completed")
        ready, _, _ = select.select([sys.stdin], [], [], 0.2)
        if ready:
            line = sys.stdin.readline()
            if not line:
                os._exit(0)
            if json.loads(line).get("method") == "session/cancel":
                return "cancelled"


def dawdle():
    """Wait for a `.go` file in the working directory, saying where with a `.dawdling` one."""
    (HOME / ".dawdling").write_text("", encoding="utf-8")
    while not (HOME / ".go").exists():
        time.sleep(0.05)
    (HOME / ".go").unlink()
    (HOME / ".dawdling").unlink()


def answer(session, words):
    """A delivered message: its text is the paragraph after the head, and the reply repeats it."""
    said = words.split("\n\n")[1] if "\n\n" in words else words
    said = "\n".join(said.splitlines()[1:-1]) if said.startswith("<<<") else said  # between the two marks
    if "dawdle" in said:
        dawdle()
    if "die" in said:
        os._exit(3)
    if "quiet" not in said:
        text(session, f"Reply: {said}")
    return "end_turn"


def captain(session, words):
    """A stream's captain woken by an event: the orders its `default` lists, through `orders.py`, as the
    suite's stand-in captain gives them (`captain_stand_in.py`)."""
    import re
    import subprocess
    found = re.search(r"Event (\S+) \(", words)
    where = re.search(r"read (\S+\.json)\. The", words)
    if not found or not where:
        return "end_turn"
    held = json.loads((HOME / where.group(1)).read_text(encoding="utf-8"))
    for one in held.get("default") or []:
        argv = [sys.executable, "scripts/agents/orders.py", one["verb"]]
        if one.get("slice"):
            argv.append(one["slice"])
        for name in ("note", "why", "text"):
            if one.get(name):
                argv += [f"--{name}", str(one[name])]
        subprocess.run([*argv, "--event", found.group(1)], cwd=HOME, check=False, capture_output=True)
    text(session, f"Captain: answered {found.group(1)}.")
    return "end_turn"


def turn(number, session, words):
    PROMPTS[session] = PROMPTS.get(session, 0) + 1
    if words.startswith(MESSAGE):
        return answer(session, words)
    if words.startswith("You are the captain of"):
        return captain(session, words)
    # A role at the head of the prompt, set off by a rule, is acknowledged and not echoed: the words the
    # stand-in acts on are the person's own, after it.
    if "\n---\nThe board" in words:  # a console's fold of the board rides after the question: not the words
        words = words.split("\n---\nThe board", 1)[0]
    if "\n---\n" in words:
        text(session, "Role given. ")
        words = words.rsplit("\n---\n", 1)[1]
    words = words.strip()
    update(session, sessionUpdate="agent_thought_chunk", content={"type": "text", "text": "Thinking it over. "})
    text(session, f"Drawn: {words}")
    # What the stand-in does is keyed on the first line only: a stage's prompt carries a rule about asking
    # under its first line, and a word in that rule is not an instruction to this script.
    words = words.split("\n", 1)[0]
    if "plan" in words:
        update(session, sessionUpdate="plan", entries=[{"content": "Write the page", "status": "completed"},
                                                       {"content": "Check it", "status": "in_progress"}])
    if "dawdle" in words:
        dawdle()
    if "die" in words:
        os._exit(3)
    if words == "count":
        text(session, f" prompt {PROMPTS[session]} in {session}")
        return "end_turn"
    if "linger" in words:
        return linger(session)
    if " fairway=" in words:  # a captain's drive: the lines the chart says this slice publishes, and a demo
        for marker in (".linger", ".dawdle", ".busy"):
            if (HOME / marker).exists():
                (HOME / marker).unlink()
                if marker == ".linger":
                    return linger(session)
                if marker == ".busy":
                    return busy(session)
                dawdle()
        asked_once(number, session)
        drove(words)
        return "end_turn"
    allowed, cancelled = permission(number * 10 + 1, session, HOME / "prototype" / "index.html")
    if cancelled:
        return "cancelled"
    if allowed:
        (HOME / "prototype").mkdir(exist_ok=True)
        (HOME / "prototype" / "index.html").write_text("<title>Play</title>\n", encoding="utf-8")
        (HOME / "brief").mkdir(exist_ok=True)
        (HOME / "brief" / "prd.md").write_text("# Requirements\n\n## What it must do\n\n- Book a boat.\n",
                                                encoding="utf-8")
    if "outside" in words:
        allowed, cancelled = permission(number * 10 + 2, session, Path("/etc/hosts"))
        text(session, "wrote outside" if allowed else "refused outside")
    if "slow" in words:
        _, cancelled = permission(number * 10 + 3, session, Path("/etc/slow.txt"))  # outside: the person is asked
        if cancelled:
            return "cancelled"
    if "ask" in words:
        result, _ = ask(number * 10 + 4, "elicitation/create", {
            "sessionId": session, "message": "Which colour?", "mode": "form",
            "requestedSchema": {"type": "object", "properties": {"answer": {"type": "string"}}}})
        said = (result or {}).get("content") or {}
        text(session, f"You said: {said.get('answer', '(nothing)')}")
    return "end_turn"


def asked_once(number, session):
    """What a captain's drive asks mid-turn, once each, where a marker is in `STAND_IN_MARKS` (the berth where it
    is not set — a berth is made at run time, so a suite names a folder of its own): `.outside` a write beyond
    the project, `.readin` a read of `STAND_IN_READ` (a file of the project outside the berth), `.askq` a
    question. What it was answered is written beside the marker, `<marker>-said`."""
    marks = Path(os.environ.get("STAND_IN_MARKS") or HOME)
    for marker in (".outside", ".readin", ".askq"):
        if not (marks / marker).exists():
            continue
        (marks / marker).unlink()
        if marker == ".outside":
            said, _ = permission(number * 10 + 2, session, Path("/etc/hosts"))
        elif marker == ".readin":
            path = Path(os.environ.get("STAND_IN_READ") or HOME / "specs/ordering/chart.yaml").as_posix()
            call = {"toolCallId": f"call-r{number}", "title": f"Read {path}", "kind": "read", "status": "pending",
                    "locations": [{"path": path}], "rawInput": {"filePath": path}}
            update(session, sessionUpdate="tool_call", **call)
            said, _ = ask(number * 10 + 5, "session/request_permission", {
                "sessionId": session, "toolCall": call,
                "options": [{"optionId": "yes-once", "name": "Allow once", "kind": "allow_once"},
                            {"optionId": "no-once", "name": "Reject", "kind": "reject_once"}]})
        else:
            said, _ = ask(number * 10 + 4, "elicitation/create", {
                "sessionId": session, "message": "Which colour?", "mode": "form",
                "requestedSchema": {"type": "object", "properties": {"answer": {"type": "string"}}}})
        (marks / f"{marker}-said").write_text(json.dumps(said), encoding="utf-8")


def drove(words):
    """What a fake `/sail` writes (`tests/captain_fixture.py`), from the chart: `mark-set` per mark in the
    slice's `sets`, then an accepted demo, into the fairway's deck log under the working directory."""
    import datetime
    import re
    found = re.search(r"`(\S+) fairway=(\S+)`", words)
    if not found:
        return
    slice_id, fairway = found.group(1), found.group(2)
    for chart in sorted((HOME / "specs").glob("*/chart.yaml")):
        block = re.search(rf"^  {re.escape(slice_id)}:\n((?:    .*\n)*)", chart.read_text(encoding="utf-8"), re.M)
        if not block:
            continue
        sets = re.search(r"sets: \[([^\]]*)\]", block.group(1))
        marks = [m.strip() for m in (sets.group(1) if sets else "").split(",") if m.strip()]
        path = HOME / ".slipwai" / "logs" / chart.parent.name / f"{fairway}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [{"kind": "mark-set", "fairway": fairway, "slice": slice_id, "mark": mark} for mark in marks]
        lines.append({"kind": "demo", "fairway": fairway, "slice": slice_id, "verdict": "accepted"})
        with path.open("a", encoding="utf-8") as handle:
            for body in lines:
                handle.write(json.dumps({"v": 1, "t": now, **body}) + "\n")
        return


def main():
    signed_out = "--signed-out" in sys.argv
    options = [{"id": "model", "type": "select", "category": "model", "name": "Model", "currentValue": "a",
                "options": [{"name": "A", "value": "a"}, {"name": "B", "value": "b"}]}]
    for line in sys.stdin:
        message = json.loads(line)
        number, method, params = message.get("id"), message.get("method"), message.get("params") or {}
        if method == "initialize":
            # A sign-in run in a terminal is offered only to a client that says it can run one, as the
            # Claude adapter does: a client that said nothing was offered no way to sign in at all.
            able = ((params.get("clientCapabilities") or {}).get("auth") or {}).get("terminal") is True
            send(id=number, result={"protocolVersion": params.get("protocolVersion"),
                                    "agentInfo": {"name": "stand-in", "version": "0.1"},
                                    "agentCapabilities": {"loadSession": True},
                                    "authMethods": METHODS if able else METHODS[:1]})
        elif method == "authenticate":
            if params.get("methodId") == "login":
                signed_out = False
                send(id=number, result={})
            else:
                send(id=number, error={"code": -32602, "message": f"{params.get('methodId')} is not a way to sign in"})
        elif method == "session/new" and signed_out:  # as Gemini does: no session for nobody
            send(id=number, error={"code": -32000, "message": "nobody is signed in"})
        elif method == "session/new":
            send(id=number, result={"sessionId": mint(), "configOptions": options})
        elif method == "session/load" and params.get("sessionId") not in minted():
            send(id=number, error={"code": -32002, "message": f"no session {params.get('sessionId')} here"})
        elif method == "session/load":
            update(params["sessionId"], sessionUpdate="user_message_chunk",
                   content={"type": "text",
                            "text": "You are drawing a product with a person.\n\n---\n\nhello from before"})
            update(params["sessionId"], sessionUpdate="user_message_chunk",
                   content={"type": "text", "text": "and once more"})
            text(params["sessionId"], "earlier: hello again")
            send(id=number, result={"configOptions": options})
        elif method == "session/set_config_option":
            options[0]["currentValue"] = str(params.get("value") or "")
            send(id=number, result={"configOptions": options})
        elif method == "session/prompt":
            words = " ".join(str(block.get("text", "")) for block in params.get("prompt") or [])
            if words.strip().endswith("signed out"):
                send(id=number, error={"code": -32000, "message": "Authentication required"})
                continue
            send(id=number, result={"stopReason": turn(number, params["sessionId"], words)})
        elif number is not None:
            send(id=number, error={"code": -32601, "message": f"{method} is not known here"})


if __name__ == "__main__":
    main()
