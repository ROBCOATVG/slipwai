# Changelog

No public releases yet. Release notes are recorded here newest first.

## 1.1.0 — MINOR

**`/drive` bounds its convergence loop, checks the branch before it reads the artifacts, and gives a
delegate the one legal way to watch a test fail.** Measured on a project running the generated workflow:
convergence and the rework it ordered cost one slice 12.9 times its implementation, because the stage's exit
condition was the judgement of the model being looped and nothing bounded it; a `/drive` on a branch
fifty-seven commits behind trunk wrote a second example map for a slice that had shipped, because every
artifact the ladder reads is a property of the commit it is on; and two delegates in a row reached for
`git stash` and a copied-aside backup, both forbidden, because they needed to observe a failure without
dirtying the tree and the safety page forbade the routes without naming one. Now the convergence rung stops
at two passes by default and appends what is still open as Phase 4 tasks, only a `CRITICAL` or `HIGH` finding
re-opens it and only a `CRITICAL` re-opens it past the bound, the first pass is handed every abstraction level to account for, the tree is checked clean after
every pass including a stopped one, and a stopped pass's last line is a lead to re-run rather than a finding
to file. The entry-stage evidence names the branch, its head and its distance from trunk, and an unreachable
remote reads as *could not verify*, never as *current* or as every slice unclaimed. The implement brief and
the safety page name the sanctioned move — change the production file, run the test, restore that one path —
and ask whether each RED was observed before the implementation existed. A brief may name where a fact lives
without asserting what it says, the host derives concurrency from disjoint manifests rather than waiting for a
`[P]` the task list only applies to production-code contention, and `./init` says to restart the session
before delegating, since a harness reads its agent types once.

**`/drive` delegates implementation on two settings a project sets once and changes at any time — how much
one delegate is handed, and how many RED tests one cycle opens with — with `/drive-settings` as the checked
way to change either.** A project running the generated workflow measured most of a slice's implementation
wall as each fresh delegate re-reading the same plan, map, precedent and test file, one task at a time, and
ten of that slice's tasks as proofs with nothing to turn green because a rule had been cut up to fit one test
per increment. `.specify/drive.json`, beside the models table, now carries `delegate` — `story`, every rule of
one user story as its own cycle in one context; `rule`; or `task` — and `cycle` — `rule`, a rule's examples
together, each failing for its own stated reason, stub-first; or `example`, one at a time. The defaults are
`story` and `rule`. A story is never a cycle unit, since that is the batch Principle V prohibits, and
`scripts/agents/drive.py` refuses it. Two vetoes override the defaults on a slice: no story tags falls to
`rule`, and a map without numbered rules falls to `task` and `example`. Whatever the boundary, siblings with
disjoint manifests run concurrently and a delegate may fan its work out inside its boundary under four
constraints; one cycle is never parallel. `make check-agents` holds the file's shape, the stage line says both
settings beside the model, and the implement entry records `delegate=`, `cycle=` and `split=N`, which `make
benchmark` shows per slice.

`/who-runs` is renamed `/model-delegation-settings`, so the two commands that set how `/drive` delegates read as a
pair: which model runs each stage, and how implementation is handed out and driven. Its behaviour is unchanged.

`/whats-next` joins `/where-are-we`: the board answers how far along the work is, and this answers what to do
now — one slice, one stage, one command and the reason, in at most six lines, read off the same artifacts and
running nothing.

With it, four smaller things the same project reported. The generated Makefile names its Go modules once, in
`GO_MODULES`, and both `lint` and `format` read it, so the two can no longer cover different paths. `./init`
installs Spec Kit at the release `project.json` now records as `speckitSource`, so restoring the ignored
projections is no longer a silent upgrade to upstream HEAD; `SPECIFY_SOURCE` still overrides it. The
extension contract gains its sixth obligation: a file the user must hand-edit is a merge target, never a write
target. And the event-model renderer says which variable to set when Chromium refuses to start as root.

**Catch-up.** `commands/who-runs.md` is gone and `commands/model-delegation-settings.md` arrives in its place;
the merge offers the deletion and `make agents` reprojects the harness copies, so a harness that still lists
`/who-runs` has not been reprojected. `.specify/drive.json` and the `speckitSource` field of `project.json` arrive
through the merge;
a project that wants one delegate per task, or one test per cycle, runs `/drive-settings` once. A project that
wants to stay on the Spec Kit it has edits `speckitSource` before its next `./init --integration`. `make
format` and `make lint` now read `GO_MODULES`: a Go module the project added under `packages/` by hand goes on
that line, once.

**`make mutation` on a Go service keeps its report, and `make mutation SINCE=<branch-or-commit>` prices the
stage per change rather than per repository.** The report was Gremlins' own `gremlins.json`, written inside
the staging tree `scripts/go-mutation.py` builds and deletes, so the target left a scrollback where a slice
record expects its evidence; it is now copied to `<service>/gremlins.json` before the cleanup, whether the
run passed or failed, and git-ignored beside `coverage.out`. `SINCE` scopes the run to the production files
that differ from that ref: a project measured 324 mutants in 31 minutes where seven belonged to the change
being driven, and a stage that expensive gets routed around rather than read. The unscoped target is
unchanged and is the full sweep.

The scope is computed from git before anything is staged, not handed to Gremlins' `--diff`, which is
unusable from a module in a subdirectory: it resolves changed paths against the repository root, matches
them against paths within the module, and reports every mutant SKIPPED and the run successful — verified
against 0.6.0, from the module directory and the repository root alike. Gremlins has no include list either,
so the scope is a complement of `--exclude-files` patterns generated per run, and because that flag replaces
the yaml's list rather than adding to it, the wrapper reads `.gremlins.yaml`'s own exclusions and passes
them back. A change confined to files the project already excludes scopes to nothing and says so, rather
than failing as a run that mutated nothing. An `exclude-files` written inline is a loud failure: a scope
silently read as empty is the one outcome that would mutate what the project excluded on purpose.

**Catch-up.** A Go service's mutation stage takes all of this through the merge — `scripts/go-mutation.py`,
the `mutation:` recipe, the `.gitignore` line, the note above the target and the yaml's comments — so there
is nothing to install and no answer to give. Two things to look at while resolving that merge. A project
that edited `apps/<service>/.gremlins.yaml` or the `mutation:` recipe meets a conflict in the comments or on
the recipe line: keep its own values and take the `$(if $(SINCE),...)`, which
is what makes `SINCE` reach the script. And `gremlins.json` is now ignored at any depth, the way
`coverage.out` already is — a mutation report a project keeps deliberately, as a slice record's evidence,
must not be named `gremlins.json` or it stops being committed; name it for the run it belongs to, as a
report recovered by hand before this version already had to be. Anything a project built to rescue the
report from the staging directory can go.

**The unit of a RED-GREEN-REFACTOR increment is one rule of the example map, not one test, and RED is a
failing assertion rather than a failing build.** A project running the generated workflow found the tasks
command routinely emitting tasks with an empty GREEN — proofs over behaviour earlier tasks had produced,
ten of one slice's twenty-five — every one passing the moment it was written, which the constitution
template classifies as a defect in the test. Both documents came from this factory and disagreed. The
proof-only task is a symptom of the unit being too small: a rule had to be cut up to fit one test per
increment, and the offcuts are the tasks that produce nothing. So Principle V in both profiles' constitution
templates now takes one rule with its examples as the increment, written together or one at a time as the
implementer judges, never spanning rules; and it adds the clause that makes that safe — whatever an example
names exists far enough to compile against before the example is written, so each example fails for its own
stated reason and a red build is never a red test. `/example-map` writes rules that own their examples
(`R1`…`Rn`, each heading carrying its scenarios), never renumbered once cited and never retrofitted onto a
map already implemented. The tasks brief and template cut one task per rule and fold a proof-only task into
the increment it guards, and the implement delegate takes a task or a rule, chooses how to drive it, and may
fan its increment out to sub-delegates over disjoint files under four constraints: a manifest that is a
subset of its own, evidence verified against the tree rather than relayed, nothing it spawns writing
`tasks.md`, and one report with one cycle's evidence.

**Catch-up.** A ratified `.specify/memory/constitution.md` is human-owned and is not overwritten by the
merge. Amend its Principle V by hand if this project wants the rule as its unit — the amendment is MINOR under
the template's own versioning policy, since work built one test at a time stays compliant — and carry the
stub-first clause even if it does not, since that clause holds whatever the unit. Maps already agreed keep
their shape; the rule-owned format applies from the next slice mapped.

## 1.0.0

**A `./init` rerun that asks nothing of Spec Kit no longer reinstalls it, so adding an extension or
re-answering an axis finishes where github.com is unreachable.** Every `./init` ran
`specify init --here --force`, and where the `specify` CLI is not already installed that means fetching
Spec Kit from its repository — so `./init --extension codegraph` in an offline sandbox, or
`./init --repository <url>` once the forge tools were finally there, died on the network before doing any
of the local work it was actually asked for. Now, when the argument scan leaves nothing to forward and
`.specify/integration.json` records an installed integration — the file only `specify init` writes, since
generation itself ships presets under `.specify/` — the bootstrap is skipped and the script says so.
Anything Spec Kit-bound still delegates exactly as before: the first `./init`, and any rerun passing
`--integration <agent>` or another forwarded flag.

**Slipwai is available as an open-source project.** Version 1.0.0 is the first
release in the public version line: a one-shot scaffolder for product
monorepos, with generated verification, delivery workflows, migration support,
and coding-agent guidance.

