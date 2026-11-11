PATCH

### Fixed

- **An agent the board fetched can be signed in to from the board.** On a machine with nothing but the board
  and the tools it installed, the first conversation ended with "the agent refused session/prompt:
  Authentication required" and there was nowhere to sign in: Claude Code's only sign-in is a command run in
  a terminal, the board never told the agent it could run one, so the agent offered none, and the `claude`
  the agent carries is not a command on the machine. The board now says so at the handshake. *Settings*
  shows a **Sign in** button per way the agent offers; pressing one opens a window running the agent's own
  sign-in, which opens the browser, and the page waits and says how it ended. On Linux the page gives the
  line to run, now the whole command the agent named rather than `npx` with the arguments. A conversation
  refused for want of a sign-in says where to sign in instead of the bare refusal.

**Catch-up:** none. On a machine made ready by an older build, press *Make ready again* in *Settings* once:
the ways to sign in are what the agent said at that handshake.
