---
description: Find consequential gaps in an artifact before planning, or in what was built afterwards
argument-hint: [artifact-or-feature-or-diff]
---

# Gaps

Two passes, selected by what is named. Neither invents a requirement, and a clean result is a valid outcome
when it says what was checked.

## Before planning — tighten the artifact

Named an artifact that is not built yet — {{artifact}}, a specification, mockups.

**On the feature's `spec.md`**, run `/speckit-clarify` first when its result is not already there. Clarify
writes a `## Clarifications` section back into the
specification (`None.` when it found nothing to ask). Once clarify has finished, start
`/speckit-checklist` and the survey phase of `skills/find-gaps/SKILL.md` in parallel, both against that same
clarified snapshot. Checklist writes `specs/<feature>/checklists/`; the parallel survey is read-only and
returns candidate gaps. Wait for both. Then run the find-gaps conversational loop below on the host, using
the checklist and survey together. No parallel worker edits `spec.md`, so neither reads a moving source or
overwrites an answer.

Read `skills/find-gaps/SKILL.md` and run the conversational loop it describes over the named artifact:
take the completed survey, ask one question at a time, write the answer back as a new criterion or a
recorded state, confirm.
Missing states, unhandled edges, unverifiable wording, and a slice still hiding an "and" are what this pass
is for, and this is the last point at which each of them is a paper edit. On an example map, a mock-up, or a
slice's own criteria, clarify and checklist do not run; they are the feature's, once, but the same
find-gaps loop runs here. A gap needing a product decision is a question for the user, never a criterion
written from context.

## After implementing — trace the promise

Named a feature or diff, or nothing at all — the committed diff — read `skills/acceptance-review/SKILL.md`
and trace each acceptance promise to an observable test and a reachable production path. Report only
missing, contradictory, or unreachable behaviour, and separate a confirmed defect from a product question.
Read-only: no edits.
<!-- section: event -->

Compare event names, schemas, {{identity}}, and model links with the implementation in the same pass.
<!-- end section -->

It runs once per capability, at the ladder's *Capability gates* rung, over the capability's whole diff —
every slice under it merged and converged — and per slice, over the slice diff after convergence, only under
the `open` release mode.

Run this pass **after** the installed Spec Kit converge command reports converged, never before it.
Converge appends tasks for work the artifacts require and the code lacks; ahead of it, this pass reports
unbuilt tasks as gaps and buries the findings that actually need judgement. `/speckit-analyze` is not this
pass and not the one above: it runs after tasks and before implementation, and it only asks whether
`spec.md`, `plan.md` and `tasks.md` still agree.
