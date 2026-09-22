"""The stop table: every stop `/drive` makes, what `/cruise` does there instead, and where the answer is recorded.

Split from `cruise.py` because that module is at its budget, and because the table is the one part of the
command that varies with what the project is — the release rows only under a production target, the gaps
row reading the profile's own artifact, three more rows in an adopted repository — so it is the part most
often read on its own. The two paths the runner and the audit write, `LOG` and `REPORT`, live here because
the table is the first thing that names them; `cruise.py` re-exports both.
"""
from __future__ import annotations

from ..origin import Adoption
from .cruise_agents import BOSUN, DEMO_LOG, HAND

LOG = "specs/cruise-log.jsonl"
REPORT = "specs/<feature>/cruise-report.md"


def stop_table(event: bool, target: str, adoption: Adoption | None) -> str:
    """Every stop `/drive` makes, what `/cruise` does there instead, and where the answer is recorded."""
    criteria = "`examples.md`" if event else "the criteria in `spec.md`"
    rows = [
        ("The checkout is behind trunk, or the fetch failed",
         "Fetch and fast-forward where the tree is clean; rebase a `slice/<id>` branch that has local commits. "
         "A conflict parks; a fetch that cannot run parks and says so. Never derive from a stale tree",
         f"`{LOG}`"),
        ("Principles: the constitution is unratified",
         "`constitution: ratify` — the skipper drafts it with `/speckit-constitution` from the spec and the "
         "owner brief, answers `/constitution-coverage`, and ratifies it with the line `ratified by cruise "
         "(skipper) — pending human review`. `park` stops here instead",
         "`constitution.md`, a decision entry"),
        ("Product specification missing",
         "Refuse to start. A spec is the one thing a person brings; `/cruise` writes no product from nothing",
         "—"),
        ("Which service or bounded context owns a slice",
         "Decide against each service's recorded `purpose`; where none covers it, record the purpose the spec "
         "implies with `slipwai describe-service <name> --purpose` and decide. Contexts by the language test, "
         "recorded the same way with `--context`",
         "the model or plan, `project.json`, a decision entry"),
        (f"Slice gaps: a question at a time over {criteria}",
         "The conversational loop runs with the owner as the other party: each gap is answered — host or "
         "skipper by `decide` — and written back as the criterion or state. `gaps=N` still counts",
         f"{criteria}, a decision entry per question"),
        ("A delegate hands back a product question in `plan.md`",
         "Answer it, un-block the slice, re-dispatch with the entry as a pointer, never as a conclusion",
         "`plan.md`, a decision entry"),
        ("Converge appended Phase 4 tasks; the after-converge `/gaps` says stop",
         "Already bounded by the ladder: continue to the demo as `commands/drive.md` says", "—"),
        ("The demo stop",
         f"Delegate to `{HAND}` with exactly what the stop hands a person, plus the acceptance script; take its "
         "verdict as the actor's and re-enter the ladder where demo feedback re-enters. Acceptance says "
         f"`accepted-by: {HAND}` on the register row or status flip",
         f"`{DEMO_LOG}`, `benchmark.json` `outcome=`, the register"),
        ("The ready set is empty",
         "Not a stop: the completion audit below. Only an audit with nothing left is `done`",
         f"`{REPORT}`, decision entries"),
        ("An input that is genuinely unavailable — a credential, an external system, a person's approval",
         f"Never invented. Mark the slice blocked, take the next ready slice, and hand the blocker to `{BOSUN}` "
         "(*Blocked*, below): a stub behind the port, recorded as a stub. Park only at the catastrophic, or "
         "when the bosun could not move it",
         "a decision entry, the stub in `plan.md`, ⛔ on the board"),
    ]
    if target != "none":
        rows.insert(5, (
            "Release constraint",
            "Take the stage's own recommendation. `release: flagged` — every slice continues or opens a flag "
            "seeded `off`, so every merge is dark and a person flips keys. `park` stops at the push instead",
            "`plan.md`, the flag file, a decision entry"))
        rows.insert(6, (
            "\"A release they want now\" — no flag, or a flag already on, before the push",
            "Never answered by the machine: a release nobody asked for is on the catastrophic list. Under "
            "`flagged` it does not arise; where it does, park with the exact question", "a `parked` line in the log"))
    if adoption is not None:
        rows += [
            ("Ground: a convergence row still `unrecorded` on an axis the slice touches",
             "A fact about the world is not a decision, and is never invented. The row stays `unrecorded`; the "
             "bosun works on the survey's `detected` value as a stated assumption, never marked `confirmed`",
             "a decision entry naming the assumption"),
            ("The change-strategy ADR at `Accepted`",
             "The word is a person's. The bosun proceeds on the recommendation at `Proposed` and says so",
             "the ADR at `Proposed`, a decision entry"),
            ("Quick wins and method slices offered from the programme",
             "Take the programme top-first, as the stage recommends", "`project.json` `planned`, a decision entry"),
        ]
    body = "\n".join(f"| {index} | {stop} | {does} | {recorded} |" for index, (stop, does, recorded)
                     in enumerate(rows, start=1))
    return f"| # | Where `/drive` stops | What `/cruise` does there | Recorded in |\n|---|---|---|---|\n{body}"
