#!/usr/bin/env python3
"""Feedback points: the observables of a feature, ranked by what delaying a person's judgement of them costs.

A merge is an engineering event: trunk took the slice. A feedback point is a product event: a person can
observe something — a screen, a read model under the API, an automation's side effect, an outbound
translation — and what they say could change what gets built next. On the chart those are the `state-view`,
`automation` and actor-facing `translation` slices; a `state-change` is observable only through one of them,
so building it without its reader buys no feedback. recap merged fifteen slices in two days, every one a
state-change or an inbound sync, and the person who opened Try it saw a starter page and three links.

Four terms per observable, each read off an artifact the project already has and printed beside its
sources, so a person can disagree with a number rather than with a ranking:

- **Uncertainty** — what the observable would let a person judge: the `decisions.md` entries written to
  it, its marks or its surface that the host or the skipper took rather than a human, weighted by their
  `Confidence` (medium counts more than high, low more than medium); the mock states still `parked` on its
  surface; the clarifications answered with the recommended option. A decision a human took counts nothing.
- **Blast radius** — the slices not yet merged that steer by those marks, with everything below them in the
  slice graph. Each one built before the feedback arrives is one that may be revisited, and a mark is set
  once.
- **Urgency** — a commitment point ahead: a sibling about to set one of those marks at its plan, a reader
  of one about to merge. Past the point the term drops, because the cost has been paid.
- **Cost to surface** — the slices still needed to make it observable, a `given` in its story counting half
  a slice and a producer counting the producer's own distance, plus a screen to style and a flag to turn on.

Cost of delay is the first three together; the score is cost of delay over cost to surface — the shape of
weighted-shortest-job-first, applied to information rather than features. The weights are the first
guesses, printed so they can be argued with (feedback-points plan, open point 4).

    python3 scripts/agents/clearance.py --feedback      # every observable, ranked, with every term and its sources
    python3 scripts/agents/feedback.py --json           # the same rows, for a board
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402

#: The patterns a person can judge directly. A `translation` counts where it faces an actor (outbound).
OBSERVABLE = ("state-view", "automation")
#: The first guesses. `confidence` weights an agent-made decision by how sure the stage said it was.
WEIGHTS: dict[str, float] = {"high": 1, "medium": 2, "low": 3, "parked-state": 2, "clarification": 1,
                             "given": 0.5, "producer": 1, "commitment": 0.5, "screen": 1, "flag": 1}
_HEAD = re.compile(r"^## (D\d+)\s*[—-]\s*(.*)$", re.MULTILINE)
_FIELD = re.compile(r"\*\*([^*:]+):\*\*\s*(.*?)(?=\s+·\s+\*\*[^*:]+:\*\*|$)")
_ID = re.compile(r"(?<![\w-])([A-Za-z]{1,6}\d{1,3})(?![\w-])")


def is_observable(charted: dict, slice_id: str) -> bool:
    body = (charted.get("slices") or {}).get(slice_id) or {}
    pattern = str(body.get("pattern") or "")
    return pattern in OBSERVABLE or (pattern == "translation" and bool(body.get("actor")))


def observables(charted: dict) -> list[str]:
    return [str(slice_id) for slice_id in (charted.get("slices") or {}) if is_observable(charted, str(slice_id))]


def seen_through(charted: dict, slice_id: str) -> str:
    """The nearest observable downstream of a mark this slice sets, in chart order, or `""` for none —
    which is a slice whose work nobody can judge until something reads it."""
    if is_observable(charted, slice_id):
        return slice_id
    sets = set(clearance.sets_of(charted, slice_id))
    for other in observables(charted):
        if sets & set(clearance.steered_by(charted, other)):
            return other
    return ""


def decisions(feature: str) -> list[dict[str, str]]:
    """Every entry of `specs/<feature>/decisions.md`, as `check-decisions` holds it: id, title and fields."""
    path = clearance.SPECS / feature / "decisions.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    heads = list(_HEAD.finditer(text))
    found = []
    for index, head in enumerate(heads):
        body = text[head.end(): heads[index + 1].start() if index + 1 < len(heads) else len(text)]
        fields = {"id": head.group(1), "title": head.group(2).strip()}
        for line in body.splitlines():
            if line.lstrip().startswith("- "):
                fields.update({label.strip(): value.strip() for label, value in _FIELD.findall(line)})
        found.append(fields)
    return found


def weight_of(entry: dict[str, str]) -> float:
    """What one decision is worth as uncertainty: nothing where a human took or confirmed it, or it was
    overturned; otherwise its confidence, a missing confidence reading as medium."""
    by, status = entry.get("Decided by", "").lower(), entry.get("Status", "").lower()
    if by.startswith("human") or "confirmed by human" in status or "overridden" in status or "overturned" in status:
        return 0
    return WEIGHTS.get(entry.get("Confidence", "medium").lower().split()[0], WEIGHTS["medium"])


def about(entry: dict[str, str], slice_id: str, marks: set[str]) -> bool:
    """Whether a decision was written to this observable: its `Slice` is it, or its `Written to` names it or
    one of the marks it steers by or sets."""
    if entry.get("Slice", "").strip() == slice_id:
        return True
    written = entry.get("Written to", "")
    return slice_id in _ID.findall(written) or any(mark in written for mark in marks)


def parked_states(feature: str, slice_id: str) -> list[str]:
    """The mock states still `parked` whose row or heading names this slice."""
    path = clearance.SPECS / feature / "mockups/mock-states.md"
    if not path.is_file():
        return []
    found, heading = [], ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#"):
            heading = line.strip("# ").strip()
        elif "parked" in line.lower() and (slice_id in line or slice_id in heading):
            found.append(f"{heading}: {line.strip('- ').strip()}" if heading else line.strip("- ").strip())
    return found


def clarifications(feature: str, slice_id: str, marks: set[str], counted: set[str]) -> list[str]:
    """Clarifications answered with the recommended option that name this slice or its marks and are not
    already counted as a decision."""
    path = clearance.SPECS / feature / "spec.md"
    if not path.is_file():
        return []
    found = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("- Q:"):
            continue
        named = set(re.findall(r"\((D\d+)\)", line))
        if named & counted:
            continue
        if slice_id in _ID.findall(line) or any(mark in line for mark in marks):
            found.append(line.strip("- ").strip()[:120])
    return found


def uncertainty(feature: str, charted: dict, slice_id: str) -> tuple[float, list[str]]:
    marks = set(clearance.steered_by(charted, slice_id)) | set(clearance.sets_of(charted, slice_id))
    score, sources, counted = 0.0, [], set()
    for entry in decisions(feature):
        if not about(entry, slice_id, marks):
            continue
        weight = weight_of(entry)
        counted.add(entry["id"])
        if weight:
            score += weight
            sources.append(f"{entry['id']} ({entry.get('Confidence', 'medium').split()[0]}, "
                           f"{entry.get('Decided by', '?').split(' (')[0]}) — {entry['title'][:80]}")
    for state in parked_states(feature, slice_id):
        score += WEIGHTS["parked-state"]
        sources.append(f"parked mock state — {state[:80]}")
    for asked in clarifications(feature, slice_id, marks, counted):
        score += WEIGHTS["clarification"]
        sources.append(f"clarification — {asked[:80]}")
    return score, sources


def blast_radius(charted: dict, folded: clearance.Folded, slice_id: str) -> tuple[int, list[str]]:
    """Every unmerged slice, other than this one, steering by a mark this one steers by or sets — and
    everything below those in the slice graph, the walk `abreast.critical` does."""
    marks = set(clearance.steered_by(charted, slice_id)) | set(clearance.sets_of(charted, slice_id))
    depends, _ = clearance.slice_graph(charted)
    reached: set[str] = set()
    frontier = [str(other) for other in (charted.get("slices") or {})
                if str(other) != slice_id and str(other) not in folded.merged
                and marks & set(clearance.steered_by(charted, str(other)))]
    while frontier:
        one = frontier.pop()
        if one in reached:
            continue
        reached.add(one)
        frontier += [other for other, deps in depends.items() if one in deps and other not in folded.merged]
    found = [one for one in (charted.get("slices") or {}) if str(one) in reached]
    return len(found), found


def urgency(charted: dict, folded: clearance.Folded, slice_id: str) -> tuple[float, list[str]]:
    """The commitment points ahead of this observable: a claimed sibling about to set one of its marks at
    its plan, and a claimed reader of a set mark about to merge. Each raises the multiplier by half."""
    marks = set(clearance.steered_by(charted, slice_id)) | set(clearance.sets_of(charted, slice_id))
    points = []
    for other in folded.claimed:
        if other == slice_id or other in folded.merged:
            continue
        setting = [mark for mark in clearance.sets_of(charted, other) if mark in marks and mark not in folded.marks]
        if setting:
            points.append(f"{other} is claimed and about to set {clearance.said_list(setting)} at its plan")
            continue
        reading = [mark for mark in clearance.steered_by(charted, other) if mark in marks and mark in folded.marks]
        if reading:
            points.append(f"{other} is claimed and reads {clearance.said_list(reading)}; its merge builds on them")
    return 1 + WEIGHTS["commitment"] * len(points), points


def distance(charted: dict, settled: set[str], slice_id: str, seen: set[str]) -> float:
    """How many slices a producer is from being buildable: itself, plus each unset mark it waits on."""
    if slice_id in seen:
        return 0
    seen.add(slice_id)
    cost = WEIGHTS["producer"]
    for mark in clearance.steered_by(charted, slice_id):
        if mark in settled:
            continue
        setter = clearance.setter_of(charted, mark)
        cost += distance(charted, settled, setter, seen) if setter else WEIGHTS["producer"]
    return cost


def has_web_app() -> bool:
    try:
        manifest = json.loads((clearance.ROOT / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return any(isinstance(one, dict) and one.get("kind") == "web"
               for one in (manifest.get("deployables") or {}).values())


def flagged() -> bool:
    try:
        held = json.loads((clearance.ROOT / ".specify/cruise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return str(held.get("release", "")) == "flagged"


def cost_to_surface(charted: dict, folded: clearance.Folded, settled: set[str],
                    slice_id: str) -> tuple[float, list[str]]:
    """What it takes to put this observable in front of a person from here. Zero once it has merged."""
    if slice_id in folded.merged:
        return 0, ["merged: it is on trunk and Try it shows it"]
    body = (charted.get("slices") or {}).get(slice_id) or {}
    parts = [f"{slice_id} itself"]
    cost = WEIGHTS["producer"]
    given = clearance.given_by(charted, slice_id)
    for mark in clearance.steered_by(charted, slice_id):
        if mark in settled:
            continue
        if mark in given:
            cost += WEIGHTS["given"]
            parts.append(f"{mark} given by its story ({WEIGHTS['given']:g})")
            continue
        if body.get("pattern") in clearance.ANY_OF and any(m in settled for m in clearance.steered_by(charted, slice_id)):
            continue  # a view folds what exists; an unset mark it does not give is folded when it comes
        setter = clearance.setter_of(charted, mark)
        far = distance(charted, settled, setter, set()) if setter else WEIGHTS["producer"]
        cost += far
        parts.append(f"{mark} from {setter or 'nobody'} ({far:g})")
    if body.get("pattern") == "state-view" and body.get("actor") and has_web_app():
        cost += WEIGHTS["screen"]
        parts.append(f"a screen to style ({WEIGHTS['screen']:g})")
    if flagged():
        cost += WEIGHTS["flag"]
        parts.append(f"a flag to turn on in Try it ({WEIGHTS['flag']:g})")
    return cost, parts


def rank(feature: str, charted: dict, folded: clearance.Folded, settled: set[str]) -> list[dict]:
    """Every observable with its score and its four terms, highest first; merged ones last, as surfaced."""
    rows = []
    for slice_id in observables(charted):
        body = (charted.get("slices") or {}).get(slice_id) or {}
        unsure, why_unsure = uncertainty(feature, charted, slice_id)
        radius, reached = blast_radius(charted, folded, slice_id)
        urgent, points = urgency(charted, folded, slice_id)
        cost, parts = cost_to_surface(charted, folded, settled, slice_id)
        delay = unsure * (1 + radius) * urgent
        rows.append({"slice": slice_id, "pattern": str(body.get("pattern") or ""), "actor": str(body.get("actor") or ""),
                     "fairway": str(body.get("fairway") or ""), "capability": str(body.get("capability") or ""),
                     "merged": slice_id in folded.merged,
                     "score": round(delay / cost, 2) if cost else None, "cost_of_delay": round(delay, 2),
                     "uncertainty": {"score": unsure, "sources": why_unsure},
                     "blast_radius": {"score": radius, "slices": reached},
                     "urgency": {"score": urgent, "points": points},
                     "cost_to_surface": {"score": cost, "parts": parts}})
    return sorted(rows, key=lambda row: (row["merged"], -(row["score"] or 0), row["slice"]))


def unseen(charted: dict, folded: clearance.Folded) -> list[str]:
    """Unmerged slices no observable sees: work nobody can judge until something reads what it sets."""
    return [str(one) for one in (charted.get("slices") or {}) if str(one) not in folded.merged
            and not is_observable(charted, str(one)) and not seen_through(charted, str(one))]


def say(feature: str, rows: list[dict], charted: dict, folded: clearance.Folded) -> int:
    print(f"feedback: {feature} — {len(rows)} observables, ranked by cost of delay over cost to surface "
          f"(uncertainty × (1 + blast radius) × urgency ÷ cost; weights {json.dumps(WEIGHTS)})")
    for place, row in enumerate(rows, start=1):
        score = "surfaced" if row["merged"] else f"score {row['score']:g}"
        print(f"\n  {place:>2}. {row['slice']}  {row['pattern']}{' for ' + row['actor'] if row['actor'] else ''}"
              f"  {row['fairway']} / {row['capability']}  — {score}")
        u = row["uncertainty"]
        print(f"      uncertainty {u['score']:g}" + (":" if u["sources"] else " — read from nothing: no agent-made "
                                                       "decision, parked state or clarification names it"))
        for source in u["sources"]:
            print(f"        {source}")
        b = row["blast_radius"]
        print(f"      blast radius {b['score']}" + (f": {', '.join(b['slices'])}" if b["slices"] else
                                                   " — nothing unmerged steers by its marks"))
        g = row["urgency"]
        print(f"      urgency ×{g['score']:g}" + (":" if g["points"] else " — no commitment point ahead"))
        for point in g["points"]:
            print(f"        {point}")
        c = row["cost_to_surface"]
        print(f"      cost to surface {c['score']:g}: {', '.join(c['parts'])}")
    dark = unseen(charted, folded)
    if dark:
        print(f"\n  no observable sees {clearance.said_list(dark)}: what each sets, nothing on the chart reads, so "
              f"nobody can judge it until something does")
    print("\nThe split proposes its order from this: the walking skeleton first, then observables by score, each "
          "with the givens that let it go before its producers, then the producers in the order the observables "
          "need them.")
    return 0


def main(argv: list[str]) -> int:
    charted, feature = clearance.chart()
    if not charted:
        print("feedback: no chart yet, so nothing is observable")
        return 0
    found = clearance.lines(feature)
    folded = clearance.with_evidence(charted, clearance.folded(found))
    settled = folded.marks | clearance.already_set(charted)
    rows = rank(feature, charted, folded, settled)
    if "--json" in argv:
        print(json.dumps({"v": 1, "feature": feature, "feedback": rows, "unseen": unseen(charted, folded)}))
        return 0
    return say(feature, rows, charted, folded)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
