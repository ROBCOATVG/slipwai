"""What `/cruise` does when it is blocked: the bosun protocol, and the short list of things that only park.

A run used to park at the first input nobody had — a credential, a service that was down — and wait for a
person, which is the idle nobody knows about that the whole command exists to prevent. Blocked is now work
before it is a stop: a strong delegate, `sail-unblock-bosun`, is handed the blocker and takes the least surprising
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
    "making a gate pass by changing the gate — anything under `scripts/`, the `Makefile`, anything under `tools/`, CI, "
    "a harness's hook settings: a gate is satisfied in the tree it measures, or the run parks with the gate's own "
    "output as the reason",
    "a run the bosun could not move — the blocker survived its attempt, or the attempt itself would need one of the above",
)


def catastrophic_list() -> str:
    return "\n".join(f"- {item}" for item in CATASTROPHIC)


def unblock_section(script: str) -> str:
    """The `## Blocked: the bosun protocol` section of `commands/cruise.md`."""
    return f"""## Blocked: the bosun protocol

Blocked is work before it is a stop. Whenever this ladder would park — an input nobody here has, a question
whose every option seems to break a MUST, a checkout that will not rebase, a delegate that died mid-slice, a
a slice the captain re-dispatched for making no progress (`/cruise unblock: <reason>` is how it says so) — first
mark the slice blocked, take the next ready slice, and delegate the blocker to one fresh `{BOSUN}` delegate
with what was tried in its brief. Its standing brief carries the moves, in order: stub the world behind the
port the missing thing sits behind, recorded as a deliberate stub in `plan.md` so the board shows it under
*Not working yet*; narrow the reading so every MUST holds and defer the rest behind the flag, with the
amendment a person may want as an ADR at `Proposed`; repair the run. Every move is an entry in
`{DECISIONS}`, written as its own `decisions/D<n>.md` beside it,
with `Decided by: {BOSUN}`, its *Would reverse if* naming what a person must eventually
supply, and a task in the next slice to remove the stub when they do — so nothing done to get moving is done
silently, and a person reading the log sees every workaround in one place. `unblock: park` turns this off
and parks at once.

`unblocked` re-enters the ladder for the slice where it stood. `cannot` is a park with what was tried. And
`catastrophic` is the one word that always parks, because these are what no workaround may be:

{catastrophic_list()}

A park is therefore rare, and it says which of those it met, or what the bosun tried. It is written as a
line in the stream's own deck log, so `slipwai fleet` shows that stream as waiting on somebody with the
reason, and `/cruise-tell <stream>` with the answer is what resumes it.

**A failing gate is never repaired in the gate.** `make verify` red on the slice's own tree is the slice's
work. Red for a reason the tree cannot fix — a browser this machine has not got, a tool not installed, a
script of a kit's that crashes — is a park: `cruise: parked: <gate>: <its own last lines>`, so a person
reads what the gate said and not what a stage made of it. A gate reported as skipped is neither. This is
not left to the text. Two things hold it, and neither is in this session. **The `before-write` and
`before-command` guards** refuse, in a session a captain dispatched, an edit or a shell write under
`scripts/`, `tools/`, the `Makefile`, CI, the hook settings or either registry, before it lands — on every
harness with a pre-tool event, because they are points of a closed set rather than one harness's rows
(`scripts/agents/session.py`). **And the captain compares those files** before and after every stage, on
every harness, and parks the slice on any change, naming the files. A file installed under `tools/` by
`./init --extension` is not a change.
"""
