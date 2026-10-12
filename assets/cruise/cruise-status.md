---
description: Say what the fleet is doing — every stream, what it is on, what is waiting on a person — and which processes are up
argument-hint: [stream]
---

# Cruise status

Where the run stands, folded from the logs. Reading only; nothing here changes anything.

```sh
slipwai fleet $ARGUMENTS
python3 {{fleet}} list
```

{{verbatim}} **The two commands answer two different questions and the order matters.** The first is the work:
one row per stream, what it is on, when it last wrote a line, whether it is running, stalled or waiting on
somebody — and with a stream named as the argument, that stream's own lines instead. The second is only the
processes: which captains and which harbourmaster are up, by pid, and which were started and are not.

A stream can be running with nothing happening and a captain can be gone with the work finished, so never
report one as if it answered the other. Where a stream is **stalled**, say so first and say for how long; that
is the one state a board exists to make impossible to miss. Where something is **waiting on a person**, repeat
what it is waiting for, and say that `/cruise-tell <stream>` answers it. To watch the lines as they arrive,
`/cruise-watch`. To end the run, `/cruise-stop`.
