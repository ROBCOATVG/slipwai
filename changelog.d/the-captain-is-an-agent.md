MINOR

**A stream's captain can be an agent again, with the program underneath it.** The agent chooses; the program
checks and does. Which cleared slice starts next, whether a slice that missed its gate runs again and with
what words or parks and why, what to do about a slice that is stuck, what someone said to the stream, what a
slice's session asks mid-turn, and a red trunk each wake the captain's agent with an event file
(`.slipwai/run/events/<stream>/`) holding the facts and the orders it may give. It acts only through
`python3 scripts/agents/orders.py`, which signs each order with a key only the captain's session is handed;
the program checks every order again — clearance and the free slots as they are when the order is done, a
person's hold, the merge — does it or refuses it, and writes why. Where the agent is silent past its bound,
orders something not allowed, or cannot be run, the program makes that one choice by the rule it always used,
says so, and tries the agent again at the next event: a stream always runs on the program alone, and the
program's loop never waits on its captain. **The captain is an agent only over the Agent Client Protocol**,
held open with a policy that lets it read and run the project's own `orders.py` and nothing else; a captain
run headless could not be confined, so there is none — where the harness has no proven launch over the
protocol the stream runs on the program alone and says so ("no captain agent: this harness has no proven
protocol launch"). **No slice runs without limit**: between a person's words to it, a slice has at most
`2 × attempts + 1` runs that cost an attempt, counted at every dispatch from its `dispatched` deck lines,
whoever asked — five at the default two.
`agents/drive-captain.md` is its brief, rewritten for the role. `slipwai.captain_decisions` reads back what
each captain decided, for the board. Whether a slice is stuck is now one fold, `stuck.py`, shared by the
board's card and the captain.

**It does not answer a slice's questions unless a project says so.** A question a slice's session asks
mid-turn is declined as it always was, and goes down the deck log's `question` path — the skipper under
`/cruise`, a person otherwise. `"answers": true` in `harbour.json`'s `captain` lets the captain answer; then
every answer, and every refusal with words in it, is written into the stream's log as a `decision` by the
captain for a person to review. **The program cannot tell an operational question from a product one**, and
under `/cruise` the ceiling on unreviewed decisions forces nothing, so nothing else bounds what it answers:
that is why it is off. The captain still rules on a permission a slice asks outside its berth: a read inside
the project, and nothing else.

**What it costs.** Each event is one turn of the project's harness: a choice of the next slice when more may
start than there are slots, each missed gate, each new warning on a slice, each message to the stream, each
question a slice asks where answering is on. `captain.per_hour` (30 by default) is
the most a stream's captain is woken in an hour, after which the stream runs on its rules alone until the
hour has passed, and says so. Each closing record carries how long the decision took.

**A stream hears a person with or without an agent.** What is said to a stream itself, in its captain's
conversation, is read by the captain program every turn and written into the deck log as the stream's
`told`, carrying the message's id, so the harbourmaster clears a park on it exactly as it did on the line the
board used to write; a resume sent to the stream ("try now") lifts a pause the same way. A person's word to
a slice answers the park about that slice — its own, or the stream's where it names the slice. A person's
word waiting is a reason to light a captain: the harbourmaster's plan gives such a stream a session even while
it is parked, and the captain's first act is to read it. A second answer to a question, before the captain has
carried the first, replaces it; after, it reaches the slice as an ordinary message.

**When the agent fails, the stream says so and carries on.** Where the captain's own machinery fails, the
stream runs on the program alone for the rest of that run: every event still open is closed by the rule, a
message the captain had not answered is marked unaddressed, `captain.json` beside its events says
`"agent": false` with why and when, and the deck log gets one `noted` line. `noted` is a new deck kind: what
the program says about its captain — that it failed, or that its session was refused commands (one line an
event, counted) — for a person to read; nothing waits on it, so it never parks a stream, and it never counts
as a slice's progress, so it never keeps a silent stage alive. The agent is tried again when the captain is
next started. The board says so: the stream's button on the captains strip and its captain's window say it is
running on the program alone, and why, and the window lists the `noted` lines as news.

**A held slice is in sight.** A slice paused or stopped by a person, or paused by its captain, says on its card
who holds it and since when — a person's pause from the moment it is heard — and a slice its captain paused
is listed under *When you have time* beside the ones a person paused, since no timer and no rule lifts it. A
captain's park of a stuck slice is written with the cause `other`; it was written with a cause no reader
takes, which ended the captain's turn. A message over 1 MB is refused when it is sent, saying so.

Also: a person's pause or stop now stands through anyone else's stop until a person resumes it; a message
already handled keeps its receipt after the conversation key is made again, and a queued one says the key
changed, with its text; the key's file mode is not asked on Windows; a resume with nothing held is done
without a failure; the reaper reads `ps` in the C locale and checks its captain by identity; a stop of the
fleet is never taken for a fault and carried on past; a file in the run folder — nested past any parser, of
the wrong types, a link, or a pipe — is never what stops or hangs a captain; and a slice that merges while a
person's pause stands is no longer left paused; and a conversation's thread longer than one read (8 MB) is
read to its end, so a pause written last is never missed.

**Catch-up:** update the app first, then run `slipwai migrate`, then restart the harbourmaster (stop the fleet
and start it again): the deck log gains the kinds `dispatched` and `noted`, which a board, a `slipwai` command
or a harbourmaster from before this upgrade refuses to read, so a stream's log would read as broken to them.
What already guards it: once `migrate` has recorded this release in `project.json`, the project's own
`fleet.py` refuses a start, a relight or a tell asked by an older app (`app_too_old`, which reads the
`SLIPWAI_APP_VERSION` the app passes), and an older app's board says on every page that it is older and
changes nothing. Neither covers a harbourmaster already running from before the upgrade, which keeps the old
reader until it is restarted, nor a `slipwai` command from an older install run at a terminal, which passes
no version; those two are on you. The captain agent is off in an existing project until you turn it on: add `"captain":
{"agent": true, "bound": 60}` to `harbour.json` (`"answers": true` to let it answer a slice's questions,
`"per_hour"` to change its ceiling) and restart the fleet; it runs only where your harness has a proven launch
over the Agent Client Protocol. A newly generated project has it on. A `harbour.json` written by an earlier
build of this may carry `headless_bound`; it is read by nothing now and can be removed. `SLIPWAI_CAPTAIN=off` in the fleet's environment turns it off whatever the file
says, and `SLIPWAI_CAPTAIN=1` on through the project's own harness. Three things change with the agent off as
well, and need nothing from you: a person's pause or stop now holds a slice through anyone else's stop; what a
person says to a stream through the board is read by its captain program, which is lit to read it even while
the stream is parked; and a slice that has had `2 × attempts + 1` runs since a person last spoke to it parks
for a person rather than run again, across restarts and cleared parks alike.
