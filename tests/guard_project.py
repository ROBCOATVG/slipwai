"""A project small enough to make in a test, laid out the way a guard meets one.

`session.py` is where a harness's event arrives and `guards.py` is what runs an extension's guard, and the
two are files a generated project runs — so the suites that hold what a guard is handed copy them out of the
toolkit and run them as a harness would: an event on stdin, an exit code back. Nothing here imports
`slipwai`; a project has none.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parents[1] / "assets/toolkit"
#: What `session.py` needs beside it. The rest of `scripts/agents/` is the captain's, and no guard runs it.
AGENT_SCRIPTS = ("session.py", "logs.py", "tool_event.py")
#: A guard that writes down what it was handed and refuses nothing: stdin, and the variables it was promised.
PROBE = """\
import json, os, sys
from pathlib import Path
given = sys.stdin.read()
seen = {name: value for name, value in os.environ.items() if name.startswith("SLIPWAI_")}
with (Path(__file__).parent / "handed.jsonl").open("a", encoding="utf-8") as out:
    out.write(json.dumps({"stdin": given, "environment": seen}) + "\\n")
"""


class Project:
    """One temporary project with the toolkit's own session and guard scripts in it."""

    def __init__(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name).resolve()
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        for place, names in (("scripts/agents", AGENT_SCRIPTS), ("scripts/extensions", None)):
            (self.root / place).mkdir(parents=True)
            for source in sorted((TOOLKIT / place).glob("*.py"), key=lambda path: path.name):
                if names is None or source.name in names:
                    (self.root / place / source.name).write_text(source.read_text(encoding="utf-8"),
                                                                 encoding="utf-8")
        self.extensions = self.root / "scripts/extensions"
        self.registry = self.root / ".slipwai/guards.json"
        self.available = self.extensions / "available-guards.json"

    def close(self) -> None:
        self.holder.cleanup()

    def extension(self, key: str, guards: dict, **files: str) -> Path:
        """An extension as generation leaves one: its files, and what it may refuse beside the others'."""
        home = self.extensions / key
        home.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            target = home / name.replace("__", "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        offered = json.loads(self.available.read_text(encoding="utf-8")) if self.available.is_file() else {}
        offered[key] = guards
        self.available.write_text(json.dumps(offered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return home

    def elected(self, *keys: str) -> None:
        """Which extensions this project elected, as `./init` records it."""
        (self.root / ".slipwai").mkdir(exist_ok=True)
        (self.root / ".slipwai/extensions.json").write_text(
            json.dumps({"extensions": sorted(keys)}) + "\n", encoding="utf-8")

    def guards(self, *arguments: str, given: str | None = None) -> subprocess.CompletedProcess:
        """`scripts/extensions/guards.py`, with nobody at a terminal."""
        return subprocess.run([sys.executable, str(self.extensions / "guards.py"), *arguments],
                              capture_output=True, text=True, cwd=self.root, timeout=120, input=given,
                              stdin=subprocess.DEVNULL if given is None else None)

    def session(self, verb: str, event: dict, **named: str) -> subprocess.CompletedProcess:
        """`scripts/agents/session.py <verb>`, the way a harness runs it: its event on stdin."""
        environment = {name: value for name, value in os.environ.items() if not name.startswith("SLIPWAI_")}
        return subprocess.run([sys.executable, str(self.root / "scripts/agents/session.py"), verb],
                              input=json.dumps(event), capture_output=True, text=True, cwd=self.root,
                              timeout=120, env={**environment, **named})

    def handed(self, key: str) -> list[dict]:
        """Everything `PROBE` wrote down, oldest first, its stdin read as the JSON it should be."""
        path = self.extensions / key / "handed.jsonl"
        if not path.is_file():
            return []
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            row["event"] = json.loads(row["stdin"]) if row["stdin"].strip() else None
        return rows

    def agreed(self) -> dict[str, list[str]]:
        """Who may refuse at each guard, read off the registry."""
        found = json.loads(self.registry.read_text(encoding="utf-8"))["guards"]
        return {name: [body["extension"] for body in bodies] for name, bodies in found.items()}
