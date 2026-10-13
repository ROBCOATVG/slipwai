MINOR

**`generate` now finishes the project it makes: it runs `./init` in it, and the board lands there.** Until
now both faces stopped at `created: <path>`. The next step — `cd` into it and run `./init`, which installs
Spec Kit, projects the skills and commands into your coding agent, and is the one step that reaches the
network — was a sentence in the guide, and nothing in the new tree works until it has run.

In the terminal, the interview ends by running it, with your standard input, so Spec Kit can ask which agent
it is for. A scripted `slipwai generate` is unchanged: it is left with the next step unless it is given
`--init`, and `--no-init` declines it in the interview.

On the board, the interview now asks one question the terminal cannot ask well — which coding agent, from
the thirty-six the registry knows — and when the project is made the board **attaches to it**: it is that
project's board from that moment, with a card naming what was made and tailing `./init` as it runs. The
run is a child that outlives the request, so the page never hangs waiting for Spec Kit to install.

The board also gained a **Looking at** card: the directory it is a view of, and a box that points it at
another one. Moving the board no longer means stopping it and starting it again with `--root`, which is
also how you watch a `/sail` or `make cruise` that is already running somewhere else — the board is a fold
of that project's logs, so attaching to it is all there is to it.

**Catch-up:** nothing. This is the factory's own behaviour, not a project's; an existing project's `./init`
is unchanged.
