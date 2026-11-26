"""What a person does about a block: one sentence why, and the numbered steps that lift it.

manda's S97 stood parked for forty-two hours with a card that said `parked waiting on you for 2546m (past wait
bound): S97: S97 can…` and nothing else. Its owner answered *mock it up* three times from the card, and each
answer was held by the decision ceiling — thirty-four decisions unread against twelve — with nothing on the
board saying so; and what S97 waited on was a verdict on a mock-up, which a box for chat cannot give.

So every block on the board carries an action: `why`, one sentence, whole; `do`, numbered steps, each naming
the exact command or the board control that does it; and, where a person's answer to it cannot clear it,
`held`, the line saying so with the step that releases it — asked of `logs.answer_held`, the rule the
harbourmaster clears a park by, through the row's own `held`, so the board and the harbour cannot disagree.

**A closed set of kinds**, read off what the row already carries — its kind, the park's `cause` and
`waiting`, its needs — and never invented: a block this cannot place is `other`, whose why is the park's own
words in full, so nothing is cut to fit a template. A mock-up verdict is told by the park's own words naming
one (`/mockups`, a mock-up or mock state to approve), because no field says so; its card offers Approve and
Reject (`park_verdict`).
"""
from __future__ import annotations

import re
from typing import Any

from .fleet_record import clock_of
from .refusal_said import SAID

#: Every kind of block, and the only ones. `other` is the fallback that quotes the park whole.
KINDS = ("question", "ceiling", "decisions", "mockup", "grant", "person", "handback", "trunk", "machine", "demo",
         "paused", "unreadable", "probably", "obsolete", "other")
#: A park that waits on a verdict on a drawing: the stage that gives one is `/mockups`, and a person approves it.
MOCKUP = re.compile(r"/mockups\b|mock[- ]?(?:up|state)s?\b[^.;]{0,120}\b(?:approv|verdict)|"
                    r"\b(?:approv|verdict)\w*\b[^.;]{0,120}\bmock[- ]?(?:up|state)", re.IGNORECASE)
#: The feature a `/mockups` run is for, where the park names it.
FEATURE = re.compile(r"/mockups\s+([A-Za-z0-9][A-Za-z0-9._-]{0,80})")
#: A need only a person with cloud credentials can meet: a grant in the bootstrap stack, applied by `make bootstrap`.
GRANT = re.compile(r"\binfra/|\bIAM\b|\bbootstrap\b|\bses:|\biam:", re.IGNORECASE)
#: A run that stopped for a reason on the machine, not a question: it exited, went silent, or spent its budget.
MACHINE = ("exit", "silence", "budget")
PAUSED = ("limit", "trunk")
#: A park on `check-slice-scope`'s events-module rule: a change only trunk may take, in the gate's words now
#: and in the words it used before issue 168. manda's S115 parked on it with a card that said *a person or the
#: host lands it on main*, which names nobody on the board.
EVENTS_RULE = re.compile(r"the events module (?:may only grow|is the contract and grows additively)", re.IGNORECASE)
#: What the gate saw, where its refusal says: `… and this change reads as a member removed (…). Events …`.
EVENTS_SAW = re.compile(r"this change reads as (.+?)\. Events already")


def first_sentence(text: str) -> str:
    """The first sentence of what a block says, whole, without the slice's own `S97: ` at its head."""
    said = re.sub(r"\s+", " ", text.partition(SAID)[0]).strip()  # a refused gate's log is not its reason
    said = re.sub(r"^[A-Za-z0-9_.-]{1,40}: ", "", said)
    found = re.match(r"(.+?[.!?])(?:\s|$)", said)
    return (found.group(1) if found else said).strip()


def words_of(row: dict[str, Any]) -> str:
    """Everything a block says of itself: its why and each of its needs."""
    return " ".join([str(row.get("what") or ""), *(str(need.get("what", "")) for need in row.get("needs") or [])])


def kind_of(row: dict[str, Any]) -> str:
    """Which kind of block a waiting row is, read off what it carries."""
    kind, cause = str(row.get("kind") or ""), str(row.get("cause") or "other")
    if kind in ("unreadable", "decisions", "question"):
        return kind
    if row.get("obsolete"):
        return "obsolete"
    if row.get("probably") == "yes":
        return "probably"
    if kind == "told":
        return "handback" if row.get("needs") else "other"
    if kind != "parked":
        return "other"
    if row.get("waiting") == "decision-review" or cause == "ceiling":
        return "ceiling"
    if row.get("paused") == "yes" or cause in PAUSED:
        return "paused"
    if MOCKUP.search(words_of(row)):
        return "mockup"
    if EVENTS_RULE.search(words_of(row)):
        return "trunk"
    if cause == "question":
        return "question"
    if any(need.get("by") == "person" for need in row.get("needs") or []) or cause == "host":
        return "grant" if GRANT.search(words_of(row)) else "person"
    if cause in MACHINE:
        return "machine"
    return "demo" if cause == "demo" else "other"


def feature_of(row: dict[str, Any]) -> str:
    """The feature a mock-up verdict is for: the one the park's `/mockups <feature>` names, or the stream's."""
    named = FEATURE.search(words_of(row))
    return named.group(1) if named else str(row.get("feature") or "")


def told_from_terminal(row: dict[str, Any]) -> str:
    """The terminal's way to say what the card's box says: the project's own `fleet.py tell`."""
    named = str(row.get("aim") or row.get("slice") or "")
    aim = f" --slice {named}" if named else ""
    return f'`python3 scripts/agents/fleet.py tell {row.get("fairway", "")}{aim} "<your answer>"`'


def answer_step(row: dict[str, Any]) -> str:
    named = str(row.get("aim") or row.get("slice") or "")
    box = f"press Send to {named}" if named else "press Send"
    return f"Type your answer in this card's box and {box} — or, in a terminal, {told_from_terminal(row)}."


def reading_step(unread: int, ceiling: int | None) -> str:
    """How many decisions to read to come under the ceiling, and the two controls that count it."""
    if ceiling is None:
        return ("Read the unread decisions: Mark read under Waiting on you › Read and mark read on the board. "
                "harbour.json has no `decision_ceiling` the board can read; set one with "
                "`slipwai telegraph --set decision_ceiling=<n>`.")
    owed = max(1, unread - ceiling)
    return (f"Read {owed} of the {unread} unread decisions — press Mark read on each, or I have read all, under "
            f"Waiting on you › Read and mark read on the board — so no more than {ceiling} stand unread; or raise "
            f"the ceiling with `slipwai telegraph --set decision_ceiling={unread}`.")


def held_reason(row: dict[str, Any]) -> str:
    """What each `logs.answer_held` word means, said to the person whose answer it held."""
    held, unread, ceiling = str(row.get("held") or ""), int(row.get("unread") or 0), row.get("ceiling")
    if held == "ceiling":
        return f"{unread} unread decisions, ceiling {ceiling}"
    if held == "review":
        return "this park waits on the decisions being read, and no message lifts it"
    if held == "uncounted":
        return "the board cannot read the harbour's decision ceiling, so it cannot say this answer will count"
    return ""


def held_line(row: dict[str, Any]) -> str:
    """`Your answer 'mock it up' (09:19) is HELD: 34 unread decisions, ceiling 12`, or `""` where nothing is held.

    The answer is the newest of the person's: the `told` their captain wrote from it, or the message still in
    the slice's inbox (`talk_placed`), which becomes that `told` and is held the same way."""
    reason = held_reason(row)
    if not reason:
        return ""
    told = row.get("answered") or {}
    placed = row.get("answer") or {}
    text, at = ((told.get("text"), told.get("t")) if told else (placed.get("text"), placed.get("t")) if placed
                else ("", ""))
    if not text:
        return ""
    word = "MAY BE HELD" if row.get("held") == "uncounted" else "HELD"
    return f"Your answer '{text}' ({clock_of(str(at or ''))}) is {word}: {reason}"


def release_step(row: dict[str, Any]) -> str:
    """The step that lets a held answer through, where one is held."""
    if row.get("held") in ("ceiling", "review"):
        return reading_step(int(row.get("unread") or 0), row.get("ceiling"))
    if row.get("held") == "uncounted":
        return reading_step(int(row.get("unread") or 0), None)
    return ""


def plain_of(row: dict[str, Any]) -> str:
    """The plain line a block leads with: its first unmet need's, or a question's own, or `""` (#172)."""
    owed = [need for need in row.get("needs") or [] if need.get("met") != "yes"]
    return next((str(need["plain"]) for need in owed if need.get("plain")), "") or str(row.get("plain") or "")


def need_steps(row: dict[str, Any]) -> list[str]:
    """One step per need not met yet: a person's, done and then ticked; the fleet's, ticked by trunk; and the
    mender's or a merge's, which are nobody's to do, said so — each in its plain words where it has them."""
    steps = []
    for need in row.get("needs") or []:
        if need.get("met") == "yes":
            continue
        said = str(need.get("plain") or need.get("what") or "")
        whose = f" ({need['whose']})" if need.get("whose") else ""
        if need.get("who") == "mender":
            steps.append(f"Nothing: the mender will do this — {said}")
        elif need.get("who") == "merge":
            steps.append("Nothing: " + str(need.get("whose") or "it lands with its slice's merge."))
        elif need.get("by") == "person":
            steps.append(f"{said}{whose} — then press Done beside it on this card.")
        else:
            steps.append(f"Land on trunk: {said}{whose} — it ticks itself when {need.get('how') or 'trunk has it'}.")
    return steps


def steps_for(kind: str, row: dict[str, Any]) -> tuple[str, list[str]]:
    """The why and the steps of one kind of block, before any held answer's release is put first."""
    fairway, named = str(row.get("fairway") or ""), str(row.get("aim") or row.get("slice") or "")
    said = first_sentence(str(row.get("asked") or row.get("what") or ""))
    log = f"`slipwai fleet {fairway}`"
    if kind == "unreadable":
        return (f"The {fairway} log has a line nobody can read, so its captain stops at every start.",
                [f"Open `.slipwai/run/logs/<feature>/{fairway}.jsonl` and repair the line the fault names: "
                 f"{row.get('what', '')}", "Nothing else: the harbourmaster relights the captain on its next pass."])
    if kind == "obsolete":
        return (f"An earlier slipwai wrote this park, and the move {row['obsolete']} carried it across; nothing in "
                f"this harness acts on it any more.",
                ["Press Dismiss on this card: it leaves the board, and nothing else waited on it."])
    if kind == "probably":
        steps = [f"If it is on trunk, press Done beside it: {need.get('what', '')}" for need in row.get("needs") or []
                 if need.get("met") != "yes"]
        return ("Its slice has merged and nothing left on it can be checked against trunk, so it is probably done.",
                [*steps, f"If one is not, say so to the stream: {told_from_terminal(row)}."])
    if kind == "decisions":
        unread, ceiling = len(row.get("decisions") or []), row.get("ceiling")
        if row.get("blocking") != "yes":
            return (f"{unread} decision(s) in {fairway} wait to be read; nothing is held up by them yet.",
                    ["Read them in the decision log and press Mark read on each, under Waiting on you › Read "
                     "and mark read."])
        return (f"{fairway} is over its decision ceiling, so it parks until a person reads what was decided.",
                [reading_step(unread, ceiling if isinstance(ceiling, int) else None)])
    if kind == "ceiling":
        return (f"{fairway} parked because more decisions stand unread than its ceiling allows.",
                [reading_step(int(row.get("unread") or 0), row.get("ceiling")),
                 "Nothing else: the harbourmaster clears the park on its next pass once the count is under."])
    if kind == "paused":
        lifts = clock_of(str(row.get("until") or ""))
        when = f"at {lifts}" if lifts else "when trunk is green" if row.get("cause") == "trunk" else "by itself"
        return (f"Paused, nothing for you to do: it lifts {when}.",
                [f"Nothing: the harbourmaster carries it on {when}.",
                 "To try sooner, press Try the paused slices now anyway at the top of the board."])
    if kind == "question" and row.get("kind") == "question" and row.get("slice") == "chart":
        # The chart's context answer is posted as `"slice": "chart"` *so nothing waits on it* (`commands/chart.md`):
        # the chart goes ahead on the recommendation. Said as a wait, manda's D495 read as the thing to answer
        # before Continue the build, when the button was the one thing that moved the project.
        return ("Nothing waits on this: the chart goes ahead on the recommendation it names, and this asks you to "
                "confirm it or say what is wrong.",
                [f"Read the question{' ' + str(row['id']) if row.get('id') else ''} above; its decision entry has "
                 "the evidence.", f"If it is wrong, say why: {answer_step(row)} The chart is redone from your answer."])
    if kind == "question" and row.get("kind") == "question":
        # The row is the question in its own words already; said a third time it is noise (`test_bridge`).
        return (plain_of(row) or f"{row.get('slice') or fairway} asked a question only a person can answer, and "
                                  f"waits for it.",
                [f"Read the question{' ' + str(row['id']) if row.get('id') else ''} above.", answer_step(row)])
    if kind == "question":
        return said, ["Read the question in the park above.", answer_step(row)]
    if kind == "mockup":
        feature = feature_of(row) or "<feature>"
        whose = f"{named}'s" if named else "this"
        return (said, [f"Have the state drawn: run `/mockups {feature}` in a session in this project (skip this "
                       f"if `specs/{feature}/mockups/storyboard.html` already shows it).",
                       f"Look at it in `specs/{feature}/mockups/storyboard.html`.",
                       f"Press Approve or Reject on {whose} card on the board: that writes "
                       f"`specs/{feature}/mockups/mock-states.md` as the storyboard's verdict does, and answers the "
                       f"park. Reject asks for one line on what to change."])
    if kind == "trunk":
        saw = EVENTS_SAW.search(words_of(row))
        what = f" — the gate saw {saw.group(1)}" if saw else ""
        whose = named or fairway
        return (f"{whose} needs a change to its events module that only trunk may take: the events module may only "
                f"grow on a slice branch{what}.",
                ["Land that change on trunk as a commit of its own, from a checkout of main, with `make verify` "
                 "green before you push. Nothing on the board lands it for you yet.",
                 f"Then press I have landed it, carry on: {whose} merges trunk and carries on from where it "
                 f"parked."])
    if kind in ("grant", "person", "handback"):
        said = plain_of(row) or said
        steps = need_steps(row)
        if kind == "grant":
            steps.append("A person with admin cloud credentials applies the grant from a checkout of main: "
                         "the change in `infra/bootstrap/main.tf`, then `make bootstrap`.")
        if row.get("cause") == "host" and kind != "handback":
            steps.append("Once it is on trunk, press I have landed it, carry on.")
        if kind == "handback":
            if any(need.get("met") != "yes" and need.get("who") == "spent" for need in row.get("needs") or []):
                # The edit by hand is the fallback, not the instruction: the mender lands these (`deck.mend_again`),
                # and is asked again only where it would take them and has spent its attempts (#172).
                steps.insert(0, "Press Have the mender try again: it makes these edits on a branch of its own, runs "
                                "the gates and lands them. Or make them on trunk yourself:")
            steps.append("It leaves the board once the last need is met.")
        return said, steps or [answer_step(row)]
    if kind == "machine":
        return (said, [f"Read what it said last: {log}, or this card's own lines.",
                       "Repair what stopped it — the environment, the checkout, a missing tool — on this machine.",
                       f"Send it on: {answer_step(row)}"])
    if kind == "demo":
        return (said, [f"Read the demo's verdict and what it walked: {log}, or this card's own lines.",
                       f"Say what to change, or that it is right as it is: {answer_step(row)}"])
    whole = re.sub(r"\s+", " ", str(row.get("what") or "").partition(SAID)[0]).strip()
    return whole, ["Decide what it needs from you: the park above is the captain's own words.", answer_step(row)]


def action(row: dict[str, Any]) -> dict[str, Any]:
    """The action line of one waiting row: its kind, why, numbered steps, any held answer, and — for a mock-up
    verdict — the feature whose drawing Approve and Reject give it on."""
    kind = kind_of(row)
    why, steps = steps_for(kind, row)
    release = release_step(row) if kind not in ("ceiling", "decisions") else ""
    if release:
        steps = [f"First: {release} Until then no answer here clears the park.", *steps]
    found = {"kind": kind, "why": why, "do": steps, "held": held_line(row)}
    if kind == "mockup":
        found["verdict"] = feature_of(row)
    return found


def acted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The waiting rows, each with its action."""
    return [{**row, "action": action(row)} for row in rows]


def said_lines(row: dict[str, Any], indent: str = "    ") -> list[str]:
    """The action as the terminal prints it: `Why:`, the HELD line where there is one, then `Do:` and its steps."""
    found = row.get("action") or action(row)
    lines = [f"{indent}Why: {found['why']}"]
    if found.get("held"):
        lines.append(f"{indent}{found['held']}")
    lines.append(f"{indent}Do:")
    lines += [f"{indent}  {number}. {step}" for number, step in enumerate(found["do"], 1)]
    return lines
