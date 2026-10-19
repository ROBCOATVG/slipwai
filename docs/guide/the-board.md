# The board

**The board is a web page that runs on your own machine.** Use it to start a project, watch a run, and
answer the fleet. This page describes every screen and every control, and says which file each control
writes.

Every control on the board runs a `make` target or a project script that you can also run in a terminal.
The board does not keep a second copy of anything. It reads the project's files and logs again on every
request.

---

## Open the board

| Command | What it does |
|---|---|
| `slipwai` | Opens the board in your browser. It starts the board first if nothing is serving it |
| `slipwai bridge --serve` | Serves the board at `http://127.0.0.1:8099`. `--port` and `--root <directory>` change the port and the directory |
| `slipwai bridge install` | Keeps the board running as a login service for your own account. No root access is needed |
| `slipwai bridge uninstall` | Removes that login service |
| `slipwai bridge --publish <file>` | Writes a read-only copy of the live cards to one HTML file. The copy has no controls |

The board binds the loopback address, `127.0.0.1`, by default. Other machines cannot reach it. Use `--host`
only if you want other machines to reach the controls.

**Each window has its own seat.** A seat is an id in the window's address, `?seat=<id>`. The seat decides
which directory that window looks at. Two windows can look at two projects at the same time. A generate in
one window moves that window only.

The button **Install this board** appears when your browser offers to install the page as an app. The theme
toggle is remembered in your browser.

---

## The tabs

The board has four tabs. The Voyage is a separate window, so that you can leave it open.

### Board

- **Looking at** — the directory that this window looks at. Type another directory and press **Look
  here** to move this window. Nothing restarts.
- **The project card** — the project's name and one sentence about where it stands. **Open the voyage ↗**
  opens the Voyage for this project in a new window.
- **Start something** — links to the next two tabs, with the command that does the same job.

### Start a project

This is the `slipwai generate` interview as a form. The questions come in the same order and offer the
same answers.

- A quickstart fills in the questions below it. You can still change every answer.
- **Dev tooling** has one checkbox for each extension installed on this machine.
- A folder field has a button that opens your machine's own folder chooser.
- **Generate** makes the project. The window then moves to the new project and runs `./init` there. When
  you gave a requirements document, the board then runs `make draft`. The card **Made &lt;name&gt;** shows
  what `./init` and `make draft` print while they run.

### Adopt a repository

This installs the method around code that already exists.

1. Type the repository's directory, and where the method's files go (default `delivery`).
2. Press **Look**. The board reads the repository and shows what it found. Nothing is written yet.
3. Read **What would be written**: the new files, and your files that get text added between markers.
4. Press **Adopt &lt;name&gt;** to write them.

### Packages

This is the chandlery, the index of packages that slipwai can install. Each row shows a package and its
state. **Install** installs it in the same way as `slipwai install`. A package from a publisher you have not
trusted yet has a checkbox **accept &lt;publisher&gt;**. Tick it to trust that publisher. An installed
package that has a newer version says so.

---

## The Voyage window

The Voyage shows where one project stands and how its run is going. Its title is
*Voyage · &lt;project&gt;*. It updates itself: it asks the board for news every 2.5 seconds while a stage is
working, and every 8 seconds when nothing is working. When the project gains a new kind of file, such as a
first storyboard, the window reloads itself.

The cards come in this order, from the top.

### The stage strip

The strip shows the stages in order: **PRD**, **Init**, **Constitution**, **Specification**,
**Storyboard**, **Event model**, **Chart & split**, **Slices** and **Accepted**. Each stage shows its state,
a short detail, and the file that proves it.

| State | Meaning |
|---|---|
| ✓ done | The stage's file exists |
| ● working | The board's own child process, or the fleet, is doing this stage now |
| ! waiting on you | The stage needs a person. Its title links to the card that needs you |
| to do | Not started |
| faint | Skipped. The stage is not on this profile, for example the event model on the standard profile |

The sentence under the strip says what the project is doing now and what moves it on. Beside it are the
buttons for the next step. Each button appears only when it can be pressed.

| Button | Runs | Appears when |
|---|---|---|
| **Draw the surfaces** | `make surfaces` | There is a specification, nothing is drawn yet, and the board is not running anything |
| **Continue the build** | `make launch` | The active feature has a specification and no chart. On the event-modelling profile it needs a model too. Nothing on the board is running or failed |
| **Cast off the fleet** | `make cruise` | There are slices to work, the fleet is not running, and the board is not running anything |
| **Stop the fleet** | `make cruise-stop` | Part of the fleet is running. It asks each captain to stop. The captain ends the stage it is running, writes a `stopped` line naming its slice, and gives its claim back. The slice is carried on when the fleet is cast off again |
| **Open specs/&lt;feature&gt;/spec.md** | Nothing. It opens the specification, rendered, in a new tab | There is a specification |

On the event-modelling profile, before there is a model, the chip *Model it next* replaces **Continue the
build**.

### Next features

This card appears when an idea under `docs/intake/` is not yet specified or killed. **Continue the next
feature** moves the earliest one:

- An idea that waits for confirmation: the board writes `docs/intake/<slug>/confirmed`.
- An idea that waits for assessment: the board runs `make assess`.

### What to expect

This card says what the current stage does, roughly how long it takes, and whether it stops for a person. A
stage that waits for you by design looks the same as a stage that has hung. This card tells you which one it
is.

### Made &lt;name&gt;

This card shows what the board's own child process prints: `./init`, `make draft`, `make surfaces`,
`make model-next` or `make launch`. The chip shows *running*, *done* or *stopped*, and a clock.

### The model

On the event-modelling profile, this card shows `docs/event-model/model.drawio` in draw.io's viewer. Each
slice is coloured by where it stands. The viewer is read-only.

- Drag to pan. Use the mouse wheel to zoom.
- The buttons nudge left, right, up and down, zoom out and in, reset to actual size (**1:1**), fit the whole
  model (**Fit**), and open it full screen (**⤢**).
- The arrow keys, `+`, `-`, `0` and `f` do the same when the canvas has focus.

The board fetches the viewer once from `viewer.diagrams.net` and keeps it. Where that fails, open
`docs/event-model/model.drawio` in draw.io.

### Built screens

This card appears when the design review has photographed screens. For each feature it shows the mock-ups
that were **Intended** beside the screens that were **Built**. **Open the running app** opens the app, when
the project records where it runs.

### Storyboard

This card appears when the mock-up stage has drawn something. It shows the storyboard, or each mock-up
when there is no storyboard. Each tile opens the page at full size in a new tab.

Under it is the verdict form:

| Control | Writes |
|---|---|
| **Approve storyboard** | `specs/<feature>/mockups/mock-states.md`, with every drawn state `approved`. Then the board starts the next step: `make model-next` on the event-modelling profile, `make launch` on the standard profile |
| **Disapprove**, with a reason in the box | The same file, with every drawn state `parked:` and your reason. A reason is required. Nothing else starts |

Both buttons lock when the storyboard has a verdict. To change a verdict, edit `mock-states.md`.

### The work

The slices, in four columns: **To do**, **Working**, **Waiting on you** and **Done**. Each slice shows its
fairway and what clearance says about it.

### Waiting on you

Every open park, and every message to a fairway that its captain has not read yet. A park shows how long it
has waited, and whether it is past the wait bound.

Click a row to open it. It shows the last 20 lines from that fairway's deck log, and an answer box. Type an
answer and press **Send**. The board writes a `told` line into that fairway's deck log. The captain reads it
at its next boundary. A `told` that comes after a park also clears that park: the harbourmaster writes the
`cleared` receipt on its next pass and then lights the captain again. [The workflow](the-workflow.md#how-to-clear-a-park)
says more.

### Say something to a stream

One answer box for each fairway that has written a line. **Send** writes a `told` line in the same way.

### Streams

One row for each fairway: **Stream**, **Feature**, **Piece of work** (the slice), **State**, **Waiting**,
**Last line**, **Tokens** and **Merged**. Click a row to open that captain's whole log.

| State | Meaning |
|---|---|
| running | The captain is working, and its log is still moving |
| stalled | The log has had no new line for longer than the stall bound. Look at this one |
| waiting on you | The fairway is parked |
| done | Its last slice merged, and no slice of it waits |
| idle | Its last slice merged, and its next slice waits on clearance |
| not started | The fairway's log has no line yet |
| clearance unavailable | Its last slice merged, and the board could not read clearance to say what is next |

### Settings

One box with a tab for each settings file that the project has. A tab for a file that the project does not
have is not shown.

| Tab | What it sets | Writes |
|---|---|---|
| **Speed** | The telegraph: **Full ahead**, **Half ahead**, **Slow ahead**, **Dead slow** or **Stop**. One press sets every number under Fine tune together. The table shows what each position sets | `harbour.json` |
| **Fine tune** | Each number of the telegraph by itself. Change the numbers, then press **Apply** | `harbour.json` |
| **Who answers** | Who answers at each stop of the run. See below | `.specify/cruise.json`, through `scripts/agents/cruise.py --set` |
| **Delegation** | What one implementation delegate is handed (one user story, one rule or one task), and what one RED cycle opens with (a rule's examples together, or one example) | `.specify/sail.json`, through `scripts/agents/sail.py --set` |
| **Models** | Which role, and so which model, runs each stage of the ladder | `.specify/models.json`, through `scripts/agents/models.py --set` |

A captain reads each of these files at its next boundary. A change applies to the next stage, not to the
stage that is running now.

**The Who answers tab** has one row for each stop:

| Row | Values |
|---|---|
| A product question | the stage's recommendation, or the skipper · the skipper, every time |
| An unratified constitution | the skipper drafts and ratifies it · park and ask me |
| A block | the bosun works around it · park and ask me |
| A release | continue behind a flag, so every merge is dark · park and ask me |
| The specification, storyboard and model | stop for me at each · advance on their own |

The value that stops for a person is drawn amber. The line above the rows names every stop where this run
will stop for you.

The last row is the `upstream` setting. **advance on their own** makes the board start each upstream step
when the step before it ends well. [The workflow](the-workflow.md#the-upstream-setting) lists its limits.

### Last lines

The newest lines from every log, newest at the bottom.

---

## What the board does by itself

The board starts something without a button press in two cases only:

1. **After Generate.** It runs `./init`, and `make draft` when the project starts from a requirements
   document.
2. **When `upstream` is `advance`.** Each time a window polls, the board checks whether the step before
   ended well and nothing is running. If so, it presses the next upstream button: draw, approve, or continue
   the build. Only one window presses at a time.

Everything else waits for a person.

---

## The board as data

`http://127.0.0.1:8099/board.json` returns the fold of the logs as JSON: the streams, the inbox, the speed
and the feed. Use it from a script.

## Next

→ **[The workflow](the-workflow.md)** — every step, who does it, and where it stops.

Other pages: [start here](start-here.md) · [your first feature](first-feature.md) ·
[let it cruise](let-it-cruise.md) · [the vocabulary](../../GLOSSARY.md)
