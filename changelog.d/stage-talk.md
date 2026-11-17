MINOR

**A storyboard can be talked about without being approved or disapproved.** Under the Storyboard card on the
Voyage's Screens tab is a conversation with the session that drew it, carried on from its kept session, so it
already holds the research and the review: its turns live, what it is doing and for how long, and Stop. Ask
about a finding, ask to see or change a state — it changes the page there and then — or answer one of its
questions; what you decide is written down by the session where `/mockups` keeps such things (the feature's
`decisions.md`, and the question marked answered where it was asked). Talking never approves: Approve and
Disapprove stay the only verdicts, and stay buttons — refused, with the reason, while something you said to the
drawing is still waiting to be said or answered.

**A verdict stands for the pages it was given on.** `mock-states.md` now records, above each surface, the page
and what it said when the verdict was given. A page that says something else since — changed in a
conversation, by hand, renamed or deleted — no longer carries that verdict: the board says which surfaces, the
buttons come back, and a conversation that changed one takes its block out of the file once. A change to
`storyboard.html`, the flow between the surfaces, withdraws nothing.

**The drawing declares what it left to discuss.** `/mockups`, and the board's own prompt to the drawing, now
ask for two lines at the top of `specs/<feature>/mockups/research.md` — `Blockers open: N` and
`Questions open: N` — kept true as findings and questions are settled. They are read forgivingly (bold, a list
marker, a quote, a table, either case, both on one line) and matter only to a board set to advance by itself;
a drawing without them ends well, is shown and can be approved, and `make surfaces` only notes it. Under the
storyboard the board lists what the drawing found — its own count first, then the
Blocker findings and open questions it could read off `review.md`, `review-*.md`, `gaps.md` or `review/`,
collapsed, each with a button that opens the conversation on it, nothing sent — and says so where what it
could read differs from the drawing's count. Only the count decides anything.

**What is said to a stage is kept and said.** Every turn of a conversation with a stage is written beside its
session in the run folder (`stages/<command>/talk.jsonl`), so it can be read after the next stage has started
and after the app restarts. Something said while a stage runs is queued, shown as queued, and said when its
turn ends. After a Stop nothing starts by itself, and a message kept but not said — after a Stop, or a restart
— is shown as not delivered, with Say it now and Discard; it is never said unasked, and until it is said or
discarded neither a verdict nor Carry on is taken. A project still on the 2.0 run-folder layout, which git does
not ignore, is told so on the card before anything is typed, and to migrate; it works the moment it has.

**A running stage is visible where its result will appear, and its end is announced.** While the storyboard
is drawn, a card in its place on the Screens tab says what the stage is doing and for how long, and the tab
is marked; the model on the Model tab the same. When the stage ends the card is replaced by the result
without a reload, and *The storyboard is ready to look at* is under Waiting on you.

**`upstream: advance` no longer moves on past anything a person might want to discuss.** On the first real
run, a question asked of a finished storyboard was answered, the reply's end was read as the step ending
well, and the board approved all 49 states past a review with 14 Blockers and started the model. Now anything
a person says to a stage holds the board until they press Carry on or give the storyboard its verdict, and
every message delivered holds it again; the board never approves a storyboard whose drawing declares a Blocker
or a question open, or declares nothing, or whose verdict a changed page has withdrawn; and a later stage's
failure is not erased by talking to an earlier one. It stops and says why in the stage card and under Waiting
on you. The settings card says so.

**Catch-up:** update the app, and run `slipwai migrate` for the `/mockups` page's paragraphs on the declared
counts and on what a turn of conversation writes down, `make surfaces`'s note of them, and the setting's new
wording in `commands/cruise-settings.md`. The behaviour has changed for a project that set `upstream: advance`:
the board now stops at a storyboard whose drawing declares a Blocker or an open question — or declares nothing,
as every drawing made before this does, until you add the two lines or draw it again — and after you say
anything to a stage, until you approve, disapprove or press Carry on. At `park`, the default, it behaves as
before apart from the conversation, the running cards and the refusals above.
