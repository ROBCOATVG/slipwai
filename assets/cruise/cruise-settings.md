---
description: Show or change how /cruise runs /sail on its own — who decides, how it releases, what it demos with, when it parks
argument-hint: [key=value ...]
---

# Cruise settings

`{{config}}` holds how `/cruise` runs `commands/sail.md` with nobody at the wheel. `commands/cruise.md` says what
each value does at the stops it governs. This command is how the settings are read and how they change:
checked, at any time, and never by quietly running an iteration under different rules.

{{settings-table}}

## No argument — show the settings

```sh
python3 {{script}}
```

Report every line as printed — the value and what it controls — and whether a run is enabled at all.

## Arguments — change them

```sh
python3 {{script}} --set $ARGUMENTS
```

Each argument is `key=value` from the table, and several may be given at once. The script refuses a key it
does not know, a value outside the ones listed, and a number that is not one, and writes nothing then. Report
a refusal in its words; do not work around it by editing the file. Then commit `{{config}}` on its own, with a
message naming the change: it takes effect at the next iteration, and nothing already running is interrupted.
`{{make}} check-agents` holds the file's shape whether it was edited by hand or through this command.

## When the request is in words

"Turn it on" is `enabled=true`; "ask me before every release" is `release=park`; "let the skipper decide
everything" is `decide=skipper-always`; "sail on opus" is `model=opus` (an identifier the harness's own model
flag takes; `null` is its default); "back to the defaults" is every key at the value the table shows.

Two kinds of request are **not** settings and are answered by pointing somewhere else. *How hard to push* —
how many streams at once, how much a slice may spend, how long a wait may last, how many retries — is the
telegraph, one lever, `slipwai telegraph <position>`. *Stopping a run that is going* is `/cruise-stop`
(`python3 {{fleet}} stop`), which asks every captain to stop at its next boundary. Neither belongs in this file,
and a setting added here for either would be a second place to look.
