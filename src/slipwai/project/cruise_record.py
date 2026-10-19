"""The two records a run writes in a fixed shape: a decision, and a demo.

Their shapes live here, apart from the command that shows them and the brief that repeats them, because
three things are written from them — `commands/cruise.md`, the owner brief, and the `check-decisions` gate's
expectations — and a shape stated once cannot drift between them.

**There were three.** The checkpoint — `specs/cruise-checkpoint.md`, rewritten at every stage boundary so a
compacted context could resume — went with the runner in 7.7d, along with the stop file, the pid, the feed,
the stream, the watch cursor and the two inbox files. Each of those was state held outside the logs by the
one process that held the run, which is exactly what could not survive that process dying or a second machine
joining. What a compacted context reads now is the deck log, which is written anyway because it is what the
captain reads, and so is never stale and costs the stage nothing extra.
"""
from __future__ import annotations

from .cruise_agents import BOSUN, BROWSER, HAND, SKIPPER

# Where `/cruise`'s settings live, and the script that reads them. Both are all that is left of the runner:
# the settings outlived the loop because they were never the loop's — they are the answers a run gives at
# `/sail`'s stops, which a captain's dispatched `/sail` reads exactly as a person's would have.
CONFIG = ".specify/cruise.json"
SCRIPT = "scripts/agents/cruise.py"
# The rule that makes a decision entry also an ADR, stated once for the command and read by its tests. `{REPORT}`
# is `cruise_stops.REPORT`, which the command substitutes.
ADR_RULE = """\
**A decision that outlives its slice is also an ADR.** Ask the `architecture-decisions` skill's one question
of every entry, host-decided or skipper-decided: would reversing it cost a migration rather than a refactor —
an event's schema or name, stream identity, tenancy, the store, personal data, identity, a new dependency, a
published contract? Where it would, write `docs/adr/NNNN-<title>.md` in Nygard's five sections at `Proposed` —
the run never accepts its own architecture decision — with the next unused number, allocated here the way
`D<n>` is, and name it in the entry's `Written to` beside the artifact. The entry is the log of what was
decided; the ADR is where the next slice looks for why, and `{REPORT}` lists every ADR still `Proposed`."""
DECISION_ENTRY = f"""## D<n> — <the question, in one line>
- **Stage:** <stage> · **Slice:** <id> · **When:** <ISO instant> · **Stream:** <fairway>
- **Question:** <as the stage raised it>
- **Options:** <each, marking the one the stage recommended>
- **Decision:** <one>
- **Why:** <in the actor's terms> · **Read against:** <what already answered this — this project's own
  convention and where it is written, the specification, the constitution, standing D<m> — or `the method's
  default` where none of them did>
- **Decided by:** host (stage recommendation) | host (standing decision D<m>) | {SKIPPER} (<model>) | {BOSUN} | human
- **Confidence:** high | medium | low · **Would reverse if:** <the one condition>
- **Written to:** <the artifact paths the answer went into>
- **Status:** standing | awaiting human confirmation | confirmed by human <date> | overridden by D<m> |
  overridden by human <date>"""
DEMO_ENTRY = f"""## <ISO instant> — <accepted | behaviour | implementation> · <slice id> · {HAND} (<model>)
- **Started with:** <the literal command or URL> · **Seeded:** <what, or none>
- **Driven through:** {BROWSER} | <harness browser tool> | HTTP | CLI — <why, where not the first>
- **Examples:** <one line each — R1 e1: passed · R2 e1: failed, expected X, saw Y · R3 e2: unreachable, why>
- **Evidence:** <paths under demo/>
- **Feedback:** <what re-entered the ladder and at which stage, or the note for the next slice>"""
