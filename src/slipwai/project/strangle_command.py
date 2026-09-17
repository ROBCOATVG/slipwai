"""`commands/strangle.md`, `docs/change-strategy.md` and the retirement ledger: the Choose and Slice stages of adoption.

Only an adopted repository (brownfield adoption; experimental as `AGENTS.md` defines the word) gets
these. `/strangle <capability>` moves one capability out of the code that was here into a new home, behind
a routing seam, with the data strategy decided and a row written in the retirement ledger — and it refuses to
move a behaviour nothing has pinned. `docs/change-strategy.md` is the essay behind it: the three strategies,
the order to change in, what to do about data and infrastructure. It is an asset of the adoption
(`assets/adoption/docs/change-strategy.md`) rather than of the toolkit, because a generated greenfield project
has nothing that was here to change; `__DELIVERY__/` in it is spelled for the project's layout on the way in.
"""
from __future__ import annotations

from ..assets import ADOPTION_ROOT
from ..catalog import CATALOG, families
from ..layout import Layout
from ..origin import Adoption
from ..programme import programme_table
from ..services import App, wrapped_of
from ..strategy import SAYS
from ..targets import managed

RETIREMENT = "retirement.md"
RETIREMENT_LEDGER = """# Retirement ledger

What `/strangle` has moved out of the code that existed before the delivery method did, one row per capability:
from where, to where, routed by what, pinned by which tests, and where it stands. A capability is *routed* when
the seam can send its traffic either way, *moved* when the new home serves it, *retired* when the old path
serves none of it, and *removed* when the old code is gone. Rows are appended, never rewritten; a status changes
by a new row. The programme is finished when every row is *removed* — and a ledger nobody writes to is the first
sign that a programme has quietly become a second system beside the first.

| Date | Capability | From | To | Routed by | Pinned by | Status |
|---|---|---|---|---|---|---|
"""


def strategy_page(layout: Layout, adoption: Adoption | None = None) -> str:
    """`docs/change-strategy.md`, opening with what is recommended for this repository, its one layout-dependent path
    spelled for this project."""
    text = (ADOPTION_ROOT / "docs/change-strategy.md").read_text()
    text = text.replace("__DELIVERY__/", f"{layout.delivery}/" if layout.moved else "")
    if adoption is None or not adoption.strategy:
        return text
    marker = "## Three strategies, not two"
    return text.replace(marker, recommendation_section(adoption, layout) + marker, 1)


def recommendation_section(adoption: Adoption, layout: Layout) -> str:
    """What `why` and the map recommend, what has to hold first, when it stops, and how it becomes a decision."""
    record = adoption.strategy
    strategy = record.get("recommended", "leave-it")
    because = "\n".join(f"- {reason}" for reason in record.get("because", []))
    before = "\n".join(f"- {line}" for line in record.get("before", [])) or "- nothing the map can see"
    adr = layout.under("docs/adr")
    if record.get("decided"):
        decided = (
            f"**Decided: `{record['decided']}`**, by `{record.get('adr')}` — the row on the map reads "
            f"`{'done' if record.get('finished') else 'decided'}`. A different strategy is a new ADR that supersedes it."
        )
    else:
        decided = (
            f"**Nothing is decided yet.** A recommendation is the factory's reading; the decision is a person's, written "
            f"as an accepted ADR under `{adr}/` (Nygard's five sections, as `0001` shows) carrying one line "
            f"`Strategy: <leave-it | in-place | modular-monolith | strangler-fig | rewrite>`. `/survey` reads "
            "it, the map's Strategy row moves to `decided`, and `/strangle` will not move a capability until that "
            "line says `strangler-fig`. *Leave it* is a decision like any other and finishes the axis; rewrite is never "
            "recommended here, and an ADR that chooses it says why the other two cannot work. The word `Accepted` is "
            "the person's: an agent drafts the ADR at `Proposed`, puts the five strategies and this recommendation to "
            "them as a question, and changes the Status only after they have said, of that text, that they accept it."
        )
    return f"""## Recommended for this repository

**`{strategy}`** — {SAYS.get(strategy, strategy.replace('-', ' '))}.

{because}

Before anything architectural is worth starting, the map says these have to hold:

{before}

It stops {record.get('stop', 'when the trigger is answered')}.

{decided}

### The programme

Every improvement the record shows, in the order to take them, each paced by the strategy: quick wins are now
whatever it is; a build below the floor — Ant with its jars committed — is first whatever it is, since nothing
above it can be fetched, dated or audited until the build declares its dependencies (*Separate the layers*); an
application nobody has proved starts is next, its run path written in `survey/running.md` and the command that
starts it and proves it answers recorded as `smoke`, before any slice changes code that was here; the
platform and the ladder's rungs are a big bang per rung under changing in place, over
time under a strangler fig — the new home current from day one, the old home only if it stays — and recorded
but not scheduled under *leave it*; the tooling an ecosystem has and nothing here runs is one tool per slice,
green through the ratchet before it is recorded. `/drive`'s Convergence stage offers from the top. Nothing here
is ticked off by hand: `/survey` derives this again from the tree and the record, and a step done is gone.

{programme_table(record.get('programme') or [])}

"""


def routing_seam(target: str) -> str:
    if managed(CATALOG, target):
        return (
            "This project deploys to a managed target, so the routing seam is the flag transport it already has: a "
            "flag per capability, declared `off`, read through the flag reader, with the new home behind it and "
            "`make flag` as the switch. `docs/deployment.md` says what a flip costs and which undo button it is."
        )
    return (
        "This project deploys to infrastructure the factory does not manage, so the routing seam is one the "
        "repository already has or gains for the purpose: a reverse-proxy or router rule, a feature toggle the "
        "legacy system already reads, a message subscription moved from one consumer to another. Name it, say how "
        "it is switched and switched back, and write that in `docs/deployment.md` beside the release path."
    )


def new_home(apps: list[App]) -> str:
    wrapped = wrapped_of(apps)
    generatable = [app for app in wrapped if app.language in families()]
    lines = [
        "- **A generated service beside the code**: `/add-service <name> --language <language> --purpose \"…\"` — the "
        "factory scaffolds a service with the gate, the hexagonal layout and the axes, and the capability moves into "
        f"it. Languages it can generate: {', '.join(f'`{family}`' for family in families())}."
    ]
    if generatable:
        lines.append(
            "- The same language as the code that is here, for "
            + ", ".join(f"`{app.name}`" for app in generatable)
            + ", so the team keeps one language while the architecture changes."
        )
    lines.append(
        "- **A module inside the existing code**, where the strategy is the modular monolith in place: a context "
        "directory with its own `public` module, held to the import gate by declaring `\"layout\": \"hexagonal\"` on "
        "the application's record in `project.json`."
    )
    lines.append(
        "- Lifting the *existing* code into a generated service (`add-service --from <path>`) is not built; when it "
        "is, it is the extraction step here. Until then the capability is rewritten into its new home behind the "
        "seam, which is what the pinned tests exist to make safe."
    )
    return "\n".join(lines)


def decision_line(adoption: Adoption | None) -> str:
    record = (adoption.strategy if adoption else None) or {}
    if record.get("decided"):
        return f"`{record['decided']}` (decided by `{record.get('adr')}`)"
    return f"`null` — recommended `{record.get('recommended', 'leave-it')}`, decided nothing"


def strangle_command(apps: list[App], layout: Layout, target: str, adoption: Adoption | None = None) -> str:
    ledger = layout.under(RETIREMENT)
    pinned = layout.under("survey/pinned.md")
    view = layout.under("survey/structure.md")
    return f"""---
description: Move one capability out of the code that was here into a new home, behind a routing seam, and record it in the retirement ledger
argument-hint: <the capability to move, and where its requests enter>
---

# Strangle

Read `docs/change-strategy.md` first — the three strategies, the order to change in, and why dual-write is a
trap — and `skills/finding-seams/SKILL.md`. This command is one turn of the strangler fig: one capability, one
seam, one row in `{ledger}`. It is the Slice stage of adopting the method around code that existed before it.

## Refuse what is not ready

- If `$ARGUMENTS` names no capability, or names the whole system, stop and ask which capability, for which
  actor, and where its requests enter (an HTTP route, a message, a scheduled job, a file drop).
- If `{pinned}` has no row for the behaviour this capability carries, stop: run `/characterise` for it first.
  A capability moved without its behaviour pinned is a rewrite with no way to tell a change from a regression.
- If `project.json`'s `why` says the trigger is a runtime, a framework or a packaging that has to go, say so:
  those are lower rungs on `docs/change-strategy.md`'s ladder and cheaper with a green gate; the strangler is
  the architecture rung and comes after them unless the capability itself is the trigger.
- **No decision, no strangling.** `project.json`'s `strategy.decided` must read `strangler-fig`. Today it
  reads {decision_line(adoption)}. A recommendation is not a decision, and neither is this command's argument:
  where `decided` is `null` or names another strategy, stop, say what is recorded, and point at the way to
  decide — an accepted ADR under `docs/adr/` with a `Strategy: strangler-fig` line, then `/survey`
  (`docs/change-strategy.md`, *Recommended for this repository*). Going beyond the recorded decision is how a
  programme quietly becomes a second system beside the first.

## Decide the seam

Read `{view}` first: its entry points are where a capability's requests enter, its most-depended-on files are
what a cut there drags along — the last to move and the first to pin — and its hotspots are where the next change
lands anyway. A seam at an entry point with little of the shared core behind it is the cheap one; say which
lines of the view chose it.

{routing_seam(target)}

The seam is decided and written in the slice's plan before the code exists, with how it is switched back —
the same release-constraint decision `/drive` asks for, made concrete.

## Decide the data

`project.json`'s `database.schema` says where the schema lives; `docs/deployment.md` says who else reads the
tables. One writer per fact: the capability's data reaches its new home by change data capture from the legacy
store or by an outbox written in the legacy system's own transaction — never by writing the same fact in two
places. Where the new home is event-sourced, its history starts at a genesis event that records what the
legacy system handed over, and the legacy system is an external system in the model. Rehearse the move against
a copy with a reconciliation report; dual-run in shadow before an actor is served; roll back at least once in
rehearsal.

## Decide the new home

{new_home(apps)}

## Do the slice

1. Write the row in `{ledger}` first, status *routed*: capability, from, to, routed by, pinned by (the
   `{pinned}` rows), today's date. A slice that is not in the ledger did not happen.
2. `/drive` the slice as any other: the pinned characterisation tests are the acceptance tests of the move
   until the plan says which of them change, and why.
3. The slice ends **dark**: the new home deployed, the seam pointing at the old path, `make verify` green. A
   new row, status *moved*, when the seam serves the new home to real actors; *retired* when the old path
   serves none of it; *removed* when the old code is deleted — and that deletion is a slice too.

## Then

Say in the handover which rung of the ladder this was, what the seam is and how it is switched back, and which
row the ledger now ends on. The programme is finished when every row reads *removed*.
"""


def strangle_files(apps: list[App], layout: Layout, target: str, adoption: Adoption | None = None) -> dict[str, str]:
    return {
        "commands/strangle.md": strangle_command(apps, layout, target, adoption),
        "docs/change-strategy.md": strategy_page(layout, adoption),
    }
