MINOR

**`slipwai adopt --next` says where an adopted repository stands in the sequence the adoption report names —
what is done, what is next, and why — so the plan survives the scrollback.** That report is printed once, at
the end of the longest output this factory produces, and the sequence it names spans days and four tools;
`docs/adoption.md` carries the same list but is introduced there as a record of what was wrapped rather than
as the plan. Nothing is remembered now: every step leaves a mark, and `--next` reads them. Spec Kit writes
`.specify/integration.json`, the first gate run writes the ratchet baseline, `/ground` moves a row of the
convergence map off `unrecorded`, the root Makefile gains its `-include`, and a strategy is an accepted ADR
with a `Strategy:` line. It writes nothing itself, and it names the applications nobody has yet proved start.
A repository adopted by an earlier version needs nothing: the marks are the ones it was already leaving.

**A recorded command that changes directory first no longer reports the shell's `cd` as a tool this machine
is missing.** Every build that is not at the repository root is recorded as `cd <dir> && <build>`, and the
report read the first word off that line and asked the PATH for it — so a repository with four such builds
was told `` `cd` is not on PATH here `` above a list of all fifteen of their targets, with the one tool that
really was missing a line among them. The tools a command runs are now every shell segment's program, past
any leading `VAR=value`, and never one of the shell's own words.

**`slipwai adopt --experimental-intro` turns on the reshaped adoption intro while it is being built.** The
questions a terminal cannot answer well — what a directory is, what it is called, what it owns — are being
moved to the coding agent, which can read the code before asking. The switch (or `SLIPWAI_EXPERIMENTAL_INTRO=1`)
is how to walk that shape before it is the only one; today it removes the first of them, the language, which
the line above it has already printed and which `--language NAME=LANGUAGE` still corrects. Default off:
without it the interview asks exactly what it asked before. Experimental within an experiment (#74).
