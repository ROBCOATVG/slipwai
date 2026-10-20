PATCH

**Only a person's message answers a park, and the decision ceiling waits for a reading.** Every `told`
line used to clear whatever park was open, including a slice's own note to the host, so parks cleared each
other and a fairway parked on nineteen unread decisions was cleared by the next slice's note. The board,
the MCP server and `fleet.py tell` now write `by: person` on a person's message, or `by: session` under a
dispatched session, and only a person's clears a park. While more decisions stand unread than
`decision_ceiling` allows, no message clears a park. The park the captain writes at the ceiling says
`waiting: decision-review` and is cleared once the decisions are read or the ceiling is raised.
