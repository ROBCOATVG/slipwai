"""A stand-in for a stream's captain agent, run once per event with the event file's path, for the suite.

`STAND_IN_CAPTAIN` says how it behaves. `today` (the default) gives exactly the orders the event's `default`
lists — what the fixed rule would do — through `orders.py`, as a real captain does: the suites run with it
must leave the same deck log as without it. Every other mode misbehaves, writing its order files itself
(signed with the key it was handed, so that it is the program's own check that is proved, not the script's):

- `silent` says nothing until it is ended; `die` exits mid-decision having said nothing;
- `uncleared` starts a slice the event did not offer; `greedy` starts every slice offered and one more;
- `retry` retries whatever the event allows; `merge` orders a merge; `malformed` writes a file that is not
  JSON; `unsigned` and `forged` give an order with no signature or one made with another key;
- `flood` gives forty orders at once; `lift` resumes the slice named in `STAND_IN_TARGET`;
- `message` sends `STAND_IN_TARGET` a message and then does as `today`; `tamper` writes a file into the
  project and then does as `today`.
"""
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

EVENT = Path(sys.argv[1])
HELD = json.loads(EVENT.read_text(encoding="utf-8"))
MODE = os.environ.get("STAND_IN_CAPTAIN", "today")
ORDERS = Path(os.environ["SLIPWAI_CAPTAIN_ORDERS"])
KEY = bytes.fromhex(os.environ["SLIPWAI_CAPTAIN_KEY"])
PREFIX, COUNT = secrets.token_hex(2), [0]
FIELDS = ("v", "id", "t", "event", "fairway", "verb", "slice", "ask", "text", "note", "why", "needs", "of",
          "options", "interrupt")


def order(verb, secret=KEY, **said):
    t = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    COUNT.append(1)  # ids that sort in the order they were given, so the program reads them in that order
    body = {"v": 1, "id": f"{t.replace('-', '').replace(':', '')}-{PREFIX}{len(COUNT):02x}", "t": t,
            "event": HELD["id"], "fairway": HELD.get("fairway") or os.environ.get("SLIPWAI_CAPTAIN_FAIRWAY", ""),
            "verb": verb, **said}
    signed = json.dumps({name: body.get(name) for name in FIELDS}, sort_keys=True, ensure_ascii=False)
    if secret:
        body["sig"] = hmac.new(secret, signed.encode("utf-8"), hashlib.sha256).hexdigest()
    ORDERS.mkdir(parents=True, exist_ok=True)
    aside = ORDERS / f".{body['id']}.json.part"
    aside.write_text(json.dumps(body), encoding="utf-8")
    os.replace(aside, ORDERS / f"{body['id']}.json")
    return body


def through_the_door(one):
    """One order through `orders.py`, as the real captain gives it."""
    argv = [sys.executable, os.environ["SLIPWAI_CAPTAIN_ORDERS_PY"], one["verb"]]
    target = one.get("slice") or one.get("ask")
    if target:
        argv.append(str(target))
    for name in ("note", "why", "text", "needs", "of"):
        if one.get(name):
            argv += [f"--{name}", str(one[name])]
    if one.get("interrupt"):
        argv.append("--interrupt")
    argv += ["--event", HELD["id"]]
    subprocess.run(argv, check=False, capture_output=True, text=True)


def today():
    for one in HELD.get("default") or []:
        through_the_door(one)


target = os.environ.get("STAND_IN_TARGET", "")
cleared = [one["slice"] for one in (HELD.get("facts") or {}).get("cleared") or []]
if MODE == "silent":
    time.sleep(600)
elif MODE == "die":
    os._exit(3)
elif MODE == "uncleared" and HELD["kind"] == "choose-next":
    order("start", slice=target or "BIL-02")
elif MODE == "greedy" and HELD["kind"] == "choose-next":
    for one in [*cleared, target or "BIL-02"]:
        order("start", slice=one)
elif MODE == "retry" and HELD["kind"] == "gate-failed":
    order("retry", slice=HELD["slice"], note="once more")
elif MODE == "merge":
    order("merge", slice=HELD.get("slice") or target)
elif MODE == "malformed":
    ORDERS.mkdir(parents=True, exist_ok=True)
    (ORDERS / "20261116T000000Z-badbad.json").write_text("{not json", encoding="utf-8")
elif MODE == "unsigned":
    for one in HELD.get("default") or []:
        order(one["verb"], secret=b"", **{k: v for k, v in one.items() if k != "verb"})
elif MODE == "forged":
    for one in HELD.get("default") or []:
        order(one["verb"], secret=b"a slice's own key", **{k: v for k, v in one.items() if k != "verb"})
elif MODE == "flood":
    for count in range(40):
        order("say", text=f"order {count}")
elif MODE == "lift":
    order("resume", slice=target, why="carry on")
elif MODE == "tamper":
    # A captain with a shell that reaches the project and changes it, then orders as the rule would.
    project = Path(os.environ["SLIPWAI_CAPTAIN_ORDERS_PY"]).resolve().parents[2]
    (project / "tampered.txt").write_text("a captain was here\n", encoding="utf-8")
    today()
elif MODE == "message":
    through_the_door({"verb": "message", "slice": target, "text": "the captain says: mind the rounding"})
    today()
else:
    today()
