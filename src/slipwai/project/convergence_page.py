"""`docs/convergence.md`: the convergence map, rendered from the rows `project.json` records — never written by hand.

The page carries a marker with a digest of the rows it was rendered from, so `scripts/check-convergence.py` can
tell a page that no longer matches the record — somebody edited a row and did not run `/survey` — from one that
does. Brownfield adoption (experimental as `AGENTS.md` defines the word).
"""
from __future__ import annotations

import hashlib
import json

from ..convergence import AXES, BY_KEY, Row, summary
from ..layout import Layout
from .adopted import EXPERIMENTAL

MARKER = "<!-- convergence: {digest} -->"


def digest(rows: list[Row]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]


def convergence_page(project_name: str, rows: list[Row], layout: Layout, converged: dict | None = None) -> str:
    at, below, unrecorded = summary(rows)
    ended = (
        f"\n\n**Converged** with slipwai {converged.get('with')}: the material moved from `{converged.get('from')}/` "
        "to the root, and the distinction between this repository and a generated one has ended. The rows stay as the "
        "record of where it stood.\n" if converged else ""
    )
    table = "\n".join(
        f"| {BY_KEY[r['axis']].title} | `{r['rung']}` | `{r['target']}` | {r['evidence'] or '—'} | "
        f"{r['planned'] or '*not yet*'} | `{r['provenance']}` |"
        for r in rows if r["axis"] in BY_KEY
    )
    ladders = "\n\n".join(
        f"### {axis.title}\n\n" + "\n".join(
            f"{i + 1}. `{rung}` — {axis.means[rung]}" + (" ← a generated project sits here" if rung == axis.target else "")
            for i, rung in enumerate(axis.rungs)
        )
        for axis in AXES
    )
    return f"""{MARKER.format(digest=digest(rows))}
# Where `{project_name}` stands

{EXPERIMENTAL}

A generated project starts at the top of every ladder below and the method keeps it there. This repository
started wherever it was; this page says where that is, axis by axis, and the loop climbs one rung per slice
until nothing here differs from a generated project — at which point `slipwai converge` makes it one. **{at}** of
{len(rows)} axes are at their target, **{below}** below it, **{unrecorded}** unrecorded.{ended}

Every row is a fact `project.json` holds under `convergence`, with where it came from: `detected` from the tree,
`confirmed` or `overridden` by a person, `unrecorded` where nothing has said. Nothing is a default. To move a
row, establish the rung — a slice, a decision, a pinned seam — then say so in `project.json`; `/survey`
(`slipwai adopt --refresh`) re-reads the tree and regenerates this page, and `{layout.make} check-convergence`
fails a row the tree contradicts or a page that no longer matches the record. `/drive` reads this before the
first slice and offers the next unplanned row as a method slice beside the product's.

| Axis | Where it stands | Target | Evidence | Planned as | Provenance |
|---|---|---|---|---|---|
{table}

## The ladders

{ladders}
"""
