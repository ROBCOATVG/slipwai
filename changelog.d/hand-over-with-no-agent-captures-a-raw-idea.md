MINOR

**With no agent to launch, the hand-over captures a raw idea instead of nothing.** Where the board can launch
no agent, **Hand over a further feature** used to say so and stop: the words and the document went nowhere.
The card now says before you type that there will be no conversation, keeps what you say and attach, and
offers **Capture as an idea, not discussed**. The idea is written under `docs/intake/<slug>/` as any other,
with a `not-discussed` file beside its brief; the **Next features** tab lists it as *not discussed with an
agent*; and `/assess` is told what that means — nobody asked whether it is one feature or what is being asked
for, so the assessment asks first, and answers `needs-clarification` rather than guessing its way to a `go`.
`make assess` says so as it starts. Where an agent can be launched nothing changes: the conversation is the
only way in, and there is no button that skips it.

**Catch-up:** `slipwai migrate` brings `commands/assess.md`, `scripts/agents/assess.py` and
`docs/intake/README.md` their new wording; an idea captured before this has no mark and is read as discussed.
