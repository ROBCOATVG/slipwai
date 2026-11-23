"""A refused merge in one sentence, with the gate's own words kept for whoever opens them.

manda's S81 was refused six times, and the board pasted each refusal as it came: `the full gate failed on
slice/S81 rebased onto origin/main: make[1]: *** [test] Error 1 — it said: ⎯⎯⎯⎯⎯⎯[6/6]⎯ | npm error Lifecycle
script…`. What a person needs first is the sentence — *S81's merge gate failed 6 tests in the merge worktree,
after its own gate passed in its berth* — and the log only when they go looking.
"""
from __future__ import annotations

import re

#: How the harbourmaster words a full gate that failed after the rebase (`harbourmaster.land`).
FULL = re.compile(r"^the full gate failed on (?P<branch>\S+) rebased onto (?P<onto>\S+?):", re.IGNORECASE)
#: Where the gate's own output starts in a refusal.
SAID = " — it said:"
#: How a test runner counts what failed: vitest's `[3/6]⎯` rules, and `6 failed` as vitest, jest and pytest say it.
OF = re.compile(r"\[\d+/(\d+)\]⎯")
FAILED = re.compile(r"\b(\d+) failed\b")
#: The rules and pipes a pasted log is drawn with, which say nothing in a sentence.
RULES = re.compile(r"[⎯─━—]{3,}|\s\|\s")


def failed_count(said: str) -> int:
    """How many tests the gate's output says failed, or 0 where it does not say."""
    counted = [int(one) for one in OF.findall(said)] + [int(one) for one in FAILED.findall(said)]
    return max(counted, default=0)


def summary(slice_id: str, why: str) -> str:
    """The refusal as one sentence: a failed merge gate by what failed and where, anything else by its own
    words up to where the gate's output starts, with no rule or pipe of a pasted log in it."""
    head, _, said = why.partition(SAID)
    if FULL.match(head):
        count = failed_count(said or why)
        what = f"failed {count} test{'s' if count != 1 else ''}" if count else "failed"
        return (f"{slice_id or 'The slice'}'s merge gate {what} in the merge worktree, after its own gate passed "
                f"in its berth.")
    return " ".join(RULES.sub(" ", head).split())


def raw(why: str) -> str:
    """The gate's own words, one line of the log a line, for the disclosure under the sentence."""
    _, _, said = why.partition(SAID)
    return "\n".join(one.strip() for one in said.split(" | ") if one.strip()) if said else ""
