PATCH

**The captain agent's four decisions can be evaluated against recorded moments, and the score is advice.**
`make evals` puts each case under `evals/captain/cases/` to the captain through the project's own harness,
several times, and reports for each decision how often the agent gave an order a person would accept, gave a
plainly wrong order, gave an order nobody foresaw, or gave nothing within its bound. It also reports how often
the agent agreed with itself and what each run cost, beside what always giving the same order or saying
nothing would score. It scores the order, never the wording, and an accepted order with another order beside
it is not right. `make evals-rescore` judges a saved run again after labels change, and calls no agent. Of the
41 cases, 30 were cut from two recorded fleets and 11 are synthetic, made up for moments the fleets never
had. Each one is unsigned until a person confirms it. Nothing gates on the score (`docs/captain-evals.md`).

**Catch-up:** nothing; the evals are the keel repository's own, and a project carries none of them.
