"""The seventh review of the captain agent: what the program says of its agent, a long thread, and a late pause.

1. A `noted` line — the captain program saying something about its own agent — is no slice's progress: alone in
   flight or not, it does not restart a silent stage's clock, at the piece and through a run with the stand-in
   captain.
2. A thread longer than one read is read to its end on the first read of a fresh process, so a person's pause
   written last is never missed.
3. A person's pause that lands after the captain's park was checked, and before it took effect, wins over the
   park where the turn reads how its slices ended (`sail_out`), not only in `ended`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from test_captain_agent import AgentBase
from test_captain_helm import loaded

from slipwai import logs, talk

#: A session that writes no line of its own, while a `noted` line naming no slice lands every half second, as
#: the captain program writes one; it outlives the stage's bound by far.
NOTING = """import sys, json, pathlib, datetime, time
fairway = sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
for _ in range(30):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, "kind": "noted", "fairway": fairway, "by": "captain program",
                                 "what": "The captain's session was refused a command"}) + "\\n")
    time.sleep(0.5)
"""
SILENCED = "nothing was written to the deck log"


class NotedTest(AgentBase):
    def setUp(self) -> None:
        super().setUp()
        self.program = loaded(self.root, "captain")

    def test_a_noted_line_is_no_slice_s_progress_alone_or_beside_another(self) -> None:
        found = [logs.entry("noted", fairway="ORD", by="captain program", what="the agent failed"),
                 logs.entry("heartbeat", fairway="ORD"),
                 logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed")]
        self.program.FLIGHT.clear()
        self.program.FLIGHT["ORD-01"] = {}
        self.assertEqual([e.kind for e in self.program.mine(found, "ORD-01")], ["heartbeat", "mark-set"])
        self.program.FLIGHT["ORD-02"] = {}
        self.assertEqual([e.kind for e in self.program.mine(found, "ORD-01")], ["mark-set"])

    def test_through_a_run_a_session_that_writes_nothing_is_ended_whatever_the_program_notes(self) -> None:
        self.budget(minutes=0.05)  # three seconds of silence ends a stage
        self.settings(bound=20)
        self.granted("ORD-01")
        held = self.root / "noting-sail.py"
        held.write_text(NOTING, encoding="utf-8")
        clean = {"SLIPWAI_SAIL": f"{sys.executable} {held}"}
        said = self.turn("today", **clean)
        parked = " ".join(str(e.fields.get("why", "")) for e in self.read("ORD") if e.kind == "parked")
        self.assertIn(SILENCED, parked, said)


class LongThreadTest(AgentBase):
    def test_a_pause_written_last_on_a_thread_longer_than_one_read_is_read_by_a_fresh_reader(self) -> None:
        home = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        home.mkdir(parents=True)
        line = json.dumps({"v": 1, "t": "2026-11-17T09:00:00Z", "kind": "seen", "id": "x" * 40}) + "\n"
        path = home / "thread.jsonl"
        with path.open("w", encoding="utf-8") as out:
            out.write(line * (int(talk.THREAD_READ * 1.2) // len(line)))
        talk.note(home, "paused", by="person", why="lunch")
        self.assertGreater(path.stat().st_size, talk.THREAD_READ)
        talk.READ.pop(path, None)  # what a fresh process has read of it: nothing
        self.assertEqual(talk.halted(home), ("paused", "person", "lunch"))
        talk.note(home, "resumed", by="person")
        self.assertEqual(talk.halted(home)[0], "", "and what is appended after is read from where it ended")

    def test_a_long_thread_is_read_through_the_one_reader_a_bounded_piece_at_a_time(self) -> None:
        home = talk.place(logs.run_dir(self.root), "ORD", "ORD-02")
        home.mkdir(parents=True)
        (home / "thread.jsonl").write_text("".join(json.dumps({"kind": "seen", "id": str(n)}) + "\n"
                                                   for n in range(400)), encoding="utf-8")
        asked: list[int] = []
        real = talk.read_bytes

        def counted(path: Path, limit: int = talk.LARGEST, start: int = 0) -> Any:
            asked.append(limit)
            return real(path, limit, start)
        with mock.patch.object(talk, "THREAD_READ", 1000), mock.patch.object(talk, "read_bytes", counted):
            self.assertEqual(len(talk.thread(home)), 400)
        self.assertGreater(len(asked), 1)
        self.assertEqual(set(asked), {1000})


class LatePauseTest(AgentBase):
    """`sail_out` with the slice's own work stood in for: the captain's park was checked and set, then a person
    paused the slice, then its session ended on the captain's stop."""

    def setUp(self) -> None:
        super().setUp()
        self.program = loaded(self.root, "captain")
        self.program.ON.update(feature="ordering", fairway="ORD")

    def turned(self, person: bool) -> list[str]:
        program = self.program
        home = program.conversation("ORD", "ORD-01")

        def work(slice_id: str, feature: str, fairway: str) -> tuple[bool, str]:
            # The captain's park passed `stuck_check` — nobody held the slice — and was set on the slice...
            self.assertEqual(program.stuck_check("ORD", slice_id)({"verb": "park", "slice": slice_id}, []), "")
            program.FLIGHT[slice_id]["parking"] = "going in circles"
            # ...its stop was carried out, and a person's pause landed before the turn read how it ended.
            talk.note(home, "stopped", by="captain:ORD", why="going in circles")
            if person:
                talk.note(home, "pausing", by="person", why="lunch")
            raise program.Halted("stopped", "captain:ORD", "going in circles")
        with mock.patch.object(program, "work", work):
            return list(program.sail_out("ordering", "ORD", ["ORD-01"], False))

    def ends(self) -> list[tuple[str, Any, Any]]:
        return [(e.kind, e.fields.get("by") or e.fields.get("cause"), e.fields.get("paused")) for e in self.read("ORD")
                if e.kind in ("parked", "stopped")]

    def test_a_person_s_pause_after_the_park_was_checked_wins_where_the_turn_reads_the_end(self) -> None:
        self.assertEqual(self.turned(person=True), ["captain: ORD-01 paused by person — lunch"])
        self.assertEqual(self.ends(), [("stopped", "person", True)])

    def test_with_no_person_s_pause_the_captain_s_park_is_written_and_read_by_every_reader(self) -> None:
        self.assertEqual(self.turned(person=False), ["captain: ORD parked at ORD-01 — going in circles"])
        self.assertEqual(self.ends(), [("parked", "other", None)])


if __name__ == "__main__":
    import unittest
    unittest.main()
