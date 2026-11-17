PATCH

**A captain agent's orders, asks and pauses do what they say.** Fixes from a review of the whole captain-agent
build, each proved through the real captain program with a stand-in captain:
- **An order whose words hold ordinary punctuation is no longer refused.** The captain session's policy read
  the whole command for `;`, `$`, a backtick and the like, so a `--why` quoting a failure or a price was
  refused and the event went to the rule. It now reads the command as a shell would: anything inside single
  quotes is words, and what a shell would run as more than the one order is refused, with the rule that
  refused it in the `noted` line. The captain's brief and prompt say to single-quote every prose value.
- **A captain's `ask` reaches a person.** It is listed under *Waiting on you*, holding work up, in every run —
  no skipper answers a captain — drawn once in the captain's window with its options and a box, and the
  answer is put to the captain naming the ask it answers.
- **A captain's pause holds from the moment it is given**, as a person's does, so a slice whose turn a bound
  ended is not run again until it is resumed; a person's hold still outranks it.
- **Words a captain acted on are read.** The `told` a person's words to the stream became gets a `read`
  receipt, tied to it by its inbox id, so it no longer parks the stream as unanswered an hour later.
- **A captain may allow a slice a read inside the project from a berth of its own**, as the rule always said;
  measured against the berth, it could allow none.
- **What a captain reads, and lets be read, is decided on the real path.** A link is what it leads to, case
  is no disguise, and the conversation key, environment and key files, `.slipwai/` and `.git/` are read by
  nobody through a captain; a slice may be allowed one plain file of the project, and the captain's own
  session reads only the project. Its policy judges any request carrying a command as a command, decides on
  everything the session already said of a tool call, refuses an order command with its own environment,
  folder or extra words, and names the keys of any request shape it did not expect in the `noted` line.
- **Only words answer words.** A person's message to the stream is read when the captain says something,
  asks, or routes it on — not because it paused a slice on the same event.
- **A slice a captain paused before it started is listed and said**, with who holds it and why.
- **Smaller.** A stuck slice's park carries the needs the captain named. A `start` or a stuck slice's `park`
  says on its result whether it was carried out, and *What it decided today* says so. `SLIPWAI_CAPTAIN` in
  the environment changing what `harbour.json` would give is said once, on the stream's output and beside its
  events for the board — never in the deck log. `orders.py` writes an unsigned order only in the
  evals' own project. *Interrupt now* on a captain's queued message keeps it the captain's. A project's first
  decision appears on an open board. The console's model is told it answers questions and is no part of
  the fleet. A pause or stop in the deck's own words says whose it was. An answer from a parked slice's card
  is the answer on its park's row. A question no slice owns is answered to its stream's captain. A long
  *Tell every captain* is kept whole, and turns said in one second draw in the order they were said.

**Catch-up:** run `slipwai migrate`, which carries the new scripts and brief; a project migrated by this build must be
opened with this build, since another build with the same version string may not know its deck kinds.
