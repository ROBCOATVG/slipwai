MINOR

**A cruising run no longer stops to wait for a reply nobody owes it.** Under `/cruise` with
`decide: recommended-first` or `skipper-always`, a slice's note that has gone unanswered past `wait_bound`,
and a count of unread decisions over `decision_ceiling`, used to park the whole fairway. One of these stopped
a fairway overnight because of a slice's own note about an ignore file. Both now stay on the board under
*Waiting on you*, to be read whenever you get to them, and the fairway carries on. A cruising fairway still
parks for anything no agent may supply. Outside cruise, both rules work exactly as before.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/inbox.py` and `captain.py`.
