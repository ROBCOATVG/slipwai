#!/usr/bin/env python3
"""The code index kept healthy, kept current and asked first — by the harness and the runner, not by a brief.

A `/cruise` iteration met all four ways an adopted index fails to be used, with nobody making a mistake. The
database was corrupt when the iteration started, and CodeGraph's own commands did not say so: on a malformed
`codegraph.db`, `codegraph status` reports the index up to date and `codegraph sync` exits 0, and only a query
fails. The watcher that keeps it current was off, which CodeGraph decides for itself in a sandbox. Delegates
reached the index as a deferred tool they had to load by name first, and grepped instead. And nothing counted
which delegate asked it. Each of those is a place a sentence in a brief was the only control.

So this script holds the index at the points the harness and the runner already own:

    python3 scripts/agents/code_index.py health   # open it, integrity-check it, rebuild a corrupt one, sync a stale one
    python3 scripts/agents/code_index.py sync     # Claude Code's PostToolUse hook: a delegate came back; sync
    python3 scripts/agents/code_index.py guard    # Claude Code's PreToolUse hook: a symbol search before the index

`health` is what `scripts/agents/cruise.py` runs before every iteration, and what a person runs to repair an index
by hand. The database is ignored by Git and derived from the source, so a corrupt one loses nothing by being moved
aside (to `.codegraph/corrupt/`, the latest only) and rebuilt. `sync` keeps the index current while an iteration is
still editing: after each delegate returns rather than on CodeGraph's watcher, because the watcher is what was off.
`guard` refuses a search of the source for a symbol — the Grep tool, or `grep`, `rg`, `ag`, `ack`, `git grep` or a
`sed -n '/pattern/p'` through the shell — from a session or a delegate that has not asked the index yet, and names
the route that answers instead. A symbol is a name the index holds a definition for, or a name shaped like one
(camelCase, PascalCase with a second hump, snake_case). Words and phrases are prose, and a search confined to
documents is text search, which is right for them: `spec.md`, `decisions.md`, the PRD, `model.yaml`, a test's string.
Once the agent has asked the index, its greps are its own business.

Every route here runs the version the MCP server runs (`CODEGRAPH`), so two versions never write one database.
Standard library only, like every script the toolkit ships. Nothing here fails a command it hooks: a hook that
cannot decide allows the call.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json` (see models.py)."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


SCRIPT = Path(__file__).resolve()
ROOT = project_root(SCRIPT, 2)
# The one pin: the MCP server `./init --extension codegraph` writes, the repo-local `scripts/codegraph`, and every
# command below all run this release. `codegraph help` in it lists the query verbs INDEX_QUERY names.
CODEGRAPH = "@colbymchenry/codegraph@1.6.0"
DIRECTORY = ROOT / ".codegraph"
DATABASE = DIRECTORY / "codegraph.db"
ASIDE = DIRECTORY / "corrupt"
# Which session and delegate has asked the index, for `guard`: inside the index's own ignored directory.
ASKED = DIRECTORY / "asked.json"
EXTENSIONS = ROOT / ".slipwai/extensions.json"
# The gate beside this script's directory, whose reading of index against tree `health` shares.
GATE = SCRIPT.parents[1] / "check-codegraph.py"
# A command that asks the index something, as against one that maintains it (`sync`, `init`, `index`, `serve`).
INDEX_QUERY = re.compile(
    r"\bcodegraph(?:@[\w.-]+)?\s+(query|explore|context|node|files|callers|callees|impact|affected)\b")
# How long a sync or a rebuild may take before the step gives up and says so.
SYNC_SECONDS, BUILD_SECONDS = 120, 900
# The words a refusal starts with, which is how the stream shows where `guard` refused a call.
REFUSED = "code-index: refused"
SEARCHERS = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}
# Documents, whose words a text search is right for: a search confined to these is never a symbol search.
DOCUMENT = re.compile(r"(^|/)(docs|specs|\.specify)(/|$)|\.(md|mdx|txt|ya?ml|json|feature|csv|drawio|html)$")
IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
SHAPED = re.compile(r"[a-z0-9][A-Z]|[A-Za-z0-9]_[A-Za-z0-9]")


def adopted() -> bool:
    """An index is here, or the extension was elected and the index is due."""
    if DIRECTORY.is_dir():
        return True
    try:
        return "codegraph" in (json.loads(EXTENSIONS.read_text()).get("extensions") or [])
    except (OSError, ValueError, AttributeError):
        return False


def route() -> list[str] | None:
    """How to run the pinned CLI: through `npx` where Node is, or an installed `codegraph` where it is not."""
    if shutil.which("npx"):
        return ["npx", "-y", CODEGRAPH]
    if shutil.which("codegraph"):
        return ["codegraph"]
    return None


def cli(*arguments: str, seconds: int = SYNC_SECONDS) -> tuple[bool, str]:
    command = route()
    if command is None:
        return False, "neither `npx` nor `codegraph` is on PATH"
    try:
        done = subprocess.run([*command, *arguments], cwd=ROOT, text=True, capture_output=True, timeout=seconds,
                              stdin=subprocess.DEVNULL, env={**os.environ, "CODEGRAPH_NO_UPDATE_CHECK": "1"})
    except subprocess.TimeoutExpired:
        return False, f"`codegraph {' '.join(arguments)}` took longer than {seconds}s"
    except OSError as error:
        return False, str(error)
    said = (done.stdout + done.stderr).strip().splitlines()
    return done.returncode == 0, said[-1].strip("│└● ").strip() if said else ""


def damage() -> str | None:
    """Why the database cannot be trusted — it does not open, or SQLite's integrity check fails — or None."""
    try:
        with sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True) as connection:
            verdict = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as error:
        return str(error)
    if verdict and verdict[0] == "ok":
        return None
    # SQLite reports every damaged cell on its own line; the first says what kind of damage, the count how much.
    lines = [line for line in str(verdict[0] if verdict else "no verdict").splitlines() if line.strip()
             and "in database main" not in line]
    return lines[0] + (f", and {len(lines) - 1} more" if len(lines) > 1 else "") if lines else "no verdict"


def gate() -> Any:
    """`check-codegraph.py`, loaded, for its reading of which tracked files the index is behind on."""
    import importlib.util
    sys.dont_write_bytecode = True  # no `__pycache__/` beside the gate in the project
    specification = importlib.util.spec_from_file_location("check_codegraph", GATE)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def behind() -> int | None:
    """How many tracked files the index has never seen or read before they changed; None where it cannot say."""
    found = gate().drift()
    return None if found is None else len(found[1]) + len(found[2])


def set_aside() -> str:
    """Move the database and its journal files under `.codegraph/corrupt/`, keeping only this latest copy."""
    shutil.rmtree(ASIDE, ignore_errors=True)
    ASIDE.mkdir(parents=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    for suffix in ("", "-wal", "-shm", "-journal"):
        source = DATABASE.with_name(DATABASE.name + suffix)
        if source.exists():
            source.rename(ASIDE / f"{stamp}-{source.name}")
    return (ASIDE.relative_to(ROOT)).as_posix()


def health() -> dict[str, Any]:
    """Make the index one an iteration can query, and say what that took: `current`, `synced`, `built`, `rebuilt`,
    `unreachable` (no route to the CLI) or `failed` (the step ran and the index is still not right). Nothing where
    no index was adopted."""
    if not adopted():
        return {}
    began = time.monotonic()
    result: dict[str, Any] = {}
    if route() is None:
        result = {"state": "unreachable", "detail": "neither `npx` nor `codegraph` is on PATH, so nothing can "
                                                    "maintain or query the index"}
    elif not DATABASE.is_file():
        done, said = cli("init", "-y", ".", seconds=BUILD_SECONDS)
        result = {"state": "built", "detail": "there was no database; built it with `codegraph init`"}
        if not done:
            result = {"state": "failed", "detail": f"no database, and `codegraph init` failed: {said}"}
    elif (problem := damage()) is not None:
        where = set_aside()
        done, said = cli("init", "-y", ".", seconds=BUILD_SECONDS)
        result = {"state": "rebuilt", "detail": f"the database failed its integrity check ({problem}); moved it "
                                               f"to {where}/ and rebuilt it with `codegraph init`"}
        if not done:
            result = {"state": "failed", "detail": f"the database failed its integrity check ({problem}), was moved "
                                                   f"to {where}/, and `codegraph init` failed: {said}"}
    else:
        stale = behind()
        if stale:
            done, said = cli("sync", ".")
            result = {"state": "synced", "detail": f"{stale} tracked file(s) were ahead of the index; synced it"}
            if not done:
                result = {"state": "failed", "detail": f"{stale} tracked file(s) ahead of the index, and `codegraph "
                                                       f"sync` failed: {said}"}
        else:
            result = {"state": "current", "detail": "opens, passes its integrity check, and describes the tree"}
    if result["state"] in ("built", "rebuilt", "synced"):
        problem, stale = (damage() if DATABASE.is_file() else "no database was written"), None
        if problem is None:
            stale = behind()
        if problem is not None or stale:
            result = {"state": "failed", "detail": f"{result['detail']}, and it is still "
                      + (f"not sound ({problem})" if problem else f"behind on {stale} file(s)")}
    result["seconds"] = round(time.monotonic() - began, 1)
    return result


# --- which calls search the source for a symbol ---------------------------------------------------------------------


def symbols(names: list[str]) -> set[str]:
    """Which of these names the index holds a definition of."""
    if not names or not DATABASE.is_file():
        return set()
    try:
        with sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True) as connection:
            marks = ",".join("?" * len(names))
            return {row[0] for row in connection.execute(
                f"SELECT DISTINCT name FROM nodes WHERE kind NOT IN ('file', 'import') AND name IN ({marks})", names)}
    except sqlite3.Error:
        return set()


def symbol_of(pattern: str) -> str | None:
    """The pattern as the symbol(s) it names, or None where it is words: every alternative must be one identifier,
    and each must be shaped like a symbol or be a name the index defines."""
    stripped = re.sub(r"\\[bB<>]|[\^$()]|\\\(|\\\)", "", pattern)
    parts = [part for part in re.split(r"\\?\|", stripped) if part]
    if not parts or not all(IDENTIFIER.fullmatch(part) for part in parts):
        return None
    known = symbols(parts)
    if all(SHAPED.search(part) or part in known for part in parts):
        return "|".join(parts)
    return None


def documents_only(paths: list[str], globs: list[str]) -> bool:
    """A search confined to documents: every path and every include pattern names one, and at least one was given."""
    named = [item for item in [*paths, *globs] if item]
    return bool(named) and all(DOCUMENT.search(item.rstrip("/*").replace("**", "")) or DOCUMENT.search(item)
                               for item in named)


def commands_of(command: str) -> list[list[list[str]]]:
    """The command's pipelines, each a list of the words of its stages, split where the shell splits them: on `;`,
    `&&`, `||` and newlines between pipelines and on `|` between stages — never inside a quoted pattern."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    pipelines: list[list[list[str]]] = [[[]]]
    try:
        for token in lexer:
            if token in (";", "&&", "||", "&", ";;"):
                pipelines.append([[]])
            elif token == "|":
                pipelines[-1].append([])
            else:
                pipelines[-1][-1].append(token)
    except ValueError:
        return []
    return [[words for words in pipeline if words] for pipeline in pipelines if any(pipeline)]


def shell_searches(command: str) -> list[tuple[str, list[str], list[str]]]:
    """Each search the command runs over files: its pattern, the paths it names and its include patterns. A search
    reading another command's output — `git ls-files | grep Cue` — is over names, not source, and is not one."""
    found = []
    for pipeline in commands_of(command):
        for position, words in enumerate(pipeline):
            while words and "=" in words[0] and not words[0].startswith("-"):
                words = words[1:]
            if not words:
                continue
            program = Path(words[0]).name
            if program == "git" and len(words) > 1 and words[1] == "grep":
                program, words = "grep", words[1:]
            if program == "sed":
                scripts = [word for word in words[1:] if not word.startswith("-")]
                address = re.match(r"^/((?:\\.|[^/])+)/", scripts[0]) if scripts else None
                if address:
                    found.append((address.group(1), scripts[1:], []))
                continue
            if program not in SEARCHERS:
                continue
            pattern, paths, globs, rest = None, [], [], words[1:]
            index = 0
            while index < len(rest):
                word = rest[index]
                if word in ("-e", "--regexp") and index + 1 < len(rest):
                    pattern, index = rest[index + 1], index + 2
                    continue
                if word.startswith("--include=") or word.startswith("--glob="):
                    globs.append(word.split("=", 1)[1])
                elif word in ("-g", "--glob", "--include", "-t", "--type") and index + 1 < len(rest):
                    globs.append(rest[index + 1] if word not in ("-t", "--type") else f"*.{rest[index + 1]}")
                    index += 1
                elif word.startswith("-"):
                    pass
                elif pattern is None:
                    pattern = word
                else:
                    paths.append(word)
                index += 1
            if pattern is not None and (paths or position == 0):
                found.append((pattern, paths, globs))
    return found


def symbol_search(tool: str, given: dict[str, Any]) -> str | None:
    """The symbol a tool call searches the source for, or None where it searches documents, words, or nothing."""
    if tool == "Grep":
        glob = given.get("glob") or (f"*.{given['type']}" if given.get("type") else "")
        if documents_only([str(given.get("path") or "")], [str(glob)]):
            return None
        return symbol_of(str(given.get("pattern", "")))
    if tool == "Bash":
        for pattern, paths, globs in shell_searches(str(given.get("command", ""))):
            if not documents_only(paths, globs) and (symbol := symbol_of(pattern)):
                return symbol
    return None


def index_query(tool: str, given: dict[str, Any]) -> bool:
    return tool.startswith("mcp__codegraph__") or (tool == "Bash" and bool(INDEX_QUERY.search(str(given.get("command", "")))))


# --- the hooks ------------------------------------------------------------------------------------------------------


def event() -> dict[str, Any]:
    try:
        read = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return read if isinstance(read, dict) else {}


def asker(happened: dict[str, Any]) -> str:
    """Whose call this is: the session, and the delegate inside it where there is one."""
    return f"{happened.get('session_id', '?')}:{happened.get('agent_id') or 'host'}"


def load_asked() -> dict[str, float]:
    try:
        read = json.loads(ASKED.read_text())
    except (OSError, ValueError):
        return {}
    return read if isinstance(read, dict) else {}


def guard() -> int:
    """Refuse a symbol search of the source from whoever has not asked the index yet; record who has."""
    happened = event()
    tool = str(happened.get("tool_name", ""))
    given = happened.get("tool_input") if isinstance(happened.get("tool_input"), dict) else {}
    if not DATABASE.is_file() or route() is None:
        return 0
    asked = load_asked()
    who = asker(happened)
    if index_query(tool, given):
        asked[who] = time.time()
        try:
            ASKED.write_text(json.dumps(dict(sorted(asked.items(), key=lambda pair: pair[1])[-200:])) + "\n")
        except OSError:
            pass
        return 0
    if who in asked:
        return 0
    symbol = symbol_search(tool, given)
    if symbol is None:
        return 0
    first = symbol.split("|")[0]
    print(f"{REFUSED}: `{symbol}` is a symbol, and this repository's code index answers who calls it, what it calls "
          f"and what a change to it reaches. Ask it first: `scripts/codegraph callers {first}`, `scripts/codegraph "
          f"impact {first}` or `scripts/codegraph explore {first}` through the shell, or the codegraph_explore tool. "
          "A text search is for words in documents — spec.md, decisions.md, model.yaml, a test's string — and once "
          "the index has been asked in this context a search for a symbol is allowed too.", file=sys.stderr)
    return 2


def sync() -> int:
    """A delegate came back, having edited what it edited: bring the index up to it. Never fails the call."""
    if DATABASE.is_file() and route() is not None:
        cli("sync", ".")
    return 0


# --- what the stream says each delegate did --------------------------------------------------------------------------


def delegate_use(stream: Path, only: int | None = None) -> dict[int, list[dict[str, Any]]]:
    """Per iteration of a runner's stream, per agent — the host session, then each delegate in the order it was sent —
    how often it asked the index, which symbols it searched the source for before it had, and how often `guard`
    refused it. Claude Code marks a delegate's events with `parent_tool_use_id`; a harness whose stream does not
    is counted as the host alone."""
    found: dict[int, list[dict[str, Any]]] = {}
    if not stream.is_file():
        return found
    iteration, agents = 0, {}
    for line in stream.read_text(errors="replace").splitlines():
        if line.startswith("# iteration "):
            iteration = int(line.split()[2])
            if only is not None and iteration != only:
                continue
            agents = {"": {"agent": "host", "queries": 0, "searched_first": [], "refused": 0}}
            found[iteration] = list(agents.values())
            continue
        if only is not None and iteration != only:
            continue
        try:
            happened = json.loads(line)
        except ValueError:
            continue
        if not isinstance(happened, dict) or iteration not in found:
            continue
        owner = agents.get(str(happened.get("parent_tool_use_id") or ""), agents[""])
        message = happened.get("message") if isinstance(happened.get("message"), dict) else {}
        for block in message.get("content") if isinstance(message.get("content"), list) else []:
            if not isinstance(block, dict):
                continue
            given = block.get("input") if isinstance(block.get("input"), dict) else {}
            if block.get("type") == "tool_use":
                name = str(block.get("name", ""))
                if name in ("Agent", "Task"):
                    agents[str(block.get("id", ""))] = {"agent": str(given.get("subagent_type") or "delegate"),
                                                        "queries": 0, "searched_first": [], "refused": 0}
                    found[iteration].append(agents[str(block.get("id", ""))])
                elif index_query(name, given):
                    owner["queries"] += 1
                elif not owner["queries"] and (symbol := symbol_search(name, given)):
                    owner["searched_first"].append(symbol)
            # An error result carrying the hook's words: an index answer quoting this file is not a refusal.
            elif block.get("type") == "tool_result" and block.get("is_error") and REFUSED in json.dumps(block.get("content")):
                owner["refused"] += 1
        item = happened.get("item") if isinstance(happened.get("item"), dict) else {}
        if happened.get("type") == "item.started":
            if (item.get("type") == "mcp_tool_call" and item.get("server") == "codegraph") or (
                    item.get("type") == "command_execution" and INDEX_QUERY.search(str(item.get("command", "")))):
                owner["queries"] += 1
            elif item.get("type") == "command_execution" and not owner["queries"]:
                symbol = symbol_search("Bash", {"command": item.get("command", "")})
                if symbol:
                    owner["searched_first"].append(symbol)
    return found


def use_lines(iteration: int, agents: list[dict[str, Any]]) -> list[str]:
    """The feed's and `status`'s account of one iteration: the queries per agent, then each agent that searched the
    source for a symbol before asking the index."""
    counts = ", ".join(f"{agent['agent']} {agent['queries']}" for agent in agents)
    lines = [f"cruise: iteration {iteration} asked the code index {sum(agent['queries'] for agent in agents)} time(s) — "
             f"{counts}"]
    for agent in agents:
        if agent["searched_first"]:
            shown = ", ".join(f"`{each}`" for each in dict.fromkeys(agent["searched_first"]))
            lines.append(f"cruise:   {agent['agent']} searched the source for {shown} before asking the index")
        if agent["refused"]:
            lines.append(f"cruise:   {agent['agent']} was refused {agent['refused']} symbol search(es) until it asked")
    return lines


def main(argv: list[str]) -> int:
    verb = argv[0] if argv else ""
    if verb == "health":
        said = health()
        print(f"code-index: {said['state']} — {said['detail']}" if said else "code-index: no index adopted here")
        return 1 if said.get("state") in ("failed", "unreachable") else 0
    if verb == "guard":
        return guard()
    if verb == "sync":
        return sync()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
