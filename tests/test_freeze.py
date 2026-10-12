"""The freeze: the strangler's precondition, and the one `/strangle` asks for first (15.9).

A strangler fig grows beside a system that is standing still. Where the legacy system keeps gaining
features, every capability that moves has to be re-read against what the old one did last fortnight, the
pinned tests go stale on somebody else's release, and the retirement ledger stops meaning anything — which
is the failure `docs/change-strategy.md` exists to prevent, arriving through the back door.

So the agreement is a precondition and not a technique: no new features in the legacy system, bug fixes
only, no schema changes, agreed by somebody who can hold other teams to it. It is recorded where the
strategy itself is recorded — on the accepted ADR — because it is the same decision seen from the legacy
system's side, and both halves have to survive the next `/survey` together.

Three claims. **Both answers are read off the ADR**: `agreed`, with who agreed it, and `absent`, with what
the programme does instead. **Silence is neither**, and is read as nothing recorded rather than as a freeze
nobody mentioned. And **`/strangle` says where it stands today and refuses the first capability on
silence** — it never invents either answer, because a freeze nobody recorded is one nobody agreed to.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.project.strangle_command import strangle_files
from slipwai.services import App
from slipwai.strategy import decision_of, with_recommendation

DELIVERY = Layout("delivery")
ADR = """# 0002. Change strategy

Date: 2026-10-12

## Status

Accepted

## Context

A capability has to change and the system cannot stop.

## Decision

Strategy: strangler-fig
{freeze}

## Consequences

None yet.
"""


def wrapped() -> App:
    return App("shop", ".", "service", "javascript", None, 0, generated=False, commands={"test": None})


def essay() -> str:
    return strangle_files([wrapped()], DELIVERY, "existing", None)["docs/change-strategy.md"]


def strangle(adoption: Adoption) -> str:
    return strangle_files([wrapped()], DELIVERY, "existing", adoption)["commands/strangle.md"]


def decided(root: Path, freeze: str) -> Adoption:
    """The adoption of a repository whose accepted ADR decides the strangler, saying `freeze` about it."""
    (root / "delivery/docs/adr").mkdir(parents=True, exist_ok=True)
    (root / "delivery/docs/adr/0002-strategy.md").write_text(ADR.format(freeze=freeze), encoding="utf-8")
    return with_recommendation(root, DELIVERY, Adoption(why="a new capability has to ship"), [wrapped()])


class FreezeTest(unittest.TestCase):
    """The strangler's precondition, asked before the first capability moves."""

    def test_an_agreed_freeze_is_read_off_the_strategy_adr_with_who_agreed_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "delivery/docs/adr").mkdir(parents=True)
            (root / "delivery/docs/adr/0002-strategy.md").write_text(
                ADR.format(freeze="\nFreeze: agreed — Priya Raman, head of platform, 2026-10-09"),
                encoding="utf-8")
            record = decision_of(root, DELIVERY)
            self.assertEqual(record["freeze"]["state"], "agreed")
            self.assertIn("Priya Raman", record["freeze"]["said"])

    def test_an_absent_freeze_is_recorded_as_absent_with_what_is_done_instead(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "delivery/docs/adr").mkdir(parents=True)
            (root / "delivery/docs/adr/0002-strategy.md").write_text(
                ADR.format(freeze="\nFreeze: absent — the legacy team ships fortnightly; each release is "
                                  "re-pinned by /characterise before the next capability moves"),
                encoding="utf-8")
            record = decision_of(root, DELIVERY)
            self.assertEqual(record["freeze"]["state"], "absent")
            self.assertIn("re-pinned", record["freeze"]["said"])

    def test_an_adr_that_says_nothing_about_it_records_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "delivery/docs/adr").mkdir(parents=True)
            (root / "delivery/docs/adr/0002-strategy.md").write_text(ADR.format(freeze=""), encoding="utf-8")
            self.assertIsNone(decision_of(root, DELIVERY)["freeze"])

    def test_the_command_asks_for_it_before_the_first_capability_moves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command = strangle(decided(Path(directory), ""))
            self.assertIn("**No freeze, no first capability.**", command)
            self.assertIn("no new features in the legacy system, bug fixes only, no schema changes", command)
            self.assertIn("Today it reads `absent` — nothing", command)

    def test_the_command_says_what_the_adr_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agreed = strangle(decided(Path(directory), "\nFreeze: agreed — Priya Raman, 2026-10-09"))
            self.assertIn("`agreed` — Priya Raman, 2026-10-09", agreed)
        with tempfile.TemporaryDirectory() as directory:
            instead = strangle(decided(Path(directory), "\nFreeze: absent — re-pinned every fortnight"))
            self.assertIn("`absent` — re-pinned every fortnight", instead)

    def test_the_essay_names_the_freeze_as_what_the_strangler_needs(self) -> None:
        page = essay()
        row = next(line for line in page.splitlines() if line.startswith("| **Strangler fig**"))
        self.assertIn("freeze", row)

if __name__ == "__main__":
    unittest.main()
