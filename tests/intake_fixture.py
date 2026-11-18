"""A board whose project has its first specification, and a hand-over on the stand-in agent `tests/test_acp.py`
uses: the real conversation, over the protocol, with the other end of the wire held still."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest import mock

from board_fixture import BoardTest

from slipwai import board_settings, intake_talk
from slipwai.board_settings import Launch
from slipwai.intake_talk import READY, Handover

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
#: What a person says that the stand-in, which repeats what it is told, turns into the agent's ready line.
CLEAR = f"Billing for clubs. {READY}"


class HandoverTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        patched = mock.patch.object(board_settings, "SETTINGS", self.root / "board.json")
        patched.start()
        self.addCleanup(patched.stop)
        (self.root / "specs/001-demo").mkdir(parents=True)
        (self.root / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        self.launch = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "")
        self.talk = self.opened()
        self.addCleanup(intake_talk.TALKS.clear)

    def opened(self) -> Handover:
        """The project's hand-over as a board just started would hold it: a new object over the same folder."""
        talk = Handover(self.root.resolve(), launch=self.launch)
        intake_talk.TALKS[self.root.resolve()] = talk
        self.addCleanup(talk.cancel)
        return talk

    def settle(self) -> dict:
        for _ in range(400):
            said = json.loads(self.get("/handover.json?since=0")[1])
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the hand-over never finished answering")

    def say(self, message: str, document: dict | None = None) -> dict:
        body = {"message": message, **({"document": document} if document else {})}
        self.assertEqual(self.post("/handover/say", body), (200, "asked"))
        return self.settle()

    def written(self) -> list[str]:
        """Every file under `docs/intake/`, as a path from it."""
        home = self.root / "docs/intake"
        return sorted(one.relative_to(home).as_posix() for one in home.rglob("*") if one.is_file())
