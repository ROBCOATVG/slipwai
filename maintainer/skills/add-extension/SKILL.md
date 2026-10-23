---
name: add-extension
description: Publish a slipwai extension — optional dev tooling a project elects at ./init — and meet the six obligations its entry point is held to. Use when adding a tool, not a language or a target.
---

# Adding an extension

An extension is optional dev tooling a project elects at `./init`. It never changes generated code, which
is the line between it and everything else: if what you are adding changes what the skeleton looks like,
you want `add-module` or `add-target`.

`docs/extensions.md` in the keel is the contract. This is how to get through it.

## Start it

```sh
slipwai package new lens
cd lens
make check
```

The scaffold passes all six obligations on the day it is written. That is deliberate: the first thing you
do is break none of them.

## The six, and what each one actually asks of you

| Obligation | What it means in your `init.py` |
| --- | --- |
| **Idempotent** | Running it twice does what running it once did. Write files whole; never append |
| **Non-fatal** | A tool that is not on this machine is a message and `return 0`, never a failed `./init` |
| **Projects** | Your `AGENTS.md` block sits between `<!-- extension:<key>:begin -->` and `:end` |
| **Gated** | Writing an index, a cache or a lock means shipping a `check-<key>.py` or a `check` hook |
| **Recovers** | Every message about a problem names the command that fixes it |
| **Merges** | Everything outside your markers is a person's and stays exactly as it was |

`python -m slipwai.conformance --extension .` runs four of them against a scratch project and reads the
other two. A check it could not reach says `not run` with the reason rather than passing quietly.

## Hooks

`slipwai hooks` prints the closed set. Attach to one; you do not add one.

```json
{ "hooks": { "init": "init.py", "after-stage": { "run": "hooks/sync.py", "stages": ["implement"] } } }
```

**A hook is a second belt.** The captain's controls work with every hook removed, a hook that fails is a
`hook` line and never a failed stage, and the one exception is `check`, which is a gate and therefore may
fail. Design accordingly: a hook that has to run for your extension to be useful is a hook whose failure
your users will meet as your extension silently not working.

## Your entry point runs in a project, not in slipwai

Standard library only. A generated project has no slipwai to import, and the import error arrives at
`./init` where nothing can explain it. What you *may* import is the toolkit's own `scripts/` — its
`extensions/guidance.py` is how an election is recorded and each harness's MCP file written.

## Publishing

Same four verbs as any package. `make register CHANNEL=…`, then a pull request.

## The mistake worth naming

**Writing to a file a person edits, outside your markers.** It will be the thing that makes people stop
running `./init`, and you will hear about it a long time after it starts happening.
