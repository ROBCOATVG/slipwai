---
description: Show or change which model runs each stage of /sail
argument-hint: [stage=role | harness.role=identifier ...]
---

# Model delegation settings

`.specify/models.json` says which model runs each stage of `/sail`'s ladder, by role — `strong` where a
stage decides what to build or whether it was built, `fast` where the input is already fully specified on
paper — and what each role maps to on the harness this project is initialised for. This command is how the
table is read and how it changes: as and when, in one step, checked, and never by quietly picking a different
model inside a delegation.

## No argument — show the table

```sh
python3 scripts/agents/models.py
```

Report it as printed: the installed harness, whether it can choose a model for a sub-task at all and how
(`scripts/agents/registry.json`, `subagentModel`), then each stage's role, the model or the host model, and
why. No harness installed is a line of its own — `./init --integration <agent>` records one.

## Arguments — change it

Each argument is one of two edits, and the first thing to decide is which one the person means:

- `stage=role` moves a stage between roles — `implement-shipwright=strong` puts implementation back on the
  model running `/sail`. The keys are the stages: {{stage-keys}}, and `default` for any stage without a row of its
  own. A stage whose key ends in a crew member's name is one with a delegate; the rest run on the host. A
  stage's name before the rename — `implement` for `implement-shipwright` — is still accepted and resolved.
- `harness.role=identifier` changes what a role runs on — `claude.fast=haiku`, or `claude.skipper=opus` to
  put a bigger model on `/cruise`'s product decisions than on driving. `host` is the model running `/sail`;
  `null` is no identifier mapped, which the line before each stage then says.

Pass them through exactly as given:

```sh
python3 scripts/agents/models.py --set $ARGUMENTS
```

It rewrites the agent types as it goes: `agents/sail-<stage>.md` is projected into the installed harness
with the model this table resolves, so a change here that left them behind would take effect on one harness
and not another, and `make check-agents` would report drift in a file nobody edited. The line saying so is
part of the output; report it.

The script refuses a stage the ladder does not have, a harness the registry does not know or records no
mechanism for, and any change that would leave the table malformed — and writes nothing then. Report a refusal
in its words; do not work around it by editing the file. A role a stage newly names is added as `null` under
every harness: say so, and ask for the identifier rather than inventing one.

Then show the line for each stage the change touches (`python3 scripts/agents/models.py implement`) and commit
`.specify/models.json` on its own, with a message naming the change. The choice is versioned with the project,
and a change buried in a slice's commit is a change nobody finds.

## When the request is in words

"Use the cheap model for implementation" is two possible edits, and the identifier is the part not to guess.
Where the harness's mechanism takes an alias the registry names (`identifiers` under its `subagentModel`), use
that spelling; otherwise ask which identifier, since model names are provider-specific and go stale. Never map
a role for a harness this project is not initialised for, and never for one the registry says cannot switch —
the script refuses the second, and the first is a setting nothing reads. A change takes effect at the next
stage `/sail` runs; nothing already running is interrupted. `{{make}} models` prints the same table.
