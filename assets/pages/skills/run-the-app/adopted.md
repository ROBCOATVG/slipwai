---
name: run-the-app
description: How to run and demonstrate {{project-name}}. Use when asked to run, start, demo, or screenshot the app, or when a slice reaches its demo checkpoint. The applications here existed before this method did, so this skill says what is known and where to write the rest.
---

# Running {{project-name}}

The applications in this repository existed before the delivery method was installed around them, so nothing
here was generated and the factory does not know how any of them starts:

{{applications}}

`project.json` records, for each, how its own build answers the Make targets (`commands`), and the Makefile
under `layout.delivery` runs those. How to *run* one — the command, the port, what has to be seeded first, the
runtime it needs — is written in **`{{ledger}}`**, and that file is the whole of this skill: read it first. Where
it still says *not yet proven*, find the run path the way the existing README, container file or CI config
says, prove it once, and write it there — never here. This file is listed in `.written`: the factory's own,
replaced by `slipwai migrate`, and anything written into it is lost with the next version. The demo a slice
ends with is what the ledger exists for, and a run path that has to be rediscovered at the demo is the same
cost as having none.
