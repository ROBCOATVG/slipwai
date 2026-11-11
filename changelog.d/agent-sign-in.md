PATCH

**An agent the board fetched can be signed in to from the board.** On a machine with nothing but the board
and the tools it installed, the first conversation ended with "the agent refused session/prompt:
Authentication required" and there was nowhere to sign in: Claude Code's only sign-in is a command run in a
terminal, the board never told the agent it could run one, so the agent offered none, and the `claude` the
agent carries is not a command on the machine. The board now says so at the handshake. *Settings* shows a
**Sign in** button per way the agent offers; pressing one opens a window running the agent's own sign-in,
which opens the browser, and the page waits and says how it ended. On Linux the page gives the line to run,
now the whole command the agent named rather than `npx` with the arguments. A conversation refused for want
of a sign-in says where to sign in instead of the bare refusal.

The sign-in follows what each agent offers, checked at the handshake of twenty-one of the registry's agents.
A sign-in that names a command is run as one whatever type the agent gave it: Copilot, Auggie, Kilo and Kimi
give none, and were asked to sign in over the protocol, which did nothing. The command is the one that
works for that agent: the one it named where that says more than its arguments (`opencode auth login`, not
`opencode --login`), the launch with the arguments where the named one is no command at all (Qoder's
`node login`, pi's `pi-acp`), and never another agent's (Kilo names `opencode`). An agent that opens no
session until somebody signs in — thirteen of them — is made ready and offered its sign-ins, where it used
to be recorded as one that could not be made ready and passed over by *Auto*; what it said is kept, since
Droid's carries the code to enter. An agent that gives no name of its own is called by the registry's.

**Catch-up:** none. On a machine made ready by an older build, press *Make ready again* in *Settings* once:
the ways to sign in are what the agent said at that handshake.
