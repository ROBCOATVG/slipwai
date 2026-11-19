#!/usr/bin/env python3
"""What a guard is told about one tool call: the harness's event, in the keel's words and no more of it.

A harness hands its hook a JSON object in its own spelling — Claude Code's `tool_name`, `tool_input`,
`session_id`, `cwd`, and `agent_id` where a sub-agent made the call. A guard is written once and runs
wherever a harness has such an event, so it is handed the keel's spelling instead, built here, and
`docs/extensions.md` lists the same fields in the same order: `tests/test_guard_event.py` holds the two and
the keel's own list to one another, so the page cannot promise a field this does not send.

**A field that is not there is left out.** An empty string is a claim — *the path was nothing* — and one
guard reads that as *the whole tree* and the next as *no evidence*. A key that is absent is neither.

**And a guard is handed the search, not the session.** The harness's event also names the transcript, the
permission mode and the call's own id. None of them is copied: a guard decides about one search, and the
path to everything a person and an agent said to each other is not part of a search.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

#: Every field a `before-search` guard may find in its event, in the order the contract page lists them.
FIELDS = ["v", "point", "tool", "query", "pattern", "path", "glob", "type", "command", "cwd", "session",
          "agent", "agent_type", "stage", "slice", "fairway"]
#: The contract's own version. A field added is not a new version; a field that changes its meaning is.
VERSION = 1
#: What a search names, each under the key the harness's own tool input uses for it.
SEARCHED = ("pattern", "path", "glob", "type", "command")
#: The longest `SLIPWAI_QUERY` may be. It travels as an argument and then as a variable, and a platform
#: refuses a process whose arguments are too long — which used to mean a long enough shell command reached
#: no guard at all. The event on stdin carries the whole of it.
QUERY_LIMIT = 16_000


def said(value: object) -> str:
    """A field as text, or nothing: only a string that says something is a field."""
    return value if isinstance(value, str) and value.strip() else ""


def tool_input(raw: dict) -> dict:
    given = raw.get("tool_input")
    return given if isinstance(given, dict) else {}


def whose(raw: dict, about: dict[str, str]) -> dict[str, str]:
    """Where the call was made and by whom: the session, and the sub-agent inside it where there is one."""
    named = {"cwd": said(raw.get("cwd")), "session": said(raw.get("session_id")),
             "agent": said(raw.get("agent_id")), "agent_type": said(raw.get("agent_type")),
             **{word: about.get(word, "") for word in ("stage", "slice", "fairway")}}
    return {word: value for word, value in named.items() if value}


def query(raw: dict) -> str:
    """The one string a guard was handed before the event was: the pattern, else the command."""
    given = tool_input(raw)
    return said(given.get("pattern")) or said(given.get("query")) or said(given.get("command"))


def search(raw: dict, about: dict[str, str]) -> dict[str, object]:
    """A search about to run, as a `before-search` guard reads it on stdin."""
    given = tool_input(raw)
    told: dict[str, object] = {"v": VERSION, "point": "before-search"}
    named = {"tool": said(raw.get("tool_name")), "query": query(raw),
             **{word: said(given.get(word)) for word in SEARCHED}}
    told.update({word: value for word, value in named.items() if value})
    told.update(whose(raw, about))
    return {word: told[word] for word in FIELDS if word in told}
