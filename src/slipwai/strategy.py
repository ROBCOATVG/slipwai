"""Which change strategy this repository's trigger and its map recommend — *leave it* included — and what,
if anything, has been decided.

Brownfield adoption (experimental as `AGENTS.md` defines the word). `docs/change-strategy.md` says a programme
whose trigger is an end-of-life runtime stops after the language and framework rungs and has succeeded, and that
one whose trigger is "cannot ship" finds its problem at the architecture rung and needs the five below it first.
This is that page's judgement made mechanical enough to write on the map: the trigger (`project.json`'s `why`)
is read for what it names — a platform, a delivery problem, a change problem, a capability or a host — and the
map says what has to hold before anything architectural is worth starting. A trigger that names none of them,
or no trigger at all, recommends leaving the architecture where it is; the delivery rungs pay off regardless.

A recommendation is not a decision. The decision is an accepted ADR under `docs/adr/` carrying a `Strategy:`
line, read from the tree like every other fact, and `/strangle` refuses to go beyond it. *Leave it* is a decision
like any other, and finishes the axis. Rewrite is never recommended; a person decides it, and says why.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from .convergence import detected
from .layout import Layout
from .origin import STRATEGIES, Adoption, current
from .programme import option, phrase, programme
from .services import App

# How each strategy reads in a sentence: a hyphenated key is a value, not English, and `in-place` on its own says
# nothing at all. Used wherever a recommendation or a decision is written out in prose.
SAYS: dict[str, str] = {
    "leave-it": "leave the architecture where it is",
    "in-place": "change it in place",
    "modular-monolith": "a modular monolith in place",
    "strangler-fig": "a strangler fig",
    "rewrite": "a rewrite",
}
# What a trigger can name, in the order one is read for — the platform first, because a runtime that is out of
# support is the cheapest thing to fix and the one most often mixed into everything else.
TRIGGERS: tuple[tuple[str, str, str, str], ...] = (
    ("platform", r"end.of.life|\beol\b|out of support|unsupported|no longer supported|java\s*[678]\b|python\s*2\b|"
                 r"\.net framework|runtime|framework|upgrade|version|security (patch|fix|update)|vulnerab|\bcve\b",
     "in-place",
     "after rung 1 or 2 of the ladder — language version, framework — the programme has succeeded"),
    ("delivery", r"cannot ship|can'?t ship|slow to (ship|release|deploy)|releases? (take|are)|deploy(ment)?s? (is|are|"
                 r"take)|manual(ly)? deploy|lead time|outage|incident|regression|break(s|ing)? (in )?production|"
                 r"downtime|cannot release|can'?t release",
     "in-place",
     "when a change reaches production through one automated path with a green gate in front of it; only a "
     "problem that survives that is the architecture's"),
    ("host", r"\bcosts?\b|licen[cs]e|hosting|data ?cent|on.prem|move to (aws|azure|gcp|the cloud)|\bcloud\b|"
             r"kubernetes|containeri",
     "in-place",
     "after rungs 3 to 5 — packaging, runtime, host — with the architecture unchanged"),
    ("change", r"cannot change|can'?t change|hard to change|coupl|spaghetti|no tests|untest|nobody understands|"
               r"fragile|afraid|big ball|legacy code|technical debt",
     "modular-monolith",
     "when the contexts are found and each is behind its own `public` module under the import gate — no second "
     "deployable, no routing seam"),
    ("capability", r"new (feature|capabilit|product|market|customer)|scal(e|ing)|split|teams?\b|extract|"
                   r"microservice|separate|independent|multi.?tenan",
     "strangler-fig",
     "when the capabilities that had to change serve from their new home and the retirement ledger reads "
     "*removed* for each; the rest may stay where it is"),
)
# A whole line — `Strategy: strangler-fig`, however it is emphasised — and not a sentence that mentions the line: the
# first real ADR had "the `Strategy:` line here reads" in its Consequences, which read as the strategy `line`.
ADR_STRATEGY = re.compile(r"^\W*strategy\W*:\W*([a-z-]+)\W*$", re.IGNORECASE | re.MULTILINE)
ADR_ACCEPTED = re.compile(r"^## Status\s*\n+\s*Accepted\b", re.MULTILINE)


def rung_of(rows: list[dict], axis: str) -> str:
    return next((str(row.get("rung")) for row in rows if row.get("axis") == axis), "")


def preconditions(rows: list[dict], strategy: str) -> list[str]:
    """What the map says has to hold before the strategy is worth starting — the delivery rungs first, always."""
    found = []
    path = rung_of(rows, "path-to-production")
    if path in ("unknown", "manual", "scripted"):
        found.append(f"a pipeline that deploys on a passing `verify` — the path to production is `{path or 'unknown'}`")
    net = rung_of(rows, "safety-net")
    if net in ("none", "tests-exist"):
        found.append(f"a green suite in the gate — the safety net is `{net or 'none'}`")
    if rung_of(rows, "structure") == "as-found":
        found.append("every application's role recorded — the structure is `as-found`")
    if strategy == "strangler-fig":
        found.append("a seam requests enter through — an entry point in `survey/structure.md` with little of the "
                     "shared core behind it — and the data question answered (`docs/change-strategy.md`, *Data*)")
    if strategy in ("strangler-fig", "modular-monolith"):
        found.append("`/characterise` pinning each seam before it moves — the `pinned` rung, held per slice")
    return found


def expired_products(products: list[dict]) -> list[dict]:
    """Each product past its end of life, once.

    The platform record holds a row per *application* per product, so a repository whose four npm packages all
    run the same Node has four rows saying the same thing — and the strategy page listed the same sentence four
    times, under `because` and again under `before`. What the reader needs is the products, and a product is
    its title and version however many applications run it.
    """
    seen: dict[tuple[str, str], dict] = {}
    for product in products:
        if product.get("status") != "end-of-life":
            continue
        seen.setdefault((str(product.get("title")), str(product.get("version"))), product)
    return list(seen.values())


def platform_before(products: list[dict]) -> list[str]:
    """What the tree says about the platform, as a precondition: every product past its end of life, and the essay's
    option for each. Rungs 1 and 2 of the ladder come first whatever the strategy, so this leads the `before` list."""
    return [
        f"the platform in support — {phrase(p)}; the way up is {option(p)}" for p in expired_products(products)
    ]


def recommend(why: str | None, rows: list[dict], products: list[dict] = ()) -> dict:  # type: ignore[assignment]
    """The strategy the trigger and the map recommend, with the reasons, what has to hold first, and when it stops.
    `products` is the platform record's list: a product out of support is a platform problem the tree names, which
    goes before any strategy `why` names, and is the recommendation itself where `why` names none."""
    behind = platform_before(list(products))
    tree_says = [f"the tree names a platform problem: {phrase(p)}" for p in expired_products(list(products))]
    platform_stop = next(stop for kind, _, _, stop in TRIGGERS if kind == "platform")
    if not why:
        if behind:
            return {"recommended": "in-place", "trigger": "platform",
                    "because": ["no business trigger is recorded, and the tree itself names a platform problem, for "
                                "which `docs/change-strategy.md` says change it in place", *tree_says],
                    "before": [*behind, *preconditions(rows, "in-place")], "stop": platform_stop}
        return {
            "recommended": "leave-it", "trigger": None,
            "because": ["no business trigger is recorded, so nothing is asking for the architecture to change; the "
                        "delivery rungs below pay off whatever the trigger turns out to be"],
            "before": preconditions(rows, "leave-it"),
            "stop": "now, as far as the architecture goes; record `why` in `project.json` when there is one",
        }
    named = [(kind, strategy, stop) for kind, pattern, strategy, stop in TRIGGERS if re.search(pattern, why, re.I)]
    if not named:
        if behind:
            return {"recommended": "in-place", "trigger": "platform",
                    "because": [f"the trigger — {why!r} — names no problem this factory reads, but the tree names a "
                                "platform problem, for which `docs/change-strategy.md` says change it in place",
                                *tree_says],
                    "before": [*behind, *preconditions(rows, "in-place")], "stop": platform_stop}
        return {
            "recommended": "leave-it", "trigger": None,
            "because": [f"the trigger — {why!r} — names neither a platform, a delivery problem, a change problem, a "
                        "capability nor a host, so no strategy follows from it; leave the architecture where it is "
                        "until it does, and take the delivery rungs below, which pay off regardless"],
            "before": preconditions(rows, "leave-it"),
            "stop": "now, as far as the architecture goes",
        }
    kind, strategy, stop = named[0]
    because = [f"the trigger names a {kind} problem" + (
        f" (and also: {', '.join(k for k, _, _ in named[1:])})" if len(named) > 1 else ""
    ) + f", for which `docs/change-strategy.md` says {SAYS[strategy]}"]
    because += tree_says
    if strategy in ("strangler-fig", "modular-monolith"):
        because.append("the architecture rung is last on the ladder: every rung below it is cheaper with a green gate "
                       "and pinned seams, and none of them needs an architectural decision")
    return {"recommended": strategy, "trigger": kind, "because": because,
            "before": [*behind, *preconditions(rows, strategy)], "stop": stop}


def decision_of(root: Path, layout: Layout) -> dict:
    """The strategy an accepted ADR decides, with the ADR — the highest-numbered accepted one naming a strategy — or
    nothing, which is what a recommendation is until a person writes one."""
    decided: dict = {"decided": None, "adr": None}
    for path in sorted((root / layout.under("docs/adr")).glob("*.md")):
        text = path.read_text(errors="replace")
        # An ADR accepted under an older factory's spelling still decides — `Strategy: modernise-in-place` is read
        # as `in-place` — because the decision is the person's and a rename here is not a reason to lose it.
        named = [current(match.group(1).lower()) for match in ADR_STRATEGY.finditer(text)]
        strategy = next((name for name in named if name in STRATEGIES), None)
        if strategy and ADR_ACCEPTED.search(text):
            decided = {"decided": strategy, "adr": layout.under(f"docs/adr/{path.name}")}
    return decided


def ledger_finished(root: Path, layout: Layout) -> bool:
    """Whether every capability in the retirement ledger has reached *removed* — its last row says so — and there is
    at least one. An empty ledger has finished nothing."""
    text = (root / layout.under("retirement.md")).read_text(errors="replace") if (
        root / layout.under("retirement.md")).is_file() else ""
    last: dict[str, str] = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0] not in ("Date", "---") and not cells[0].startswith("-"):
            last[cells[1]] = cells[6].strip("*").lower()
    return bool(last) and all(status == "removed" for status in last.values())


def with_recommendation(root: Path, layout: Layout, adoption: Adoption, apps: list[App]) -> Adoption:
    """The adoption with its `strategy` record — recommended, decided, finished — and the map recomputed so
    the Strategy row reads from it."""
    rows = detected(apps, adoption)
    decided = decision_of(root, layout)
    record = {
        **recommend(adoption.why, rows, (adoption.platform or {}).get("products") or []), **decided,
        "finished": bool(decided["decided"]) and (decided["decided"] == "leave-it" or ledger_finished(root, layout)),
        # Every improvement the record shows, in order, paced by the decided strategy — none while nothing is decided.
        "programme": programme(adoption, apps, decided["decided"]),
        "provenance": "detected",
    }
    adoption = dataclasses.replace(adoption, strategy=record)
    return dataclasses.replace(adoption, convergence=detected(apps, adoption))
