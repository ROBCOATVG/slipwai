# The Spec Kit preset

`.specify/presets/standard/` is where [MinimumCD](https://minimumcd.org/minimumcd/) is installed into Spec
Kit, without editing a single Spec Kit file in place.

- [Never edit a Spec Kit file in place](#never-edit-a-spec-kit-file-in-place)
- [What the preset overrides](#what-the-preset-overrides)
- [Extension hooks](#extension-hooks)

## Never edit a Spec Kit file in place

Spec Kit installed the `/speckit-*` skills, the five templates in `.specify/templates/`, and the bash
scripts they call — and it recorded a SHA-256 for each in `.specify/integrations/*.manifest.json`. Those
hashes are what make `specify integration upgrade claude` automatic: untouched files are replaced, edited
ones are preserved and reported.

`make check-speckit` holds every listed file to its hash, with one reading: the `/speckit-*` skills sit in the
harness directory — `.claude/skills/` for Claude Code — which is in `.gitignore` because the project's own
projections land there too, so a fresh clone has the manifest and none of those files. The gate reads an
absent harness directory as a clone nobody has run `./init` in yet and says so; a file missing or edited while
its directory is present is drift.

So editing one in place does not fail loudly — it quietly converts every future upgrade into a manual
reconciliation, because the upgrade now protects your edit instead of delivering the new upstream version.

**Customisations go in the preset**, which shadows a core template by name at the priority
`.specify/presets/.registry` sets. Core stays pristine, and anything not overridden keeps inheriting
upstream improvements. To change how a template behaves:

```bash
specify preset resolve plan-template      # which file actually wins, and from which layer
```

Then edit the file it names. If that path is under `.specify/templates/`, the override does not exist yet —
add it to `.specify/presets/standard/templates/` and declare it under `provides.templates` in
`preset.yml`, rather than editing the core file. In YAML, **quote every string** in that manifest: an
unquoted `version: 1.0` parses as a float and Spec Kit reports the whole preset as corrupted without naming
the field.

From Spec Kit 1.0.9 on, its bash scripts compose the templates a preset declares with PyYAML, on the bare
`python3` they call — without it, `.specify/scripts/bash/create-new-feature.sh` stops with "PyYAML is
required to resolve preset template composition". `./init` checks for that after installing Spec Kit and
installs it where it can: into the user site, or — where this Python refuses pip outside a venv (PEP 668:
Homebrew's, Debian's) — into a venv at `.delivery-tools/venv` that shares the system's packages, printing the
`PATH` line that puts it first. Rerun `./init` after changing the Python on your PATH.

`make check-speckit` enforces all of this and runs inside `make verify` — in-place edits, deleted managed
files, a preset with no or invalid `preset.yml`, and a declared override whose file is missing (which
silently falls back to the core template). It reads the committed manifests directly rather than shelling
out to the CLI, so it needs no Spec Kit CLI and no network. Upgrading is still the CLI's job:

```bash
specify integration status                # what has drifted, and what upstream suggests
specify self upgrade && specify integration upgrade claude
```

## What the preset overrides

One template, and deliberately only one. Overriding a template is a decision to maintain it forever, so it
is taken only where the core version would actively mislead — and the constitution is the one place it
does. This repository has a floor that `make check-constitution` enforces; the core constitution template
states no floor at all, so drafting from it produces a document that reads as ratified and fails the gate.

- **constitution-template** — fifteen principles pre-written, with placeholders only where a project
  genuinely differs. Five of them are minimum CD: continuous integration on trunk, one automated path to
  production with the pipeline as release authority, build-once with deploy separated from release,
  feedback budgets that gate the suite, and the same Definition of Deployable for agent-generated change.
  The rest are what the skills in `skills/` teach: idempotency and retry safety, the complexity rung
  recorded rather than assumed, the hexagonal boundary, acceptance-driven development from Given/When/Then,
  stub-backed integration tests pinned to a contract, observability with alerting rather than dashboards,
  versioning and tolerant readers, privacy with erasure designed before the first record, ubiquitous
  language and domain types, quality gates, and a governance clause.

`spec-template`, `plan-template`, `tasks-template` and `checklist-template` are **not** overridden. Nothing
in this profile's floor is expressible only in them, so they fall through to core and pick up upstream
improvements for free. (The event-modelling profile does override plan and tasks, because a slice on a
global event model is a shape the core templates have no place to record. This profile has no such shape.)

**The constitution ships as a template and must be ratified before the first slice is planned.** Every
later gate — the plan's Constitution Check, review, `make check-constitution` itself — refers back to it,
so an unratified constitution silently weakens all of them:

```bash
grep -n '\[[A-Z_]\{3,\}\]\|\[ONE_PARAGRAPH' .specify/memory/constitution.md
```

If that matches anything, run `/speckit-constitution` and stop until it is done. `./init` cannot do this —
it is a bootstrap script, and this is a facilitated conversation.

Two boundaries the gates hold from opposite directions, once that file exists:

```bash
make check-constitution   # it still carries minimum CD and the practices the skills teach
make check-speckit        # it does not mandate event sourcing, which this profile did not scaffold
```

The second one is not a style preference. `project.json` claims no event-sourcing capability here, so a
constitution mandating it would be ratifying an obligation nothing in the repository can meet. If that is
the architecture you want, scaffold with `--profile event-modelling` instead.

## Extension hooks

Every `/speckit-*` command looks for `hooks.before_<phase>` and `hooks.after_<phase>` in
`.specify/extensions.yml` around itself, and is told to say nothing when the file is absent — which agents
narrate anyway, so most projects meet this feature as a line explaining that two hooks were skipped.

The hooks registered there wrap the constitution phase on both sides — `before_constitution` prints the
required coverage while it is still cheap to write, `after_constitution` checks what was written before the
phase that could fix it in one edit has ended — plus a host compact suggestion after tasks, convergence after
implement, and a promise trace after converge. Read the file: each one carries its own reasoning.

Two things to know before adding your own. **Never set `condition:`** — the commands are instructed not to
evaluate condition expressions and to skip any hook carrying one, so it prevents the hook firing rather than
narrowing when it does. And the file is in no Spec Kit manifest, so it is yours to edit; `make check-speckit`
has no opinion about it.
