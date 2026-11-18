MINOR

**A slice's card says where the slice is, and a capability is filmed once.** A card said a chip and, behind
a click, the board's own facts: a clearance word, a raw timestamp, the files on a branch. `Implementing ·
11/15` read as nearly done with a demo, a review and a merge still ahead, and the line under it was whatever
command the agent had run a second ago.
- **Closed, a card in flight is the ladder.** Six steps — Examples, Plan, Build, Demo, Review, Merge — with
  the one it is on, how long its stage has been open, what is still to come, and the task in hand rather
  than the last command.
- **Opened, it is how the slice got there.** Each step with when it began and how long it took, read off the
  berth's `benchmark.json`; under the step it is on, the last lines of its activity log and the link to its
  live window; and the work the slice has taken so far, by its stages' own time.
- **The columns keep themselves current.** The page's one poll (`/live.json`) redraws them every few seconds and puts back the
  cards a person had open; they were drawn once and stood until something else reloaded the page.
- **The Now strip repaints again.** It shared the id `now` with the passage's sentence, so its poll replaced
  that sentence and never touched the strip. And a slice moving from working to waiting changes the page's
  signature: both were the letter `w`.
- **One film per capability.** The demo hand recorded a file per example: in one project, twenty-nine clips of
  half a second to four, one of them the sign-in page. It films the capability's walk once now —
  `python3 scripts/agents/try_it.py film start|chapter|stop <feature> <capability>` keeps the marks — holding
  each result on screen and saying, per example, who is signed in and what they are about to do. The board
  plays it under *On film* with a chapter per slice and that sentence under the picture, serves it in byte
  ranges so a chapter can be sought, and a slice's card links to its chapter. Clips already recorded stay
  listed where they were. A project gets the new verb and the hand's new brief with `slipwai migrate`.

**Catch-up:** the card, the live columns and the film's player need nothing: they are the board's. For the
hand to film a capability, run `slipwai migrate`, which brings `try_it.py film` and the hand's new brief; a
capability walked before then keeps its clips until it is walked again.
