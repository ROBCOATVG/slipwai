"""`survey/structure.md`: the architecture view, rendered for the two decisions that need it.

The Structure axis of the convergence map climbs `as-found` → `named` → `laid-out` → `hexagonal` → `typed`, and
`/strangle` has to choose a seam; both want to know where anything starts, what depends on what and where change
happens. `structure.py` reads that; this page says it, per wrapped application, and ends with what the reading
means for the map and for the cut. Written by `adopt`, rewritten by `adopt --refresh`; never edited by hand.
"""
from __future__ import annotations

from ..assets import VERSION
from ..layout import Layout
from ..origin import Adoption
from ..programme import option, phrase, staleness
from ..structure import AppStructure, Structure

RUNG_STEPS = {
    "as-found": "record what each application is — the entry points above say it: a `start` script, a main package or a "
                "web SDK is a service, a `bin` a tool, a test directory a suite — as `kind` on its record in "
                "`project.json` with provenance `confirmed`, then `/survey`; the row moves to `named`",
    "named": "move each application under `apps/<name>/`, the layout a generated project has, as a slice of its own — "
             "the wrappers and recorded commands follow the path in `project.json`; the row moves to `laid-out`",
    "laid-out": "give each application the hexagonal layers a generated service has — `domain/`, `ports/`, `adapters/` — "
                "and declare `\"layout\": \"hexagonal\"` on its record, which puts it under `make check-imports`; the "
                "row moves to `hexagonal`",
    "hexagonal": "record a `typecheck` command for every application and make it green through the ratchet; the row "
                 "moves to `typed`",
    "typed": "nothing: this is where a generated project sits",
}


def entry_lines(view: AppStructure) -> str:
    lines = [
        f"- **{point.what}** — `{point.path}`" + (f": `{point.runs}`" if point.runs else "")
        for point in view.entry_points
    ]
    return "\n".join(lines) or (
        "- nothing in the tree names one: no start script, main package, program, container command or Procfile. "
        "Something starts this some way nobody has written down — a question for the person, and a line for "
        "`docs/deployment.md` once answered."
    )


def module_table(view: AppStructure) -> str:
    rows = "\n".join(f"| `{module.path}` | {module.files} | {module.languages} |" for module in view.modules)
    return f"| Directory | Files | Mostly |\n|---|---|---|\n{rows}\n" if rows else "No subdirectory holds code.\n"


def dependency_line(view: AppStructure) -> str:
    if not view.manifest:
        return "No dependency manifest this survey can read."
    if not view.dependencies:
        return f"`{view.manifest}` declares no runtime dependencies."
    shown = ", ".join(f"`{name}`" for name in view.dependencies[:12])
    more = f", and {len(view.dependencies) - 12} more" if len(view.dependencies) > 12 else ""
    return f"{len(view.dependencies)} declared in `{view.manifest}`: {shown}{more}."


def counted_table(rows: tuple[tuple[str, int], ...], what: str) -> str:
    body = "\n".join(f"| `{path}` | {count} |" for path, count in rows)
    return f"| File | {what} |\n|---|---|\n{body}\n"


def churn_section(view: AppStructure, found: Structure) -> str:
    if found.commits == 0:
        return "No Git history could be read."
    if found.commits < 5:
        return (
            f"{found.commits} commit(s) in the history, which is too little for a hotspot to mean anything; this "
            "section fills in as the repository's history does."
        )
    window = f"since {found.since}; " if found.since else ""
    # The commits before the method arrived, so the section reads the same on every `/survey`: what the repository's
    # history said about where change happens when the method was installed, not a count that moves with every commit.
    return (
        f"{view.commits} of the {found.commits} commits before the method arrived ({window}{found.authors} author(s)) "
        f"touched this application. The files they touched most:\n\n{counted_table(view.hotspots, 'Commits')}"
    )


def graph_section(view: AppStructure, found: Structure) -> str:
    if not found.graph.present:
        return f"Not read: {found.graph.note}."
    header = (
        f"Read from {found.graph.note}: {found.graph.files} files, {found.graph.nodes} symbols, "
        f"{found.graph.edges} edges across the repository."
    )
    if not view.depended_on and not view.depending:
        return f"{header} No edge crosses between two of this application's files."
    return (
        f"{header}\n\n**Most depended on** — the files the most other files call, import or reference. A slice "
        f"through one of these touches everything below it; pin before changing.\n\n"
        f"{counted_table(view.depended_on, 'Files depending on it')}\n"
        f"**Depending on the most** — the files that reach the most other files; where the wiring is.\n\n"
        f"{counted_table(view.depending, 'Files it depends on')}"
    )


def platform_section(view: AppStructure, record: dict) -> str:
    products = [p for p in (record.get("products") or []) if p.get("app") == view.name]
    if not products:
        return (
            "Nothing the survey can date: no runtime pin, no framework version it knows in the manifest, no image in a "
            "`Dockerfile`. `/ground` asks which version this actually runs on; the answer goes in `toolchain.version` "
            "with `confirmed` provenance, and the next `/survey` dates it here."
        )
    rows = "\n".join(
        f"| {p['title']} | {p['version']} | `{p['status']}` | {p['eol'] or '—'} | {p['evidence']} |" for p in products
    )
    behind = [p for p in products if p["status"] == "end-of-life"]
    ways = "\n".join(f"- **{phrase(p)}.** The way up: {option(p)}." for p in behind)
    said = (
        f"\n\nOut of support, and so a platform problem the tree names before any strategy "
        f"(`docs/change-strategy.md`, *Recommended for this repository*):\n\n{ways}" if behind else ""
    )
    return (
        f"Dated {record.get('dated')} against the factory's support table of {record.get('snapshot')} "
        f"(endoflife.date; JUnit and the servlet API kept by hand).{staleness(record)}\n\n"
        f"| Product | Version | Support | Until | Read from |\n|---|---|---|---|---|\n{rows}{said}"
    )


def app_section(view: AppStructure, found: Structure, platform: dict) -> str:
    return f"""## `{view.name}` — `{view.path}`

### Where anything starts

{entry_lines(view)}

### What it is made of

{module_table(view)}
### What it declares it depends on

{dependency_line(view)}

### What it runs on

{platform_section(view, platform)}

### Where change happens

{churn_section(view, found)}

### What the graph says

{graph_section(view, found)}
"""


def map_section(adoption: Adoption, layout: Layout) -> str:
    rows = {row.get("axis"): row for row in (adoption.convergence or []) if isinstance(row, dict)}
    structure = rows.get("structure") or {}
    rung = structure.get("rung", "as-found")
    ladder = "\n".join(
        f"- {'**' if step == rung else ''}`{step}`{'** — here' if step == rung else ''}: {'to move on, ' if step != 'typed' else ''}{how}"
        for step, how in RUNG_STEPS.items()
    )
    platform = rows.get("platform") or {}
    return f"""## What this means for the map

The Structure row of `{layout.under('docs/convergence.md')}` stands at `{rung}`
({structure.get('provenance', 'unrecorded')}; {structure.get('evidence', 'no evidence recorded')}). The ladder, and what
each rung asks of this repository:

{ladder}

The Platform row stands at `{platform.get('rung', 'unknown')}` ({platform.get('provenance', 'unrecorded')};
{platform.get('evidence', 'no evidence recorded')}). It climbs `unknown` → `inventoried` → `supported` → `audited`
as *What it runs on* above is dated, brought into support product by product — each an option above, offered as a
method slice, never a version the factory bumps — and given an `audit` command the gate runs. `/survey` reads every
product against the table on the day it runs, so a runtime that leaves support while the work goes on moves this row
by itself — and re-dates the reading only when a product, a version, a status or the table moved, so the date above
is the day something last changed and not the day somebody last looked.

A rung is claimed only once the fact behind it holds; `make check-convergence` fails a row the tree contradicts.
"""


def cut_section(layout: Layout) -> str:
    return f"""## Where to cut

For `/strangle`: a capability's seam is one of the entry points above — a route, a command, a job, a process — with
as few of the most-depended-on files behind it as possible. The files every other file depends on are the last to
move and the first to pin (`/characterise`, `{layout.under('survey/pinned.md')}`). The hotspots are where the next
change lands anyway, so a seam there pays for itself; a capability nothing has touched in the whole window is a
candidate to leave where it is (`docs/change-strategy.md`).
"""


def structure_page(found: Structure, adoption: Adoption, layout: Layout) -> str:
    sections = "\n".join(app_section(view, found, adoption.platform or {}) for view in found.apps) or (
        "No application that existed before the method is recorded, so there is nothing here to read.\n"
    )
    return f"""# Architecture view

Written by `slipwai adopt` ({VERSION}) from the tree, its Git history and — where `.codegraph/` holds an index —
CodeGraph's graph; `/survey` rewrites it. Nothing here is inferred: a file is an entry point because a manifest or
its own name says so, a hotspot because commits touched it, a dependency because the graph holds the edge.
Experimental: see `../docs/adoption.md`.

{sections}
{map_section(adoption, layout)}
{cut_section(layout)}"""
