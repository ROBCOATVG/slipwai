#!/usr/bin/env python3
"""The rules that read differently by the rung a slice's service is on, and the two that read the same.

A service's **write model** is `events` — the log is the truth and current state is a fold of it — or
`state` — the service keeps current state, and the events the model names are contracts raised after the
write and never replayed. `project.json` records it per deployable as `eventSourced`, and this is the one
place the model gate asks.

**What changes with the rung is the write model, and nothing else.** `chart.py` renders fairways from
`context` and `service`, marks from `evt` frames and steers-by from `reads`, and reads none of `stream`,
`guard`, `folds` or `materialisation` — so the division of work does not know which rung a service is on,
and the rendered chart of a model is the same whichever rung either of its slices is on. Three fields move:

- `stream` is **required** at `planned` on both rungs, and means different things: the stream an append
  carries the expected version of, or the row or aggregate one transaction locks, with its version.
- `guard` and `folds` are **refused by name** on `state`. A guard is a boundary drawn over a tag query and
  a fold is a replay; both need a log, and a slice that names one on a state-stored service is describing
  machinery that service was never given.
- `liveBudget` is **not asked** on `state`. It bounds the fold a `live` state-view does on every query, and
  a service that folds nothing has no such ceiling to name. `materialisation` keeps all three of its words.

`model-matches-code` is unchanged: an event is a file on either rung.

**The two naming rules are not rung rules.** They hold on both, and they are here because this is the
module the gate already reaches for a rule about what a slice says rather than how it is shaped. Each comes
from a Good / Bad / Why table in `skills/event-modeling/references/naming.md`, which is where the reasoning
is written out at length.
"""
from __future__ import annotations

import re

#: The verbs that name the row rather than the business fact. Dudycz calls modelling this way *property
#: sourcing*: the model records that a column changed, which is what the table already knew, and the one
#: thing a reader wanted — what happened — is nowhere. `Created` is on the list for the same reason as the
#: rest, and comes off it with `crud: true`, because a CMS page and a settings record honestly are CRUD.
CRUD_VERBS = ("Created", "Updated", "Deleted", "Changed", "Modified")
#: `OrderNotShipped` names the absence of a thing, which nothing can raise: an event is something that
#: happened. The fact underneath it is a failure, a rejection or an expiry, and it carries why.
NEGATIVE = re.compile(r"(?:^|[a-z0-9])(Not|Never|Un)[A-Z]")


def crud_fault(name: str) -> str | None:
    """Why this event name is a column and not a fact, or None where it is a fact.

    The verb is the tail of the name, so `OrderCreated` is caught and `CreatedAccountRejected` is not: the
    rule is about what the event says happened, which is the last word.
    """
    for verb in CRUD_VERBS:
        if name.endswith(verb) and name != verb:
            subject = name[: -len(verb)]
            return (
                f"`{name}` names the write and not the fact: {verb.lower()} is what the table did. Name "
                f"what happened to the {subject.lower() or 'thing'} in the business's own word — "
                f"`{subject}Placed`, `{subject}Cancelled`, `{subject}Confirmed`. Where this honestly is "
                f"CRUD — a CMS page, a setting — the frame says `crud: true` with a `because`"
            )
    return None


def negative_fault(name: str) -> str | None:
    """Why this event name is an absence, or None where it is something that happened."""
    if NEGATIVE.search(name) is None:
        return None
    return (
        f"`{name}` names something that did not happen, and nothing raises an absence. The fact is the "
        f"failure itself — `ShipmentFailed`, `PaymentDeclined`, `HoldExpired` — with a `reason` attribute "
        f"carrying which of the ways it went wrong this was"
    )


def naming_findings(slice_id: str, frames: list, held: frozenset[str] = frozenset()) -> list[str]:
    """`event-is-not-crud` and `event-is-not-negative`, over one slice's event frames, on either rung.

    `held` are the names the project already had in a log when these rules reached it
    (`check.held_event_names`). Neither rule asks about one: the only compliant move would be to rename a
    stored event, which nothing can do. Every other rule still reads the frame.
    """
    findings: list[str] = []
    for frame in frames:
        if not isinstance(frame, dict) or frame.get("type") != "evt":
            continue
        name = frame.get("name")
        if not isinstance(name, str) or not name or name in held:
            continue
        if not frame.get("crud") and (fault := crud_fault(name)) is not None:
            findings.append(f"{slice_id}: {fault}")
        elif frame.get("crud") and not str(frame.get("because", "")).strip():
            findings.append(
                f"{slice_id}: `{name}` declares `crud: true`, which needs a `because` saying why this one "
                f"honestly is a field update — unstated, it is the exemption everything gets"
            )
        if (fault := negative_fault(name)) is not None:
            findings.append(f"{slice_id}: {fault}")
    return findings


def write_model_findings(slice_id: str, item: dict, sourced: bool, planned: bool) -> list[str]:
    """What this slice may say about its write side, given the rung its service is on.

    `sourced` is the service's `eventSourced`; `planned` is whether the slice has reached a status that owes
    an answer. A slice on a service nothing recorded is read as state-stored, which is the axis's own
    `absent` and the honest answer about a service nobody vouched for.
    """
    if sourced:
        return []
    findings: list[str] = []
    if item.get("guard") is not None:
        findings.append(
            f"{slice_id}: names a `guard`, which draws a boundary over a tag query and needs a log to "
            f"query. This slice's service keeps current state (`eventSourced: false` in project.json): its "
            f"consistency boundary is the row or aggregate one transaction locks, which is `stream`"
        )
    if item.get("folds"):
        findings.append(
            f"{slice_id}: names `folds`, which replays earlier events into the state a decision is made "
            f"over. This slice's service keeps current state, so there is nothing to replay — the decision "
            f"loads what the service already holds, decides, and saves at the version it read"
        )
    if planned and item.get("pattern") == "state-change" and not item.get("stream"):
        findings.append(
            f"{slice_id}: a planned state change on a state-stored service names the row or aggregate one "
            f"transaction locks in `stream`, with its version. It is the concurrency ceiling either way, "
            f"and `guard` is not the alternative here that it is on the event-sourced rung"
        )
    return findings
