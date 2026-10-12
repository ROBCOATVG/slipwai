"""`/cruise`: `/sail` with nobody at the wheel — the agent as driver and product owner, until the specs are satisfied.

`/sail` stops for a product decision, an unavailable input, an exhausted split and the next demo. `/cruise` runs
the same ladder — not a copy — and at each stop does what the owner or the actor would have: decides, on the host
where the stage recommends or a standing decision covers it and through `sail-decide-skipper` where the question is
open; demos through `sail-demo-hand`; and audits the specification against what shipped where the split runs out.
Every answer goes where `/sail` would have written a person's, and once more in `decisions.md` — and, where
reversing it would be a migration, into an ADR at `Proposed` — so a person can read and overturn every one.

**Typed, it casts off**: `scripts/agents/fleet.py` starts the harbourmaster and a captain per stream, and the
session takes the watch seat. `assets/cruise/cruise.md` is what a captain's dispatched `/sail` reads — the rules
for the stops when nobody is at the wheel — and it is one page rather than two because the answers must be the
same whoever asks.

There is no outer loop here any more, and the parts that were one are gone with it: the four last lines, the
checkpoint file, the stop file, the kick-off argument that reached one iteration. What replaced them is the
deck log, which a captain reads and which is written anyway.

What is left in Python is what `docs/generated-prose.md` keeps out of an asset. `SETTINGS` is the one list the
config file, `/cruise-settings`, the command page and `scripts/agents/cruise.py` are all written from, and the
table on the page is rendered from it so the two cannot drift. The sentence naming the upstream stages agrees
with the profile inside itself, which is rendering rather than prose. The one branch that is a whole paragraph
— what an adopted repository is told about the two stops that are a person's word — is a section the page
carries and this module selects.
"""
from __future__ import annotations

import json

from ..assets import CRUISE_ROOT
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App
from .cruise_agents import OWNER_BRIEF, SKIPPER
from .cruise_hand import hand_section
from .cruise_record import ADR_RULE, DECISION_ENTRY, SCRIPT
from .cruise_seat import values as seat_values
from .cruise_stops import REPORT, stop_table
from .cruise_unblock import unblock_section
from .prose import page

# There is no last line any more, and that is the change this file turns on. The loop read one sentence at
# the end of a session — `cruise: continue`, `done`, `parked: …`, `stopped: human` — and a session that ended
# on anything else was no progress to it. A captain reads the deck log instead: every mark the chart's `sets`
# names, plus the demo, written during the turn. The rule is the same one — *a stage that wrote no line made
# no progress* — but it is now checked against what the stage produced rather than against what it said.
# Every setting, its values, its default and what it controls — the one list the config, the command, the
# settings command and `scripts/agents/cruise.py` are all written from.
SETTINGS: tuple[tuple[str, tuple[str, ...] | str, object, str], ...] = (
    ("enabled", ("true", "false"), False, "whether `/cruise` runs at all; `false` is a refusal that says so"),
    ("decide", ("recommended-first", "skipper-always"), "recommended-first",
     "who answers a product question: the host where the stage recommends an answer or a standing decision "
     "covers it and `sail-decide-skipper` otherwise, or `sail-decide-skipper` for every question"),
    ("release", ("flagged", "park"), "flagged",
     "the release-constraint stage: every slice continues or opens a flag seeded off, so every merge is dark; "
     "or park at the push and let a person say it is a release they want"),
    ("constitution", ("ratify", "park"), "ratify",
     "an unratified constitution: the skipper drafts and ratifies it, marked pending human review; or park"),
    ("hand", ("browser", "http", "cli"), "browser",
     "the top of the hand's ladder for a demo; each falls through to the next where it cannot run"),
    ("unblock", ("bosun", "park"), "bosun",
     "what a block becomes: work for `sail-unblock-bosun` first — a stub, a narrower reading, a repair — parking only "
     "at the catastrophic or when it fails; or a park at once"),
    # `stuck_after`, `max_iterations`, `max_hours` and `poll_minutes` were here until 7.7d and are not any
    # more: each was a budget on a loop that no longer exists. What bounds a run is the telegraph
    # (`harbour.json`), which is one lever rather than four numbers nobody set.
    ("model", "a model identifier or null", None, "the model the ladder itself runs on — the driver, and every "
     "stage `.specify/models.json` maps to `host`; null is the harness's default, which nobody at the wheel chooses"),
)
COMMENT = (
    "How /cruise runs /sail with nobody at the wheel. Change it with /cruise-settings (python3 "
    f"{SCRIPT} --set key=value), checked; `make check-agents` holds the shape. commands/cruise.md says what "
    "each value means. `enabled: false` is the default: a project has to ask for this."
)
# Which stages are upstream of the split, which is a sentence agreeing with the profile rather than a
# paragraph somebody edits — the event model is a stage of one profile and not of the other.
UPSTREAM = {
    True: "principles, the specification, the event model and the split",
    False: "principles, the specification and the split",
}


def cruise_config() -> str:
    """`.specify/cruise.json` as generated: every setting at its default, and where it is explained."""
    table: dict[str, object] = {"_comment": COMMENT, **{key: default for key, _, default, _ in SETTINGS}}
    return json.dumps(table, indent=2, ensure_ascii=False) + "\n"


def settings_table() -> str:
    def spelled(values: tuple[str, ...] | str) -> str:
        return " \\| ".join(f"`{value}`" for value in values) if isinstance(values, tuple) else values

    rows = "\n".join(
        f"| `{key}` | {spelled(values)} | `{json.dumps(default)}` | {controls} |"
        for key, values, default, controls in SETTINGS
    )
    return f"| Setting | Values | Default | Controls |\n|---|---|---|---|\n{rows}"


def values(
    event: bool = False, target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> dict[str, str]:
    """Every value a page under `assets/cruise/` may name, pooled with the seat's.

    Pooled rather than one set per page because `commands/cruise.md` carries the watch seat and the seat's
    own pages carry the sentence about a folded output: no page here names only its own module's values,
    and the digest gate is what holds each page to the text it had.
    """
    return {
        **seat_values(layout),
        "owner-brief": OWNER_BRIEF,
        "skipper": SKIPPER,
        "report": REPORT,
        "decision-entry": DECISION_ENTRY,
        "adr-rule": ADR_RULE.replace("{REPORT}", REPORT),
        "hand": hand_section(layout.make),
        "unblock": unblock_section(SCRIPT),
        "stop-table": stop_table(event, target, adoption),
        "settings-table": settings_table(),
        "upstream": UPSTREAM[event],
    }


def cruise_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    """`commands/cruise.md`: the ladder's stops answered with nobody at the wheel."""
    del apps  # the ladder's own text already carries the profile's services; nothing here is per service
    return page(CRUISE_ROOT, "cruise.md", values(event, target, layout, adoption),
                ("adopted",) if adoption is not None else ())


def cruise_settings_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-settings`: the settings shown, or changed through the checked `--set`."""
    return page(CRUISE_ROOT, "cruise-settings.md", values(layout=layout))
