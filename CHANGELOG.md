# Changelog

No public releases yet. Release notes are recorded here newest first.

## 1.3.0 — MINOR

**`slipwai adopt` refuses an unclean tree, a directory that is not a Git repository, or one already holding a
`project.json` before it surveys anything or asks anything — not after.** The check ran as `adopt` began
writing, which is the right place for it to be enforced but the wrong place to find out: on a repository of
twelve thousand files it meant waiting through the survey, answering the interview, and only then being told
that none of it could be kept. `adopt` still checks when it writes, because it is a library function and that
contract is its own; the command line now checks first as well.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**`slipwai adopt` no longer wraps anything in a terminal: every buildable directory the survey finds is
recorded as a candidate, and which of them is an application is answered by the coding agent, with the code in
front of it.** [ADR 0003](docs/adr/0003-a-wrapped-application-begins-as-a-candidate.md) has the reasoning and
the evidence. `Wrap it as the application …? [Y/n]` defaults to yes and is asked of somebody who has not read
the directory; on the first real monorepo this met, that wrapped three asset bundles and a test suite as
applications, under names taken from their directories, with every `purpose` left blank — and there was no way
back, because a re-survey reports an unwrapped directory but has never removed a record.

So `project.json` gained the state it was missing. `deployables` says what somebody has established;
`candidates` says what was merely found, with the path, the language, the commands the build answers and the
file that found it. It is the same distinction `unrecorded` already draws for every row of the convergence
map, and it is why no un-wrap command had to be written: nothing is wrapped, so nothing needs unwrapping.

What follows from it: **`make verify` refuses while nothing is confirmed** and names what confirms one, because
a gate with nothing to hold has not been given its subject and a green run over zero applications is the false
assurance this exists to prevent. **The terminal asks one question** — the forge — and shows the rest as facts;
the language, the kind, the commands, what each directory owns, where the schema and the infrastructure live,
how a change reaches production and why the work is happening all move to the agent or to a conversation.
**`/ground` opens with the candidates**, one at a time, saying what it thinks each is and why from what it
read, before asking. **`slipwai adopt --confirm <name>`** records the answer — with `--as` for a name that is
not the directory's, and `--kind`, `--purpose`, `--command` and `--hexagonal` for the rest — builds the entry
and regenerates everything that reads it, so `deployables` is never edited by hand; **`--decline <name>`** drops
a candidate with nothing recorded in its place. **`--next`** names confirming as the step before the map's rows.
`--yes` stays the unattended path it has always been: it confirms every candidate as found, and the report now
says plainly that nobody looked.

This is the only intro. The per-directory interview it replaces — wrap it? language? kind? these commands?
what does it own? the schema, the infrastructure, the release path, why — is gone, and in a terminal `adopt`
now runs `./<delivery>/init` once its commit is made unless `--no-init` says otherwise. It arrived behind
`--experimental-intro` and `SLIPWAI_EXPERIMENTAL_INTRO=1` while it was being built; the flag is still accepted
and chooses nothing, so a script that passes it keeps working, and the variable is no longer read.

**Catch-up.** Nothing. A repository adopted before this has its applications in `deployables` already, which is
confirmation by an earlier factory and is left alone; it has no `candidates` key, which reads as an adoption
with nothing outstanding, and `--confirm` says so rather than inventing work. Two readers of an adopted record
— `--next` and `--refresh` — now tolerate a manifest with no deployables, which is the honest state between
`adopt` and the first confirmation; `add-service` still refuses one, since it needs an application to take a
language and a port from.

**`slipwai adopt` establishes which coding agent the material is for, instead of leaving it to a question
`./init` asks one step too late.** `./init` projects the canonical skills, commands and agent types into one
harness's native locations, and it has always asked which — after `adopt` had already finished. That ordering
makes the answer useless to the adoption itself, because the questions worth handing to a coding agent are the
ones asked before there is one. It was also mostly answerable without asking: a run started from inside a
harness is told so by its environment, and a repository whose team already uses one says so in the tree
(`.claude/skills`, `.gemini/commands`, `.github/copilot-instructions.md`). `adopt` now reads both and records
the answer in `project.json` under `agent`, with the evidence and `detected` provenance; `--integration <agent>`
names it outright, recorded `overridden`, and `./init` asks nothing where the record already says. What nothing
establishes stays `unrecorded` and is said out loud — a directory two harnesses read names neither, a tree that
reads for two records neither, and a thirty-six-row list is not a question a terminal can ask well — so `./init`
keeps its own question for exactly the case it is still needed in.

**Catch-up.** Nothing. A repository adopted by an earlier factory has no `agent` key, which reads as the
question still being open, and `./init --integration <agent>` answers it the way it always did. A re-survey
carries the key as recorded rather than re-reading it: which agent gets the material is not something the tree
says.

**`slipwai adopt --init` runs `./init` once the adoption is committed, so a terminal adoption can end in one
step rather than four.** Off unless asked for: `./init` reaches Spec Kit's source, and making every `--yes` in
a script or a test need the network to finish would be a poor trade for saving a line. It runs last and never
inside the commit, so an unreachable source costs the adoption nothing — the commit is already made, the
failure says so, and `slipwai adopt --next` keeps naming `./init` as the step you are on. What it writes is
left uncommitted and yours to read, exactly as in a project the factory generated. `--no-init` is the default
said out loud.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**`slipwai adopt --next` says where an adopted repository stands in the sequence the adoption report names —
what is done, what is next, and why — so the plan survives the scrollback.** That report is printed once, at
the end of the longest output this factory produces, and the sequence it names spans days and four tools;
`docs/adoption.md` carries the same list but is introduced there as a record of what was wrapped rather than
as the plan. Nothing is remembered now: every step leaves a mark, and `--next` reads them. Spec Kit writes
`.specify/integration.json`, the first gate run writes the ratchet baseline, `/ground` moves a row of the
convergence map off `unrecorded`, the root Makefile gains its `-include`, and a strategy is an accepted ADR
with a `Strategy:` line. It writes nothing itself, and it names the applications nobody has yet proved start.
A repository adopted by an earlier version needs nothing: the marks are the ones it was already leaving.

**A recorded command that changes directory first no longer reports the shell's `cd` as a tool this machine
is missing.** Every build that is not at the repository root is recorded as `cd <dir> && <build>`, and the
report read the first word off that line and asked the PATH for it — so a repository with four such builds
was told `` `cd` is not on PATH here `` above a list of all fifteen of their targets, with the one tool that
really was missing a line among them. The tools a command runs are now every shell segment's program, past
any leading `VAR=value`, and never one of the shell's own words.

**The questions a terminal cannot answer well move to the coding agent, which can read the code before
asking.** What a directory is, what it is called, what it owns, and first of all the language, which the line
above it had already printed. The candidate state is what finished the move; see the entry that introduces
it.

**The code index is kept sound, kept current and asked first by the harness, not by a sentence in a brief.** A
`/cruise` iteration on an indexed project started against a corrupt `.codegraph/codegraph.db` — which CodeGraph's
own `status` and `sync` report as up to date — repaired it by hand, asked it once and went back to grep, and its
delegates located symbols with `grep -n` and `sed -n` although their brief said to ask the index; nothing counted
who asked it. Now:

- Before every iteration the runner opens the database, runs SQLite's integrity check, moves a corrupt one to
  `.codegraph/corrupt/` and rebuilds it, and syncs one the tree has moved past; the log entry's `index` says which.
  A Claude Code session takes the same step when it opens (a `SessionStart` hook), so a person's `/drive` starts on
  a sound index too, and hears about it only when something was done. `python3 scripts/agents/code_index.py health`
  is the same repair by hand.
- `scripts/codegraph` runs the pinned CLI (`@colbymchenry/codegraph@1.6.0`, the version the MCP server now runs
  too) through `npx`, or an installed `codegraph`, so every session with a shell — a delegate's included — has a
  route. Claude Code's `.mcp.json` entry carries `alwaysLoad`, so `codegraph_explore` is loaded at session start
  instead of behind the tool-search step a delegate had to take by name.
- Claude Code's `PreToolUse` hook refuses a search of the source for a symbol — a name the index defines, or one
  shaped like one — from any session or delegate that has not asked the index yet, naming the command that
  answers; words, phrases and searches confined to documents are text search and never refused. A `PostToolUse`
  hook syncs the index each time a delegate returns, because CodeGraph turns its own watcher off where it decides
  it is sandboxed.
- `check-codegraph` no longer skips a database that fails the integrity check: where the CLI is reachable it
  rebuilds it, and syncs a stale index, before comparing, and fails only where the index cannot be made sound and
  current — so `make verify` on any harness mends a broken index rather than going red on it
  (`CODEGRAPH_GATE_NO_SYNC=1` compares without repairing).
- The log entry's `index_use`, the feed and `cruise.py status` count index queries per delegate and name each
  that searched the source for a symbol before asking.

The hooks and per-delegate counts are Claude Code's; on other harnesses the runner's repair, the gate, the wrapper
and a per-iteration count hold.

**Catch-up.** `slipwai migrate` brings the scripts, the hooks and the delegate briefs. Run `make agents` (or
`./init --extension codegraph`) once in a project that adopted the index, so `.mcp.json` and the `AGENTS.md` block
name the pinned server with `alwaysLoad`, and commit the result.

**`make verify` on the `aws` target fails when the service stack declares IAM the deploy role cannot create.**
The bootstrap stack gives the deploy role PowerUserAccess and IAM on roles named `<project>-*`, and nothing
held `infra/service/` to that: a generated project added an `aws_iam_user`, passed every gate, and met the
limit at the production apply — refused on `iam:CreateUser` part-way through. `check-deploy-role` reads both
stacks and fails on every `aws_iam_*` resource whose create or delete action the policies attached to the
deploy role do not grant on that kind of IAM resource, and on any IAM type it has no row for. Its message,
and `scripts/deploy.py`'s when an apply is refused on an `iam:` action anyway, name where the fix is: a
statement in `infra/bootstrap/main.tf` and a `make bootstrap` by a person with admin credentials — not the
service stack, not the pipeline and not the IAM console.

**Renaming a resource is a `moved` block, and the guidance says so.** The same project renamed a CloudFront
response-headers policy with no `moved` block; OpenTofu created the new one and destroyed the old one before
updating the distribution that still used it, and CloudFront refused with 409. `infra/README.md` on both
targets, and the production rule in `AGENTS.md`, now say that a renamed or moved resource gets a `moved` block
and one dropped from the code a `removed` block, and what `tofu plan` shows when either is right.

**Catch-up.** `slipwai migrate` brings the gate. If it fails on a stack that deploys today, the resource it
names was granted by hand outside `infra/bootstrap/`: put the grant in `bootstrap/main.tf` and run
`make bootstrap`, so the next bootstrap does not take it away.

**A slice with a screen now has its design decided before it is built and reviewed on the rendered screen
before the demo, as two `/drive` rungs, not as a sentence nothing asked anyone to act on.** Three new screens
reached a demo with every `check-ux-gates` gate green and still showed default-blue links, labels crammed
against their fields, a raw UUID and a diagram drawn as a bare rectangle: the design skills were installed and
`AGENTS.md` named them, but no stage of the ladder asked for them, so a delegate briefed from the plan styled
from the tokens, ran the gates and stopped. Where the project has a browser app:

- **Screen design**, between *Plan and tasks* and *Implementation*: `docs/design.md` holds the decision each
  screen needs, `skills/frontend-design`'s second pass has been over the plan, and `tasks.md` records a
  `Designed:` line per screen under `## Design review`.
- **Design review**, between *Implementation* and *Convergence*: each screen rendered, a screenshot per state,
  read against `skills/web-interface-guidelines`, every finding fixed or given its reason on a `Reviewed:`
  line. A green gate is evidence for this rung, never the rung.
- A slice with no screen says `No screen in this slice` once, and both rungs are done.

The ladder names only what every browser app ships with. The `uipro` extension's `AGENTS.md` block now puts its
search into *Screen design*, and the `ux-gates` block puts `make check-ux-gates` and the kit's `design-review.md`
and `wcag-checklist.md` into *Design review*, so a project that did not adopt them reads about neither. The
`drive-tasks` brief and the event-modelling tasks template carry the steps inside the styling task and leave the
`## Design review` heading. The demo stop checks the record. Under `/cruise`, `drive-hand` also looks at every
screen on its browser walk and writes what it sees as `design:` notes in the demo log's **Feedback**.

**Catch-up.** `slipwai migrate` brings the ladder, the brief and the template. A slice already past
*Implementation* whose `tasks.md` has no `## Design review` enters `/drive` at *Screen design*: write the
`Designed:` lines for the screens that were built, then run the review. In a project that adopted `uipro` or
`ux-gates`, run `make agents` once so its `AGENTS.md` block names the rung, and commit the result.

**A flag that describes the adoption is refused on a `--confirm` or `--decline` run, rather than read and
thrown away.** `slipwai adopt --confirm shop --integration cursor` looked like it recorded a coding agent and
recorded nothing: the settling path never reads those flags. It now names each one and says where it belongs —
`--integration` after the method is installed is `./init`'s. The same rule the intro already applies
to flags that describe an application, and nothing that previously worked stops working: a flag that did
nothing now says so.

**`check-codegraph` no longer fails a repository for files CodeGraph deliberately declined.** It inferred what
should be indexed from the suffixes already in the index, so a vendored `bootstrap.min.js` beside a `src/app.js`
read as a hole in the graph — and a real adoption failed a gate that `codegraph sync` said was already up to
date, the two tools calling each other wrong. Which files belong in the index is CodeGraph's decision; a file
the index has never seen is now a finding only where it appeared *after* the index last ran, which is the
question the check was always asking.

**A harness that cannot be projected says where its skills live instead of only that they are elsewhere.** The
registry already records the reason — Hermes keeps them at `~/.hermes/skills` — and the refusal now quotes it,
because a person told "outside the repository" still has to go and find out where.

**`docs/change-strategy.md` stopped opening by asserting that `make verify` is green.** It is written before
any gate has run, and on a repository whose build tool is not on the machine it is not true. The page says what
the gate actually does instead: runs the build's own commands, green where the ratchet has a baseline to hold
them to and plainly red where it does not.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**A migration no longer lands on gates nothing true can satisfy: `check-benchmark` warns rather than fails, the one
event model charges a slice to its own feature, and a project's slice history can be baselined for the adversary
log once.** A project migrating from a 1.2.0 snapshot met two gates that arrived in 1.2.0 without a word in its
catch-up note. `check-benchmark` failed on every slice finished before benchmark records existed, and those records
can only be taken at the time, so the only ways to pass were to invent them or never push again. It now prints
each of those findings as a `warning:` and passes, and its own self-test is still what fails it. Both it and
`check-decisions` counted every `status: implemented` slice in `docs/event-model/model.yaml`, which is the whole
project's, against every feature they checked: a second feature failed for the first feature's slices, and
nothing done inside the second could fix that. A slice now counts only for the feature its `spec` or `gwt` path
is under, or, where it names none, the feature holding `slices/<id>/`. An implemented slice that no feature holds
is reported once. `python3 scripts/check-decisions.py --adversary-baseline` writes, once, a `## <id> · predates
the adversary gate · <date>` row for every done slice with no row. The gate accepts that row. The row says the
slice was never attacked, and `/adversary` never relies on it. A second baseline is refused.

Four smaller fixes, found on the same migration. `make verify` now runs `check-python` first, and it names the
interpreter when `python3` is older than the 3.10 the gate scripts need. Before this, a non-interactive macOS
shell that found `/usr/bin/python3` (3.9) first died inside whichever gate first used a newer feature.
`check-codegraph` and `code_index.py health` now tell a database they cannot open apart from a damaged one. On
macOS's system SQLite, CodeGraph's WAL database with no `-shm` beside it refuses a read-only open. It is now
read with `immutable=1`, and an open failure is reported as one and never moves the database aside, so `health`
no longer rebuilds a sound index in a loop. The code index finds a Node that nvm, volta or fnm installed when a
hook's shell has none on `PATH`, and says that is the likely cause when it finds none. `check-ux-gates.py` can
now be loaded with `importlib` without being registered in `sys.modules`, and it says to unset an
`UX_GATES_SHARD` value it refuses.

**Catch-up.** These gates are new or stricter since 1.1: `check-benchmark` (warns since this release),
`check-decisions`' adversary rows (1.2.0), `check-deploy-role` on `aws` (1.3.0), `check-ux-gates` sharding and
its CI job (1.3.0), and `check-python` (1.3.0). If `check-decisions` reports `no row for` slices finished
before you migrated, run `python3 scripts/check-decisions.py --adversary-baseline` once and commit the rows it
writes. Slices finished after that need the row `/adversary` writes. Make sure the `python3` your shell finds
first is 3.10 or newer. Nothing else needs doing: the rest arrives whole with the merge.

**`/ground` asks, before anything about the repository, how much each answer should explain itself — and holds
to the answer.** Spelling out what every option writes, what moves because of it and what it costs is what
somebody meeting a codebase or this method for the first time needs to answer safely; it is also how a
question set becomes a wall to skim for somebody on their second adoption who already knows what confirming
an application does. So it is asked once, the agent says which it would pick for this person and why, and
either form can be changed at any question. The short form drops the elaboration and not the honesty: what
the agent thinks and why, from what it read, stays, and *I don't know* stays an answer on offer.

**And `slipwai adopt --refresh` no longer drops the outstanding candidates and the recorded agent.** A
re-survey reads the tree, and neither is a fact about the tree — a candidate is a question nobody has
answered yet, and which coding agent gets the material is `./init`'s. Rebuilding the record without them left
`project.json` holding two candidates while the `/ground` regenerated in the same run had lost the section
that asks about them: a generated file disagreeing with the record it is generated from, which is the one
thing this must not do. Found by running the command over a real adoption mid-way through.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**`/ground` can record its answers one at a time and commit them once, as it says to.** `adopt --confirm`,
`adopt --decline` and `adopt --refresh` refused any uncommitted change at all, so the first answer was refused
by what `./init` had just left for the person to read, the second by the first, and the refresh by the rows it
exists to follow — and the first repository taken end to end got through by committing after every answer. They
now refuse only where they would write over somebody's work: a path they write, from the factory's `.written`
listing or the survey's pages, holding an uncommitted change that is not what slipwai last left there. What
slipwai left is recorded by digest in `.delivery-tools/written.json`, which every `.gitignore` the factory has
written already ignores, so it belongs to the checkout and is never committed. It is kept out of `.git` on purpose: Codex runs an agent's
commands in a sandbox that makes `.git` read-only, and a record there was silently never written.
`project.json`, what `./init` wrote and a person's own source no longer stop anything, because none of them is
written. `slipwai adopt` itself still refuses an unclean tree: it commits, and the `git reset --hard HEAD^` it
offers as the undo would take uncommitted work with it.

**The code-index guard holds only searches of its own repository.** A session opened in one repository searched
another checkout and was refused, because `version` is a name the first repository's index defines — an index
that cannot answer anything about code it never read. Where a search runs is now read from the hook's `cwd`, a
Grep `path`, or a `cd` earlier in the shell command, and a search wholly outside the repository is allowed.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.

**`/ground` now has to say what each answer on offer will do, not just what it is called.** The first real run
of the command over a brownfield monorepo produced a page of sound reasoning per candidate and then collapsed
it into option labels — *Yes — hold its lint*, *Yes, as recommended* — and the person answering it replied
"Not sure, what do you think?" and, once, "check yourself". A person reads the options, not the paragraph
above them, so that is where the consequence has to be: each answer names what it writes, what moves because
of it, and what it costs. Three rules go with it: a question the tree can settle is read and settled rather
than put as a menu; a recommendation always comes with the reasoning that produced it, never a bare list; and
*I don't know* is offered as one of the answers every time rather than merely accepted when volunteered,
because a question that does not offer it manufactures an answer.

**And a runtime past its end of life is named once, however many applications run it.** The platform record
holds a row per application per product, so a repository whose four npm packages all run Node 20 had the same
sentence four times under the strategy's `because` and four more under its `before`. The reader needs the
products; a product is its title and its version.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**`/ground`'s long form says what being an application commits you to, before it asks about the first one.**
The question was "is this an application?", and the natural reading of the word is "something that gets
deployed" — so a person could agree to put a directory's lint and tests in front of every change without knowing
that was what they were agreeing to. In the long form the agent now says, once and in this repository's terms,
that an application here is a directory whose build the gate holds: its commands join `make verify`, which every
change has to pass, the person's and `/drive`'s and `/cruise`'s; the gate's CI runs it on every pull request;
`/drive` can change it once somebody has recorded how it starts. It says what declining leaves behind, that
leaving a directory a candidate is *not yet decided*, and that neither answer can be taken back by a command yet —
so an unsure answer is best left open.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.

**Go's CI cache is keyed on the files a workspace has.** `actions/setup-go` keys its cache on a root `go.sum`,
and a generated Go project is a workspace — `go.work` and `go.work.sum` at the root, each module's `go.sum`
beside its `go.mod` — so the step found nothing to key on, cached nothing, and said so only as a warning while
the run stayed green and downloaded and compiled every module from cold. `verify.yml` and `deploy.yml` now
name every module's `go.sum` and `go.work.sum` as `cache-dependency-path`.

**A language somebody spoke brings its own toolchain.** The survey reads each directory once, by the first
ecosystem that recognises it, so a directory with a `package.json` beside a `requirements.txt` is Node. Saying
it is Python — with `--language`, or through the `--confirm` that `/ground` runs once it has read the code —
moved the language and left `kind: node` behind it, and a refresh then put the reading back over the answer.
The toolchain is what CI installs, so the record was describing a pipeline that cannot run. It now follows the
language where the tree has a build in that language to follow, is left alone where it has none rather than
invented, and a refresh holds what a person settled and says what the tree now reads instead.

**Claude Code's hooks find their scripts from any directory.** They were written as repository-relative paths
and run with whatever directory the session is in, so a session opened in a subdirectory ran
`python3 delivery/scripts/agents/cruise.py` against a path that is not there — and a hook that fails is silent.
They are written from `$CLAUDE_PROJECT_DIR` now, and the two other harnesses the factory writes hooks for —
Cursor's `.cursor/hooks.json` and Gemini CLI's `.gemini/settings.json` — change to the root Git names
(`cd "$(git rev-parse --show-toplevel)" && …`) before they run, since neither harness shares a variable
for it. `make agents` rewrites them; nothing else is asked of a repository already generated.

**A command that needs an application says that confirming one is the missing step.** Between `adopt` and the
first confirmed candidate there is nothing for a frontend to sit beside, and `slipwai add-frontend web` — which
is what `./init` had just said to run — answered "project.json names no deployables, so there is nothing to add
a service to". True, and the same sentence a manifest that names none gets. It now names the candidates and the
command that settles one.

**An extension tells a wrapped repository to run the script it actually has.** `./init --extension codegraph`
is advice nobody can follow where the adoption put `init` under `delivery/`. The three shipped extensions
derive the path from where they are, in all ten places they print it.

**`slipwai adopt --next` runs to the loop rather than stopping at a ready repository.** It ended at the
strategy ADR — wrapped, gated and asked to do nothing — and the first person to take it end to end had to be
told the rest in chat. It now names `/speckit-constitution` before the first spec, because `check-constitution`
fails the moment `specs/` exists over the template it installed, then `/speckit-specify`, `/drive` once by
hand, and `make cruise`. A constitution in a repository where `./init` has never run reports as pending, which
is what it is.

**`--command app:test=` records none, as `-` does.** An empty value is what a shell leaves when a variable is
unset, and recording `""` wrote a target that runs nothing and reads as one somebody chose. The report now
says what each target was vouched for with, so a written no is visible where it was decided.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.

**`slipwai adopt --confirm` and `--refresh` now re-derive the harness projections, so `make verify` is not red
the moment `/ground` finishes.** Confirming a candidate changes which languages the record names, which
rewrites the skills' prose, which makes every copy under `.claude/skills/` differ from its canonical source —
and `check-agents` fails. Both real adoptions hit it and fixed it by hand with `make agents`. The factory
writes the canonical files, so the factory re-derives what copies them, exactly as `migrate` already does
after a merge. A projector that cannot run is reported rather than raised: the record is written and good
either way.

**And the typecheck the survey proposes for a TypeScript directory with no script of its own now passes
`--skipLibCheck`.** A bare `tsc --noEmit` gave seventeen errors on a real adoption, every one of them inside
`node_modules` where two dependencies ship disagreeing types — nothing the project can fix, and the ratchet
baselines the whole failure as a blanket excuse for the check. With lib types skipped the same tree is green,
and a type error the project actually wrote is what turns it red. A directory with its own `typecheck` script
keeps it, whatever it says.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**The ratchet now sees findings in an application that is not at the repository root — which, until now, it
never did.** A tool prints the paths it found relative to the directory it ran in, and a wrapped application's
build runs in its own: `cd admin-dev/themes/new-theme && npm exec -- tsc`. Every path it reported was resolved
against the repository root alone, where nothing of that name exists, so the run found no findings at all and
fell back to comparing the exit code — which passes a second error tomorrow exactly as it passed the first.
On a real adoption a plain type error in the project's own source was invisible to it. That is the ratchet
failing at the one thing it exists for, silently, on precisely the repositories it was written for: the ones
whose applications live in subdirectories. A path is now resolved against the directory the build runs in as
well as the root — `project.json` records it — and recorded root-relative either way, so a finding compares
the same however the tool that printed it spelled it.

**Catch-up.** An adopted repository with an application below its root should re-record: its `lint` or
`typecheck` entry in `baseline.json` is almost certainly `{"exit": N, "findings": []}`, which excused the whole
command. `make ratchet-tighten` after reading what the command actually reports replaces it with the findings
that are really there, and the gate holds to no new ones from then on.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**`slipwai adopt` no longer names `./init` as the next step and then runs it two lines later.** Where
`--init` is going to run it, the report says it is running now and what that leaves for you to commit; the
rest of the sequence is unchanged, since only the first line was ever about that step.

**And where `adopt` could not tell which coding agent the material was for, the record now catches up with
the answer `./init` collected.** Handing the question on was right — a tree that reads for three harnesses is
a decision and not a guess — but the answer then existed only in Spec Kit's own file while `project.json`
still said nobody had established one, and `slipwai adopt --next` went on offering `--integration` for a
question somebody had already answered. `harness.py` now reads `.specify/integration.json` as a source of its
own, and the strongest one: a person answered `./init`, so it is recorded `confirmed`, and it outranks both
the environment a run started in and what the tree reads, which are readings rather than answers. A record
that already names a harness is left alone, and one a person overrode is never moved by a later step.

Found by running the candidate intro over PrestaShop, whose tree reads for Claude Code, GitHub Copilot and
Gemini CLI at once — which is the case the ambiguity rule was written for, and the first time it has been met
in the wild.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

**The UX render gates are spread from the first screen: side by side, sharded across six CI jobs, and scoped
to what a pull request changed.** Each per-file render gate launches its own browser, four per preview, so
their cost is linear in `screens/`: a generated project with 225 previews spent 24 minutes of a 33-minute
`verify` in them. `check-ux-gates` now runs its gates concurrently (`UX_GATES_JOBS`, one per processor by
default); `UX_GATES_SHARD=k/n` runs every n-th gate from the k-th, so n jobs cover every gate exactly once;
and `UX_GATES_SINCE=<ref>` renders only the previews whose own file, or a local stylesheet they link or
`@import`, changed since the merge base with `<ref>` — every preview again when the gate, the extension, the
lockfile or `verify.yml` moved, or when Git cannot say. The file gate over `src/` always runs. And
`./init --extension ux-gates` now writes a `ux-gates` job into `verify.yml`, between markers: six shards, each
installing the pinned kit and Playwright's Chromium and setting `UX_GATES_REQUIRE=1`, scoped to the base commit
on a pull request and whole on `main`. Until now the generated CI never installed the kit, so its render gates
were reported skipped there on every run; they are now measured before a deploy, which waits on `verify`.

**Catch-up.** Run `./init --extension ux-gates` once in a project that adopted the gates, and commit the job it
adds to `.github/workflows/verify.yml`. A project that wrote its own UX-gate job should remove it first. A project that patched the gate should know
what the upstream script no longer takes: `UX_GATES_SHARD` accepts only `k/n` (`1 <= k <= n`), and any other
value — `none` included — fails the gate, so unset it to run every gate; and `check-ux-gates.py`'s entry points
are `main()` and the `UX_GATES_*` variables, its helpers are not a contract, and a test that loads it with
`importlib` should call `main()` with the environment set rather than reach into them.

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

