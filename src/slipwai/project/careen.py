"""The careen: one hardening slice per fairway, and the list of what every stage stowed into it.

A ship is careened by heeling it over on a beach to work on the hull — the part you cannot reach while it is
sailing. This is that: the work a slice could not finish and was not allowed to carry.

The first attempt had no such place, so work went two ways and both were wrong. Gaps were **carried**: 18
moved from S08 to S09, 31 from S09 to S13, 46 from S12 to S13, until two whole slices existed only to
collect the debt — and a slice that inherits a gap pays for it without having chosen to. Or findings were
**argued**: 129 adversary findings over 21 rounds, 64 of them LOW and most about wording, with slice S20
still ending on five open ones. Neither is a decision about whether the work matters.

So version 2 gives it a named destination and a bar. A finding below the fairway's severity bar is
**stowed**: written here with the slice that found it, and the slice merges. The careen is a slice of its
own, in the same fairway, that each fairway runs when its planned slices are done, and its demo is that the
findings are closed. Work is never dropped; it is moved somewhere a person can see the size of it.

**A finding that leaves a feature unusable or untrustworthy for its actor is never deferred** — the owner's
rule (slipwai#154). A CRITICAL is never stowed: data of one actor reaching another, or an actor gaining a
role, is not a thing to look at later. Nor, whatever its severity and whatever the bar, is one of the kinds
in `NEVER_STOWED_KINDS`: each was a MEDIUM stowed on a real run at a HIGH bar — a coerced request body that
countersigned an agreement, a control character that forged a line in a signed PDF, a removed person still
mailed, a rounding that fed a valuation — and each left its feature unusable or untrustworthy for the actor
it was built for. They park or are fixed like a finding above the bar.

The careen is not the demo and not the flag. It runs before the fairway's flag is hoisted, which is a
release-readiness ordering, and it has nothing to do with the capability demos a person attends.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from ..telegraph import BAR, SEVERITIES

#: The severity a finding has to reach to stop a merge where `harbour.json` names none. The telegraph's
#: own default, so there is one: MEDIUM rather than HIGH because the experiment's LOWs were genuinely wording
#: and its MEDIUMs genuinely were not. No telegraph position moves it.
DEFAULT_BAR = BAR
#: Never stowed, whatever the bar says.
NEVER_STOWED = "CRITICAL"
#: The owner's rule, in the words every page that states it uses.
RULE = "A finding that leaves a feature unusable or untrustworthy for its actor is never deferred"
#: The kinds of finding never stowed whatever their severity and whatever the bar, each by the tag a finding
#: carries (`kind: <tag>`) and what it covers. Each parks or is fixed like a finding above the bar.
NEVER_STOWED_KINDS = {
    "validation-bypass": "input coercion or a validation bypass on a state-changing route",
    "document-forgery": "forgery or injection into a generated document — a PDF, an email",
    "erasure-leak": "personal data that survives, or leaks, after deletion or erasure",
    "money-arithmetic": "wrong arithmetic in a money or financial figure",
}


def never_stowed(kind: str | None) -> bool:
    """Whether a finding's kind keeps it out of the careen whatever its severity.

    No kind is the ordinary case and decides nothing. A kind that is not one of `NEVER_STOWED_KINDS` is
    treated as one of them: a finding somebody tagged meant to say it was not to be deferred, and a typo in
    the tag is not a reason to defer it quietly."""
    return bool(kind and kind.strip())


def above_bar(severity: str, bar: str = DEFAULT_BAR, kind: str | None = None) -> bool:
    """Whether a finding must close before the merge, rather than being stowed.

    An unknown severity is treated as above the bar. A typo in a severity is not a reason to let a finding
    through quietly, and the alternative — silently stowing what nobody could classify — is the failure
    this whole module exists to stop. A finding of a never-stowed kind is at the bar whatever its severity.
    """
    if never_stowed(kind):
        return True
    if severity not in SEVERITIES or bar not in SEVERITIES:
        return True
    return SEVERITIES.index(severity) >= SEVERITIES.index(bar)


def stowable(severity: str, bar: str = DEFAULT_BAR, kind: str | None = None) -> bool:
    """Whether this finding may be stowed into the careen instead of closed now."""
    return severity != NEVER_STOWED and not above_bar(severity, bar, kind)


def never_stowed_list(indent: str = "") -> str:
    """The never-stowed kinds as a page's list, one line each with the tag a finding carries."""
    return "\n".join(f"{indent}- `{tag}` — {said}" for tag, said in NEVER_STOWED_KINDS.items())


def careen_path(fairway: str) -> str:
    """Where a fairway's stowed work lives. Per fairway, like every other append-only file: two fairways
    writing one list is the shared-counter problem again, and that cost 54 renumbering commits in one night."""
    return f"fairways/{fairway}/careen.md"


def careen_page(fairway: str) -> str:
    """The file a fairway's stowed work is written into, as the first stage to stow creates it."""
    return f"""# Careen — {fairway}

What this fairway stowed, and what the careen slice closes before the flag is hoisted. One row per item,
appended by the stage that stowed it, never rewritten by hand. A row leaves this file by being done.

| Stowed | By slice | From | Severity | What it is | State |
|---|---|---|---|---|---|
| <date> | <slice-id> | adversary \\| mutation \\| gaps \\| review \\| budget | LOW | one line | open \\| done |

**Nothing CRITICAL is ever on this list.** Data of one actor reaching another, or an actor gaining a role,
is the next slice rather than something to look at later, and the stage that found it says so instead of
writing a row here.

**Nor is any finding of these kinds, whatever its severity and whatever the bar.** {RULE}:

{never_stowed_list()}

**A row is a decision, not a note.** *What it is* says what is wrong and what closing it would take, in one
line a reader who was not there can act on. A row that only names a file is a row the careen slice has to
rediscover, which is the cost the stowing was supposed to avoid.
"""


def careen_command(layout: Layout = AT_ROOT) -> str:
    """`/careen`: the hardening slice each fairway runs when its planned slices are done."""
    return f"""---
description: Run a fairway's careen — close everything its slices stowed, before the flag is hoisted
argument-hint: [fairway]
---

# Careen

One hardening slice per fairway, run when that fairway's planned slices are done and before its flag is
hoisted. A careen, on a ship, is heeling it over on a beach to work on the hull — the part nobody can reach
while it is sailing.

Read `{careen_path('<fairway>')}`. Every row with state `open` is this slice's work.

## It is a slice, and it runs the ladder like one

Claim it as `slice/<fairway>-careen`, map its examples from the rows, implement each through
RED-GREEN-REFACTOR like any other work, and take it through review, adversary and the mutation gate. A
hardening slice that skips the ladder is how hardening becomes a second quality standard.

**Its demo is: the findings are closed.** Not "most of them", and not "the ones that still matter". A row
somebody decides no longer matters is closed by saying that in the row, with the reason and who said it —
which is a decision a reader can disagree with later, where a quietly dropped row is not.

## What it may not do

- **It may not stow.** The careen is where stowing ends. A stage inside it that runs out of budget parks for
  a person instead, because the alternative is a careen that stows into the next careen.
- **It may not reach outside its fairway.** `make check-slice-scope` holds it to the paths its fairway owns,
  exactly as it holds every other slice. A row about another fairway's code was filed in the wrong place,
  and moving it is the fix.
- **It may not be the place a CRITICAL waits**, or a finding of a never-stowed kind. Neither is ever on
  the list; one found there was stowed by mistake, and it parks or is fixed now.

## When it is done

Every row reads `done`, `{layout.make} verify` is green on the rebased branch, and the fairway is ready for
whatever release decision a person takes next. That decision is theirs and has nothing to do with this
slice: the careen says the work is sound, and hoisting a flag says the business wants it live.
"""
