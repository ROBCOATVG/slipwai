PATCH

**An adopted repository's stages go to the agent the board runs on, and say so when they cannot.** `./init`'s
"Hand it to" offered whatever the tree or the environment read first, and every stage after it runs through
the harness picked there — so a board running on Claude could hand the build floor to Cursor, whose handshake
it had never signed in to, and the step stopped on "Authentication required". The menu now offers the agent
the board runs on first, after anything Spec Kit already recorded. Where an agent's handshake is refused for
want of a sign-in, the step says which agent, where to sign in, and — where the project was set up for another
agent than the board's — the `./init --integration` that switches it.

**Grounding says when nothing was chosen.** Record the answer pressed with no answer selected now says so on
the page, before anything is sent, instead of "pick one of the answers on offer".

**Catch-up:** nothing for a new adoption. A project already set up for an agent the board is not signed in to:
`./<delivery>/init --integration <the board's agent>`, or Sign in under it in Settings.
