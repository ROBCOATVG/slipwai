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

Beside them, **Tell me when it waits on me** asks your browser, once, to let the board notify you. From then
on a wait that begins while you are in another window — a storyboard to approve, a question on a card, a
brief ready to hand over — is a notification; click it and the window comes to the front at the thing that
waits. It is off until you press it, and your browser remembers the answer.

---

## The tabs

The board has six tabs. The three in the middle are the three ways in, in the order a person arrives: with an
idea, with a document, with a codebase. The Voyage is a separate window, so that you can leave it open.

### Board

- **Looking at** — the directory that this window looks at. Type another directory and press **Look
  here** to move this window. Nothing restarts.
- **The project card** — the project's name and one sentence about where it stands. **Open the voyage ↗**
  opens the Voyage for this project in a new window.
- **Start something** — links to the next two tabs, with the command that does the same job.

### Start from an idea

This is for a person who has no document. Type what the product does. The agent draws a prototype that you
can click through on the same page, writes the brief beside it, and asks only what it cannot work out. The
header shows the four steps: describe, walk the states, check, hand over.

- **The brief, as the start page will read it** counts what the brief has settled and what the build will
  have to assume. Green lines need no question. Amber lines are what the draft will decide and say it did.
- **Read the brief as a document** opens the requirements document, the people or the facts as a page.
- **Hand over** appears once the brief has a document, and is marked when the agent says the brief is
  ready. It opens the next tab with the brief's answers filled in: a confirm page that shows what the brief
  settled, with every extension on this machine ticked. **Make it** makes the project. **Change something**
  opens the whole form.
- **New conversation** starts the sketch again. A sketch keeps its conversation, so a window opened later
  shows the same turns.

### Start from a PRD

This is the `slipwai generate` interview as a form. The questions come in the same order and offer the
same answers.

- A quickstart fills in the questions below it. You can still change every answer.
- **Dev tooling** has one checkbox for each extension installed on this machine.
- A folder field has a button that opens your machine's own folder chooser.
- **Generate** makes the project. The window then moves to the new project and runs `./init` there. When
  you gave a requirements document, the board then runs `make draft`. The card **Made &lt;name&gt;** shows
  what `./init` and `make draft` print while they run.

### Start from a codebase

This installs the method around code that already exists.

1. Type the repository's directory, and where the method's files go (default `adopt`).
2. Press **Look**. The board reads the repository and shows what it found. Nothing is written yet.
3. Read **What would be written**: the new files, and your files that get text added between markers.
4. Press **Adopt &lt;name&gt;** to write them.

### Packages

This is the chandlery, the index of packages that slipwai can install. Each row shows a package and its
state. **Install** installs it in the same way as `slipwai install`. A package from a publisher you have not
trusted yet has a checkbox **accept &lt;publisher&gt;**. Tick it to trust that publisher. An installed
package that has a newer version says so.

### Settings

This names the coding agent that runs the board's conversations, over the Agent Client Protocol: the brief,
the stages a project runs from the board, and the question box on the Voyage. **Runs on** lists every agent
this machine can launch, with where each was found or what is missing. *Auto* takes the first that is ready,
else the first found. Beside it, the model, where the agent offered a choice. Under each agent: **Make
ready**, which does the handshake once and shows what the agent said of itself, **Sign in** for each way
the agent offers, and **Install** where the agent is not on this machine. The answers are saved to
`~/.slipwai/board.json`. A project's own `./init` answer still wins for its question box.

---

## The Voyage window

The Voyage shows where one project stands and how its run is going. Its title is
*Voyage · &lt;project&gt;*. It updates itself: one request every 2.5 seconds (8 while the window is hidden)
brings every part of the page that can change, and only the parts that changed are redrawn. A card you have
opened stays open, and a part you are typing in is left alone until you send or clear it. The board reads the
project once for every window and keeps that read for about two seconds; anything you press drops it, so the
next update shows what you did. When the project gains a new kind of file, such as a first storyboard, the
window reloads itself.

When something waits on you, a strip appears under the title: *Waiting on you · 3*, with how many hold work
up and how many can wait until you have time. **Show all** opens both lists; each item links to where you act
on it. **Holding work up** is a slice parked on you, a card a running stage has put up (*The agent asks you
something*), the one button the run waits on (*The specification is ready: read it, then draw the
storyboard*), and a stream log nobody can read. **When you have time** is a capability ready for you to see,
and a feedback proposal waiting for **Confirm**. A note nobody has read and a slice paused until a set time
are not counted. The same number goes on the Work tab, on the tab's title, *(3) Voyage · …*, and on the
installed board's badge, and the **Waiting on you** column holds exactly the slices this list names. The first
page shows a one-line strip when a card asks you something, and when the brief is ready to hand over.

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
| **Draw the storyboard** | `make surfaces` | There is a specification, nothing is drawn yet, and the board is not running anything |
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

### Needs a look

At the top of the Work tab. It lists only what is wrong: a red trunk, then each slice stuck on one task, going
in circles or gone quiet, and each merge the harbour refused, with a link to the slice's card. When nothing is
wrong it is one line, *5 working · nothing needs a look*.

### The captains

Above the tabs, one button for each stream: *Captain · game-nights*, with what its slices are doing — *2 at
work · 1 queued · 1 waiting on you* — and **new** when its captain has said something you have not seen. It
opens that captain's window (below). Beside them:

- **Tell every captain** — one message, placed in each captain's inbox. Each captain works out which of its
  own slices it is for. Under the box, a line for each captain says where its copy stands and, once the
  captain has sent it on, which slices it went to.
- **Ask about this project** opens the console. It reads the run's logs and answers; it never changes
  anything. Something you want done, you say to a captain or a slice.

### The work

The slices, in columns: **To do**, **Queued**, **Working**, **Waiting on you** and **Done**. Click a card to
open it: its steps, what it is doing now, and the box that answers it when it waits on you. **Cards** and
**Compact** switch the view; Compact is one line for each slice in flight, waiting first, and a line opens its
card. Your choice is remembered in this browser.

A card whose conversation has something you have not seen carries **New ·** and the last thing said. Opened,
a slice in flight shows the last message with its receipt, a one-line box that sends after its current turn,
a product question waiting on you with a box to answer it, and **Open its window**.

### From the streams

Under the work: what each stream has asked of you or left for you. Each park is grouped by what it waits on,
with its needs as a checklist and the button that answers it; then questions no park holds, hand-backs, notes
and decisions nobody has read. Click a row to open it, with that fairway's last lines and an answer box. Type an
answer and press **Send**: the board places it as a message in the inbox of the slice the row is about — the
slice a park's reason names, even where the park's own record names none — or of the stream's captain where it
is about the whole stream. Nothing is written to the deck log. A person's message to a parked slice is the
answer to its park: when the stream's captain next runs, it writes the `told` that the harbourmaster clears the
park on, and it records the answer as the decision when it carries the slice on.
[The workflow](the-workflow.md#how-to-clear-a-park) says more. A note also has **Done**, which writes a `read`
line so it leaves the list.

Once you have answered, the row shows your answer in place of the box, when you sent it and where it stands:
*sent · the captain reads it at its next turn*, *sent · the fleet is not running: read when it is cast off*,
*read by the captain*, *delivered*. While nothing has read it, **Change my answer** takes it back and sends
the new one instead. A message for a whole stream is read by its captain only where the project's `scripts/agents/` has a captain that reads its own inbox; until `slipwai migrate` brings that, it stays *sent* and nothing reads it, so answer a park from its slice's card.

Where a session limit has paused slices, **Try the N paused slices now anyway** asks each of them to resume.
**Talk to a stream's captain** links to each stream's captain window.

### A slice's window

**Open its window** on a card opens one slice in a window of its own: **Where it is** and **Example map** as
tabs, and beside them its conversation.

- What you said is on the right with its receipt beneath it: *Queued · goes in when its current turn ends*,
  *Held: this slice is at its merge*, *Delivered 11:47*, *Answered* with the reply under it, *Delivered, not
  addressed*, or *Not delivered* with why and **Send again**. A queued message has **Interrupt now** and
  **Withdraw**. A message a captain sent on says *You, through the game-nights captain*.
- What the slice asked is a card. Where `.specify/cruise.json` says the skipper answers product questions
  (cruising, with `decide: recommended-first` or `skipper-always`), nothing waits on you and the skipper's
  answer is shown. Anywhere else a product question is also an item under *Holding work up*, answered from
  the card or from the window.
- **Send** waits for the turn under way to end. **Interrupt** cancels the turn and delivers at once; a slice in
  print mode has no Interrupt, and the box says why.
- **Pause**: the turn finishes, the session is kept and the slot is given back. **Resume** carries on in the
  same session. **Stop**: the session ends now and the slice goes back to the queue; its commits stay on its
  branch and uncommitted edits in its berth. A stop you make holds the slice until you resume it, and it then
  starts in a fresh session. A slice you paused is listed under *When you have time*; one its captain paused
  is not.

The window marks what it has shown you as seen, in `.slipwai/run/board/seen.json`, for the project rather than
for one browser.

### A captain's window

A captain button opens one stream's captain: its slices in flight, each opening that slice's window; what it
decided today, read from its orders and from the events its fixed rule closed; and its conversation, with the
same receipts and, beside each message, the slices it went to. Where the stream's captain is the program alone,
the window says so and still lists the slices.

### Fleet

The Fleet tab is the machinery: **Sessions** in use against the slots, and which slice takes the next one;
**Tokens today** against the budget a day; **Trunk**, green or red with why; and one row per process (the
harbourmaster and each captain) with its state and its last line. **Open log ↗** on a captain's row opens that
captain's own window, described below. **Stop the fleet** and the settings are here too.

### The captain log window

**Open log ↗** on a captain's row in the Fleet tab opens one captain in a window of its own, titled with its fairway. It reads
the files again every 2.5 seconds; **Following** pauses and resumes that.

- **Timeline** shows every line in the fairway's deck log, with the lines in the harbour log that name the
  fairway, in time order and grouped by slice. A merge request sits beside its `granted` or `refused`
  answer, and the answer shows where the time went: queued, waiting on the merge ref, and the gate, with the
  attempt. Filter by slice or by text, show the heartbeats, or show only the harbour's answers. **raw** shows
  a line exactly as it was written.
- **Captain output** shows what the captain process printed, from `.slipwai/run/running/captain-<fairway>.out`:
  its own lines and each turn's closing message. It opens on the last 64 KB.
- **Needs you** lists this fairway's open parks, unread messages and open questions, and **Tell this
  captain** places a message in its captain's inbox; where it stands is in the captain's own window. The
  caveat under *From the streams* holds for it too.

The published copy has no captain window, because it has no server to read from.

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
| A capability's demo | the hand's verdict accepts it; the film is there when I have time · wait for me to accept it |

The value that stops for a person is drawn amber. The line above the rows names every stop where this run
will stop for you.

**A capability's demo** is the `demos` setting. With **the hand's verdict accepts it**, the default, the
hand's verdict is the acceptance. The capability's slices are done, and nothing waits for you. The hand's
film shows on the Voyage tab with **Say what it showed**, which opens the Feedback box with the capability
on it. With **wait for me to accept it**, the Feedback card lists each capability that is ready for you,
with **Accept** and **Not yet: say why**, and the film says *Ready for you*.

The last row is the `upstream` setting. **advance on their own** makes the board start each upstream step
when the step before it ends well. [The workflow](the-workflow.md#the-upstream-setting) lists its limits.

---

## What the board does by itself

The board starts something without a button press in three cases only:

1. **After Generate.** It runs `./init`, and `make draft` when the project starts from a requirements
   document.
   A project with a document and no specification is drafted the moment the board sees it, once: nobody
   holds a draft off. A draft that drafts nothing leaves **Draft the specification**, which runs it again.
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
