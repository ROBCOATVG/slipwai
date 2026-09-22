MINOR

**A typed `/cruise` now keeps going on every harness: it starts the runner, detached, instead of running the
ladder in a session nothing re-invokes.** The loop that continues a run used to have two paths — the runner
from a terminal, and an in-session ladder that only held where Claude Code's Stop hook could refuse a turn — so
in Cursor and every other harness the session ended on `cruise: continue` and waited for a person. Now the
runner is the one continuation mechanism: `python3 scripts/agents/cruise.py start` detaches it from the
session, writes its pid and a log under `.specify/`, and the command ends its turn with what `start` printed;
`stop` (and `make cruise-stop`) ends a run after the iteration in flight, or at once with `--now`; `status`
says whether a runner is running. The runner drives whichever CLI harness the machine has: the registry's
`headless` column now has a verified command for 27 of the 36 harnesses, each read from its own documentation
and dated, and the nine without say why; the runner takes the first installed harness with one on the PATH,
else any harness on the PATH, and asks every harness but Claude Code to read `commands/cruise.md` rather than
resolve a slash command. Hooks are the seatbelt inside a runner's iteration, not the control: the registry's new
`hooks` column says which harnesses can refuse the end of a turn, `scripts/agents/project.py` writes the hook
file where its shape was read (`.cursor/hooks.json` for Cursor, merged into `.gemini/settings.json` for Gemini
CLI), and `stopping` answers each in its own spelling and only in a session the runner started.

**Catch-up.** `slipwai migrate` brings the new runner, command text, Makefile targets and registry; a
repository with Cursor or Gemini CLI initialised gets its hook file on the next `./init` or `make agents`. The
stop file, the runner's pid and log, and the kept last response are now gitignored.
