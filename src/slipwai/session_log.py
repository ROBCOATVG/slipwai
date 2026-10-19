"""What a headless session is doing, in the words a person watching the board wants.

Claude Code's print mode writes one JSON event per line. The card used to say an assistant event's text, the
bare name of every tool it reached for and the result — so a session redrawing eleven screens read as a
column of `→ Write`, `→ Write`, `→ Bash`, while each of those events was carrying the file it wrote, the
sentence the agent gave its command and the job it handed a delegate. This reads them:

- a tool says what it acted on — the path, relative to the project; a shell command's own description; a
  delegate's task; a page a browser opened — and a run of the same file tool lists its paths under one name;
- a background task, a delegate or a shell left running, says when it finishes, because that is the only
  moment its line has anything new to say;
- a delegate's own tool calls are indented under it, and its prose is left out: six delegates talking at
  once is noise, and what each one *did* is the part a person checks;
- the todo list is a count and the item in hand;
- the harness's own plumbing — finding a tool, scheduling a wake-up — says nothing.

A line that is not JSON is said as it came. `Folder` holds the little that crosses lines: the last tool,
and which tasks were sent to the background.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

#: Tools that are the harness talking to itself.
QUIET = frozenset({"ToolSearch", "ScheduleWakeup"})
#: Tools whose detail is a path, and whose runs are listed under one name.
FILES = frozenset({"Write", "Edit", "Read", "NotebookEdit", "MultiEdit"})
#: Longest detail a line carries; a shell command can be a page long.
WIDE = 110


def clipped(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first if len(first) <= WIDE else first[: WIDE - 1] + "…"


class Folder:
    """Folds one session's event stream into lines, remembering what one line needs from the last."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = str(root).rstrip("/") + "/" if root else ""
        self.last = ""
        self.background: set[str] = set()

    def place(self, value: object) -> str:
        """A path or a file URL, as it sits in the project."""
        text = str(value or "")
        text = text.removeprefix("file://")
        return text.removeprefix(self.root) if self.root else text

    def detail(self, name: str, given: dict) -> str:
        """What one tool call acted on, or `""` where it says nothing more than its name."""
        if name in FILES:
            return self.place(given.get("file_path") or given.get("notebook_path"))
        if name == "Bash":
            return clipped(str(given.get("description") or given.get("command") or ""))
        if name in ("Glob", "Grep"):
            return clipped(str(given.get("pattern") or ""))
        if name in ("Agent", "Task"):
            return clipped(str(given.get("description") or ""))
        if name == "Workflow":
            found = re.search(r"name:\s*['\"]([^'\"]+)", str(given.get("script") or ""))
            return found.group(1) if found else clipped(str(given.get("name") or ""))
        if name == "Skill":
            return str(given.get("skill") or "")
        if name == "WebSearch":
            return clipped(str(given.get("query") or ""))
        if name == "WebFetch":
            return clipped(str(given.get("url") or ""))
        if name.startswith("mcp__"):
            for key in ("url", "file_path", "selector", "text", "query"):
                if given.get(key):
                    return clipped(self.place(given[key]))
        return ""

    def tool(self, name: str, given: dict, nested: bool) -> list[str]:
        if name in QUIET:
            return []
        if name == "TodoWrite":
            todos = [one for one in given.get("todos") or [] if isinstance(one, dict)]
            done = sum(1 for one in todos if one.get("status") == "completed")
            doing = next((one for one in todos if one.get("status") == "in_progress"), None)
            now = f": {clipped(str(doing.get('activeForm') or doing.get('content') or ''))}" if doing else ""
            return [f"☐ {done} of {len(todos)} done{now}"] if todos else []
        label = name
        if name.startswith("mcp__"):
            server, _, action = name[len("mcp__"):].partition("__")
            label = f"{server}: {action}" if action else server
        detail = self.detail(name, given)
        indent = "    " if nested else ""
        key = f"{indent}{name}"
        if name in FILES and detail and key == self.last:
            return [f"{indent}    {detail}"]
        self.last = key
        separator = " " if name in FILES else ": "
        return [f"{indent}→ {label}{separator + detail if detail else ''}"]

    def fold(self, line: str) -> list[str]:
        if not line.startswith("{"):
            return [line]
        try:
            event = json.loads(line)
        except ValueError:
            return [line]
        if not isinstance(event, dict):
            return [line]
        kind = event.get("type")
        nested = bool(event.get("parent_tool_use_id"))
        if kind == "assistant":
            said: list[str] = []
            message = event.get("message")
            for block in (message.get("content") if isinstance(message, dict) else None) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and not nested:
                    said += [f"• {part}" for part in str(block.get("text", "")).splitlines() if part.strip()]
                    self.last = ""
                elif block.get("type") == "tool_use":
                    given = block.get("input")
                    said += self.tool(str(block.get("name", "tool")), given if isinstance(given, dict) else {},
                                      nested)
            return said
        if kind == "system" and event.get("subtype") == "task_started":
            # Its tool line has already said it started; only a background one has more to say later.
            if event.get("is_backgrounded"):
                self.background.add(str(event.get("task_id", "")))
            return []
        if kind == "system" and event.get("subtype") == "task_notification":
            if str(event.get("task_id", "")) not in self.background:
                return []
            self.background.discard(str(event.get("task_id", "")))
            status = str(event.get("status") or "")
            summary = clipped(str(event.get("summary") or event.get("description") or "a background task"))
            self.last = ""
            return [f"✓ {summary}" if status == "completed" else f"✗ {summary} — {status or 'ended'}"]
        if kind == "result":
            text = str(event.get("result") or "").strip().splitlines()
            usage = event.get("usage")
            tokens = usage.get("output_tokens") if isinstance(usage, dict) else None
            cost = f" — {tokens:,} output tokens" if isinstance(tokens, int) else ""
            return [f"result: {text[0] if text else event.get('subtype', 'ended')}{cost}"]
        return []


def folded_line(line: str) -> list[str]:
    """One line on its own, with nothing remembered from the last: what a caller with no stream to hold
    gets, and what the card's tests read a single event through."""
    return Folder().fold(line)
