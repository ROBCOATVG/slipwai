MINOR

**A person can tell a running `/cruise` something without stopping it.** `/cruise-tell <message>` in any
session, `make cruise-tell MSG="…"`, or `python3 scripts/agents/cruise.py tell …` queues the message in
`.specify/cruise-inbox.jsonl`; the runner reads the inbox before it starts each iteration and hands the message
over as `told: <message>` in that iteration's argument — the route the kick-off takes — and the command reads it
before the first stage and acts on it first, writing what must outlive the iteration into the owner brief or a
decision entry. Between stages an iteration runs `python3 scripts/agents/cruise.py told` for what was queued since
it started, so a message can land mid-iteration without cutting a stage. A parked run resumes with a message
within the second, and a message waiting when a run is stuck goes in place of the bosun's `unblock:` iteration.
`--now` as the first word ends the iteration in flight for the message, the way `stop --now` does, and starts the
next at once; the log entry says so, and an interrupted iteration is not counted by the stuck detector. Every
message delivered is in that iteration's entry in `specs/cruise-log.jsonl` under `told`, and `/cruise-status` lists
what is queued. The watch seat queues what a person types for the run the same way and repeats what the script
said. Every setting keeps its meaning; a message never changes one.

**Catch-up.** `slipwai migrate` brings the runner, the command files and the Make target; the inbox and the
delivered file are gitignored.
