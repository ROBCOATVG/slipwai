<!-- section: verbatim -->
Put every line it printed in your reply, unchanged, in a fenced block, before anything else: the harness folds a command's output, so what it said reaches a person only through your reply.
<!-- end section -->
<!-- section: watch-seat -->
run `python3 {{fleet}} watch`. It prints every stream's
lines as they are written — one line per claim, mark, demo, merge, park and message, each saying which stream
wrote it — and returns after a minute and a half, whether or not anything arrived. **Put every line it printed
in your reply, unchanged, in a fenced block, before anything else** — the harness folds a command's output, so
the feed reaches a person only through your reply — **and then run `watch` again at once**, unless a person
has typed something or the fleet has stopped.

What watching is not: it is not how the run continues. Every captain runs in its own process and reads its own
log; this session is a window, and closing it stops nothing. So a watch the harness cut short is watched again
rather than asked about, and a turn that ends here ends nothing — which is also why watching is never a reason
to run a stage of the ladder in this session. Where the harness can run a command in the background and
re-invoke this session with its output, run `watch` that way, so the turn ends between watches and a person
can type in the gap.

**Nothing arriving is a thing to report, not a thing to wait through.** Where two watches in a row print no
lines, say so and run `slipwai fleet` once: a stream that has written nothing for a while is either thinking
or stalled, and only the board tells them apart. Where it says stalled, say which stream, for how long, and
what its last line was.

**A person typing here is talking to you, not stopping the run.** Answer them — what the feed shows, what
`{{config}}` says (`python3 {{script}}` prints every setting and what it controls), what `slipwai fleet` says,
what `{{decisions}}` records — and change a setting through `/cruise-settings` where they ask; a captain reads
it at its next boundary. {{queues}} Then watch again. Only `python3 {{fleet}} stop` or
`{{make}} cruise-stop` ends the run, and only when they ask for that. {{stands}}
<!-- end section -->
<!-- section: under-a-fleet -->
## Under a fleet

Run `slipwai fleet` first. It folds the logs, changes nothing, and prints **nothing but an empty board where
no stream has written a line** — then everything above stands exactly as written, and this section does not
apply. Where it printed rows, captains are at work. {{verbatim}}

Then the answer changes in one place: for every slice a captain holds, the step for a person — **Run:** here,
the board's ➡️ *Next* row there — is not a command to type, because a captain is on it, at the slice and stage
the row names. Say so, and say what a person can do from here: `/cruise-watch` watches the lines arrive,
`/cruise-tell <stream>` steers one, `/cruise-stop` ends the run. Where a row says a stream is **waiting on
you**, the step is what it is waiting for, and `/cruise-tell` with it is what resumes that stream.

Nothing else changes, and one thing specifically does not: the board is read from the same artifacts as ever,
so a slice no captain holds is a slice a person may take, in this session, now. A fleet running on four
streams does not make the fifth somebody else's.

<!-- end section -->
