"""The careen: one hardening slice per fairway, and the list of what every stage stowed into it.

A ship is careened by heeling it over on a beach to work on the hull — the part you cannot reach while it is
sailing. This is that: the work a slice could not finish and was not allowed to carry.

The first attempt had no such place, so work went two ways and both were wrong. Gaps were **carried**: 18
moved from S08 to S09, 31 from S09 to S13, 46 from S12 to S13, until two whole slices existed only to
collect the debt — and a slice that inherits a gap pays for it without having chosen to. Or findings were
**argued**: 129 adversary findings over 21 rounds, 64 of them LOW and most about wording, with slice S20
still ending on five open ones. Neither is a decision about whether the work matters.

So version 2 gives it a named destination and a bar. A finding below the fairway's severity bar is
**stowed**: written into the capability's own record, `stowed.md`, with the slice that found it, and the
slice merges. The harbourmaster carries those rows into the fairway's careen as the merge lands — one writer
for the shared file, because every slice of a stream writing it was a conflict on every merge (issue 154).
The careen is a slice of its own, in the same fairway, that the captain starts as the fairway's last once
its planned slices are merged, and its demo is that the findings are closed. Work is never dropped; it is
moved somewhere a person can see the size of it.

**A finding that leaves a feature unusable or untrustworthy for its actor is never deferred** — the owner's
rule (slipwai#154). A CRITICAL is never stowed: data of one actor reaching another, or an actor gaining a
role, is not a thing to look at later. Nor, whatever its severity and whatever the bar, is one of the kinds
in `NEVER_STOWED_KINDS`: each was a MEDIUM stowed on a real run at a HIGH bar — a coerced request body that
countersigned an agreement, a control character that forged a line in a signed PDF, a removed person still
mailed, a rounding that fed a valuation — and each left its feature unusable or untrustworthy for the actor
it was built for. They park or are fixed like a finding above the bar.

The careen is not the demo and not the flag. It runs once the fairway's planned slices are merged, whatever
the release state — a pre-launch product hoists no flag, so a careen that waited for one never ran — and so
before any flag is hoisted, which is a release-readiness ordering. It has nothing to do with the capability
demos a person attends.
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


#: The columns of a stowed row, the same in a capability's `stowed.md` as in the careen it is carried to.
ROW_HEADER = "| Stowed | By slice | From | Severity | What it is | State |"


def stowed_path(feature: str = "<feature>", capability: str = "<capability>") -> str:
    """Where a slice stows: its capability's own record, which `check-slice-scope` already lets it write."""
    return f"specs/{feature}/capabilities/{capability}/stowed.md"


def careen_page(fairway: str) -> str:
    """The file a fairway's stowed work is carried into, as the harbourmaster first writes it.

    `scripts/agents/careen.py` writes it in a project, which has no slipwai to import, so the toolkit holds
    the same text and the suite holds the two to one page."""
    return f"""# Careen — {fairway}

What this fairway stowed, and what its careen slice closes. The harbourmaster writes this file: on every
merge that brings a capability's `stowed.md` in, it appends that record's new rows under the capability's
own heading. A slice never writes here; it stows into its capability's record, and the careen slice is the
one that moves a row's state to `done`.

**Nothing CRITICAL is ever on this list.** Data of one actor reaching another, or an actor gaining a role,
is the next slice rather than something to look at later, and the stage that found it says so instead of
writing a row.

**Nor is any finding of these kinds, whatever its severity and whatever the bar.** {RULE}:

{never_stowed_list()}

**A row is a decision, not a note.** *What it is* says what is wrong and what closing it would take, in one
line a reader who was not there can act on. A row that only names a file is a row the careen slice has to
rediscover, which is the cost the stowing was supposed to avoid.
"""


def careen_command(layout: Layout = AT_ROOT) -> str:
    """`/careen`: the hardening slice each fairway runs as its last, once its planned slices are merged."""
    return f"""---
description: Run a fairway's careen — close everything its slices stowed, as the fairway's last slice
argument-hint: [fairway]
---

# Careen

One hardening slice per fairway, run as that fairway's last: once every planned slice of it is merged and
its careen has a row still open, its captain starts it — whatever the release state, because a pre-launch
product hoists no flag and a careen that waited for one would never run. Any flag is hoisted after it. A
person can also start it by hand with `/careen <fairway>`. A careen, on a ship, is heeling it over on a
beach to work on the hull — the part nobody can reach while it is sailing.

Read `{careen_path('<fairway>')}`. Every row with state `open` is this slice's work. The harbourmaster
wrote those rows there, one section per capability, from each capability's `{stowed_path()}` as its
slices merged; nothing else writes them.

## It is a slice, and it runs the ladder like one

Claim it as `slice/<fairway>-careen` — under `/cruise` the captain has, and the session starts in that
berth — map its examples from the rows, implement each through RED-GREEN-REFACTOR like any other work, and
take it through review, adversary and the mutation gate. A hardening slice that skips the ladder is how
hardening becomes a second quality standard.

**Its demo is: the findings are closed.** Not "most of them", and not "the ones that still matter". Close a
row by moving its state to `done` in `{careen_path('<fairway>')}` — the one file outside its own record this
slice may write, and only its state cells. A row somebody decides no longer matters is closed by saying that
in the row, with the reason and who said it — which is a decision a reader can disagree with later, where a
quietly dropped row is not. When every row reads `done`, record the demo as
`python3 scripts/agents/deck_line.py demo --slice <fairway>-careen --verdict accepted`, which is the gate the
captain asks for the merge on.

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
