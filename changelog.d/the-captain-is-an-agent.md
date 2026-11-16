MINOR

**A stream's captain can be an agent again, with the program underneath it.** The agent chooses; the program
checks and does. Which cleared slice starts next, whether a slice that missed its gate runs again and with
what words or parks and why, what to do about a slice that is stuck, what someone said to the stream, what a
slice's session asks mid-turn, and a red trunk each wake the captain's agent with an event file
(`.slipwai/run/events/<stream>/`) holding the facts and the orders it may give. It acts only through
`python3 scripts/agents/orders.py`, which signs each order with a key only the captain's session is handed;
the program checks every order again — clearance, the free slots, the attempts, a person's hold, the
merge — does it or refuses it, and writes why. Where the agent is silent past its bound, orders something
not allowed, or cannot be run, the program makes that one choice by the rule it always used, says so, and
tries the agent again at the next event: a stream always runs on the program alone. The captain never
answers a product question, which goes where it always went. Its session is held open over the Agent Client
Protocol where the project's sessions are, and run headless once per event otherwise; `agents/drive-captain.md`
is its brief, rewritten for the role. `slipwai.captain_decisions` reads back what each captain decided, for the
board. Whether a slice is stuck is now one fold, `stuck.py`, shared by the board's card and the captain.

Also: a person's pause or stop now stands through anyone else's stop until a person resumes it; a message
already handled keeps its receipt after the conversation key is made again, and a queued one says the key
changed, with its text; the key's file mode is not asked on Windows; a resume with nothing held is done
without a failure; the reaper reads `ps` in the C locale and checks its captain by identity.

**Catch-up:** nothing changes until you say so: an existing project runs on the program alone, as before.
To turn the captain agent on, add `"captain": {"agent": true, "bound": 60, "headless_bound": 180}` to
`harbour.json` and restart the fleet; a newly generated project has it on. `SLIPWAI_CAPTAIN=off` in the
fleet's environment turns it off whatever the file says.
