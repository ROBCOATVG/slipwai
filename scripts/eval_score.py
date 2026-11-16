"""How an eval of the captain is scored: the orders it gave, read and judged against a case's label.

**The order is scored, never its wording.** A run's orders are reduced to an *answer* — each verb it used
and the set of slices that verb named — and the answer is matched against the patterns a person wrote:
the orders they would accept, and the ones that would be plainly wrong. A retry note or a park reason is
kept beside the score for a person to read, because whether it is a good note is a judgement this file
does not pretend to make.

**Outside both sets is unjudged, not wrong.** A label is a person's account of what they would accept, and
an answer they did not foresee is a question for them, not a failure. Wrong takes precedence: an answer
that parks a slice and also retries it has done the wrong thing whatever else it did. And right is earned
whole: the accepted pattern has to account for every order given, so an accepted `none` with a `pause`
beside it is not right (`outcome_of`).

**No usable order is the fallback.** A run that wrote nothing within the bound, wrote only orders that do
not parse, or only orders the event did not allow, is one where the program applies today's fixed rule
(decision 17). Those are counted apart, because "the agent was silent" is a different finding from "the
agent was wrong".

The order file's fields are an assumption — contract 2.2 names the verbs and where the file goes, not its
keys — and `read_order` is the one place that assumption lives.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Every verb `orders.py` takes (contract 2.2), plus `interrupt`: a `message --interrupt` is scored as its
#: own verb, because a nudge and an interrupt are different answers to a stuck slice.
VERBS = frozenset({"start", "message", "interrupt", "retry", "park", "pause", "resume", "stop", "say", "ask",
                   "allow", "refuse", "none"})
#: The verbs that act on one slice and mean nothing without it.
NEEDS_SLICE = frozenset({"start", "message", "retry", "park", "pause", "resume", "stop"})
#: Where an order carries what the agent wrote for a person: kept, never scored.
TEXT_FIELDS = ("note", "why", "text", "needs", "options")
#: How a run ended, in the order the report lists them. The last three are the fallback.
OUTCOMES = ("right", "wrong", "unjudged", "silent", "malformed", "refused")
FALLBACK = ("silent", "malformed", "refused")


@dataclass(frozen=True)
class Order:
    verb: str
    slice: str
    text: str


@dataclass
class Judged:
    """One run of one case, judged: its outcome, the answer it was judged on, and what it wrote."""
    outcome: str
    answer: dict[str, list[str]]
    texts: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    @property
    def signature(self) -> str:
        """What two runs must share to have agreed: the answer, or the reason there was none."""
        if self.outcome in FALLBACK:
            return self.outcome
        return json.dumps(self.answer, sort_keys=True)


def read_order(path: Path) -> Order | str:
    """One order file as an `Order`, or the sentence saying why it is not one.

    Read as `orders.py` is expected to write it: `verb`, `slice` for the verbs that act on one, and
    `interrupt` on a `message`. `order` is read where `verb` is absent, so a writer that chose the other
    obvious key is not scored as malformed for a name.
    """
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as fault:
        return f"{path.name}: not JSON ({fault.__class__.__name__})"
    if not isinstance(held, dict):
        return f"{path.name}: not a JSON object"
    verb = held.get("verb", held.get("order"))
    if not isinstance(verb, str) or verb not in VERBS:
        return f"{path.name}: no verb orders.py takes ({verb!r})"
    slice_id = held.get("slice")
    if verb in NEEDS_SLICE and (not isinstance(slice_id, str) or not slice_id.strip()):
        return f"{path.name}: `{verb}` names no slice"
    if verb == "message" and held.get("interrupt") is True:
        verb = "interrupt"
    text = " · ".join(str(held[key]) for key in TEXT_FIELDS if held.get(key))
    return Order(verb, str(slice_id or "").strip(), text)


def order_files(directory: Path) -> list[Path]:
    """The orders in a folder, oldest name first; the program's `.result.json` beside each is not one."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.json") if not path.name.endswith(".result.json"))


def answer_of(orders: list[Order]) -> dict[str, list[str]]:
    """Each verb used and the slices it named, sorted, which is what a pattern is matched against."""
    found: dict[str, set[str]] = {}
    for order in orders:
        found.setdefault(order.verb, set())
        if order.slice:
            found[order.verb].add(order.slice)
    return {verb: sorted(slices) for verb, slices in sorted(found.items())}


def verbs_of(pattern: dict[str, Any]) -> list[str]:
    verb = pattern.get("verb")
    return [verb] if isinstance(verb, str) else [str(one) for one in verb or []]


def allowed_slices(pattern: dict[str, Any]) -> set[str] | None:
    """The slices a pattern lets an order name, or `None` where it lets it name any."""
    if "slice" in pattern:
        return {str(pattern["slice"])}
    for key in ("slices", "within"):
        if key in pattern:
            return {str(one) for one in pattern[key]}
    if "required" in pattern or "optional" in pattern:
        return {str(one) for one in [*pattern.get("required", []), *pattern.get("optional", [])]}
    return None


def matches(pattern: dict[str, Any], answer: dict[str, list[str]]) -> bool:
    """Whether an answer is what a pattern describes.

    A pattern names one verb or several (`"verb": ["message", "resume"]`, read as any of them) and at most
    one of: `slice`, the one slice they named; `slices`, exactly that set; `within`, at least one slice and
    none outside the list; `naming`, a list that includes this slice; `required` with `optional`, every
    required slice and nothing outside the two, which is how routing says "these two, or these three". With
    none of them, using the verb at all is the match.
    """
    used = [verb for verb in verbs_of(pattern) if verb in answer]
    if not used:
        return False
    named = {slice_id for verb in used for slice_id in answer[verb]}
    if "naming" in pattern:
        return str(pattern["naming"]) in named
    allowed = allowed_slices(pattern)
    if "required" in pattern or "optional" in pattern:
        return {str(one) for one in pattern.get("required", [])} <= named <= (allowed or set())
    if allowed is None:
        return True
    if "within" in pattern:
        return bool(named) and named <= allowed
    return named == allowed


def covers(pattern: dict[str, Any], order: Order) -> bool:
    """Whether a pattern accounts for this order: its verb is the pattern's, its slice one the pattern allows."""
    if order.verb not in verbs_of(pattern):
        return False
    allowed = allowed_slices(pattern)
    return allowed is None or "naming" in pattern or order.slice in allowed


#: Verbs that each put a slice somewhere different; two of them on one slice in one answer contradict.
ACTING = frozenset({"start", "retry", "park", "pause", "resume", "stop"})
#: Words to the person, which may go beside any answer without changing what it is.
ALONGSIDE = frozenset({"say"})


def faults_in(orders: list[Order], known: set[str] | None, free: int | None) -> list[str]:
    """What makes an answer wrong whatever the label says: it contradicts itself, names a slice the stream
    does not have, or starts more slices than there are free slots."""
    found = []
    acting: dict[str, set[str]] = {}
    for order in orders:
        if order.verb in ACTING and order.slice:
            acting.setdefault(order.slice, set()).add(order.verb)
        if known is not None and order.slice and order.slice not in known:
            found.append(f"`{order.verb} {order.slice}` names a slice this stream does not have")
    found += [f"{' and '.join(sorted(verbs))} on {slice_id} contradict each other"
              for slice_id, verbs in sorted(acting.items()) if len(verbs) > 1]
    starts = {order.slice for order in orders if order.verb == "start"}
    if free is not None and len(starts) > free:
        found.append(f"{len(starts)} slices started with {free} slot(s) free")
    return found


def outcome_of(label: dict[str, Any], orders: list[Order], known: set[str] | None = None,
               free: int | None = None) -> tuple[str, list[str]]:
    """Usable orders judged: right, wrong or unjudged, and the faults that made it wrong where any did.

    **Right** is an accepted pattern that matches and accounts for every order given, bar words to the
    person: an accepted order with a harmful one beside it is not right. **Wrong** is a pattern in `wrong`, a
    fault (`faults_in`), or a routing pattern (`required`) whose verbs went to the wrong set of slices.
    """
    answer = answer_of(orders)
    faults = faults_in(orders, known, free)
    if faults:
        return "wrong", faults
    if any(matches(pattern, answer) for pattern in label.get("wrong") or []):
        return "wrong", []
    accept = label.get("accept") or []
    for pattern in accept:
        if matches(pattern, answer) and all(covers(pattern, order) or order.verb in ALONGSIDE for order in orders):
            return "right", []
    routed = [pattern for pattern in accept if "required" in pattern
              and any(verb in answer for verb in verbs_of(pattern))]
    if routed and not any(matches(pattern, answer) for pattern in routed):
        return "wrong", ["the message went to the wrong set of slices"]
    return "unjudged", []


def judge(label: dict[str, Any], may: list[str], paths: list[Path], known: set[str] | None = None,
          free: int | None = None) -> Judged:
    """One run's orders against a label. `may` is the event's: an order outside it is refused by the program.
    `known` is the snapshot's slices and `free` its free slots, where it says them."""
    orders: list[Order] = []
    malformed: list[str] = []
    refused: list[str] = []
    allowed = set(may) | ({"interrupt"} if "message" in may else set())
    for path in paths:
        read = read_order(path)
        if isinstance(read, str):
            malformed.append(read)
        elif read.verb not in allowed:
            refused.append(f"{path.name}: `{read.verb}` is not among what the event allowed ({', '.join(may)})")
        else:
            orders.append(read)
    texts = [f"{order.verb} {order.slice}: {order.text}".replace("  ", " ") for order in orders if order.text]
    if not orders:
        outcome = "malformed" if malformed else "refused" if refused else "silent"
        return Judged(outcome, {}, texts, malformed, refused)
    outcome, faults = outcome_of(label, orders, known, free)
    return Judged(outcome, answer_of(orders), texts, malformed + faults, refused)


def fixed(label: dict[str, Any], may: list[str], verb: str, slice_id: str, known: set[str] | None = None,
          free: int | None = None) -> str:
    """What a captain that always gave this one order would score: the baseline a real score is read against.
    A verb that needs a slice, on an event that names none, is no order at all."""
    if verb not in may:
        return "refused"
    if verb in NEEDS_SLICE and not slice_id:
        return "malformed"
    return outcome_of(label, [Order(verb, slice_id if verb in NEEDS_SLICE else "", "")], known, free)[0]


def agreement(judged: list[Judged]) -> float:
    """The share of runs that gave the commonest answer: 1.0 is a captain that agreed with itself throughout."""
    if not judged:
        return 0.0
    return Counter(one.signature for one in judged).most_common(1)[0][1] / len(judged)


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per decision: how often right, wrong, unjudged and fallen back; agreement; time and tokens.

    `rows` is one per case: its decision, its runs' outcomes and signatures, seconds and tokens per run.
    """
    decisions: dict[str, dict[str, Any]] = {}
    for row in rows:
        held = decisions.setdefault(row["decision"], {"cases": 0, "runs": 0, "signed": 0, "agreement": [],
                                                      "seconds": 0.0, "tokens": 0, "costed": 0,
                                                      **{outcome: 0 for outcome in OUTCOMES}})
        held["cases"] += 1
        held["signed"] += 1 if row.get("signed_off") else 0
        held["runs"] += len(row["outcomes"])
        for outcome in row["outcomes"]:
            held[outcome] += 1
        held["agreement"].append(row["agreement"])
        held["seconds"] += sum(row["seconds"])
        for tokens in row["tokens"]:
            if tokens is not None:
                held["tokens"] += tokens
                held["costed"] += 1
    for held in decisions.values():
        shares = held.pop("agreement")
        held["agreement"] = sum(shares) / len(shares) if shares else 0.0
        held["fallback"] = sum(held[outcome] for outcome in FALLBACK)
    return decisions
