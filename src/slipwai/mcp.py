"""`slipwai mcp`: the read side as tools, so the agent can ask the harbour instead of being told.

Everything the board knows is already a fold over the logs, and a person reads it in a terminal beside their
agent. That is the right shape for a person and the wrong one for the agent, which then finds out what is
blocked by having somebody copy a board from one window into another. These are the same folds, reachable by
the thing that is doing the work.

**Read, and one write.** `fleet`, `stream`, `inbox`, `clearance` and `check-chart` read; `tell` writes the
one line the bridge already lets a person write — a `told` into a stream's deck log. It goes through
`bridge.tell`, so the line an agent writes is the line the page would have written: same fields, same file,
same captain reading it at its next boundary. Nothing here allocates a berth, rings the telegraph, or
touches the harbour log. Those are the harbourmaster's, and a second way to do them would be a second
control plane.

**Nothing is computed here.** Every answer is a call into the module the verb calls. A tool that drew its
own board would be a second answer to what is happening, and the one you were looking at would be whichever
window happened to be in front.

**`http.server`'s neighbour, and nothing else.** The standard library and the JSON-RPC that MCP is: a server
that needed a dependency is a server most people never run, and the keel has none. Newline-delimited JSON on
stdin and stdout, which is what a harness speaks to a stdio server.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from .assets import VERSION
from .bridge import tell
from .cli_fleet import config, lines, stream_lines
from .deck import RECENT
from .fleet import board, inbox_detail
from .project.harbour import CONFIG

#: What the server calls itself where a harness lists it.
NAME = "slipwai"
#: The protocol revision this speaks. Answered rather than echoed: a client is told what it is talking to.
PROTOCOL = "2025-06-18"
#: JSON-RPC's own codes, for the two faults a stdio server actually meets.
BAD_JSON = -32700
NO_SUCH_METHOD = -32601
#: How long one of the project's own gates may run before it is ended. A gate that hangs would otherwise
#: hang the session that asked, with nothing on the screen saying why.
BUDGET = 120


@dataclass(frozen=True)
class Tool:
    """One thing an agent may ask the harbour, and what it has to say to ask it."""

    name: str
    description: str
    answer: Callable[[Path, dict], str]
    properties: dict = field(default_factory=dict)
    required: tuple[str, ...] = ()
    writes: bool = False

    def listed(self) -> dict:
        return {"name": self.name, "description": self.description,
                "inputSchema": {"type": "object", "properties": self.properties,
                                "required": list(self.required)}}


class Refused(Exception):
    """A tool that cannot answer, said in words rather than raised as a protocol fault.

    A protocol error means the *call* was malformed; a stream that has no log is a perfectly good call with
    an answer the asker needs to read. So these come back as a tool result with `isError`, which is the
    model's to act on, and the session carries on.
    """


def harbour(root: Path) -> None:
    """Refuse a directory that is not a harbour, rather than drawing an empty board of it."""
    if not (root / ".slipwai").is_dir() and not (root / CONFIG).is_file():
        raise Refused(f"{root} is not a harbour: it has no .slipwai/ and no {CONFIG}. Run this in a "
                      f"project `slipwai generate` or `slipwai adopt` made")


def the_board(root: Path, arguments: dict) -> str:
    harbour(root)
    return "\n".join(lines(root))


def one_stream(root: Path, arguments: dict) -> str:
    harbour(root)
    fairway = str(arguments.get("fairway", ""))
    if not fairway:
        raise Refused("a stream's log needs the stream's name: `fairway`")
    limit = int(arguments.get("limit", RECENT) or RECENT)
    return "\n".join(stream_lines(root, fairway, limit))


def the_inbox(root: Path, arguments: dict) -> str:
    """Only what is waiting on a person, which is the question the board exists to answer first."""
    harbour(root)
    waiting = board(root, config(root))["inbox"]
    assert isinstance(waiting, list)
    if not waiting:
        return "waiting on you: nothing"
    said = [f"waiting on you: {len(waiting)}"]
    for row in waiting:
        detail = inbox_detail(row)
        said.append(f"  {row['fairway']:<10} {row['kind']:<7} {detail}")
    return "\n".join(said)


def delivery(root: Path) -> str:
    """Where this project keeps the keel's material, from `project.json`, or `.` where it does not say.

    Read here rather than through the manifest reader because this is the read side: a `project.json` that
    cannot be parsed is a project whose gates cannot be found, which is a sentence, not a generation
    failure. A `delivery` that is absolute or climbs out of the tree is ignored for the obvious reason.
    """
    try:
        document = json.loads((root / "project.json").read_text(encoding="utf-8"))
        said = document["layout"]["delivery"]
    except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError):
        return "."
    if not isinstance(said, str) or not said or said.startswith("/") or ".." in said.split("/"):
        return "."
    return said


def gate(root: Path, script: str) -> str:
    """Run one of the project's own gates and give back what it printed.

    Run rather than reimplemented: `clearance.py` and `check-chart.py` are the project's copies, they move
    with the project, and a keel that held a second implementation of either would answer a question the
    gate would have answered differently.
    """
    place = delivery(root)
    relative = f"{place}/{script}" if place != "." else script
    whole = root / relative
    if not whole.is_file():
        raise Refused(f"{relative} is not in this project, so there is no gate here to run. "
                      f"Run `slipwai migrate` to bring it in")
    try:
        found = subprocess.run([sys.executable, str(whole)], cwd=root, capture_output=True, text=True,
                               timeout=BUDGET)
    except subprocess.TimeoutExpired:
        raise Refused(f"{relative} was still running after {BUDGET}s and was ended") from None
    said = (found.stdout + found.stderr).strip()
    if found.returncode:
        raise Refused(said or f"{relative} exited {found.returncode} and said nothing")
    return said


def the_clearance(root: Path, arguments: dict) -> str:
    harbour(root)
    return gate(root, "scripts/agents/clearance.py")


def the_chart(root: Path, arguments: dict) -> str:
    harbour(root)
    return gate(root, "scripts/check-chart.py")


def a_told(root: Path, arguments: dict) -> str:
    """The one write: a message into a stream's deck log, through the bridge's own function."""
    harbour(root)
    try:
        return tell(root, str(arguments.get("fairway", "")), str(arguments.get("message", "")))
    except (ValueError, OSError) as fault:
        raise Refused(str(fault)) from fault


FAIRWAY = {"fairway": {"type": "string", "description": "the stream's name, as the board spells it"}}

#: Every tool, in the order `tools/list` gives them: the board first, because the question an agent has is
#: nearly always *is anything waiting on me, and is anything stuck*.
TOOLS: tuple[Tool, ...] = (
    Tool("fleet", "The fleet board: what is waiting on a person, what every fairway is doing, the telegraph "
                  "and the last lines of every log. Folded from the logs each time it is asked for.",
         the_board),
    Tool("stream", "One stream's own deck log, a line at a time — the question the board always provokes "
                   "and cannot answer, because the answer is forty lines of one file.",
         one_stream, {**FAIRWAY,
                      "limit": {"type": "integer", "description": "how many lines (default: the last few)"}},
         ("fairway",)),
    Tool("inbox", "Only what is waiting on a person: the questions streams have asked and nobody has "
                  "answered. Ask this before claiming anything.",
         the_inbox),
    Tool("clearance", "Whether each slice may start: a slice has clearance when every mark it steers by has "
                      "been set. Runs this project's own `scripts/agents/clearance.py`.",
         the_clearance),
    Tool("check-chart", "Whether the chart holds: every mark has one setter and every slice is in a "
                        "capability. Runs this project's own `scripts/check-chart.py`.",
         the_chart),
    Tool("tell", "Answer a stream: writes a `told` line into that stream's deck log, which its captain "
                 "reads at its next boundary. The one thing here that changes anything, and it is the same "
                 "line the bridge writes.",
         a_told, {**FAIRWAY, "message": {"type": "string", "description": "what to tell that stream"}},
         ("fairway", "message"), writes=True),
)


def result(found: object, id_: object) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": found}


def content(text: str, failed: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": failed}


def called(params: dict, root: Path) -> dict:
    """One `tools/call`, as the tool result the model reads — refusals included."""
    name = str(params.get("name", ""))
    tool = next((one for one in TOOLS if one.name == name), None)
    if tool is None:
        return content(f"`{name}` is not a tool this server has. There are {len(TOOLS)}: "
                       f"{', '.join(one.name for one in TOOLS)}", failed=True)
    arguments = params.get("arguments")
    try:
        return content(tool.answer(root, arguments if isinstance(arguments, dict) else {}))
    except Refused as refusal:
        return content(str(refusal), failed=True)


def answer(request: dict, root: Path) -> dict | None:
    """One request's answer, or None where it was a notification and an answer would itself be the fault."""
    id_ = request.get("id")
    method = str(request.get("method", ""))
    if id_ is None:
        return None
    if method == "initialize":
        return result({"protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": NAME, "version": VERSION}}, id_)
    if method == "tools/list":
        return result({"tools": [tool.listed() for tool in TOOLS]}, id_)
    if method == "tools/call":
        params = request.get("params")
        return result(called(params if isinstance(params, dict) else {}, root), id_)
    if method == "ping":
        return result({}, id_)
    return {"jsonrpc": "2.0", "id": id_,
            "error": {"code": NO_SUCH_METHOD,
                      "message": f"`{method}` is not a method this server answers. It serves initialize, "
                                 f"ping, tools/list and tools/call"}}


def serve_lines(said: Iterable[str], root: Path) -> list[str]:
    """Every answer to a stream of request lines, which is the whole session with the pipes taken away."""
    out = []
    for line in said:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except ValueError as fault:
            out.append(json.dumps({"jsonrpc": "2.0", "id": None,
                                   "error": {"code": BAD_JSON, "message": f"that line is not JSON: {fault}"}}))
            continue
        found = answer(request, root) if isinstance(request, dict) else None
        if found is not None:
            out.append(json.dumps(found))
    return out


def serve(root: Path, reader: IO[str], writer: IO[str]) -> None:
    """The session: one JSON object per line in, one per line out, flushed as each is written.

    Flushed line by line rather than at the end, because the client is waiting on the answer before it sends
    the next request — a buffered server and a blocked client deadlock with nothing on either screen.
    """
    for line in reader:
        for said in serve_lines([line], root):
            writer.write(said + "\n")
            writer.flush()
