---
description: Take the watch seat beside a running fleet — print each stream's lines as they are written, watch again, answer a person typing here — without starting anything
---
# Cruise watch

The watch seat on its own. `/cruise` takes it after casting off, and a `/cruise-status` between reads the board
once and stops; this sits back down on the logs, in this session, and starts nothing. Where nothing is running
it still works — the logs are there either way — and prints nothing until something writes a line, which is
what `/cruise-status` is for telling apart from a fleet that is merely quiet.
`{{make}} cruise-watch` is the same seat from a terminal. To take it: {{watch-seat}}
