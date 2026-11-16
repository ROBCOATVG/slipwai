PATCH

**The captain agent's four decisions can be evaluated against recorded moments, and the score is advice.**
`make evals` puts each case under `evals/captain/cases/` to the captain through the project's own harness,
several times, and reports for each decision how often the agent gave an order a person would accept, gave a
plainly wrong order, gave an order nobody foresaw, or gave nothing within its bound. It also reports how often
the agent agreed with itself and what each run cost. It scores the order, never the wording. `make
evals-rescore` judges a saved run again after labels change, and calls no agent. The 34 drafted cases were cut
from two recorded fleets. Each one is unsigned until a person confirms it. Nothing gates on the score
(`docs/captain-evals.md`).

**Catch-up:** nothing; the evals are the keel repository's own, and a project carries none of them.
