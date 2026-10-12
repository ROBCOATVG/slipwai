"""The three agent types `/cruise` delegates to: the skipper, who decides, the hand, who demos, and the bosun, who unblocks.

`/sail` stops for a product decision and for the demo because both belong to a person. `/cruise` runs the same
ladder with nobody at the wheel, so each of those stops has to be a delegate with a standing brief of its own:
`sail-decide-skipper` answers a product question the way the owner brief and the decision log say the owner would,
and refuses the one thing a decision can never be — a fact it does not have; `sail-demo-hand` runs the demo the
ladder hands a person, through a browser where the slice has a screen, and reports what using it revealed
in the three words the benchmark already knows.

Their briefs used to be written out here, because `agents.py` was at its budget and three more briefs would
not fit in it. They are now assets like every other brief — `assets/toolkit/agents/sail-decide-skipper.md` and its
two siblings — and what is left is what was never prose: the paths those three delegates read and write.

**This module stays, and the reason is no longer the budget that made it.** Nine modules of the cruise read
these names — `briefs.py`, `cruise.py`, `cruise_seat.py`, `cruise_hand.py`, `cruise_record.py`,
`cruise_stops.py`, `cruise_told.py`, `cruise_unblock.py` and `decisions.py` — and every one of them is a
writer of prose that `cruise.py` itself imports. Slice 16.6 tried the rejoin the plan asked for, putting these
constants back into `cruise.py` and pointing the nine at it: `check-structure.py` answered with seven import
cycles, `project.cruise_record -> project.cruise -> project.cruise_record` among them. The seam is real and it
is the direction of the arrows: the names the delegates are known by sit *below* everything that writes about
them, and `/cruise`'s own page is one of those writers rather than their home. It is the shape `metadata.py`
settled for the manifest in 16.4, met a second time.
"""
from __future__ import annotations

SKIPPER, HAND, BOSUN = "sail-decide-skipper", "sail-demo-hand", "sail-unblock-bosun"
# Where a decision is written, per feature; the shape of an entry is `cruise.DECISION_ENTRY`.
DECISIONS = "specs/<feature>/decisions.md"
OWNER_BRIEF = ".specify/product-owner.md"
# What is true about the domain rather than what this product chose: a glossary, the invariants, the
# rules a regulator or a standard imposes. Issue #27: the skipper parked on questions a written fact
# would have answered, and guessed at others it should have parked on.
DOMAIN = ".specify/domain"
DEMO_LOG = "specs/<feature>/slices/<id>/demo-log.md"
EVIDENCE = "specs/<feature>/slices/<id>/demo/"
# What the hand drives a screen with, first: a CLI, so it runs from the shell on every harness and every
# snapshot and screenshot is a file. Installed on demand the way the run skill installs Playwright, never a
# dependency of the project; it finds an existing Playwright or Chrome before downloading one.
BROWSER = "agent-browser"
BROWSER_INSTALL = "npm install -g agent-browser && agent-browser install"
