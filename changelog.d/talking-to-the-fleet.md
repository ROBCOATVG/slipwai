MINOR

**A slice and a captain each have a window to be talked to in, and everything said from the board goes to an
inbox.** A slice's window has its conversation beside *Where it is* and *Example map*: what you said with its
receipt (queued, held at its merge, delivered, answered, not delivered with **Send again**, delivered and not
addressed), **Send** after the turn under way, **Interrupt** where its session can take one (print mode says
why it cannot), **Interrupt now** and **Withdraw** on a queued message, and **Pause**, **Resume** and **Stop**
with what each does. A card carries a marker and the last thing said until its window has shown it, and opened
it has the last message, a one-line quick send and **Open its window**. Above the tabs, a button for each
stream's captain opens its window — its slices, what it decided today, its conversation — beside **Tell every
captain** and **Ask about this project**. `/tell`, the MCP `tell` tool (which now takes a `slice`), confirmed
feedback and an answer to a question place a signed message in the slice's or the captain's inbox and answer
with its id; the board writes no deck line for anything said. A product question waits on a person only where
the project says a person answers them, and a slice a person paused is listed under *When you have time*.

A message is aimed at the slice a park or question is about, and the row it was sent from shows the answer,
where it stands and **Change my answer** instead of a second box. The board's POST routes refuse a request from
another site.

**Catch-up:** run `slipwai migrate`. On a project with no captain agent, what you say to a slice — an answer on
a parked slice's card, a park's row or its group's button — reaches it as before, now through the slice's
inbox, and is shown as sent until the captain reads it. What you say to a whole stream (Tell every captain,
Tell this captain, the MCP `tell` without a slice, a question no slice asked) is read only once the project's
captain reads its own inbox, which `migrate` brings; until then the row says it is sent and nothing has read it.
