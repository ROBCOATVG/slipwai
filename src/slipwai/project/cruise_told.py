"""A person's word to a run under way: what `commands/cruise.md` says about `told: <message>`.

A run used to hear from a person twice — in the kick-off, which reaches the first iteration only, and through
the stop file. Everything in between meant editing the owner brief and hoping the next iteration read it that
way. `/cruise-tell` queues a message instead, and the runner hands it to the iteration it starts next as
`told: <message>` in the argument, the kick-off's own route; the iteration asks for later ones between stages;
and the watch seat queues what a person types for the run rather than doing anything about it itself. These
are the three paragraphs of the command that say so, kept beside each other because they name one route.
"""
from __future__ import annotations

from .cruise_agents import OWNER_BRIEF


def told_argument(script: str) -> str:
    """The kick-off paragraph's third argument: what a message is, where it reaches, and what to do with it."""
    return f"""A third is a person's: `told: <message>`
is what somebody queued for the run through `/cruise-tell` (`python3 {script} tell`) since the last iteration
started, one `told:` per message in the order they were sent, and it reaches the iteration the runner starts next —
never the one in flight, unless they ended it for the message. Read it before the first stage and act on it
first: a steer takes precedence over what the artifacts alone would make this iteration do, a fact the run lacked
is the answer to a block, and a scope or a preference is written down the way the kick-off is — into the owner
brief (`{OWNER_BRIEF}`) or a decision entry with `Decided by: human` — so it outlives this iteration. A message
never changes a setting; say so and point at `/cruise-settings` where one asks for that."""


def seat_queues(script: str) -> str:
    """The watch seat's rule for something a person types that is for the run, not for the seat."""
    return f"""Where what they typed is for the run — a steer, a fact it was missing, a scope, an
answer to the question it parked on — queue it with `python3 {script} tell <<'EOF'` … `EOF` (`/cruise-tell`),
the message as they said it, and repeat what the script printed: the next iteration carries it, a parked run
resumes with it, and `--now` as its first word ends the iteration in flight for it, which is done only when they
ask for that."""


def boundary_asks(script: str) -> str:
    """The iteration contract's read between stages, beside the look for the stop file."""
    return f"""At the same boundaries run `python3 {script} told`: it prints what a person queued through
`/cruise-tell` since this iteration started, one `told:` line each, or nothing — and what it printed is acted on
before the next stage, exactly as a `told:` argument would have been; it is taken as it is printed, so the next
iteration is not given it again, and the runner puts it in this iteration's log entry."""
