MINOR

**`clearance.py --feedback` ranks the observables by what delaying a person's judgement costs.** An
observable — a view, an automation, an actor-facing translation — scores by the agent-made decisions it
would let a person test (weighted by confidence), times the unmerged slices steering by its marks, times the
commitment points ahead of it, over what it costs to surface (a `given` is cheap, a producer is dear), every
term printed with its sources. `--order` says what each row is *seen through* and where an observable sits
below rows that add nothing a person can judge; the split's rules ask for observables in that order; the
Voyage tab shows the next three.

**Catch-up:** a project's existing order is not rewritten; `--feedback` and `--order` say what the next
`/story-splitting` would propose and the person decides. Under `/cruise` with `decide: recommended-first`
the next split run records the reorder as a decision, citing the scores.
