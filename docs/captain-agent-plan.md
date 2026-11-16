# The live board, talking to the fleet, and the captain as an agent

Decided with the owner on 2026-11-16, one question at a time. This is the record of those decisions, the
contracts the parts share, and the streams the work is built in. Measured evidence for the synchronisation
work that is *not* in this build is in issue #93.

A clickable prototype of the board this describes was reviewed and agreed. Its markup is the reference for
layout and wording, not for code: `Board.dc.html` on the owner's design canvas.

## 1. What was decided

### The board
1. **One shared poll.** A single request every 2–3 seconds returns every band that changed; the server reads
   the run once and keeps that read for about 2 seconds, shared by every poll, and drops it on any action a
   person takes. Not push. Bands that are frozen today (the Fleet tab, the Decisions count, the feedback
   points, "What to expect") move with the rest.
2. **One "Waiting on you" list**, read by the strip, the tab badge and the column. It counts five things in
   two groups. *Holding work up*: a slice parked on a question for a person; a stage ask; a pending button
   the run cannot pass without. *When you have time*: a capability with something to look at; a feedback
   proposal waiting for Confirm. A message nobody has read and a slice paused until a set time are **not**
   counted.
3. **One job per place.** The slice card is the home of where a slice is and what it is doing. The Now strip
   becomes *Needs a look*: only slices with a warning (stuck on a task, going in circles, gone quiet, a
   refused merge) and a red trunk, each saying what its captain already did about it; one line when nothing
   is wrong. "The work" has a Cards / Compact switch, Compact being one line a slice. The Fleet tab is the
   machinery only: session slots, tokens against budget, trunk, a row per process.
4. **Example map.** Every slice with an `examples.md` has an *Example map* tab in its window, drawn from the
   file: the story (yellow), a column per rule (blue), its examples under it (green, each opening on its
   Given / When / Then, ticked once `tasks.md`'s `## Examples proven` names the test that proves it), and
   the questions (red while open, faded once the line says what answered them). The card's Examples step
   carries the counts. Read-only: the file is changed by saying so to the slice.
5. **Demos.** A demo is of a capability, filmed once (built: `film.py`, `try_it.py film`). With the default
   setting nobody is asked to accept one: the hand's verdict is the acceptance, the capability's slices
   are done, and the film is an opportunity to say what it showed. Accept / Not yet is shown only where the
   project's setting says a person accepts demos.

### Talking to the fleet
6. **The Agent Client Protocol is the default for fleet sessions**, where the configured harness offers it;
   the headless print-mode path stays for the rest, and every feature below has its lesser form there.
7. **The slice's driver is held open** while a slice is being worked: one session, many prompts. It closes
   with the session's id saved while the slice waits (a park, a pause, a stop, an overnight stop) and loads
   that session when it carries on, falling back to a fresh session where the agent cannot load one.
   Review-type stages keep a fresh session. An idle driver holds no session slot.
8. **Every conversation with a slice goes through its driver.** The board never writes a stream's deck log
   again. What a person says is dropped in the slice's inbox; the driver delivers it and writes the receipt.
   The instruction to a session to "check your inbox between stages" goes.
9. **A person chooses per message**: *Send* waits for the current turn to end, *Interrupt* cancels the turn
   and delivers at once. Send is the default. On the headless path there is no Interrupt and delivery is at
   the next dispatch.
10. **Receipts.** *Queued* (may be withdrawn), *Delivered* at an instant the driver records, *Answered* with
    the reply beneath it, *Not delivered* with why and Send again. A turn that ends without a word after a
    delivery is *delivered, not addressed*: a quiet flag in the conversation, never "Waiting on you".
11. **Interrupt, Pause, Stop on every slice in flight.** Pause: the current turn finishes, the session is
    kept, the slot is given back. Stop: the session ends now, the slice goes back to the queue with why;
    commits stay on its branch and uncommitted edits stay in its berth. A slice a person paused is listed
    under *When you have time*; one its captain paused is not.
12. **What an agent asks mid-turn.** A permission inside its berth is allowed. One outside it goes to the
    slice's captain, which allows what the rules allow and refuses the rest, saying why; nothing here waits
    on a person. An operational question the captain answers. A product question follows the project's
    *who answers* setting: **the skipper by default, and nothing blocks**; only where the setting says a
    person answers does it become a card under *Waiting on you*, the turn held five minutes for a quick
    answer before the slice pauses.
13. **Where conversations live.** Each in a window of its own: a slice's (where it is, example map,
    conversation) and a captain's (its slices, what it decided today, conversation). The board carries a
    marker and the last thing said on a card, and a one-line quick send in the opened card. Captains are
    opened from a strip on the board under *Waiting on you*, one button a stream with its state. Beside
    them: **Tell every captain** (one message, each captain routes it and reports back) and **Ask about
    this project**.
14. **"Ask about this project" answers and never acts.** It is not "the harbourmaster" in any wording a
    person reads. Something a person wants done goes to a captain or a slice.

### The captain
15. **The captain becomes an agent, one per stream, and the program stays underneath it.** The agent chooses;
    the program checks and does. Clearance, session slots, stage budgets, the retry ceiling, the gate, merge
    requests, the ceiling on unreviewed decisions and being the one writer of the stream's log stay the
    program's. No switch: this is how a fleet runs.
16. **Four decisions are the agent's**, each a fixed rule today: which cleared slice starts next; after a
    failed gate, retry with what note or park with what reason; where something a person told the stream
    goes; what to do about a stuck slice (nudge, interrupt, park, tell the person).
17. **The fallback is today's rule.** Where the agent is silent past its bound (60 seconds to start with),
    asks for something not allowed, or cannot be run, the program applies the fixed rule for that one
    decision, says so on the board, and tries the agent again at the next event.
18. **Without the protocol** the same brief is run once per event, headless, handed the stream's state and
    the event. The state is the log, never the agent's memory.
19. **The skipper stays as it is.** The captain does not answer product questions.
20. **Both routes.** A slice's own box goes straight to that slice. The stream's box goes to its captain.

### Proof
21. **Tests gate the build**, in three layers: with no captain agent a stream runs exactly as today (the
    existing captain suites, unchanged); a stand-in captain that makes today's choices reproduces recorded
    runs line for line; a stand-in that misbehaves — starts an uncleared slice, exceeds its slots, retries
    past the ceiling, writes the log, says nothing, dies mid-decision — is refused or timed out every time.
22. **Evals are part of this build** and are not tests: recorded situations put to the real captain agent
    through the project's harness, scored on the order it gives (not its wording) against the orders a
    person would accept, several runs a case, reported per decision with agreement and cost. On demand and
    nightly, never a merge gate. The score is advice.

## 2. Contracts the streams share

Everything here is under `.slipwai/run/` (`logs.run_dir`), which is ignored by git and outside every scope
check. Additive only: nothing existing changes meaning.

### 2.1 A conversation (`talk/`)
A slice's is `talk/<fairway>/<slice>/`; a captain's is `talk/<fairway>/_captain/`.

- `inbox/<id>.json` — one file per thing sent to it, written whole and renamed into place by whoever sends
  (the board, a captain's order, confirmed feedback, the MCP `tell`). `{"v":1,"id","t","from","kind","text","mode"}`.
  `kind` is `say`, `pause`, `resume`, `stop` or `withdraw` (`"of": <id>`). `mode` is `wait` or `interrupt`.
  `from` is `person`, `captain:<fairway>`, `skipper` or `feedback`; a message a captain routed carries
  `"via": "captain:<fairway>"` and the id of what it routes in `"of"`.
- `thread.jsonl` — append-only, **one writer: the driver** (inside the captain's process). A line per fact:
  `seen` (an inbox file was read), `delivered` (`id`, `mode`), `reply` (`to`, `text`), `unaddressed` (`id`),
  `failed` (`id`, `why`), `withdrawn` (`id`), `ask` (`id`, `what`: `permission`|`question`, `text`,
  `options`), `answer` (`to`, `by`, `text`), `turn` (`state`: `started`|`ended`|`cancelled`, `stop`),
  `paused`, `resumed`, `stopped` (`by`, `why`), `session` (`id`, `loaded`: bool).
- A receipt is read from the two: in `inbox/` with no `delivered` → queued; `delivered` → delivered;
  `reply` → answered; `failed` → not delivered; `unaddressed` → the quiet flag.
- `session.json` — the saved session id and harness, written at close, read at open.

What the agent does (tool calls, its plan, a sentence for a person) goes on being written to the activity
log, `activity/<fairway>/<slice>.jsonl`, in the kinds `activity.py` already reads, plus `plan`.

### 2.2 The captain's orders (`orders/`)
The captain agent acts only by running `python3 scripts/agents/orders.py <verb> …` in the project, which
validates the shape and writes `orders/<fairway>/<id>.json`; the captain program reads it, checks it against
the rules, does it or refuses it, and writes `orders/<fairway>/<id>.result.json` (`done` or `refused`, `why`).
Verbs: `start <slice>`, `message <slice> --text … [--interrupt] [--of <id>]`, `retry <slice> --note …`,
`park <slice> --why … [--needs …]`, `pause|resume|stop <slice> --why …`, `say --text …` (to the person, in
the captain's conversation), `ask --text … [--options …]` (becomes *Waiting on you*), `allow|refuse <ask-id>
--why …`, `none --why …` (decline to act; the fixed rule applies).

An **event** is what wakes it: `events/<fairway>/<id>.json` with `{"v":1,"id","t","kind","slice","facts","may"}`.
`kind` is `message`, `question` (operational), `permission`, `gate-failed`, `stuck`, `choose-next`,
`trunk-red`; `facts` is the fold the decision needs; `may` lists the orders the program will accept for it.
An event is closed by its orders' results or by the fallback, recorded as `events/<fairway>/<id>.closed.json`
(`by`: `captain`|`rule`, `why`).

### 2.3 Settings
`harbour.json`: `captain: {"agent": true, "bound": 60}`. `.specify/cruise.json`: `sessions` defaults to
`protocol` where the harness's registry row has a launch; `demos` is `hand` (default) or `person`.

## 3. Rules every stream keeps

- Run tests as `make test TESTS="test_a test_b" < /dev/null` under a `timeout`; the whole suite takes about
  fifteen minutes and is run once before handing back. Also `make lint`, `make typecheck`,
  `python3 scripts/check-structure.py`.
- A module is at most 350 lines unless a `# budget: N — <why>` comment claims more; a new module is named in
  `scripts/check-structure.py`'s `TIERS` and in `scripts/bring-back.py`'s `OWN`.
- A change to a file a generated project runs moves `tests/fixtures/run-files.sha256`, only through
  `python3 scripts/fence.py --why "<what moved and that behaviour on macOS and Linux is otherwise unchanged>"`.
  A changed agent brief or command page moves its digest record with a dated reason line.
- Every script the keel ships passes `encoding=` on the same line as each read or write.
- One `changelog.d/<name>.md` per stream: `MINOR` or `PATCH` on the first line, then prose, then a
  `**Catch-up:**` line saying what an existing project does to get it.
- Slipwai supports every harness: nothing a person reads names one, and nothing depends on one.
- Version 1 is not touched.
- Comments say why, in the repository's own voice; a test's name is a sentence.
- Commit on the stream's own branch; never push.

## 4. Streams

**Wave 1, in parallel**
- **A · The board keeps itself current.** Decisions 1–3.
- **B · The example map.** Decision 4.
- **C · The driver held open, and the conversation files.** Decisions 6–11 and contract 2.1, toolkit side and
  the board's reader, with no page.
- **D · Nobody is asked to accept a demo by default.** Decision 5.

**Wave 2, once wave 1 is merged**
- **E · The captain agent.** Decisions 12, 15–20 and contract 2.2, with test layers 1–3.
- **F · The windows.** Decisions 13–14 over C's files: the slice's and the captain's windows, the card's
  marker and quick send, the captains strip, Tell every captain, and every "tell" rerouted to an inbox.
- **G · Evals.** Decision 22.

**Wave 3** — the glossary and the guides say plainly what a captain is; a whole-suite run; a review of the lot.
