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
- **Held for the merge.** From a slice's merge request to its answer nothing is delivered to it, and the
  receipt says so: a refusal takes the message back to the berth with the slice, and the slice's own gate is
  read again before the merge is asked for where a message's turn committed; a merge that lands answers it
  not delivered. A message's turn is bounded by the stage's time from its delivery; the captain's own turn
  still only by the deck lines and commits it writes, so an agent busy on tools and writing neither is ended.
- **Every message is signed, for its slice.** The board and the fleet sign what they send; a file that is not
  signed for the slice it sits in, or that was handled already, is refused with a receipt saying so, and a
  delivered message is fenced off from the rest of the prompt. A stop by a person holds the slice, across
  restarts, until a person resumes it; nobody else's resume lifts it. A message to a paused, stopped or
  merged slice says why it waits, or that it never will.
- **The protocol is the default for a new project.** `sessions` in `.specify/cruise.json` gains `auto`, which
  a newly generated project is written with: over the protocol where the registry marks the harness's launch
  proven and this machine can make it, print mode elsewhere, said in one line when it falls back. An agent
  that cannot be started at all puts that slice in print mode, said, at no attempt's cost. `print` and
  `protocol` mean what they did, and a file that says nothing is print mode, as before. In print mode a
  slice's messages are handed to it in the prompt of its next run, with no interrupt.
- **Known limit: a person's stop and pause stay on this machine.** They are on the slice's thread, which is
  in the run folder and does not travel, and a stream taken over by another machine does not see them.
  Written into the deck log they would travel, but the resume that lifts them is dropped in an inbox here
  and would not, so the hold would land somewhere nobody could lift it; that waits for the inbox to travel.

**Catch-up:** run `slipwai migrate`, which brings the new driver, `talk.py`, the captain and `auto`. Migrating
switches no project: a project's sessions stay in print mode, whether its `cruise.json` says `print` or says
nothing. To take the protocol where the harness's launch is proven — today two harnesses in the registry
are — and print mode for every other, choose it on the board's settings card under *A captain's session*,
or run `python3 scripts/agents/cruise.py --set sessions=auto`.
