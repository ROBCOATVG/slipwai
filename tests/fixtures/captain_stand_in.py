"""A stand-in for a stream's captain agent, for the suite: an agent speaking the Agent Client Protocol, as every
captain in a fleet is, held open by the program and prompted once per event with the event file's path.

`STAND_IN_CAPTAIN` says how it behaves. `today` (the default) gives exactly the orders the event's `default`
lists — what the fixed rule would do — through `orders.py`, as a real captain does: the suites run with it
must leave the same deck log as without it. Every other mode misbehaves, writing its order files itself
(signed with the key it was handed, so that it is the program's own check that is proved, not the script's):

- `silent` says nothing until its turn is cancelled; `late` answers as `today` does, `STAND_IN_DELAY`
  seconds late; `die` exits mid-decision having said nothing;
- `uncleared` starts a slice the event did not offer; `greedy` starts every slice offered and one more;
- `retry` retries whatever the event allows; `merge` orders a merge; `malformed` writes a file that is not
  JSON; `unsigned` and `forged` give an order with no signature or one made with another key;
- `flood` gives forty orders at once; `lift` resumes the slice named in `STAND_IN_TARGET`;
- `message` sends `STAND_IN_TARGET` a message and then does as `today`;
- `stopper` stops every slice in flight at every event, which is how a captain would try to run a slice for
  ever, and otherwise does as `today`;
- `script` gives, for each kind of event, the orders `SCRIPT` (JSON, `{kind: [order, ...]}`) lists, the event's
  `default` for a kind it does not name, and the default again for a kind in `SCRIPT_ONCE` after its first
  time, with `$slice`, `$inbox`, `$ask` and `$first` (the first slice offered) put for their values; what it
  was woken for and each order's exit and output go to `SCRIPT_LOG`.

With `STAND_IN_ASKS=1` each order through `orders.py` is asked for first, as a real agent asks before it runs a
command: a `session/request_permission` for an `execute` call whose command is the order command its prompt
handed it, each value in single quotes as the brief says, run by `sh -c` only where the program allows it, so
the captain session's policy (`captain_agent.permit`) is in the loop of the whole run.

Run with an event file's path instead — `captain_stand_in.py <event>` — it is the evals' captain under test,
once, as a process: their throwaway project is the one place a captain runs that way.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

MODE = os.environ.get("STAND_IN_CAPTAIN", "today")
ORDERS = Path(os.environ.get("SLIPWAI_CAPTAIN_ORDERS", "."))
KEY = bytes.fromhex(os.environ.get("SLIPWAI_CAPTAIN_KEY", ""))
PREFIX, COUNT = secrets.token_hex(2), [0]
FIELDS = ("v", "id", "t", "event", "fairway", "verb", "slice", "ask", "text", "note", "why", "needs", "of",
          "options", "interrupt")


def order(held, verb, secret=KEY, **said):
    t = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    COUNT.append(1)  # ids that sort in the order they were given, so the program reads them in that order
    body = {"v": 1, "id": f"{t.replace('-', '').replace(':', '')}-{PREFIX}{len(COUNT):02x}", "t": t,
            "event": held["id"], "fairway": held.get("fairway") or os.environ.get("SLIPWAI_CAPTAIN_FAIRWAY", ""),
            "verb": verb, **said}
    signed = json.dumps({name: body.get(name) for name in FIELDS}, sort_keys=True, ensure_ascii=False)
    if secret:
        body["sig"] = hmac.new(secret, signed.encode("utf-8"), hashlib.sha256).hexdigest()
    ORDERS.mkdir(parents=True, exist_ok=True)
    aside = ORDERS / f".{body['id']}.json.part"
    aside.write_text(json.dumps(body), encoding="utf-8")
    os.replace(aside, ORDERS / f"{body['id']}.json")


#: Where `STAND_IN_ASKS` is set: the open session, the order command its prompt handed it, and the next request
#: number, so `door` can ask the program before it runs an order.
ASKING: dict = {"session": "", "command": "", "number": 9000}


def quoted(value):
    """A value in single quotes, an apostrophe written `'\\''`, as the captain's brief says."""
    return "'" + str(value).replace("'", "'\\''") + "'"


def door(held, one):
    """One order through `orders.py`, as the real captain gives it."""
    words = [one["verb"]]  # what follows the order command, each value as the captain quotes it
    target = one.get("slice") or one.get("ask")
    if target:
        words.append(quoted(target))
    for name in ("note", "why", "text", "needs", "of", "options"):
        if one.get(name):
            value = one[name]
            words += [f"--{name}", quoted(",".join(value) if isinstance(value, list) else value)]
    if one.get("interrupt"):
        words.append("--interrupt")
    words += ["--event", quoted(held["id"])]
    if os.environ.get("STAND_IN_ASKS") == "1":
        # `raw` is what a careless or a hostile captain would write after the order command, as it stands.
        command = " ".join([ASKING["command"], *([one["raw"]] if "raw" in one else words)])
        if not ask(command):
            logged({"event": held["kind"], "order": one, "exit": None, "out": "refused permission", "command": command})
            return
        done = subprocess.run(["sh", "-c", command], check=False, capture_output=True, text=True)
    else:
        argv = [sys.executable, os.environ["SLIPWAI_CAPTAIN_ORDERS_PY"], *shlex.split(" ".join(words))]
        done = subprocess.run(argv, check=False, capture_output=True, text=True)
    logged({"event": held["kind"], "order": one, "exit": done.returncode, "out": (done.stdout + done.stderr).strip()})


def logged(entry):
    if os.environ.get("SCRIPT_LOG"):
        with open(os.environ["SCRIPT_LOG"], "a", encoding="utf-8") as out:
            out.write(json.dumps(entry) + "\n")


def ask(command):
    """Ask the program to run a command, as an agent does before it runs one: whether it was allowed."""
    ASKING["number"] += 1
    number = ASKING["number"]
    call = {"toolCallId": f"call-{number}", "title": command[:60], "kind": "execute", "status": "pending",
            "rawInput": {"command": command}}
    send(method="session/update", params={"sessionId": ASKING["session"],
                                          "update": {"sessionUpdate": "tool_call", **call}})
    send(id=number, method="session/request_permission", params={
        "sessionId": ASKING["session"], "toolCall": call,
        "options": [{"optionId": "yes", "name": "Allow once", "kind": "allow_once"},
                    {"optionId": "no", "name": "Reject", "kind": "reject_once"}]})
    for line in sys.stdin:
        message = json.loads(line)
        if message.get("id") == number and "method" not in message:
            outcome = (message.get("result") or {}).get("outcome") or {}
            return outcome.get("outcome") == "selected" and outcome.get("optionId") == "yes"
    return False


def scripted(held):
    """`script`: the orders `SCRIPT` lists for this kind of event, given through `orders.py`."""
    script = json.loads(os.environ.get("SCRIPT") or "{}")
    facts = held.get("facts") or {}
    subs = {"$slice": held.get("slice") or "", "$inbox": facts.get("inbox") or "", "$ask": facts.get("ask") or "",
            "$first": ((facts.get("cleared") or [{}])[0]).get("slice", "")}
    logged({"woken": held["kind"], "slice": held.get("slice"), "may": held.get("may"), "facts": facts})
    given = script.get(held["kind"])
    if given is None:
        given = held.get("default") or []
    if held["kind"] in os.environ.get("SCRIPT_ONCE", "").split(","):
        mark = Path(os.environ["SCRIPT_LOG"] + "." + held["kind"])
        if mark.exists():
            given = held.get("default") or []
        mark.write_text("x", encoding="utf-8")
    for one in given:
        door(held, {key: (subs.get(value, value) if isinstance(value, str) else value) for key, value in one.items()})


def decide(event):
    """What this stand-in does with one event. False where it says nothing at all (`silent`)."""
    held = json.loads(Path(event).read_text(encoding="utf-8"))
    target = os.environ.get("STAND_IN_TARGET", "")
    cleared = [one["slice"] for one in (held.get("facts") or {}).get("cleared") or []]
    if MODE == "script":
        scripted(held)
        return True
    if MODE == "silent":
        return False
    if MODE == "late":
        import time
        time.sleep(float(os.environ.get("STAND_IN_DELAY") or 4))  # answers, but after the slice it chose for
    if MODE == "die":
        os._exit(3)
    if MODE == "uncleared" and held["kind"] == "choose-next":
        order(held, "start", slice=target or "BIL-02")
    elif MODE == "greedy" and held["kind"] == "choose-next":
        for one in [*cleared, target or "BIL-02"]:
            order(held, "start", slice=one)
    elif MODE == "retry" and held["kind"] == "gate-failed":
        order(held, "retry", slice=held["slice"], note="once more")
    elif MODE == "merge":
        order(held, "merge", slice=held.get("slice") or target)
    elif MODE == "malformed":
        ORDERS.mkdir(parents=True, exist_ok=True)
        (ORDERS / "20261116T000000Z-badbad.json").write_text("{not json", encoding="utf-8")
    elif MODE == "unsigned":
        for one in held.get("default") or []:
            order(held, one["verb"], secret=b"", **{k: v for k, v in one.items() if k != "verb"})
    elif MODE == "forged":
        for one in held.get("default") or []:
            order(held, one["verb"], secret=b"a slice's own key", **{k: v for k, v in one.items() if k != "verb"})
    elif MODE == "flood":
        for count in range(40):
            order(held, "say", text=f"order {count}")
    elif MODE == "lift":
        order(held, "resume", slice=target, why="carry on")
    elif MODE == "stopper" and "stop" in (held.get("may") or []):
        state = json.loads((Path(event).parent / "state.json").read_text(encoding="utf-8"))
        for one in state.get("in_flight") or []:
            door(held, {"verb": "stop", "slice": one, "why": "again"})
    else:
        if MODE == "message":
            door(held, {"verb": "message", "slice": target, "text": "the captain says: mind the rounding"})
        for one in held.get("default") or []:
            door(held, one)
    return True


def send(**message):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
    sys.stdout.flush()


def speak():
    """The protocol's agent half, as little of it as a captain needs: a session, and a turn per prompt."""
    waiting = None
    for line in sys.stdin:
        message = json.loads(line)
        number, method, params = message.get("id"), message.get("method"), message.get("params") or {}
        if method == "initialize":
            send(id=number, result={"protocolVersion": params.get("protocolVersion"),
                                    "agentInfo": {"name": "captain stand-in", "version": "0.1"},
                                    "agentCapabilities": {"loadSession": False}, "authMethods": []})
        elif method == "session/new":
            ASKING["session"] = f"captain-{secrets.token_hex(3)}"
            send(id=number, result={"sessionId": ASKING["session"], "configOptions": []})
        elif method == "session/prompt":
            words = " ".join(str(block.get("text", "")) for block in params.get("prompt") or [])
            handed = re.search(r"by running `(.+?) <verb> ", words)
            ASKING["command"] = handed.group(1) if handed else ""
            found = re.search(r"needs you: read (\S+\.json)\. ", words)
            if found and not decide(found.group(1)):
                waiting = number  # silent: the turn stays open until the program cancels it
                continue
            send(id=number, result={"stopReason": "end_turn"})
        elif method == "session/cancel" and waiting is not None:
            send(id=waiting, result={"stopReason": "cancelled"})
            waiting = None
        elif number is not None:
            send(id=number, error={"code": -32601, "message": f"{method} is not known here"})


if __name__ == "__main__":
    if len(sys.argv) > 1:
        decide(sys.argv[1])  # the evals' captain under test, once
    else:
        speak()
