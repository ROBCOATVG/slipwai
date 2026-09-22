"""What `/cruise` does when it is blocked: the bosun protocol, and the short list of things that only park.

A run used to park at the first input nobody had — a credential, a service that was down — and wait for a
person, which is the idle nobody knows about that the whole command exists to prevent. Blocked is now work
before it is a stop: a strong delegate, `drive-bosun`, is handed the blocker and takes the least surprising
way round — a fake behind the port, a reading that keeps every MUST, a repaired checkout — and writes down
what it did. What remains a park is the catastrophic: destroying, releasing, spending, weakening security,
or discarding a person's commits, which no workaround is allowed to be.
"""
from __future__ import annotations

from .cruise_agents import BOSUN, DECISIONS

CATASTROPHIC = (
    "destroying data or history — dropping a database or volume, rewriting or deleting a shared branch, deleting "
    "what nobody can recover",
    "releasing what a person has not asked for — turning a flag on, deploying or promoting to production, merging "
    "anything that reaches a real actor",
    "spending or exposing — paying for anything, creating or revealing a secret, widening permissions",
    "weakening security — bypassing authentication, loosening a MUST about money, identity or a boundary in "
    "production code",
    "discarding a person's commits to make a checkout consistent",
    "a run the bosun could not move — the blocker survived its attempt, or the attempt itself would need one of the above",
)


def catastrophic_list() -> str:
    return "\n".join(f"- {item}" for item in CATASTROPHIC)


def unblock_section(script: str) -> str:
    """The `## Blocked: the bosun protocol` section of `commands/cruise.md`."""
    return f"""## Blocked: the bosun protocol

Blocked is work before it is a stop. Whenever this ladder would park — an input nobody here has, a question
whose every option seems to break a MUST, a checkout that will not rebase, a delegate that died mid-slice, a
run the outer loop reports as making no progress (`/cruise unblock: <reason>` is how it says so) — first
mark the slice blocked, take the next ready slice, and delegate the blocker to one fresh `{BOSUN}` delegate
with what was tried in its brief. Its standing brief carries the moves, in order: stub the world behind the
port the missing thing sits behind, recorded as a deliberate stub in `plan.md` so the board shows it under
*Not working yet*; narrow the reading so every MUST holds and defer the rest behind the flag, with the
amendment a person may want as an ADR at `Proposed`; repair the run. Every move is an entry in
`{DECISIONS}` with `Decided by: {BOSUN}`, its *Would reverse if* naming what a person must eventually
supply, and a task in the next slice to remove the stub when they do — so nothing done to get moving is done
silently, and a person reading the log sees every workaround in one place. `unblock: park` turns this off
and parks at once.

`unblocked` re-enters the ladder for the slice where it stood. `cannot` is a park with what was tried. And
`catastrophic` is the one word that always parks, because these are what no workaround may be:

{catastrophic_list()}

A park is therefore rare, and it says which of those it met, or what the bosun tried. `python3 {script}
status` shows a parked run's reason beside its checkpoint.
"""
