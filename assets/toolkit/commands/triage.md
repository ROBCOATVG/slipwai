---
description: Propose where each piece of feedback from the board goes, and change nothing else
argument-hint: [numbers]
---

# Triage

A person used the built app and said what it showed them, on the board. The board wrote each message as
`docs/feedback/NNNN-<slug>.md`: front matter with the context it knew (`slice`, `feature`, `fairway`,
`capability`, `page`, `signed-in-as`, `trunk`) and their words as the body. This proposes where each one
goes. **It proposes and changes nothing else.** A person confirms every proposal on the board, and the board
hands it on; nothing here edits a specification, a split, a chart, a deck log or code.

**Typed by a person**, run `python3 scripts/agents/triage.py` — `{{make}} triage`. It finds every record with
no `proposed`, `dropped` or `confirmed` line.

**In a session that script dispatched** (`SLIPWAI_STAGE=triage`), this file is the rules. The argument is the
record numbers, comma-separated:

1. Read each record. Then read what it is about: the feature's `spec.md`, the slice's directory under
   `specs/<feature>/slices/<slice>/` (its example map and `try-it.json` where they exist), `chart.yaml`,
   `story-split.md`, `docs/design.md`, and the names under `docs/intake/`. Read the deck logs under
   `.slipwai/logs/` for which slices are claimed and not merged: those are *in flight*. Where the record
   names no slice, find the one it is about from the page and the words; leave `slice` out only when none is.
2. **One thing per record.** A message that says two things becomes two records: keep the first in this
   file, and write each other one as the next free number, with the same context lines, `split-from: NNNN`,
   and only its own words as the body.
3. Give each record one route, the one that is true:
   - `defect` — the app does not do what the specification or an example says. Name the rule or example.
   - `change` — the app does what was specified, and the person wants something else. Name the rule.
   - `scope` — something no rule, slice or intake idea covers yet.
   - `planned` — a slice that has not been built yet already covers it. Name that slice.
   - `note` — how something should look or read, for every slice with a screen from now on.
4. Write into the front matter, one line each: `route:` the route; `slice:` the slice it is about where there
   is one; `about:` at most six words a person scans a list by; `becomes:` one sentence saying what
   confirming it would do — a fix slice after L18, an amended rule FR-041 and a new slice, an intake idea, a
   note in `docs/design.md`; `in-flight: <slice>` only for a defect or change whose slice is in flight;
   `proposed:` the UTC time, as `2026-10-21T11:06:40Z`. Then end the file with a `## Proposed` section of
   two to four short lines: why this route, quoting the rule or example it was checked against.
5. Do not change any line a person or the board wrote. Commit `docs/feedback/` on the current branch as
   `Triage feedback <numbers>`, say each number and its route, and end the session.
