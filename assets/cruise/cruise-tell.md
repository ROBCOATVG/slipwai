---
description: Tell one stream something — a steer, a fact it lacked, an answer to what it parked on — which its captain reads at its next boundary
argument-hint: <stream> <what it should know or do next>
---

# Cruise tell

A person's word to a stream that is already going. It is written as a `told` line into **that stream's own
deck log**, which is the file its captain reads at every boundary; the captain answers with a `read` line
carrying the `told`'s own timestamp, so the receipt is evidence somebody was told rather than an assertion
that somebody looked.

```sh
python3 {{fleet}} tell <<'EOF'
$ARGUMENTS
EOF
```

The first word is the stream and the rest is the message, which goes in as written — the quoted heredoc is so
a quote or a `$` inside it never reaches the shell. {{verbatim}}

**The stream is required and the command refuses without one**, naming the streams there are. That is
deliberate: there is no single run to talk to any more, and four captains each somewhere different in their
work are rarely all meant to hear the same thing. `--everyone` as the first word is the deliberate broadcast.

Nothing has to be running for this. A `told` is a line in a log, not a signal to a process, so one written
while the fleet is stopped is read by whatever is lit next — `/cruise-status` says which streams have a
captain. A message is not a setting: `/cruise-settings` is still how a rule of the run changes, and say so
where somebody asks for one through here. `{{make}} cruise-tell STREAM=<name> MSG="…"` is the same from
a terminal.
