MINOR

**A storyboard can be talked about without being approved or disapproved.** Under the Storyboard card on the
Voyage's Screens tab is a conversation with the session that drew it, carried on from its kept session, so it
already holds the research and the review: its turns live, what it is doing and for how long, and Stop. Ask
about a finding, ask to see or change a state — it changes the page there and then — or answer one of its
questions; what you decide is written down by the session where `/mockups` keeps such things (the feature's
`decisions.md`, and the question marked answered where it was asked). A page the conversation changes loses
its verdict: those states are taken out of `mock-states.md`, the file says which, and the storyboard waits on
a verdict again. Talking never approves: Approve and Disapprove stay the only verdicts, and stay buttons.

**What the drawing found is listed under it.** The review's counts, its Blocker findings first and the
research's open questions after them, collapsed, each with a button that opens the conversation on it, its
words in the box and nothing sent. Where `review.md` or `research.md` cannot be read, a link to the file and
nothing else.

**What is said to a stage is kept.** Every turn of a conversation with a stage is written beside its session
in the run folder (`stages/<command>/talk.jsonl`), so it can be read after the next stage has started and after
the app restarts. Something said while a stage runs is queued, shown as queued, and said to it when its turn
ends — never refused and never dropped.

**A running stage is visible where its result will appear, and its end is announced.** While the storyboard
is drawn, a card in its place on the Screens tab says what the stage is doing and for how long, and the tab
is marked; the model on the Model tab the same. When the stage ends the card is replaced by the result
without a reload, and *The storyboard is ready to look at* is under Waiting on you.

**`upstream: advance` no longer moves on past anything a person might want to discuss.** On the first real
run, a question asked of a finished storyboard was answered, the reply's end was read as the step ending
well, and the board approved all 49 states past a review with 14 Blockers and started the model. Now a reply
is never a step ending; anything a person says to a stage holds the board until they press Carry on or give
the storyboard its verdict; and the board does not approve a storyboard whose review has a Blocker, whose
research has an open question, or whose review cannot be read. It stops and says why in the stage card and
under Waiting on you. The settings card says so.

**Catch-up:** update the app, and run `slipwai migrate` for the `/mockups` page's new paragraph on what a turn
of conversation writes down and the setting's new wording in `commands/cruise-settings.md`. The behaviour has
changed for a project that set `upstream: advance`: the board now stops at a storyboard with Blocker findings or
open questions, and after you say anything to a stage, until you approve, disapprove or press Carry on. A
project left at `park`, the default, behaves as before apart from the conversation and the running cards.
