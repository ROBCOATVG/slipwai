"""Two sections of `commands/drive.md`: the boundary an implementation delegate is handed — a task, a rule or
a user story — and how an experiment on the method is declared, asked about, recorded and switched off.

Both come from one downstream project's measurement of its own `/drive`. Twenty-three implement delegates on
one slice spent 1.5–2.5 minutes each re-reading the same plan, map, precedent and test file, because the
boundary was the task and every task was a fresh context. Moving the boundary to the user story — every rule
that belongs to it, each its own RED-GREEN-REFACTOR cycle in one context — answers that without touching the
increment, which Principle V keeps at the rule. Testing it took an experiment, and the project had to hand-roll
one: arms in a prose table, a fenced block in its `drive.md`, an off switch that started life as a `git revert`
and stopped being one at the next commit, an arm whose licence lived in another arm's text and was read
conservatively by the first delegate to run it, and a default arm nothing announced had starved the
comparison. This is the apparatus it asked to inherit instead.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout

# Where a project declares the one experiment it is running on its own method. Absent by default: nothing here
# generates it, and deleting it is how an experiment is removed once its switch has been thrown.
EXPERIMENT = ".specify/experiment.md"
# How many rules one implementation delegate is handed. The increment inside is always the rule.
BOUNDARIES = ("task", "rule", "story")


def experiment_section(layout: Layout = AT_ROOT) -> str:
    """The two sections, after *What each stage costs*: the boundary is recorded as an arm, so it comes first."""
    return f"""### The implementation boundary: task, rule or story

The increment is always one rule (Principle V). What varies is how many rules one `drive-implement` delegate
is handed, and that is a choice this session makes and records rather than something the task list decides:

- **`task`** — one task as `drive-tasks` cut it: the finest boundary, one fresh context per increment.
- **`rule`** — one rule with its examples. Under a rule-owned map the tasks stage cuts one task per rule, so
  this and `task` coincide there.
- **`story`** — every rule belonging to one user story (`[US<n>]` on the tasks), each its own
  RED-GREEN-REFACTOR cycle in one context. This is the boundary that stops each fresh delegate re-reading the
  same plan, map, precedent and test file per rule — which was most of a slice's implementation wall where it
  was measured — while moving nothing else: the increment stays the rule, stub-first, each example failing for
  its own reason. Under it the concurrent siblings are stories whose manifests are disjoint, and inside each
  the rules run in sequence.

The default is `story` where the map is rule-owned and the tasks carry story tags, and `task` where either is
missing — a veto, not a preference, because a story boundary over a map with no agreed rule boundary has
nothing to cut on. Whichever boundary, the licence inside it is the one `agents/drive-implement.md` writes in
full — how a rule's examples may be batched, when the delegate may fan out — never a silence the delegate reads
conservatively. The delegate reports which boundary it was given, whether it batched a rule's examples, and
whether it fanned out and into how many groups; this session passes the boundary and the fan-out to the record
as `arm=<boundary>` and `split=N` on the implement entry, because two runs of one boundary that differ in
either are different experiments wearing one name, and a wall time without them means nothing.

### Running an experiment on the method

`{EXPERIMENT}`, where it exists, declares one experiment on how this project runs its own method, and this
ladder reads it before every implementation stage. Its shape, in this order:

- a **name** and a **hypothesis**: what is expected to move, and which way;
- the **arms**, each a heading that names **one** variable it moves and states in full every licence a
  delegate has under it — a permission that appears in one arm's text only is either genuinely one-sided or
  merely unrepeated, and a fresh delegate reads the silence conservatively, which is the expensive reading.
  An arm that moves two variables is refused at the point it is written: its result cannot be attributed;
- **what does not change between arms** — the constitution, the gates, the stops, the evidence every stage
  produces — written out, so the experiment measures the change and not a lowered bar;
- the **control arm**, the **default arm**, and the **stop condition**: how many slices per arm, or which
  quality signal settles it.

**Ask on every slice, and say what the record says.** Run `python3 scripts/agents/benchmark.py arms`, which
reads every slice's implement entries and prints, per arm, how many slices ran it, the last one, and how many
slices ago. Then ask which arm this slice runs, offering the slice's own previous answer where it has one and
the default otherwise, and saying out loud any arm that has not run for longer than the stop condition
needs: a default nobody deliberately assigns fills the corpus with one arm while the comparison starves, and
nothing else announces it. On the **first** delegation under an arm, read its text the way the delegate will
— alone — and write out any licence it inherits rather than states, before delegating. Record the answer as
`arm=<key>` on every implement entry of the slice, so a slice that ran as two arms shows both rather than one.

**A switch, not a revert.** Answering the control arm stops the experiment: no code changes, and the record
of what was tried stays. Removing it is deleting `{EXPERIMENT}`, which nothing else references. Never offer
`git revert` as the undo — it stopped being one the moment the next commit touched the same file.

**The comparable figure is wall time per rule proved, at equal quality** — converge findings, adversary
findings and the mutation score read beside it — never the delegation count, which every arm defines
differently by construction. `{layout.make} benchmark` prints each slice's arm beside its numbers and says
when an arm has gone unrun; two slices in two arms are two anecdotes with a hypothesis attached, and the stop
condition is what says how many it takes to be more.
"""
