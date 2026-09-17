# The Spec Kit preset

`.specify/presets/event-modelling/` is where event modelling and
[MinimumCD](https://minimumcd.org/minimumcd/) are installed into Spec Kit, without editing a single Spec
Kit file in place.

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
specify preset resolve tasks-template     # which file actually wins, and from which layer
```

Then edit the file it names. If that path is under `.specify/templates/`, the override does not exist yet —
add it to `.specify/presets/event-modelling/templates/` and declare it under `provides.templates` in
`preset.yml`, rather than editing the core file. In YAML, **quote every string** in that manifest: an
unquoted `version: 1.0` parses as a float and Spec Kit reports the whole preset as corrupted without naming
the field.

`make check-speckit` enforces all of this and runs inside `make verify` — in-place edits, deleted managed
files, a preset with no or invalid `preset.yml`, and a declared override whose file is missing (which
silently falls back to the core template). It reads the committed manifests directly rather than shelling
out to the CLI, so it needs no Spec Kit CLI and no network. Upgrading is still the CLI's job:

```bash
specify integration status                # what has drifted, and what upstream suggests
specify self upgrade && specify integration upgrade claude
```

## What the preset overrides

Registered ahead of core templates, so `/speckit-constitution`, `/speckit-plan`, and `/speckit-tasks`
produce event-model-shaped output. Three templates are overridden today; `spec-template` and
`checklist-template` deliberately are not.

- **constitution-template** — fifteen principles pre-written (event sourcing + Decider, hexagonal, ATDD
  from GWT, idempotency, versioning as permanent event contracts, integrations covered by stub-backed
  tests pinned to a contract, privacy with erasure-before-first-event, and five continuous-delivery
  principles: trunk-based CI, one path to production, build-once with deploy/release decoupled, feedback
  budgets, and the same bar for agent-generated change), with placeholders only where a project genuinely
  differs.
- **plan-template** — a Constitution Check table that forces you to state stream identity, that `decide`
  returns events *or* a rejection, that every port has a fake, and what alerts (a read model is not
  detection). Plus a **Global Event Model** gate that will not let you plan a slice which is not on the
  timeline, and asks what the model *already* says about every event this slice touches. Plus explicit
  **Stubs and Deferrals** and **Complexity Tracking** sections.
- **tasks-template** — phases pre-shaped as Setup → Foundational → one slice → Polish, with the
  foundational phase already marked skippable when you start from this repo. The slice phase opens by
  recording the slice in the global model and closes by moving it to `implemented`, so the diagram is
  updated by the same task list that builds the code.

**The constitution ships as a template and must be ratified before any modelling work.** Every later gate —
the plan's Constitution Check table, the tasks phases, review — refers back to it, so an unratified
constitution silently weakens all of them:

```bash
grep -n '\[[A-Z_]\{3,\}\]\|\[ONE_PARAGRAPH' .specify/memory/constitution.md
```

If that matches anything, run `/speckit-constitution` and stop until it is done. `./init` cannot do this —
it is a bootstrap script, and this is a facilitated conversation.

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
