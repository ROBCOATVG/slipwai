MINOR

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
