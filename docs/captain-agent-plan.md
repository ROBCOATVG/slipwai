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

6a. **A decision log a person can read.** Every decision entry carries one plain sentence a product owner
   can read without the specification open, written by whoever decides at the time and required by
   `check-decisions`; an entry written before the rule shows its question instead. On the board a decision
   is a card led by that sentence: the options with the chosen one marked, who decided, how confident, what
   would change it, and the entry as written one click away. The Decisions tab opens on what awaits a
   person's confirmation, grouped by capability then slice, with filters for stream, slice and who decided.
   Each slice's window has a Decisions tab of its own. *Change this* starts a message to the slice (its
   captain once it has merged) with the decision quoted. A person's answer in a conversation is a decision
   in the log like any other.

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
    *Who answers* settings. **A fleet cast off under `/cruise` — which is what the board's Cast off is —
    answers every one itself by default**: the stage's recommendation or the skipper (or the skipper every
    time), and nothing blocks or is listed as waiting. A person is asked only where a person is at the
    wheel: under `/sail`, in a project with no cruise settings, or for a stop the settings set to *park and
    ask me*. There it is a card under *Waiting on you*, the turn held five minutes for a quick answer before
    the slice pauses.
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

An **event** is what wakes it: `events/<fairway>/<id>.json` with `{"v":1,"id","t","kind","fairway","slice",
"facts","may","default"}`. `kind` is `message`, `question` (operational), `permission`, `gate-failed`, `stuck`,
`choose-next`, `trunk-red`; `facts` is the fold the decision needs; `may` lists the orders the program will
accept for it; `default` is the orders the fixed rule would give, in the order shape below. An event is closed
by its orders' results or by the fallback, recorded as `events/<fairway>/<id>.closed.json` (`by`:
`captain`|`rule`, `why`, `orders`: the order ids read for it, `cost`: `{"seconds", "ready_seconds", "ended":
"finished"|"bound"|"unavailable"|"changed", "via": "protocol"|"headless"|"named"|"none", "tokens": null}`). Beside the
events, `events/<fairway>/state.json` is the stream as its log says it at the moment of the event (`in_flight`,
`unmerged`, `merged`, `parked`, `stream_parked`, `attempts`, `trunk_red`, `recent`: the newest forty deck
lines without `fairway`), rewritten at every event.

*Settled in stream E (2026-11-16), for the evals and the board:*

**The order file** is one JSON object, `{"v":1,"id","t","event","fairway","verb", …, "sig"}`, `id` equal to the
file's name. `event` is the id of the event it answers — always: `orders.py` takes `--event <id>` and otherwise
the one event still open. `sig` is an HMAC-SHA256, with the key the program hands the captain's session in
`SLIPWAI_CAPTAIN_KEY`, over the JSON of the fields `v id t event fairway verb slice ask text note why needs of
options interrupt` (sorted keys, absent ones `null`); an order the program cannot verify is refused. Beyond the
six, by verb (every value a string unless said):

| verb | keys |
| --- | --- |
| `start` | `slice` |
| `message` | `slice` (a slice of this stream, or `captain:<fairway>`), `text`, `interrupt` (bool, optional), `of` (optional: the inbox id it routes; `text` may then be left out). What lands in the inbox is always the captain's — `from: captain:<fairway>`, its own `text`, and where it routes, `via`, `of` and the person's words unaltered in `quote` — so it never answers a park or a question, and its interrupt costs an attempt. A message from a captain may be routed to a slice, never on to another captain |
| `retry` | `slice`, `note` |
| `park` | `slice`, `why`, `needs` (optional) |
| `pause`, `resume`, `stop` | `slice`, `why` |
| `say` | `text`, `of` (optional: the message it answers) |
| `ask` | `text`, `options` (optional, list of strings) |
| `allow`, `refuse` | `ask` (the ask's id), `why` (for an allowed question, `why` is the answer, which the program writes as a deck `decision`, `decided_by: captain:<fairway>`, counted toward `decision_ceiling`) |
| `none` | `why` |

**`facts` by kind**, as small as the decision needs and kept stable:

| kind | `slice` | `facts` |
| --- | --- | --- |
| `choose-next` | null | `free` (slots free now), `in_flight` (slices), `cleared`: `[{"slice", "steers_by", "sets", "progress"}]` in the rule's order (`progress` 0–8, the captain's rung) |
| `gate-failed` | the slice | `slice`, `why`, `cause` (`silence`, `exit`, `demo`, `gate`), `tried`, `attempts`, `sets` |
| `stuck` | the slice | `slice`, `warnings`: `[{"kind": "long"|"circles"|"quiet", "level", "said"}]` |
| `message` | null | `inbox` (the message's id in `talk/<fairway>/_captain/`), `from`, `text`, `mode`, `t` |
| `question`, `permission` | the asking slice | `ask` (its id), `text`, `options`, `tool` (`{"title", "kind", "locations"}` for a permission, else null) |
| `trunk-red` | null | `commit`, `job`, `t` |

**Bounds.** `captain.bound` (default 60 seconds) runs from when the captain's session is ready to take the
event — over the protocol, once its turn has begun — and `captain.headless_bound` (default 180) from launch,
where a headless session cannot say when it is ready. Each closing record carries what the decision took.

**The evals' entry point.** `python3 scripts/agents/captain_agent.py decide <event> [--bound N]`, run in the
project: wakes the captain this project would run, once, with that event and the `state.json` beside it (one
is written if absent), lets it write orders under `.slipwai/run/orders/<fairway>/`, ends it at the bound, and
prints `{"exit", "timed_out", "tokens", "seconds", "orders"}`. It fits `command_captain` as it stands. A
headless session started some other way with `SLIPWAI_EVAL=1` and no key may still use `orders.py`: its orders
are written unsigned, for the eval to read; the program never acts on one.

### 2.3 Settings
`harbour.json`: `captain: {"agent": true, "bound": 60, "headless_bound": 180}` (a new project's; `"answers": false`
keeps it from answering a slice's mid-turn question; `"per_hour"`, 30 by default, is the most it is woken in an
hour; `events/<fairway>/agent-off.json` turns it off for a stream until a person removes it; absent is the
program alone, and `SLIPWAI_CAPTAIN` in the environment says first: `off`, `1` for the project's own harness,
or a command to run as the captain).
`.specify/cruise.json`: `sessions` defaults to
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
- **H · The decision log.** Decision 6a: the sentence and its check in the toolkit, the cards, the tab in
  each slice's window. *Change this* waits for F's conversation windows.

**Wave 3** — the glossary and the guides say plainly what a captain is; a whole-suite run; a review of the lot.
