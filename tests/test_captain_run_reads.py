"""Every read a captain program makes, held to one decision: through the one reader, or listed here with why.

The run folder is written by more hands than the program's — a slice's session has a shell — so what it reads
there goes through `talk.read_bytes` (and `read_json` over it): opened once, never through a link, never
waiting on a pipe, capped, and never raised on. Round 6 found reads that bypassed it one at a time; this holds
the class. Every module the captain program loads — `captain.py` and `orders.py` and whatever they import, found
from their imports, so a new module joins by being imported — is scanned for `json.load(s)`, `.read_text(`,
`.read_bytes(` and `open(`, and each call site (file:function) must be in `ALLOWED` with a reason. A new raw
read fails here until somebody decides what it is; an entry nothing matches any more fails as well.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
PROJECT = "a file of the project's own — its settings, chart, ledger or registry — not the run folder"
LOGS = ("the deck or harbour log, through `logs`, whose refusal of a line it cannot read — one nested past the "
        "parser included — is that reader's contract")
WRITES = "opened to append or write, not to read"
READER = "the one reader for the run folder itself, or the flags it opens with"
ALLOWED = {
    "abreast.py:deck_of": LOGS,
    "abreast.py:harbour_plan": PROJECT,
    "acp.py:Session.shaken": WRITES,
    "acp.py:one_at_a_time": "the machine's launch lock, in the temp directory and not the run folder: opened to "
                            "append and held, never read",
    "acp.py:Session.read": "a protocol line on the agent's stdout, not a file",
    "acp.py:Session.gone": "the agent's own stderr log, which this session opened to append; its tail, decoded "
                           "with replacement, is only said",
    "acp.py:kept_session": "the keel's board alone: no toolkit script calls it",
    "captain.py:harbour": PROJECT,
    "captain.py:cruising": PROJECT,
    "captain.py:entries": LOGS,
    "captain.py:write": WRITES,
    "captain.py:sail_model": PROJECT,
    "captain.py:decide_parked.one": WRITES,
    "captain.py:ledgered": "the dispatch ledger in the slice's berth, a tracked file of the project",
    "captain.py:release_after_publication": LOGS,
    "captain_events.py:Helm.decided": "`Helm.open`, which puts an event: not a file read",
    "claims.py:take": PROJECT,
    "clearance.py:chart": PROJECT,
    "clearance.py:lines": LOGS,
    "clearance.py:demos_setting": PROJECT,
    "clearance.py:dispatch_starts": "the dispatch ledger, a tracked file of the project",
    "clearance.py:given_by": PROJECT,
    "clearance.py:migration_hold": PROJECT,
    "clearance.py:slice_graph": PROJECT,
    "clearance.py:preferred_fairways": PROJECT,
    "clearance.py:done_marked": PROJECT,
    "clearance.py:baseline": WRITES,
    "clearance.py:numbers_from": PROJECT,
    "drive.py:setting": PROJECT,
    "drive.py:Drive.run": "`Drive.open`, which opens the session: not a file read",
    "drive.py:Drive.record": WRITES,
    "feedback.py:decisions": PROJECT,
    "feedback.py:parked_states": PROJECT,
    "feedback.py:clarifications": PROJECT,
    "feedback.py:has_web_app": PROJECT,
    "feedback.py:flagged": PROJECT,
    "fleet.py:config": PROJECT,
    "fleet.py:start": WRITES,
    "fleet.py:relight_harbourmaster": WRITES,
    "fleet.py:word_waiting": LOGS,
    "fleet.py:open_fairway_parks": LOGS,
    "fleet.py:watch": "`fleet.py watch`, a person's command that prints the logs; never the captain",
    "fleet.py:tell": WRITES,
    "fleet.py:app_too_old": PROJECT,
    "harness.py:registry": PROJECT,
    "harness.py:installed_keys": PROJECT,
    "harness.py:elected_tools": PROJECT,
    "harness.py:Ending.read": "a line of a session's own output, not a file",
    "inbox.py:settings": PROJECT,
    "inbox.py:cruising": PROJECT,
    "inbox.py:lines": LOGS,
    "logs.py:run_dir": PROJECT,
    "logs.py:read": LOGS,
    "logs.py:harbour_fold": LOGS,
    "logs.py:stream_lines": LOGS,
    "captain.py:strays": LOGS,
    "moorings.py:generator": "`project.json` as a commit holds it, printed by `git show`: a tracked file of "
                             "the project, and not read from disk at all",
    "moorings.py:linked_at": "git's own exclude file in the checkout",
    "moorings.py:mid_rebase": "git's own `head-name` under a worktree's open rebase, which no program of the "
                              "run writes",
    "stuck.py:tail_lines": "the board's reader of an activity log, opened as `talk.read_bytes` opens; the captain "
                           "reads through `talk` and hands the bytes to `stuck.parsed`",
    "stuck.py:parsed": "parses bytes it is handed, never raising: not a read",
    "talk.py:ready": WRITES,
    "talk.py:read_bytes": READER,
    "talk.py:read_json": READER,
    "talk.py:json_lines": READER,
    "talk.py:note": WRITES,
    "travel.py:last_heard": "a deck log as git holds it on a ref, not a file",
    "travel.py:push_log": LOGS,
    "travel.py:land_ref": "a file in a temporary checkout of a ref, not the run folder",
    "travel.py:in_flight_all": LOGS,
    "travel.py:in_flight": LOGS,
}


def loaded_by_the_captain() -> list[Path]:
    """`captain.py`, `orders.py`, and every toolkit script either imports, found by following their imports."""
    local = {path.stem for path in AGENTS.glob("*.py")}
    seen: set[str] = set()
    todo = ["captain", "orders"]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((AGENTS / f"{name}.py").read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                todo += [one.name for one in node.names if one.name in local]
            elif isinstance(node, ast.ImportFrom) and node.module in local:
                todo.append(str(node.module))
    return sorted(AGENTS / f"{name}.py" for name in seen)


def reads(path: Path) -> set[str]:
    """Every `file:function` in one script that reads a file by any way but the one reader."""
    found: set[str] = set()
    where: list[str] = []

    class Look(ast.NodeVisitor):
        def scope(self, node: ast.AST) -> None:
            where.append(getattr(node, "name", ""))
            self.generic_visit(node)
            where.pop()

        visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = scope

        def visit_Call(self, node: ast.Call) -> None:
            called = node.func
            through_talk = isinstance(called, ast.Attribute) and isinstance(called.value, ast.Name) \
                and called.value.id == "talk"
            raw = (isinstance(called, ast.Name) and called.id == "open") or (
                isinstance(called, ast.Attribute) and not through_talk and (
                    called.attr in ("read_text", "read_bytes", "open")
                    or (called.attr in ("load", "loads") and isinstance(called.value, ast.Name)
                        and called.value.id == "json")))
            if raw:
                found.add(f"{path.name}:{'.'.join(where) or '<module>'}")
            self.generic_visit(node)
    Look().visit(ast.parse(path.read_text(encoding="utf-8")))
    return found


class RunReadsTest(unittest.TestCase):
    def test_every_read_the_captain_program_makes_is_the_one_reader_or_decided_here(self) -> None:
        found: set[str] = set()
        for path in loaded_by_the_captain():
            found |= reads(path)
        self.assertEqual(sorted(found - set(ALLOWED)), [], "a read nobody has decided about: route it through "
                                                           "talk.read_bytes / talk.read_json, or list it with why")
        self.assertEqual(sorted(set(ALLOWED) - found), [], "listed, and no longer there: take it off the list")

    def test_the_readers_that_cannot_import_talk_open_as_it_does(self) -> None:
        """`stuck` is carried with nothing to import, so it holds its own copy of the flags: the same ones."""
        flags = [line.split("=", 1)[1].strip() for name in ("talk.py", "stuck.py")
                 for line in (AGENTS / name).read_text(encoding="utf-8").splitlines() if line.startswith("OPENING =")]
        self.assertEqual(len(flags), 2)
        self.assertEqual(flags[0], flags[1])


if __name__ == "__main__":
    unittest.main()
