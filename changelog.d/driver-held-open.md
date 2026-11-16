MINOR

**A slice's session is held open, and what is said to a slice reaches it.** Over the Agent Client Protocol a
slice's session was one prompt: the agent started, read the slice cold, ran the ladder and was closed, and a
retry started another one that read it cold again. What a person said to a slice was a line in its stream's
deck log that nothing delivered.
- **One session, many prompts.** The slice's driver stays up between turns: the captain's retry is the next
  prompt into the same session, and a turn ending is not the driver ending. A driver that is up and idle is
  not a stalled session and is not watched for silence.
- **Saved and loaded.** When the driver closes — the slice merges, parks, is paused or stopped — the session's
  id is kept beside its conversation, and the next driver loads it where the agent can, a fresh session
  otherwise. A slice whose newest stage is a review, an attack or the hand's walk starts fresh: those read
  the slice with no memory of building it.
- **The conversation files.** `.slipwai/run/talk/<stream>/<slice>/`: an `inbox/` a message is dropped into
  whole, a `thread.jsonl` the driver alone writes, and receipts folded from the two — queued, delivered,
  answered with the reply, not delivered with why, delivered and not addressed, withdrawn. `slipwai.talk`
  reads them for the board and writes a person's message (`send`); the pages move onto it next.
- **Send or interrupt.** A message waits for the turn under way and is the next prompt; an interrupt cancels
  the turn first. A turn cancelled for a message costs the slice no attempt. A message to a slice nobody is
  driving waits for its next run; one a person sends a slice parked on a question is the answer to the park,
  as a `told` from the board was.
- **Pause, resume, stop, one slice.** Pause lets the turn finish, keeps the session and gives the slot back;
  stop ends it now and puts the slice back in the queue with a `stopped` line naming who and why, its branch
  and berth as they were.
- **What the agent does is on the board**: its tool calls as they finish, its plan, and its last sentence,
  in the slice's activity log; what it asked mid-turn and the answer, on its thread.
- **The protocol is the default** where the harness print mode would run has a launch the registry marks
  proven; `sessions: print` in `.specify/cruise.json` keeps print mode. In print mode a slice's messages are
  handed to it in the prompt of its next run, with no interrupt.

**Catch-up:** run `slipwai migrate`, which brings the new driver, `talk.py` and the captain. A project whose
harness has no proven launch, or that says `sessions: print`, runs as it did.
