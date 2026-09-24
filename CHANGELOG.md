# Changelog

No public releases yet. Release notes are recorded here newest first.

## 1.2.1 — PATCH

**`make check-imports` no longer reads a test of the domain as domain code.** The gate took any file with a
`domain/` or `application/` segment in its path for that layer, so a Decider spec at
`tests/domain/<context>.spec.ts` — exactly where `adversarial-testing` and `docs/event-modeling-to-code.md`
send it — was refused for importing its test runner ("domain imports 'vitest' — only zod may be imported
here"), and so was a test beside the Decider (`decider.test.ts`, `decider_test.go`, `test_decider.py`,
`DeciderTest.java`) that named a fake adapter. Test directories (`test/`, `tests/`, `__tests__/`) and test
files are now left to the level they are; the layer itself is held exactly as before. The path is also read
relative to `apps/` and `packages/`, so a checkout that happens to sit under a directory called `domain` no
longer turns every file into domain code.

**A `/cruise` run can no longer make a gate pass by changing the gate.** A run met `check-ux-gates` failing
because two of the kit's scripts crash where Chrome is not installed, and the bosun patched
`scripts/check-ux-gates.py` to report that as skipped, committed it, and went on. Its brief now forbids
touching anything under `scripts/`, the `Makefile`, anything under `tools/`, CI or a harness's hook settings,
and says what a gate the tree cannot satisfy becomes: a park with the gate's own words as the reason. The rule
is held in two places rather than said louder. `.claude/settings.json` runs `scripts/agents/cruise.py guard`
as Claude Code's `PreToolUse` hook on every editing tool, and in a session the runner started it refuses an
edit to any of those paths before it lands. And the runner takes the content of every gate and control before
each iteration and compares it after, on every harness: a file modified, deleted or added — a file installed
under `tools/` excepted — parks the run at once, names the files on the log entry as `controls_changed`, and
counts the iteration's last line for nothing. A person's own session meets neither.

**`check-ux-gates` runs on Playwright's own Chromium where Chrome is not installed, and never reports a
crash as a pass or a failure.** The gate now asks once which browser Playwright can open — Chrome, its bundled
Chromium, or neither — and where only the bundled one opens, starts every render gate with a Node preload that
retries the kit's `channel: 'chrome'` launch without the channel, so `verify_responsive.mjs` and
`verify_target_size.mjs` run there like the kit's other three. Where no browser opens, or Playwright is not
resolvable, the render gates are counted skipped without running one, and a gate that still fails on its launch
is reported skipped rather than as a finding; `UX_GATES_REQUIRE=1` still makes every skip a failure.

**`stop --now` returns once the runner has gone, not once it was told to go.** The runner ends the iteration's
session before it exits, which takes a moment, and a `start` typed the moment `stop --now` returned found the old
runner still alive and declined to start one — after which nobody was running and the watch seat found nobody to
watch. It now waits for the runner to be gone, up to thirty seconds, and says so if it is still ending after that.

**`/where-are-we` and `/whats-next` answer beside a running `/cruise`.** Both used to answer as if the person's
session were about to take the next slice — "Run: /drive S13" while the runner was on S13. Each now runs
`scripts/agents/cruise.py where` first, a read that prints the runner's iteration, the checkpoint's slice, stage
and next step, and a park's reason, and puts those lines in the reply; the step for a person is then the runner's,
with `/cruise`, `/cruise-tell` and `/cruise-stop` as what they can do. Where no runner is running the verb prints
nothing and both commands answer exactly as before, so nothing changes outside a run.

**`/cruise-watch` takes the watch seat on its own.** `/cruise-status` reads once and stops, and a session that
typed it to answer a question had left the seat; the way back was `/cruise`, which reads as starting a run.
`/cruise-watch` sits back down where the feed left off and starts nothing, with the seat's rules — its words
and `commands/cruise.md`'s are one text — and `make cruise-watch` stays the same seat from a terminal.

**Catch-up.** `slipwai migrate` brings the hook, the runner, the gate and the command text. A run that already
carries a patched gate is found by `git log -- scripts/` and reverted by hand; the runner parks on the next
change, not on the standing one.

**A slice branch run by `/cruise` can pass `make verify` again.** `check-slice-scope` refused two files that
two other gates require on a slice branch. `specs/<feature>/decisions.md`, which `/cruise` writes where the
ladder took the decision — during a slice's stages, that is the slice's branch — and which `check-decisions`
holds to `Written to` paths that exist only there, so the record could pass on neither branch. And
`docs/event-model/model.drawio`, which `check-drawio` requires to match the `model.yaml` block the slice is
allowed to advance, and which the scope gate refused as the host's docs. Both are now a slice's to write:
`decisions.md` beside the other cumulative artifacts the host merges in split order, and the canvas because
its own gate holds it to the model, so it can carry nothing of the slice's own. `commands/drive.md` and the
`drive-slice` brief say so, and say the canvas is regenerated again after each merge.

**A slice is compared with the newest `main` the checkout knows, not with `origin/main` first.** Both
`check-slice-scope` and `check-migrations` took `origin/main` as the base whenever it existed, so a `main`
that had moved locally and not been pushed — a migration run there, then merged into the slice — put its own
files into the slice's diff, and the slice stayed red until `main` was pushed, which `/catch-up`'s *green
before pushed* rule forbids while it is red. Every `main` is now tried and the base that is newest wins.
`/catch-up` and the upgrading page also say where a migration runs: on `main`, on a clean tree, never on a
`slice/<id>` branch.

**A decision `/cruise` takes that would cost a migration to reverse is also an ADR.** `commands/cruise.md`
now puts the `architecture-decisions` skill's one question to every decision entry — an event's schema or
name, stream identity, tenancy, the store, personal data, identity, a dependency, a contract — and where the
answer is a migration, the driver writes `docs/adr/NNNN-<title>.md` at `Proposed`, numbered the way `D<n>`
is, and names it in the entry's `Written to`. The skipper returns the five sections with its entry, or says
in a line why the decision is reversible. The owner brief and the cruise report say a person accepts them.
`check-slice-scope` allows a new ADR on a slice branch, and refuses an edit to one that stands.

**Catch-up.** `slipwai migrate` brings the two gates and the command text. A slice branch red on
`decisions.md` or `model.drawio` passes as it stands after the merge; a migration already run on a slice
branch is undone with `git reset --hard ORIG_HEAD` there and run again on `main`.

## 1.2.0 — MINOR

**A benchmark bracket now counts only its own lines, an entry a session leaves open is cut off rather than left
running, and a delivered slice with no record fails `make verify`.** A run's records showed all three holes: two
skipper rounds opened while the implementers were running counted the implementers' Sonnet tokens as the
skipper's; two entries opened by an iteration that was then stopped stayed open for good; and a whole slice was
delivered with no record at all, through a gate that only ran the script's self-test. Now a line goes to the
innermost bracket covering it, and a delegate's lines to the bracket whose stage owns the type that ran them,
across every record in the project, with the request count left to another bracket written into the entry's
`read`. The `/cruise` runner closes what an iteration left open — when it ends, or when `stop --now` ends it —
and so does the next `start` in the same record, which used to stack a second entry on top and leave the first
open for good: each is `cut off` with the reason, its tokens read from the transcript it left up to where that
transcript stopped, and no signals, and the overview's notes say so. And
`python3 scripts/agents/benchmark.py check`, run by `make check-benchmark`, fails on an entry still open, on a
slice the ladder calls done (a row in `slices/README.md`, or `status: implemented` in the event model) with no
record or an unclosed one, and on a feature with done slices and no record above the slice loop. Two things
found on the way: `make check-decisions` now also holds every finished slice to a row in `adversary-log.md`,
the attack or the recorded skip `/adversary` writes after every acceptance, which nothing checked; and the
runner ends an iteration's whole process group, so `stop --now` no longer leaves a dev server the session
started running on.

**Catch-up.** `slipwai migrate` brings the script, the runner and the Make target. A project whose delivered slices
have no record will fail `make verify` on the next run: those brackets cannot be recovered, so either write the
missing records by hand as unbracketed entries, or accept the finding until the next slice.

**A bosun's decision entry passes the gate it was written for.** `commands/cruise.md` tells `drive-bosun` to
record every workaround as a decision entry with `Decided by: drive-bosun`, and `scripts/check-decisions.py`
accepted only the host, the skipper and a human — so the first run that needed the bosun left `make verify`
failing on the entry the bosun was told to write. The gate and the record template now name the bosun, alone
or with its model, beside the other four.

**Catch-up.** `slipwai migrate` brings the gate and the command text; an entry already written as
`drive-bosun` passes as it stands.

**Every tool the factory gives a project now reaches a headless `/cruise` iteration, the code index included.**
A run in a fresh checkout kept `check-codegraph` green with `codegraph sync` and answered every *who calls this*
with grep, because the only thing that connected an agent to the index was the user-level config CodeGraph's own
installer writes on the one machine `./init` ran on — nothing a container, a CI runner or the runner's fresh session
ever sees. Three things change. `./init --extension codegraph` (and `slipwai migrate`, `make agents` or a later
`./init --integration <agent>`, for a project that adopted it earlier) names the server, started through `npx`
so the connection is true wherever Node is, in the project-scoped MCP file of every harness installed here and
commits it: `.mcp.json` for Claude Code, `.codex/config.toml` for Codex, `.gemini/settings.json` for Gemini CLI,
`.cursor/mcp.json` for Cursor, `opencode.json` for opencode, `.kiro/settings/mcp.json` for Kiro — the registry's
new `projectMcp` column, each read from the harness's own documentation and dated, null with a reason for the
thirty harnesses nobody has checked, which reach the index through the CLI from the shell. Every file is a merge
target, so a server a person added stays. Every project's `.claude/settings.json` approves that server and allows
its tools, inert until the file exists. And the runner passes each row's `headlessFlags` whenever the file exists —
`--mcp-config .mcp.json` on Claude Code, whose print session in a checkout nobody has trusted ignores the
project's settings and the servers they approve (its hooks still run); a one-run trust override on Codex, which
skips every project `.codex/` layer in an untrusted project — while the Claude Code row names every tool family
the ladder reaches for in `--allowedTools` — `Bash`, `Skill`, `Agent`, `WebFetch`, `WebSearch`,
`mcp__codegraph__*` — each tried from a print session first. What an iteration needs travels on its command line. The runner says before the first iteration how the index will be
reached, or that it cannot be, and `status` says afterwards in how many iterations it was asked, so an index kept
fresh and never queried is seen rather than suspected; an index call is one line of the feed like any command.

**Catch-up.** `slipwai migrate` writes each installed harness's project MCP file where `codegraph` was adopted,
the settings entries, the registry column and the runner; commit the new files.

**A typed `/cruise` now keeps going on every harness: it starts the runner, detached, instead of running the
ladder in a session nothing re-invokes.** The loop that continues a run used to have two paths — the runner
from a terminal, and an in-session ladder that only held where Claude Code's Stop hook could refuse a turn — so
in Cursor and every other harness the session ended on `cruise: continue` and waited for a person. Now the
runner is the one continuation mechanism: `python3 scripts/agents/cruise.py start` detaches it from the
session, writes its pid and a log under `.specify/`, and the command ends its turn with what `start` printed;
`stop` (and `make cruise-stop`) ends a run after the iteration in flight, or at once with `--now`; `status`
says whether a runner is running. The runner drives whichever CLI harness the machine has: the registry's
`headless` column now has a verified command for 27 of the 36 harnesses, each read from its own documentation
and dated, and the nine without say why; the runner takes the first installed harness with one on the PATH,
else any harness on the PATH, and asks every harness but Claude Code to read `commands/cruise.md` rather than
resolve a slash command. Hooks are the seatbelt inside a runner's iteration, not the control: the registry's new
`hooks` column says which harnesses can refuse the end of a turn, `scripts/agents/project.py` writes the hook
file where its shape was read (`.cursor/hooks.json` for Cursor, merged into `.gemini/settings.json` for Gemini
CLI), and `stopping` answers each in its own spelling and only in a session the runner started.

**Catch-up.** `slipwai migrate` brings the new runner, command text, Makefile targets and registry; a
repository with Cursor or Gemini CLI initialised gets its hook file on the next `./init` or `make agents`. The
stop file, the runner's pid and log, and the kept last response are now gitignored.

**Seven things `/drive` does, or a person configures, no longer drop out under `/cruise`.** A sweep of the
autopilot against the ladder it runs found each of these, and each is now held by a test or a gate. A Codex
iteration can write: `codex exec` is read-only by default, so its registry row now runs `--sandbox
workspace-write`. The ladder's concurrent slices can edit their worktrees: a Claude Code print session under
`acceptEdits` is refused every edit outside its working directory, and the worktrees sit beside the checkout,
so the row's new `worktreeFlags` pass `--add-dir` for the directory the checkout sits in on every iteration.
The runner no longer drives a CLI that is on PATH but was never initialised here — nothing is projected for
it, so `/cruise` was unknown to it, and a run spent its stuck budget on that before parking for the wrong
reason; the refusal names the `./init --integration <key>` that adds the CLI beside what is installed. The
`hand` setting reaches the hand: the delegation brief names the rung the ladder starts at, the delegate's own
brief says it never climbs above it, and `http` and `cli` mean what the settings table says. A fetch that
could not run — no remote, or one the environment cannot reach — is what the ladder says it is, said in the
evidence line, and the run goes on; the first stop row used to park there, which parked a local-only project
on its first iteration for good. What a demo leaves running is stopped: the command stops the app once the
hand's verdict is recorded, since no person is coming to open it, and the runner ends the iteration's process
group after the session exits and says so in the feed, so the next slice's demo finds its port free. And a
refusal inside an iteration — `enabled` turned off mid-run, a missing specification — ends on a last line the
runner reads, `cruise: stopped: human` or `cruise: parked: …`, rather than a plain sentence the runner counted
as no progress. Along the way the runner now reads `.specify/cruise.json` before every iteration, which is
what `/cruise-settings` always promised: a budget, the stuck window, the poll and `enabled` change at the next
iteration, and a file a hand edit broke keeps the last good settings and says so. And the driver's own model
is a setting: `.specify/cruise.json` gains `model` (`/cruise-settings model=opus`; `null`, the default, is the
harness's own), which the runner passes through the registry row's new `modelFlag` — `--model` on Claude Code,
Codex and Gemini CLI — on every iteration, saying before the first which model the iteration runs on or that
the row has no flag for it. Under `/drive` a person chose that model when they opened the session; under
`/cruise` nobody did, and every stage `.specify/models.json` maps to `host` ran on an unchosen default.

**Catch-up.** `slipwai migrate` brings the runner, the registry rows, the command text and the hand's brief;
`make agents` re-projects the delegate types. A project driven by Codex needs nothing else. A project whose
`/cruise` was reaching the ladder through a CLI it never initialised now needs `./init --integration <key>`
for that CLI, which the refusal names.

**A person can tell a running `/cruise` something without stopping it.** `/cruise-tell <message>` in any
session, `make cruise-tell MSG="…"`, or `python3 scripts/agents/cruise.py tell …` queues the message in
`.specify/cruise-inbox.jsonl`; the runner reads the inbox before it starts each iteration and hands the message
over as `told: <message>` in that iteration's argument — the route the kick-off takes — and the command reads it
before the first stage and acts on it first, writing what must outlive the iteration into the owner brief or a
decision entry. Between stages an iteration runs `python3 scripts/agents/cruise.py told` for what was queued since
it started, so a message can land mid-iteration without cutting a stage. A parked run resumes with a message
within the second, and a message waiting when a run is stuck goes in place of the bosun's `unblock:` iteration.
`--now` as the first word ends the iteration in flight for the message, the way `stop --now` does, and starts the
next at once; the log entry says so, and an interrupted iteration is not counted by the stuck detector. Every
message delivered is in that iteration's entry in `specs/cruise-log.jsonl` under `told`, and `/cruise-status` lists
what is queued. The watch seat queues what a person types for the run the same way and repeats what the script
said. Every setting keeps its meaning; a message never changes one.

**Catch-up.** `slipwai migrate` brings the runner, the command files and the Make target; the inbox and the
delivered file are gitignored.

**The session that types `/cruise` now watches the run, and a run can no longer park on its first command.**
`/cruise` used to start the runner and end its turn, so a run that parked thirty seconds in — as every run in a
TypeScript or Go project did, because the generated `.claude/settings.json` allowed no `python3` and the headless
iteration under `acceptEdits` cannot ask — was found only by someone typing `make cruise-status`. Three things
change. `python3 scripts/agents/cruise.py watch` is the watch seat: it prints the feed from where the last watch
left off and returns at the iteration's end, a park, the run's end, once the feed has gone quiet for twenty
seconds, or after a minute and a half with nothing new, saying which — on quiet, because a harness shows a
command's output when it returns, and the feed has to reach a person as it happens; the command runs it after `start`, again while the run continues, and ends the turn when
it says parked or ended, and a person typing into that session is answered — the feed, the settings, the status,
the decision log, a setting changed through `/cruise-settings` — and then watched for again; every line `watch`
printed goes into the reply unchanged, because a harness folds a command's output and the feed has to reach the
person. `make cruise-watch` is the same seat from a terminal, and two commands sit beside it in every session:
`/cruise-status` (the runner's state and the feed's tail) and `/cruise-stop` (after the iteration in flight, or
`now`). The feed is the harness's own event stream rendered one line per command, file,
and delegate out and back: the registry's `headless` row for Claude Code now runs `--output-format stream-json
--verbose` and Codex's `exec --json`, each row saying so with its `stream`, the runner keeps the raw stream in
`.specify/cruise-stream.jsonl` beside the log, and a refused permission is in the feed the moment it happens.
And an iteration is no longer refused its own commands: Claude Code's headless row runs with `--allowedTools
Bash`, the shell allowed wholesale because no list names the compound commands an agent writes, while the
project's new `deny` rules — a plain force-push, `reset --hard`, `clean` — still refuse what they name; the
allowlist every project's `.claude/settings.json` carries now includes the toolkit's own scripts
(`python3 scripts/*`) and the Git a slice is made of, whatever the language, so a person's own session stops
prompting at every hook and gate, and a test holds it to every command `commands/cruise.md` and the hooks
issue. Which tools a whole build needs is measured rather than guessed: `python3 scripts/agents/cruise.py
denials` lists every refusal in the raw stream by tool and command with the iterations it happened in, and
`status` says when there are any. What is typed
after `/cruise` is the kick-off — what the run is for, where the PRD is — and reaches the first iteration only;
every later one runs bare and derives from disk, so the first iteration writes down what must outlive it. Every
setting keeps its meaning.

**Catch-up.** `slipwai migrate` brings the runner, the command text, the Make target, the registry rows and the
allowlist; `make agents` re-projects the hook files. The raw stream and the watch cursor are gitignored.

**A generated project can now run `/drive` on its own until the specification is satisfied: `/cruise`.**
`/drive` stops for a product decision, an unavailable input, an exhausted split and the demo, because three of
those belong to a person. `/cruise` runs the same ladder with nobody at the wheel: it decides what the ladder
would have asked — on the host where the stage recommends an answer or a standing decision covers it, through
a new `drive-skipper` delegate where the question is open — runs each demo as the actor through a new
`drive-hand` delegate, with a browser where the slice has a screen, and audits the specification against what
shipped when the split runs out, so *done* means satisfied rather than exhausted. Every decision is written
where `/drive` would have written a person's and once more in `specs/<feature>/decisions.md`, every demo in
the slice's `demo-log.md`, and a person overturns either by editing it. A block is work before it is a stop: a third delegate, `drive-bosun`, stubs the
missing thing behind its port, takes the reading that keeps every MUST, or repairs the run, and writes down what
it did; a run parks only at the catastrophic — destroying, releasing, spending, weakening security — or when the
bosun could not move it. It stops for a human and for nothing
else: `scripts/agents/cruise.py run` (`make cruise`) re-invokes it with a fresh context until it says `done`,
parks when nothing can move, and detects a run that stopped making progress. `.specify/cruise.json` holds its
settings, `/cruise-settings` changes them checked, and it ships disabled: a project has to ask for this.
`.specify/models.json` gains a `skipper` role and the `skipper`, `hand` and `bosun` stages, and the benchmark records
`driver=cruise` on every stage a run bracketed.

Three things the first runs taught it. An iteration has a unit before the split exists — the upstream stages
together, through to the first ready set — and ends only on one of its four last lines: on Claude Code,
`.claude/settings.json` runs `scripts/agents/cruise.py stopping` as the `Stop` hook, which refuses a turn that
ends mid-iteration on anything else, or on `continue` in a session no runner started (the runner marks its
sessions with `CRUISE_RUNNER`; `cruise.py loop` says which kind a session is), handing back the checkpoint's
`Next:` line. And the session running `/cruise` allocates every identifier a decision carries — the `D<n>`
goes out in the skipper's brief, the entry comes back and is appended in number order, requirements and
criteria are numbered after concurrent delegates return — so four delegates deciding at once cannot come
back as two `D3`s with overlapping requirement ranges.

**Catch-up.** `slipwai migrate` brings the command, the three agent types, the settings file and the two new rows
of `.specify/models.json`; then `./init` reprojects the agent types and, as with every new type, the harness
reads them at its next session start. Nothing runs until `enabled` is set with `/cruise-settings enabled=true`.

**A service's purpose and bounded contexts can be recorded after the scaffold: `slipwai describe-service`.**
`purpose` and `contexts` are what the delivery loop places a slice against, and `generate` and `add-service`
take them at scaffold time — but a purpose is often left unsaid at the start, and the contexts are found later,
in the model's lanes or the specification's vocabulary, which is where `/drive` says to record them. Until now
that meant editing `project.json` by hand against a file the factory owns, while `docs/architecture.md` went on
saying "no purpose recorded yet". `describe-service <name> --purpose "..." --context <name>` edits the entry in
place — a field given replaces what was recorded, one not given is kept — and regenerates every file that
prints the two fields, derived the same way `add-service` derives its set. `/drive`, `/cruise`, the
architecture page and the `add-service` report now name it wherever they say a purpose or a context is
recorded.

**An event-profile project now commits a draw.io canvas of its model, and `make verify` proves it current.**
Everything `make model` draws — the slice diagrams, the README's segments, the whole-timeline SVG, the
browsable page — is rendered through a headless browser, which is why none of it could ever be committed or
checked on every commit: a picture nothing checks quietly stops matching `model.yaml`, and that is how a
model stops being trusted. `make model-drawio` writes `docs/event-model/model.drawio`, the whole timeline as
one editable draw.io page, from arithmetic and a string — no browser, no account, no network — and
`make check-drawio`, inside `verify`, regenerates it in memory and fails on a missing or stale file with the
fix in its message. The canvas advances in the same order as the Mermaid diagram, puts each box in the same
lane, draws the same arrows and uses the same colours, because the lane and the arrows are answered once in
`scripts/event-model/model.ts` and the palette is one table both renderers read. A read of an event modelled
far earlier detours below the bands rather than crossing every box in between, every reader of one event
shares that event's corridor, and a caption under each reader names every event it reads.
`make model-drawio-test` runs the planner's and serialiser's own tests. `make model` and `make check-model`
are unchanged.

**Catch-up.** After merging, run `make model-drawio` and commit `docs/event-model/model.drawio`; until then
`make verify` fails on the missing canvas, and says so. `make verify` now needs Node in every event-profile
project — it installs `scripts/event-model`'s three dependencies on first run — and the regenerated
`.github/workflows/verify.yml` sets a Node up where the project has none of its own.

**`./init` checks that Spec Kit's scripts have the PyYAML they compose the preset templates with, and puts it
right where it can.** From Spec Kit 1.0.9 its bash scripts read a preset's `preset.yml` through the bare
`python3` they call, and a project whose python3 lacks the module learned so at its first `/speckit-specify`:
"PyYAML is required to resolve preset template composition", with no remedy — and on a Homebrew or Debian
Python the obvious `pip install` is refused too (PEP 668). Where the installed Spec Kit's scripts mention it
and `python3` cannot import it, `./init` now installs it into the user site, or, where that Python refuses
pip outside a venv, into a venv at `.delivery-tools/venv` that shares the system's packages and prints the
`PATH` line that puts it first; where neither is possible it says exactly what to install. Never fatal, and
silent on a Spec Kit whose scripts never mention it. `docs/speckit-preset.md` says the same.

**Catch-up.** `slipwai migrate` brings the new `./init`; rerun it once after the merge on a machine whose
`python3` lacks PyYAML.

**`./init --extension uipro` installs UI/UX Pro Max as a skill in the project's own catalogue.** It is an
offline design-system generator — a Python search over local data that answers which pattern, style,
palette, type pairing, chart types and UX rules fit a product of this kind — and it lands in the root
`skills/` as one skill, so `make agents` projects it into every harness and `check-agents` holds the
projections to it, rather than as the fifteen per-harness copies its own installer would write. The copy is
ignored by Git and reproducible from the pinned CLI version. The `AGENTS.md` block says when to reach for it
(the first screen `docs/design.md` has no decision for), that the persisted `design-system/<slug>/MASTER.md`
is committed as the input `tokens.css` is filled from, and that the design page stays the one a slice reads
first and wins where the two disagree. A project with no browser app is refused with the command that would
change that.

**Catch-up.** Nothing arrives by merge. Adopt it with `./init --extension uipro` where a browser app exists;
a checkout that adopted it elsewhere sees the pointer and reinstalls with the same command.

**A project with a browser app now gets two design skills, and its design page and demo stop tell a slice
when to use them.** The catalogue had 49 skills about how work is done and none about what a screen should
look like or how to check one before it is demonstrated. `frontend-design` (Anthropic's, vendored verbatim at
a pinned commit, Apache-2.0) is the deciding half: ground the design in the subject, plan a compact token
system, review it against the brief for the generic defaults a generated page tends to cluster around, then
build. `web-interface-guidelines` is the checking half: Vercel's Web Interface Guidelines — accessibility,
focus, forms, motion, typography, content handling, the anti-patterns to flag — pinned into the skill as a
file rather than fetched before each review, because a review that needs the network is one that silently
does not happen in a sandbox or a CI runner. Both declare `capabilities: frontend` and ship only where there
is a browser app to design; `docs/design.md`'s *Rules a slice follows* now says to reach for the first before
the first screen and the second before the demo, and the demo stop's styled check names the review as its
second half. Skill counts in the docs are 51.

**Catch-up.** A merge brings both skills whole; `make agents` (or `./init`) re-projects them into every
harness. A project with no browser app receives nothing new.

**`./init --extension ux-gates` puts objective UX gates in `make verify`.** It installs plugin87's
ux-ui-agent-skills kit under `tools/ux-gates/` (ignored by Git, pinned, reproducible) and adds
`check-ux-gates`: the kit's no-literal-values gate over each browser app's `src/` — a colour, pixel size or
duration outside `tokens.css` fails the build, which is the rule `docs/design.md` already stated, now
measured — and, where Node and Playwright are present, its real-render gates over every `*.html` under
`<app>/screens/`: contrast in light and dark across default, hover and focus, visible focus, target size,
no overflow at phone widths, and axe. With no browser the render gates are reported as skipped, never as
passed; a checkout without the kit is likewise skipped, and `UX_GATES_REQUIRE=1` makes that the failure it
is wherever the kit is expected. The generated baseline passes the file gate: the focus ring's width and
offset became tokens (`--focus-ring`, `--focus-ring-offset`) rather than the two literal pixels they were.
Every generated Makefile carries the target whether or not the extension is adopted; unadopted, it says so
and passes.

**Catch-up.** A merge brings the new Makefile target and `scripts/check-ux-gates.py`, and the tokenised
focus ring in `tokens.css` and `base.css` (take the factory's side unless the project restyled the ring).
Adopt the gates with `./init --extension ux-gates` where a browser app exists.

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

