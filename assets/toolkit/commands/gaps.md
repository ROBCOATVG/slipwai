---
description: Find consequential gaps in an artifact before planning, or in what was built afterwards
argument-hint: [artifact-or-feature-or-diff]
---

# Gaps

Two passes, selected by what is named. Neither invents a requirement, and a clean result is a valid outcome
when it says what was checked.

## Before planning — tighten the artifact

Named an artifact that is not built yet — {{artifact}}, a specification, mockups — read
`skills/find-gaps/SKILL.md` and run the conversational loop it describes: survey, ask one question at a
time, write the answer back as a new criterion or a recorded state, confirm. Missing states, unhandled
edges, unverifiable wording, and a slice still hiding an "and" are what this pass is for, and this is the
last point at which each of them is a paper edit. A gap needing a product decision is a question for the
user, never a criterion written from context.

## After implementing — trace the promise

Named a feature or diff, or nothing at all — the committed diff — read `skills/acceptance-review/SKILL.md`
and trace each acceptance promise to an observable test and a reachable production path. Report only
missing, contradictory, or unreachable behaviour, and separate a confirmed defect from a product question.
Read-only: no edits.
<!-- section: event -->

Compare event names, schemas, {{identity}}, and model links with the implementation in the same pass.
<!-- end section -->

Run this pass **after** the installed Spec Kit converge command reports converged, never before it.
Converge appends tasks for work the artifacts require and the code lacks; ahead of it, this pass reports
unbuilt tasks as gaps and buries the findings that actually need judgement.
