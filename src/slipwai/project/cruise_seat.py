"""The three commands a person types beside a running `/cruise`: `/cruise-status`, `/cruise-stop` and `/cruise-tell`.

Each is a shell command and the rule for what to do with what it printed. The rule matters more than the
command: a harness folds a command's output to a few lines, so a status or a feed reaches a person only through
the reply, and each of these says so in the same words the watch seat in `commands/cruise.md` uses.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from .cruise import SCRIPT
from .cruise_record import INBOX, RUNNER_LOG, STOP_FILE

# The rule every seat command shares: the harness folds a command's output, so the reply carries it.
VERBATIM = ("Put every line it printed in your reply, unchanged, in a fenced block, before anything else: the harness "
            "folds a command's output, so what it said reaches a person only through your reply.")


def cruise_status_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-status`: whether a runner is running, what the log says, and the tail of the feed."""
    return f"""---
description: Say whether a /cruise runner is running, how the last iteration ended, whether it is parked and why, and show the tail of its feed
argument-hint: [lines]
---

# Cruise status

Where a `/cruise` run stands, from disk: the runner's pid file, the iteration log, and the feed the runner
writes as each iteration works. Reading only; nothing here changes the run.

```sh
python3 {SCRIPT} status
tail -n ${{ARGUMENTS:-40}} {RUNNER_LOG}
```

{VERBATIM} The first command says whether a runner is running, how many iterations
have run, what the last one ended on, whether the run is parked and for what, and whether any command was
refused a permission (`python3 {SCRIPT} denials` lists those). The second is the feed's tail — one line per
command, file, and delegate out and back — with the number of lines as the argument, forty by default; where
the log does not exist yet, say that no run has started here. To keep watching the run as it happens, type
`/cruise`: it finds the runner running and takes the watch seat. To end the run, `/cruise-stop`.
"""


def cruise_stop_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-stop`: end the run after the iteration in flight, or at once with `now`."""
    return f"""---
description: End a /cruise run after the iteration in flight, or at once with `now`
argument-hint: [now]
---

# Cruise stop

A person's stop, the one thing a `/cruise` run stops for. Without an argument the run ends after the iteration
in flight — the command checks between stages, finishes the stage's own writes, commits what is green, and
ends. With `now`, the iteration in flight is ended too: its increment commits are on the slice branch, and the
next run re-derives its stage from disk, so nothing is lost but the stage's uncommitted work.

```sh
python3 {SCRIPT} stop $(test "$ARGUMENTS" = now && echo --now)
```

{VERBATIM} Then say one thing more: `{STOP_FILE}` is now present, and `/cruise` refuses to
start another run until it is removed — `rm {STOP_FILE}` when they want one. Where no runner was running, the
script says so and the file is written anyway, for the same reason. `{layout.make} cruise-stop` is the same
from a terminal, `CRUISE_FLAGS=--now` for the immediate form.
"""


def cruise_tell_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-tell`: queue a message for the next iteration, or end the one in flight for it with `--now`."""
    return f"""---
description: Queue a message for a running /cruise — a steer, a fact it lacked, a scope — which the next iteration carries; `--now` ends the iteration in flight for it
argument-hint: [--now] <what the run should know or do next>
---

# Cruise tell

A person's word to a run that is already going. It is queued, never pushed into the iteration in flight: the
runner reads the inbox before it starts each iteration and hands the message over as `told: <message>` in that
iteration's argument — the route the kick-off takes — and the iteration itself asks for what was queued
between stages. With `--now` as the first word, the iteration in flight is ended for it, the way `/cruise-stop
now` ends one, and the next iteration starts at once with the message; its increment commits are on the slice
branch, and the stage's uncommitted work is what it costs.

```sh
python3 {SCRIPT} tell <<'EOF'
$ARGUMENTS
EOF
```

The message goes in as written — the quoted heredoc is so a quote or a `$` inside it never reaches the shell —
and `--now` is read from its first word. {VERBATIM} It says whether the message waits for the iteration in
flight to end, resumes a parked run, or ended the iteration for it — and, where no runner is running, that the
first iteration of the next run carries it. What was queued and not yet taken is in `{INBOX}`; `/cruise-status`
lists it, and every message an iteration was given is in that iteration's entry in the run's log. A message
is not a setting: `/cruise-settings` is still how a rule of the run changes. `{layout.make} cruise-tell
MSG="…"` is the same from a terminal, `CRUISE_FLAGS=--now` for the immediate form.
"""


def under_cruise_section() -> str:
    """The section `/where-are-we` and `/whats-next` end with: how the answer changes while a `/cruise` runner is
    going, and — by the verb printing nothing otherwise — how it does not change at all where none is."""
    return f"""## Under a `/cruise` run

Run `python3 {SCRIPT} where` first. It reads the run's pid file, log and checkpoint, changes nothing, and
prints **nothing where no runner is running** — then everything above stands exactly as written, and this
section does not apply. Where it printed lines, a run is going. {VERBATIM} Then the answer changes in one
place: the step for a person — **Run:** here, the board's ➡️ *Next* row there — is not a command to type,
because the runner is on it, at the slice and stage those lines name. Say so, and say what a person can do
from here: `/cruise` watches the run, `/cruise-tell` steers it, `/cruise-stop` ends it; where the lines say
the run is parked, the step is what the park names, and `/cruise-tell` with it resumes the run. Nothing else
changes: the board is read from the same artifacts, and a slice the runner holds is one in progress, never
one to take.
"""
