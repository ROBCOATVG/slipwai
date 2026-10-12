"""The project a captain runs in, and the fake `/sail` its suites sail it with.

Not a test module — `unittest discover` collects `test_*.py` only — so this holds what two suites share and
asserts nothing itself. The chart and the fake are rendered from one table: they were two copies, and the
fake set `Placed` whatever slice it was driving, which passed only because nothing read the chart's `sets`.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
CARRIED = ("captain.py", "clearance.py", "inbox.py", "logs.py", "berths.py", "ids.py",
           # The captain dispatches a headless session of the installed harness, so it imports the
           # module that decides which one and the registry that module reads. Every case here sets
           # `SLIPWAI_SAIL`, so neither is consulted — but the import has to resolve.
           "harness.py", "registry.json",
           # The claim a captain takes before it writes `claimed`, and what travels between machines when
           # a lapsed one is taken over.
           "claims.py", "travel.py")
#: The chart these tests run against, as data, so the fake `/sail` below sets the marks this says it does.
#: They were two copies and the fake set `Placed` whatever it was driving, which passed only because the
#: captain did not read the chart's `sets` — exactly the gap slice 7.8 closes.
SLICES: dict[str, tuple[str, list[str], list[str]]] = {
    "ORD-01": ("ORD", ["Placed"], []),
    "ORD-02": ("ORD", ["Paid"], ["Placed"]),
    "BIL-01": ("BIL", ["Charged"], ["Paid"]),
    # A slice that publishes nothing: its whole gate is the demo, which is the one-rule case and not a
    # special one.
    "BIL-02": ("BIL", [], ["Charged"]),
}
CHART = "slices:\n" + "".join(
    f"  {slice_id}:\n    fairway: {fairway}\n    sets: [{', '.join(sets)}]\n"
    f"    steers_by: [{', '.join(steers)}]\n"
    for slice_id, (fairway, sets, steers) in SLICES.items())


def fake_drive(verdict: str = "accepted", marks: bool = True, demo: bool = True) -> str:
    """A fake `/sail`, as the real one is seen from here: a process that writes lines and exits.

    Its argv is `<slice> <fairway>`. What it writes is what the chart says that slice publishes, so a fake
    that is right about one slice is right about all of them.
    """
    table = {slice_id: sets for slice_id, (_f, sets, _s) in SLICES.items()}
    return f"""import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
lines = []
if {marks!r}:
    lines += [{{"kind": "mark-set", "fairway": fairway, "slice": slice_id, "mark": mark}}
              for mark in {table!r}[slice_id]]
if {demo!r}:
    lines.append({{"kind": "demo", "fairway": fairway, "slice": slice_id, "verdict": {verdict!r}}})
with path.open("a", encoding="utf-8") as handle:
    for body in lines:
        handle.write(json.dumps({{"v": 1, "t": now, **body}}) + "\\n")
"""


WORKS = fake_drive()
#: A fake that is alive and writing nothing, which is the failure that cost the first attempt seventeen
#: iterations and which looks identical from outside to one that is working hard.
SILENT = "import time\ntime.sleep(600)\n"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in CARRIED:
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "captain.py"
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        # A git repository, because a generated project is one and because the claim a captain takes before
        # it writes `claimed` is a ref. No remote: a harbour with no forge is the case that has to keep
        # working with no network, and it is where the claim is the local ref rather than a mirror of one.
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=False,
                       capture_output=True)
        self.budget(minutes=5)

    def budget(self, minutes: float, **held: object) -> None:
        # `wait_bound` in seconds-worth-of-minutes: these tests stand in for the harbourmaster by writing
        # its answer, and where they do not the captain should give up quickly rather than sit out the
        # hour a real harbour allows.
        (self.root / "harbour.json").write_text(json.dumps(
            {"stages": {"default": {"minutes": minutes, "tokens": 400}}, "wait_bound": 0.05, **held}),
            encoding="utf-8")

    def harbour(self, *entries: logs.Entry) -> None:
        """Write the harbourmaster's own lines. One process holds the credentials; here that is the test."""
        path = self.root / logs.HARBOUR
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def grant(self, slice_id: str, commit: str = "a1b2c3d", asked: int = 0) -> None:
        """The answer the harbourmaster would write, written before it is asked for.

        The captain matches on the request's id, so an answer that is already there is read on the first
        poll — which keeps these tests about the captain rather than about two processes meeting.
        """
        request = f"merge-{slice_id}-{asked}" if asked else f"merge-{slice_id}"
        self.harbour(logs.entry("granted", harbour=True, fairway=SLICES[slice_id][0], request=request,
                                what="merge", slice=slice_id, commit=commit))

    def refuse(self, slice_id: str, why: str, resolve: bool = False, asked: int = 0) -> None:
        request = f"merge-{slice_id}-{asked}" if asked else f"merge-{slice_id}"
        self.harbour(logs.entry("refused", harbour=True, fairway=SLICES[slice_id][0], request=request,
                                why=why, resolve=resolve))

    def read_harbour(self) -> list[logs.Entry]:
        path = self.root / logs.HARBOUR
        if not path.is_file():
            return []
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)

    def sail(self, body: str) -> str:
        path = self.root / "fake-sail.py"
        path.write_text(body, encoding="utf-8")
        return f"{sys.executable} {path}"

    def captain(self, fairway: str, sail: str, timeout: float = 90,
                machine: str = "") -> subprocess.CompletedProcess:
        import os
        named = {"SLIPWAI_MACHINE": machine} if machine else {}
        return subprocess.run([sys.executable, str(self.script), fairway, "--once"],
                              capture_output=True, text=True, cwd=self.root, timeout=timeout,
                              env={**os.environ, "SLIPWAI_SAIL": sail, **named})

    def hold(self, fairway: str, machine: str) -> None:
        """Another machine takes this fairway's claim, through the same command its captain would."""
        import os
        done = subprocess.run([sys.executable, str(self.root / "scripts/agents/claims.py"),
                               "--take", fairway], capture_output=True, text=True, cwd=self.root,
                              env={**os.environ, "SLIPWAI_MACHINE": machine})
        assert done.returncode == 0, done.stdout + done.stderr

    def claimed_by(self, fairway: str) -> str:
        """The machine the claim ref says holds this fairway, or `""` where nobody does."""
        shown = subprocess.run(["git", "show", "-s", "--format=%an%x1f%s",
                                f"refs/slipwai/claims/{fairway}"], capture_output=True, text=True,
                               cwd=self.root, check=False)
        if shown.returncode != 0:
            return ""
        who, _, state = shown.stdout.strip().partition("\x1f")
        return "" if state.strip() == "released" else who

    def deck(self, fairway: str, *entries: logs.Entry) -> None:
        path = self.root / logs.deck_path("ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def read(self, fairway: str) -> list[logs.Entry]:
        path = self.root / logs.deck_path("ordering", fairway)
        if not path.is_file():
            return []
        return logs.fold(path.read_text(encoding="utf-8").splitlines())


