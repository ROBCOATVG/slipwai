# The workflow, end to end

**This page lists every step from a requirements document to an accepted capability.** For each step it
says who does the step, what starts it, what file it writes, and whether it stops for a person. The other
guide pages teach the steps one at a time. Use this page to see the whole route on one page.

The words *fairway*, *captain*, *harbourmaster*, *mark* and *park* are defined in
[the vocabulary](../../GLOSSARY.md). The board shows a fairway as a **stream**. Both words mean the same
thing.

---

## The route

The board's **Voyage** window shows the same steps as a strip of stages. A stage is *done* when the file in
the "Writes" column exists. Nobody types a status. [The board](the-board.md) describes each control.

| # | Step | Who does it | What starts it | Writes | Stops for a person? |
|---|---|---|---|---|---|
| 1 | Requirements | You | `slipwai generate --prd <file>`, or the brief field on the board's form | `docs/prd.md` | No |
| 2 | Init | `./init` | The interview, when it ends | `.specify/integration.json` | No |
| 3 | Constitution | The agent, in a headless session | `/draft`, or `/speckit-constitution` | `.specify/memory/constitution.md` | No. Read it afterwards |
| 4 | Specification | The agent, in the same draft | `/draft`, or `/sail` with the next feature | `specs/<feature>/spec.md` | Yes, by default. See [the upstream setting](#the-upstream-setting) |
| 5 | Storyboard | The agent draws. You give the verdict | **Draw the surfaces** (`make surfaces`), or `/mockups` | `specs/<feature>/mockups/*.html`, then `mock-states.md` | Yes, by default |
| 6 | Event model | The agent, on the event-modelling profile only | Approving the storyboard (`make model-next`), or the modelling skill | `docs/event-model/model.yaml` | Yes, by default |
| 7 | Chart and split | The agent, in a headless session | **Continue the build** (`make launch`), or `/launch` | `specs/<feature>/chart.yaml` and the slices | No |
| 8 | Slices | The fleet: one captain per fairway, and one harbourmaster per machine | `/launch` casts off. **Cast off the fleet** (`make cruise`), or `/cruise` | Deck logs and the harbour log | Only when a captain parks |
| 9 | Accepted | You, as the actor | A demo, when a capability's last slice merges | An `accepted` line | Yes, at every demo |

On the standard profile, step 6 is skipped. The chart comes from the specification instead, and approving
the storyboard starts step 7.

---

## Steps 1 to 4: from a document to a specification

1. Give `slipwai generate` a requirements document. It copies the document in as `docs/prd.md`.
2. The interview runs `./init` when it ends. `./init` installs Spec Kit for your coding agent. It reaches
   the network once, here.
3. Type `/draft`, which runs `make draft`. The board runs it for you when the project starts from a
   document. One headless session writes the constitution and the first specification. The specification
   lists every decision that the document did not settle under `## Assumptions`.
4. Read the specification. On the board, press **Open specs/&lt;feature&gt;/spec.md**.

A further feature goes to `/sail`. `/sail` writes a record under `docs/intake/` and asks whether the idea
is really a new feature. Spec Kit then assesses it. A specification is written only after a yes and a go.
On the board, the **Next features** card has the button **Continue the next feature** for the earliest
idea that is waiting.

## Step 5: the storyboard

1. Press **Draw the surfaces**. The board runs `make surfaces`. A headless session researches each screen,
   draws a wireframe for each one, and writes a storyboard page that links them.
2. Open the storyboard and read every state of every screen.
3. Give one verdict for the whole storyboard:
   - **Approve storyboard** marks every drawn state `approved` in `mock-states.md`.
   - **Disapprove** marks every drawn state `parked:` with your reason. A reason is required. Without one,
     the next drawing cannot know what to change.

Approving starts the next step at once. On the event-modelling profile the board runs `make model-next`. On
the standard profile it runs `make launch`. Disapproving starts nothing. The storyboard waits until the
mock-up stage draws it again (`/mockups` in the agent).

Both buttons lock when the storyboard has a verdict. To change a verdict, edit `mock-states.md`.

This stop exists for a reason. A screen that nobody saw becomes a read model, a route and a set of tests.
All three cost more to change than a drawing.

## Step 6: the event model

On the event-modelling profile, the model comes next. `make model-next` writes the model from the approved
storyboard. You can also model in the agent with the modelling skill. The model is
`docs/event-model/model.yaml`. `make model` renders it, and the board shows it in draw.io's viewer.

## Step 7: the chart and the split

Press **Continue the build**. The board runs `make launch`. One headless session writes the chart and
splits the feature into slices. The chart names the fairways, the marks each slice sets, and the marks
each slice steers by. Then `make launch` casts off the fleet.

**Continue the build means "this specification is good to build from".** Read the specification before
you press it.

## Step 8: the fleet works the slices

The fleet has two kinds of process:

- **A captain** works one fairway. At each turn it reads the logs, takes the next slice that clearance
  allows, writes `claimed`, and runs `/sail` in its berth. A captain holds no credential and never merges.
- **The harbourmaster** is one process per machine. It copies marks between fairways, allocates berths,
  answers a captain's requests, and performs each merge after the full gate passes on trunk.

The speed is set by [the telegraph](let-it-cruise.md#the-telegraph-one-lever-for-the-whole-run).

### When a captain ends a stage

A captain watches the log, not the agent. It ends a stage that shows no progress for the stage bound. The
stage bound is the longest stage budget in `harbour.json`.

Two things count as progress:

- a new line in the fairway's deck log;
- a new commit on the slice's branch, `slice/<id>`.

The commit counts because the implement rung commits one example at a time and writes no deck line until
its mark. Before this rule, a slice that committed fourteen times in ninety minutes was ended as "no
progress".

### When a captain parks

A **park** is a `parked` line in a deck log. It means that the fairway stopped and needs a person. The
board shows every open park under **Waiting on you**, with how long it has waited.

- **One park per stop.** When the agent parks its own stage, the captain keeps that park and its reason.
  It does not add a second park on top.
- **A parked fairway is not restarted.** The harbourmaster does not light a captain for a fairway that has
  an open park. A captain started there would read the park and exit at once.

### How to clear a park

Tell the fairway something. Use one of these:

- the answer box under **Waiting on you**, or **Say something to a stream**, on the board;
- `/cruise-tell <fairway> <the answer>` in the agent.

Each writes a `told` line in the fairway's deck log. On its next pass, the harbourmaster writes a
`cleared` receipt in the harbour log for every open park that the message came after. The receipt keeps
your message as the answer. On the pass after that, the harbourmaster lights the captain again.

A project generated before this change has older copies of `scripts/agents/`. In that project a message
does not clear a park. Upgrade the project with `slipwai migrate`.

## Step 9: the demo and acceptance

When the last slice of a capability merges and its gates pass, the capability is demoed to you as the
actor. Accept it, or say no with notes. The notes go back into the slice. The release mode decides what a
merge means before that demo: see [release modes](../reference/release-modes.md).

---

## The upstream setting

Steps 4, 5 and 6 each end at a stop for a person, by default. The setting `upstream` in
`.specify/cruise.json` controls these three stops.

| Value | What happens |
|---|---|
| `park` (the default) | Each step stops. You press the next step's button, or approve the storyboard |
| `advance` | Each step starts the next one when it ends well. The board draws the storyboard, approves it, models it on an event-modelling project, and continues the build |

**Set it on the board.** Open **Settings**, then the **Who answers** tab. Find the row *The specification,
storyboard and model*. Press **stop for me at each** or **advance on their own**.

**Or set it in the agent:**

```text
/cruise-settings upstream=advance
/cruise-settings upstream=park
```

Read these limits before you set `advance`:

- **A step that failed stops the advance.** What a failed step made is not safe to build on without a
  person.
- **A disapproved storyboard stops the advance.** A disapproval is a person's no.
- **Anything that the board is already running stops the advance** until it ends.
- **The board advances only while a board window is open.** It advances when a window polls it, and every
  open window polls every few seconds. With no window open, nothing advances.
- **An approval that the board gives says so.** The first line of `mock-states.md` is a comment that names
  the setting. You can tell it apart from your own verdict. The board's buttons lock once there is a
  verdict, so to replace it with your own, edit `mock-states.md`.

A project whose `.specify/cruise.json` has no `upstream` key reads it as `park`. Its own `make check-agents`
still passes. Setting the value writes the key into the file.

---

## What still stops for a person

These stops apply whatever `upstream` says:

1. **The demo.** You accept each capability as the actor.
2. **A park.** A captain parks when it needs a person, and the fairway waits until you tell it something.
3. **The decision ceiling.** When a fairway takes `decision_ceiling` decisions that nobody has read, it
   parks itself.

The other stops of a run — a product question, an unratified constitution, a block and a release — are on
the same **Who answers** tab. [Let it cruise](let-it-cruise.md) explains them.

## Next

→ **[The board](the-board.md)** — every screen and every control, and the file each one writes.

Other pages: [start here](start-here.md) · [your first feature](first-feature.md) ·
[let it cruise](let-it-cruise.md) · [the vocabulary](../../GLOSSARY.md)
