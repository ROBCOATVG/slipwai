# Writing the first slice

Use `/sail` at any point. It derives the first incomplete stage from artifacts rather than conversation
memory, stepping back above the slice loop when scope has not been specified, modelled, or split yet, and
drives one actor-visible path to its demo.

## Files a slice normally touches

```text
specs/<feature>/slices/<id>/examples.md   rules, examples, Given/When/Then
docs/event-model/model.yaml               timeline, {{write-identity}}, event contract
{{slice-files}}
```

Add delivery or driven adapters only when the slice crosses those boundaries. A modelled screen is part of
the same vertical slice; do not ship only the backend beneath the white box.

## Artifact lifetime

Feature scope and cumulative contracts stay in the feature directory. A slice's plan, research, data model,
quickstart and tasks live under `specs/<feature>/slices/<id>/` from the day they are written: the canonical
paths the Spec Kit commands resolve to (`specs/<feature>/plan.md` and the other four) are links into that
directory, made by `/sail` before the plan command runs, ignored by git and never committed — so two slices
planned at once never overwrite each other's record. Given/When/Then examples live there from the day they
are mapped. Finishing a slice marks it done rather than moving it: `status: implemented` in the model, which
the ready set and the progress board both read. A `slices/README.md` register — one row per slice, accepted
when it is — is worth its ten lines, so the next slice does not re-derive the convention.

The demo is a feedback boundary, not completion. Route feedback to the stage that owns it, demonstrate the
revision, then—after acceptance—run an adversarial pass where this slice changed attack surface or closed
the split, mutation analysis where configured, and `make verify` before the ready slices (not done, every
`depends_on` done). Every unclaimed ready slice runs concurrently in the band its state admits — preparation
on clearance alone, implementation once its own marks are set and no question stands open — one delegate
per slice on a `slice/<id>` branch in its own worktree, refilled at every boundary, merged in split order and
held to the shared-surface rule by `make check-slice-scope` (`commands/sail.md`, *Running ready slices
concurrently*); a harness that cannot delegate takes the earliest in split order and names the rest.
