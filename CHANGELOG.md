<!-- One entry per release, newest first, assembled by `make release` from `changelog.d/`.
     Never edited by hand above the line a release wrote: write a fragment instead. -->

# Changelog

What changed in each release, for the person who just upgraded. `slipwai upgrade` prints the entries
between the version you had and the version you got, so this file and that command say the same thing.

Each entry's level — `PATCH`, `MINOR` or `MAJOR` — is the highest any of its changes claimed.

## 2.0.0rc1 — MAJOR

**A place a project is deployed to is a package now, the way a language and an extension already are.**
`slipwai package new --kind target <name>` writes one that this keel reads on the first try: a `target.json`
the catalog takes its row from, a `TARGET` object answering the target protocol, both stacks — the account's
and the service's — and the two scripts that apply them. `slipwai package check` runs a conformance profile
of its own over it: the declaration, the protocol, that both stacks are made of files the package actually
ships, and the same version rule every other kind is held to. A channel can list it, `slipwai search --kind
target` finds it, and `slipwai package release` and `register` build and publish it, all through the code
paths the other two kinds already used.

This is the protocol, not the clouds: `aws` and `azure` are still in the keel and still work exactly as they
did. What this buys today is that somebody can write a target package and have the keel tell them, locally
and without an account, whether it is one.

**Catch-up:** nothing. No project changes, and every existing package of either other kind is read as it
was.

**`import-surface.txt` now promises each kind of package its own list, and the gate reads a target package
against the target's.** The file carries a section per kind — `[language]`, `[target]` — and each has the
same ceiling of twenty: the number is about how far into the keel any one package may reach, not a budget
shared out between kinds. Nothing a language was promised has changed, and a list with no section header in
it still means exactly what it meant, which is the language's.

`check-structure` walks `packages/*/slipwai_target_*/` beside the language packages it already walked, and
refuses a target that imports a keel module the target section does not list — in both directions, as the
language surface is held: a line naming a module the keel has not got still fails the gate whichever section
somebody wrote it in.

The target section holds one line, `slipwai.target_protocol`. That is the module a target package has to
import to export a `TARGET` at all, and a line here cannot be withdrawn, so the rest of what a cloud needs
arrives when a cloud is a package and has been seen to need it.

**Catch-up:** nothing for a project. A language package maintainer need change nothing — the list a language
is held to is the same twenty modules it was.

**`slipwai target install` puts a cloud on the machine, and `slipwai target list|remove|check` are the rest
of the verb.** A target arrives the four ways the other two kinds do — a name looked up in the chandlery, a
package directory, a release file, or a git URL — and `--target <name>` offers it from the moment it lands.

The install is a stage, an **admission** and a rename, and the admission is what makes it a target's rather
than an extension's: the package's Python is imported and asked for `TARGET`, and a managed target is held
to every member the protocol requires. A cloud that cannot be imported, or that answers `shapes` with files
it does not ship, would otherwise be found out at `make bootstrap` — partway through an apply, with half a
stack already created in somebody's account. Nothing lands half-way: staged under a hidden name the loader
skips, admitted, then renamed into place.

**Catch-up:** nothing yet. A project generated before a target was installed does not offer it until
`slipwai migrate` is run in it, which is what the verb says when the install finishes.

**A target package in the package directory is loaded, and what it offers joins the menus.** A cloud is
found by the same walk that finds a language, read for its `target.json` without importing anything, and
imported for its `TARGET` only when a project is actually being written. Its row joins `targets`, the keel
answers it offers gain it among the targets they are offered under, what it provisions each of them as is
recorded against it, and the answers that are its own — a cloud's identity service, say — are declared into
the catalogue the way a language declares its frameworks.

A refused target is refused alone and in one line, so a second cloud installed beside a broken one still
generates projects, and the two faults that cannot be known on the publisher's machine — an axis or option
this keel does not declare, and a name something already holds — are said here rather than there.

**Catch-up:** nothing. A keel with no target package installed offers exactly what it offered before.

**AWS and Azure are packages now, and the keel names neither.** `slipwai target install aws` is what puts
AWS on a machine; until it is run, `slipwai generate` offers `none` and `existing` and nothing else, and the
answers only a cloud can provision — Cognito, Entra ID, Auth0, managed Postgres — are not in the menu
because nothing there could provision them.

Everything a project going to a cloud is given travels with that cloud: both stacks, the scripts that
bootstrap and deploy, the deployment drawing and the production decision record, the tools `./init` checks
for, the parts of the pipeline that are its own, the words its README section is written round, and what
`add-service` says afterwards. The keel keeps the shape around them — one apply at a time, apply then smoke,
production behind `AUTO_PROMOTE`, a rollback that re-applies the release before — so a third place to deploy
to is a package somebody publishes rather than a branch somebody adds to `generate`.

**Catch-up:** a project already generated on either cloud is unchanged and needs nothing. A keel upgraded
past this release will not generate another one until the package is installed: `slipwai target install aws`
or `slipwai target install azure`. `slipwai target list` says what is there.

**The keel names no place a project is deployed to, and a gate says so.** The last mentions of a cloud in
`src/slipwai/` were defaults, examples and prose — a matrix row planned against a cloud by name, a list of
managed-Postgres products, a docstring whose example was somebody's identity service — and each is now read
off the catalogue or said in words that are not a product's.

Eight lines still name a cloud, and none of them is a destination: a CI system or an infrastructure file
read off a repository being adopted, the format of a leaked access key, words people say about hosting, a
JDK distribution's image name. Each is listed with the reason taking the name out would make it worse, and
anything else fails the gate.

**Catch-up:** nothing. Nothing a project carries changed.

**`check-structure` now refuses a keel module that names a target package, exactly as it already refused one
that names a language.** An absolute import of a `slipwai_target_*` module anywhere in `src/slipwai/` fails
the gate, and anywhere means anywhere — a deferred import inside a function is still the keel knowing a
cloud, and it is the shape somebody reaches for when the top of a file is being watched.

Both rules are read off the one table the gate walks the packages by, so a kind of package the keel may not
name is refused the day it is declared rather than the day somebody remembers to add a branch for it.

**Catch-up:** nothing. No keel module names one today, so this changes no behaviour; it stops one from
starting to.

**Two machines can no longer run a captain for the same fairway.** A fairway is now claimed by a git ref,
`refs/slipwai/claims/<fairway>`, taken by a push that a second taker cannot win — which is an atomic
compare-and-swap on every forge there is, with nothing of ours running and no server to keep up. A captain
takes it before it writes a single line, and the machine that cannot take it is told **who holds it and
since when** instead of quietly appending to the same deck log through a second worktree. That was a merge
conflict in the one file the whole design promises will never have one, and where one side forced the ref
it was lines nobody could tell were missing.

Nothing is ever deleted: the ref is a chain of commits whose author is the machine and whose message says
`held` or `released`, so `git log refs/slipwai/claims/ordering` still answers *who had this fairway last
Tuesday*. A harbour with no `origin` takes the same claim locally, through the same compare-and-swap made
smaller, and says that it is local to this machine.

**You can take a fairway by hand, the same way:**

```sh
python3 scripts/agents/claims.py                     # who holds what
python3 scripts/agents/claims.py --take ordering     # and --release when you are done
```

**`held_by` in `story-split.md` is now rendered from those refs and written by nothing.** There were two
answers to *who holds this fairway* — a name somebody typed in that table, and a running process with a pid
file — and a third would have been worse than either. `make decisions` folds the column from the refs,
`make check-rendered` refuses a split whose cells say anything else, and a harbour with no forge renders
`—` and says why, because a claim no other machine can see routes nobody.

**Catch-up:** `slipwai upgrade` brings `scripts/agents/claims.py`. Take `held_by` out of your own hands:
run `make decisions` once and commit what it writes, or `make check-rendered` will refuse the names that
are in there now.

**The logs now actually travel between machines, and so does the work that is still in flight.** Both the
captain and the harbourmaster have run `git fetch origin refs/slipwai/logs/*` on every pass since the loop
existed, and nothing anywhere ever *wrote* those refs — the fetch was ceremony, a second machine saw none
of the first's lines, and getting one machine's log onto another was somebody with `scp`. The
harbourmaster now writes them.

**One ref per writer, and nothing is ever merged into one file.** A deck log's writer is whichever captain
holds that fairway, so it travels as `refs/slipwai/logs/<fairway>`; a harbour log's writer is that
machine's harbourmaster, so it travels as `refs/slipwai/logs/harbour/<machine>`. Each has exactly one
writer and neither can conflict. **A push that is not an append is refused by name**, because a log whose
ref holds lines the local file does not is a log that is about to drop them with nothing saying which —
and that is the one failure in this design you cannot recover from. The same rule holds on the way in, so
a ref and a file that disagree about their shared past leave each other alone rather than one quietly
winning.

**A claim now lapses, and the half-finished slice comes with it.** A captain killed outright never
released its claim, so a closed laptop parked a fairway until somebody ran `claims.py --release` on a
machine that might be switched off. A claim held by a machine nothing has been heard from for its lease is
now taken over — and because a captain holds no credential and a slice branch lived only on the machine
that built it, the harbourmaster also pushes each fairway's in-flight branch every pass as
`refs/slipwai/wip/<fairway>`. The taking captain brings that branch into its own berth and re-dispatches
`/sail`, which enters at the first incomplete stage: a machine four rungs into a slice is carried on from
rung five rather than started again. A lease without the branch was rejected outright, because a takeover
that silently discards four rungs of work is worse than a fairway that stays held.

**The lease is derived, not chosen.** It is twice the longest stage budget, so a captain that writes
nothing for `stage_bound` ends that stage itself before any lease could reach it — the guarantee falls out
rather than being asserted — and it moves with the telegraph for free, because every stage budget is
scaled by the position you ring. Liveness is judged on the later of the pushed log and the local one, so
more evidence of life only ever makes a lease *less* likely to fire.

**A new deck-log line says where a stream changed hands:** `taken-over`, carrying the slice and the
machine it came from. It is the one thing in a fairway's history a later reader cannot work out from any
other line — two machines' work in one chain, with nothing saying where the join is.

**See what has travelled:**

```sh
python3 scripts/agents/travel.py     # every log ref, and every in-flight branch
```

**Catch-up:** `slipwai upgrade` brings `scripts/agents/travel.py`. Nothing to run and nothing to change: a
harbour with no `origin` goes on exactly as before, and one with a forge starts pushing on its
harbourmaster's next pass.

**The harbour log is one file per machine now, folded into one history on read.** "One writer per harbour"
is unambiguous with one machine and means nothing with three: three harbourmasters appending to
`.slipwai/logs/harbour.jsonl` is the same conflict in the same shared file that the deck logs were split up
to avoid, and electing one of them would need an election — and the elected one could not push another
machine's in-flight work anyway, because berths are local. So each machine writes
`.slipwai/logs/harbour/<machine>.jsonl` and every reader folds the lot by the instant each line records.
The single writer is removed rather than elected. Your existing `harbour.jsonl` is left exactly where it is
and read alongside the new ones, because a migration that moves a log is one that can lose a line.

**The merge is the one thing that genuinely needs a decider, and a ref is the decider.** A harbourmaster
takes `refs/slipwai/merge` before it rebases and gives it back afterwards — the same compare-and-swap a
captain uses to claim a fairway, so two machines never rebase onto one trunk at once and the one that loses
the race waits rather than racing. A machine still waiting when `wait_bound` runs out says which machine
has been merging and since when, and names the command that frees a ref a dead machine left behind.

**Catch-up:** nothing to run. `slipwai upgrade` brings the scripts; the first pass each machine makes
writes its own log, and the board shows all of them together from then on.

**A berth's database is named after its machine as well as itself.** `app_orca` is now
`app_<machine>_orca`, so two people whose harbours point at one database server cannot allocate the same
database — which they could before, silently, with the failure arriving as a migration that dropped
somebody else's table. Nothing has to be configured to stop it; the collision is gone from the arithmetic
rather than refused by a check.

Ports are unchanged and deliberately so: a port is reachable from one machine, so two machines' blocks are
not in the same space at all and putting the machine into them would waste the arithmetic that makes a
block safe. `collisions()` now compares ports within a machine and databases across all of them, so handing
it two machines' berths is the check that the machine in the name does what it is there for.

**Catch-up:** a berth that already exists keeps the database it has until you remake it — `slipwai berth
remove <name>` then `add` — and nothing forces you to, because a harbour alone on its database server was
never colliding with anything.

**`slipwai package plugin <directory>` writes a Claude Code plugin, so `/sail` can be installed without
generating anything.** Until now the delivery material was files in a generated project — `commands/`,
`skills/`, `agents/` — and reaching it meant having a project to reach it in. The verb renders the same
material into `.claude-plugin/plugin.json` and the three directories beside it, and a person with nothing
but a checkout of their own code installs it and has the loop. `--profile event-modelling` renders the
modelled catalogue instead of the standard one.

**The plugin is rendered, never kept, so the two routes cannot say different things.** Every file comes out
of the same function `./init` calls for the same path: `commands/sail.md` is `command_files`' answer, the
agent types are `agent_files`', and the skills are the toolkit's own. There is no second copy of a command
anywhere, which is what the slice was for — two install routes each carrying their own `sail.md` would be
two live answers to what `/sail` says.

**Two things a plugin cannot carry, and it says which.** The four skills written around a language's own
code — `domain-driven-design`, `event-sourcing`, `hexagonal-architecture`, `testing` — are left out whole,
because their prose is built from example markers a *language package* answers and a plugin is rendered
with no project to ask. And `skills/run-the-app`, which names a project's own applications. Everything else
in the catalogue ships, unpruned: a project withholds a skill its answers say it cannot use, and a plugin
has no answers to withhold on.

**The hooks run only where there is a project to run them in.** `hooks/hooks.json` carries the same points
and the same verbs as a generated project's `.claude/settings.json`, so there is still one control plane —
but a plugin is installed once and used in every directory a person opens, most of which are not projects.
Each command therefore runs `scripts/agents/session.py` only where that file is; where it is, the script's
own exit status is what the harness sees, so a guard that refuses a tool call still refuses it.

**Catch-up:** nothing. An existing project keeps writing the same files from the same functions; the plugin
is a second door to them, not a change to what is behind it.

**`slipwai mcp` serves the read side as MCP tools, so the agent can ask the harbour what is waiting.** Until
now the board was something a person read in a terminal beside their agent, which meant the agent found out
what was blocked by having somebody copy a board from one window into another. Six tools now answer it
directly: `fleet` (the board), `stream` (one fairway's deck log), `inbox` (only what is waiting on a
person), `clearance`, `check-chart`, and `tell`.

**`tell` is the only one that changes anything, and it is the write the bridge already allows.** It goes
through the same function the page does, so the `told` line an agent writes into a stream's deck log is the
line a person typing into the bridge would have written — same fields, same file, read by that fairway's
captain at its next boundary. Nothing here allocates a berth, rings the telegraph or writes the harbour
log; those are the harbourmaster's and a second route to them would be a second control plane.

**The answers are the same fold, not a second one.** `fleet` is literally what `slipwai fleet` prints and
`stream` is what `slipwai fleet <stream>` prints. `clearance` and `check-chart` run the project's *own*
scripts rather than reimplementing them, so a project whose gates have moved on gets its gates' answer and
not the keel's memory of it. A gate that fails comes back as an error result carrying what it said, which
is the thing the model has to read.

**It needs nothing installed.** Newline-delimited JSON-RPC on stdin and stdout, written against the
standard library, the way the bridge is three routes of `http.server` and nothing else. A harness starts it
as a child process: `slipwai mcp --root <project>`.

**Catch-up:** add the server to your harness's MCP configuration — `slipwai package plugin` writes that
configuration for Claude Code. A directory that is not a harbour is told so by name rather than drawn as an
empty board.

**`slipwai package harness <directory> --harness <key>` lays the same material where a harness that is not
Claude Code reads it.** Claude Code gets a plugin, which is its own mechanism and nobody else's; every other
harness installs material by having files in the right places, and `registry.json` already declares where
those are for thirty-six of them. The verb writes the skills, the commands and the agent types at that
harness's own paths, in its own command extension and its own argument placeholder, and writes its
project-scoped MCP configuration pointing at `slipwai mcp`.

**One renderer, one row per harness.** There is no per-harness code anywhere: every answer comes out of the
registry row, so a thirty-seventh harness is a row and nothing else. A test walks all thirty-six, renders
each, and holds every file it produced to a path that harness's own row declares.

**Codex reads commands from `.codex/prompts` now.** Its row said it had no commands directory, so every
command reached it through the commands-as-skills fallback. The row now names the directory, which means
`./init` installs `/sail` there too — the same change, in one place, reaching both routes. A Codex project
written before this keeps what it has; re-running `./init` moves it.

**What a harness cannot be given, it is told it cannot be given.** Gemini's commands are TOML and Goose's
are YAML, which `./init` renders inside a project where there is one spelling and not two; Hermes reads its
skills from the person's home rather than the project; twenty-nine harnesses have no project MCP file
anybody has verified. Each of those is a line the verb prints, naming what the harness reaches it by
instead, rather than a file quietly missing.

**Catch-up:** `./init --integration codex` or `make agents` moves an existing Codex project's commands into
`.codex/prompts`. Nothing else changes for any other harness.

**`docs/reference/install-routes.md` says which of the three ways of installing the delivery material is
supported: `./init` in a project slipwai generated or adopted.** The Claude Code plugin and the per-harness
material are conveniences, and each says so on its own part of the page rather than in one caveat at the
top. When a convenience disagrees with a generated project, the generated project is right and the
convenience is the bug.

**The reason is where the gates already are.** `make verify`, `make test-docs` and the conformance suite
all run against generated projects. Nothing drives a slice through an installed plugin, and nothing can
prove per-harness material without the harness — `registry.json` still records `proven: false` for every
one of the thirty-six.

**The page says what each convenience cannot carry**, which is the part a person needs before they pick
one: a plugin has no project to ask for a language, so the four skills written around a language's code are
not in it; a harness whose commands are TOML gets none, because `./init` renders those inside a project
where a stage's model resolves.

**And a gate keeps the page honest both ways.** `tests/test_install_routes.py` holds the page to the routes
the keel actually has — a route it does not name fails, and so does one it names that does not exist — and
holds each convenience to being *rendered from* the supported route rather than maintained beside it. Both
verbs print the page, so somebody using a convenience is told it is one.

**Catch-up:** nothing to do. If you install by a route other than `./init`, read the page before you file a
difference as a bug.

**The captain and the harbourmaster are agent types now, with briefs of their own.** `agents/` shipped
eleven types and every one of them was a delegate *inside* a slice — the shipwright, the quartermaster, the
lookout. The two roles the glossary defines as *running* the loop had no brief at all, because they were a
Python programme. `agents/drive-captain.md` and `agents/harbour-harbourmaster.md` are what is left when the
programme goes: a loop narrated by Python is not native to a harness, and a loop a persona drives is.

**Each says what it may not do, which is the half that matters.** The captain holds no credential and asks
for anything outside its berth with a `request` line; it never merges to trunk; it never writes
`.slipwai/logs/harbour.jsonl` or another fairway's deck log; it does not decide a product question. The
harbourmaster is the only writer of the harbour log, never writes a captain's, drives no slice, and **is not
a merge queue** — the glossary's own words.

**The captain's log vocabulary is the keel's, not a paraphrase of it.** Every deck-log kind the keel has is
in the brief with the fields it carries, held by a test against `logs.DECK_KINDS`, because a captain that
invents a kind writes lines the board refuses to fold and then believes it reported something.

Both are projected into every harness's own agent location by the same projection as the other eleven, and
both travel in `slipwai package plugin` — so a session that has the material has the two roles that know
what to do with it, rather than a persona somebody has to remember to paste in.

**Catch-up:** `slipwai migrate` writes the two new files into `agents/` and re-projects them. Nothing you
have is replaced.

**The way you start a project here can be written down once and given a name.** A quickstart is one file
holding the languages a project wants installed, one answer per axis, and the extensions it elects.
`slipwai quickstart save <name> --suits '<a sentence>'` writes what the project you are standing in
actually has; `slipwai quickstart show <name>` says in plain words what it would do before it does any of
it; and `slipwai generate <project> --quickstart <name>` gives those answers to a new one. A name is looked
up in `~/.slipwai/quickstarts`, and a path is read where it is, so a team's own can live beside their
repository.

Every answer it gives is a flag you could have typed, and a flag you do type wins: the generation prints
each one it filled in, so the transcript shows what was chosen on your behalf. A quickstart names its
packages by range rather than by the version that happened to be installed the day it was saved, and one
that names a package this machine has not got is refused with the command that installs it.

**Catch-up:** nothing. An existing project gains nothing and loses nothing; stand in one and run
`slipwai quickstart save` to turn it into the way you start the next.

**`slipwai generate` now offers your quickstarts before it asks anything about languages or storage.** The
first question is *start from one of these?*, and each row is the sentence that quickstart says about the
product it suits — not the packages it names, because the person this helps most is the one who has never
heard of a chandlery. Choosing one answers the foundation, the target, the language, the browser framework
and every axis at once, and prints each answer against the flag that would have given it, so you can see
what was chosen on your behalf.

Declining is one keystroke: the first row is "ask me every question", it is the default, and there is
deliberately no default quickstart. If you have never saved one, nothing is asked at all and the interview
is exactly as it was. A quickstart whose packages this machine has not got is shown as not ready, with the
command that installs them, rather than quietly left out of the list.

A project generated from a quickstart carries `.slipwai/quickstart.json`, and its `./init` elects that
quickstart's extensions from it instead of showing the extension menu — `./init --extension <key>` still
wins, and still adds one later.

**Catch-up:** nothing.

**A quickstart is a package now, so an organisation can publish its own.** `kind: quickstart` goes through
the chandlery beside the languages and the extensions: `slipwai search --kind quickstart` lists what is
published, `slipwai show <name>` says what one would install and elect, and `slipwai quickstart install
<name>` fetches it — after which `slipwai generate <project> --quickstart <name>` works with nothing else
set up. The publisher's verbs are the ones they already know: `slipwai package new --kind quickstart`,
`package check`, `package release` and `package register`.

`package check` on a quickstart runs no conformance suite, because there is no code in one. It answers the
two things that matter instead: that the document reads, and that every package it names is named by a
**range** rather than by one version. A quickstart that pinned `==1.2.3` is refused — published, it would
hold every team that installed it to the afternoon it was written, and the first thing anyone would do is
edit the file, at which point it has stopped being a shared decision.

**Catch-up:** nothing. `slipwai search --kind quickstart` shows whether anyone has published one where you
are looking.

**The question about letting an extension refuse a tool call is asked once per quickstart, not once per
project.** If the quickstart you generated from already records a yes for a guard, `./init` allows it and
asks you nothing: you answered that when you wrote the quickstart. If an extension has *gained* a guard
since, you are asked about that one, named on its own, and the agreement you already gave stands whatever
you say about the new one.

A project generated from no quickstart is asked about everything, exactly as before, and silence is still
no: `./init` run with nobody at a terminal agrees to nothing new.

**Catch-up:** nothing. `python3 scripts/extensions/guards.py --elect <keys>` still allows an extension's
guards by hand in a project that is already set up.

**There is a worked quickstart to copy, called `typescript-ui`.** TypeScript on both sides, Event
Modeling, a React browser app, Postgres, and `codegraph`, `uipro` and `ux-gates` elected. It is in
[docs/reference/typescript-ui](../docs/reference/typescript-ui/), with the reasoning beside it, and it can
be installed from a checkout or published to a channel like any other package.

**It is an example and not a default.** Nothing installs it, nothing offers it until you do, and
`slipwai generate` still opens with *ask me every question*. A default quickstart would be a default set of
third-party extensions chosen for every project anybody generates, and this keel does not choose those. Run
`slipwai quickstart show typescript-ui` before using it: it prints every answer it would give, including
that it carries an agreement for `codegraph` to refuse a search.

**Catch-up:** nothing. `slipwai quickstart install docs/reference/typescript-ui` from a checkout, then
`slipwai generate bookings --quickstart typescript-ui`.

**There are five more worked quickstarts to copy, one per shape of project.** `laptop-trial` (Python,
SQLite in a file, nothing to install or log into), `aws-customer-product` (Python and React on AWS, Postgres,
two Cognito pools), `azure-staff-service` (Java on Spring in an Azure subscription, Entra ID, no public
sign-up), `existing-platform-service` (Go joining a platform somebody else owns and provisioning nothing) and
`internal-tool` (TypeScript either side under the standard profile). Each is a directory under
[docs/reference](../docs/reference/) with the reasoning beside it, and each installs from a checkout or
publishes to a channel like any other package.

**They are examples to copy, and not defaults.** Nothing installs them, nothing offers them until you do, and
`slipwai generate` still opens with *ask me every question*. Five quickstarts shipped as defaults would be
five sets of answers chosen for every project anybody generates, which is the thing 13.5 declined to do with
one. Run `slipwai quickstart show <name>` before using one: it prints every answer it would give, and every
one of those answers is a flag you could have typed instead.

**The gate is the part that lasts.** `tests/test_shipped_quickstarts.py` holds every directory shipped here
to parsing through the keel's own reader, carrying a `suits`, naming its packages by range rather than by
pin, and naming only answers the catalogue offers — under the profile that asks for them and the target that
can carry them. `internal-tool` is the case that proves the last clause: under `standard` neither
`write-model` nor `persistence` is a question, so it names neither, and a quickstart that named one anyway
would be offered in the menu and refused at generation.

**Catch-up:** nothing. `slipwai quickstart install docs/reference/<name>` from a checkout, then
`slipwai generate <project> --quickstart <name>`. The two cloud ones need their target first —
`slipwai target install aws` or `slipwai target install azure` — because a quickstart names languages and
extensions and cannot name a target, so neither is greyed out in the interview on a machine without it.

**`slipwai` typed on its own now opens the board instead of printing a usage message.** The verb that needs
no argument is the one that shows you where you are: your fleet, folded from the logs, in a page. In a
directory that is no project it opens anyway — empty, with the two things you can start from there, so
somebody who has just installed this and knows nothing else has somewhere to go. `slipwai --help` is what
prints the verbs now, and every one of them is reachable exactly as it was.

Run from a script it is unchanged. A standard input that is not a terminal, and `--no-browser`, print the
same usage message they always did: a tool run without a person has nobody to show a page to, and a server
it could not see would be worse than the list it expected.

**Catch-up:** nothing. `slipwai fleet` and `slipwai bridge` are the same commands they were.

**A project can now be generated from the board.** The interview `slipwai generate` asks in a terminal is a
page on the board as well: the same questions, in the same order, with the same options and the same
refusals, because both faces read `catalog.json` rather than writing the questions down. Answer the ones
that decide the others — where it goes to production, which language — and the rest are asked again from the
catalogue, so the page never offers a combination the generator would turn down.

What it is held to is not that the two descriptions agree. A gate drives the terminal interview with every
question answered by its default, generates the same project from the board, and compares the two trees file
for file; a default the page disagreed with would show up as a different file. Generation itself is still
the verb — the board runs `slipwai generate` with the flags your answers come to, so there is one path into
a written project and not two.

**Catch-up:** nothing. `slipwai generate` in a terminal is unchanged.

**The board can adopt a repository you already have, and it shows you the list first.** Point it at a
directory and it reads the tree: every directory that builds, with the file that gave it away, where CI
runs, where the schema is versioned, how a change reaches production today. Under that is the thing a
terminal cannot do well — every path adoption would add, and every file of yours it would add to, named
before a single byte is written. Nothing happens until you press Adopt.

Looking is a read and leaves the repository exactly as it was; a directory that is not a clean Git
repository without a `project.json` is refused where the list would have been, as the verb refuses it, and
before the tree is surveyed rather than after. Adopting runs `slipwai adopt` itself, so what lands is the
one commit that command has always made.

**Catch-up:** nothing. `slipwai adopt` in a terminal is unchanged.

**The board is one page whatever started it.** The fleet, starting a project and adopting a repository are
three tabs of one server on one port, each with a URL you can keep and come back to. `slipwai bridge` opens
it at the board, `slipwai fleet --page` does the same without giving up the printed board it has always had,
and `slipwai` on its own opens it as it did before.

**And none of them starts a second one.** A verb run while a board is already serving opens a tab on that
board instead of binding a rival on another port — two servers each sure they were the board was a real way
to end up looking at a stale page and not knowing it. The published read-only copy has no tab bar, because
it is one file and a link to a route it does not carry would be the two copies disagreeing.

**Catch-up:** nothing, with one thing worth knowing: `slipwai bridge` now opens your browser as well as
serving. Where there is no browser to open — a server, a container — it serves exactly as before and prints
the URL.

**The board has a Packages tab: what this copy has, what the chandlery offers, and a button that installs
one.** Languages, extensions, targets and quickstarts, a table each, with the installed ones first and a
version against every row — so finding out that a package exists no longer means knowing that `slipwai
search` exists. A row whose newer release is published says so beside the one you have.

**It installs through the verbs and not around them.** Pressing Install calls the same function `slipwai
language install` and `slipwai extension install` call, so a package is staged, hashed and admitted the one
way, and what the page prints is what the terminal would have. A channel that cannot be read is said above
the rows rather than instead of them: what is installed here is still listed, because a short listing that
does not say it is short is how somebody concludes a package does not exist when a mirror was down.

**A publisher is accepted on the page, deliberately.** An extension, a target or a quickstart from a
publisher this machine has not accepted carries a tick-box naming them, and the install is refused until it
is ticked — the same question `--accept-publisher` asks in the terminal, asked where the person already is.
A language's row has no box, because nothing on the language path asks.

**Catch-up:** nothing. `slipwai` or `slipwai bridge` opens the board; the tab is on it. The published
read-only copy has no tab bar and does not serve the route, which is unchanged: it is a file on a Pages
site, and a page offering to install something onto the machine serving it would be the two copies
disagreeing about what they are.

**The board installs as an app.** Chrome and Edge now offer to install it — there is a button beside the
theme toggle, and the browser's own offer in the address bar — and an installed board opens in its own
window from the dock or the Start menu, with no address bar and nothing to type. For somebody who never
wanted a terminal, that is the difference between a tool they can open and a command they have to remember.

**It cannot start the server, and it says so rather than failing like one.** The board is a server on your
own machine and installing a window did not install that, so when nothing is listening the installed window
gets a page saying exactly that, with the one word that starts it — instead of the browser's own connection
error, which tells a person who does not open terminals nothing they can act on. That page is the only thing
kept offline: everything else goes to the network every time, because a dashboard is a fold of files that
change under it and a cached board would be the one view that is a memory rather than a reading.

**Catch-up:** nothing. Open the board and press Install, or use your browser's own install control. The
published read-only copy is unchanged and offers none of this: it is a file on a Pages site, and an offer to
install a board that is not yours would be the two copies disagreeing about what they are.

**A fifth slice status, `observed`: what the code already does, and the model did not design.** A
repository the method was installed around was designed — just not here. Its order handler, its status
columns and its jobs are somebody's design, and a model that records them as `implemented` claims the
method authored them. `observed` is the honest word for them.

It carries `code` and `gwt` that point at what is already there, and they must exist: a slice claiming to
record real behaviour with nothing to point at is a guess wearing a status field.

It is exempt from `model-matches-code`, and that is why it is confined to a service `project.json` records
`"generated": false`. Nothing the keel did not write contains `OrderPlaced` until a slice raises it — the
names in an `observed` slice are business facts somebody read *off* the code, not identifiers in it. On a
generated service that exemption would be a way of never being asked whether the model and the tree still
agree, so `check-model` refuses it there by name: if it is built it is `implemented`, and if it is not
built yet it is `planned`.

It is on the timeline and it is not work. A later slice may `reads` what it sets — that is the join, and
the reason the model is global rather than one per feature — but `/sail` never offers one. Its marks are
set by the code existing, so anything steering by them is cleared the moment the chart is drawn, and no
captain is sent to build what already ships. The move from `observed` to `implemented` is a slice of work,
not an edit to a field.

**Catch-up:** nothing. The status is new, so no existing model uses it.

**A cross-service `reads` from a state-stored service is refused until that service says how it
publishes.** On the `state` rung an event is modelled always and emitted only where something reads it.
Within one service that reader is reached by a call the use case makes — the `pcr` frame — and no message
is sent at all. The moment the reader is *another* service, there is no log for it to subscribe to: the
event is raised in process, lost on the one failure that matters, and the model names a mark nobody can
consume.

`check-model` now says so, naming the producing service rather than the slice that noticed, because it is
the producer's rung that has to move. It is cleared by recording how that service publishes, on its own
deployable in `project.json`:

```json
"billing": { "kind": "service", "eventSourced": false, "publishes": "outbox" }
```

`outbox` is the events written to an outbox table in the same transaction as the state write, which is
what T023 builds. `bus` and `cdc` are there because a project that already publishes some other way should
name that one: a second mechanism beside a working one is what this rule is trying not to cause. The field
is absent on every service the keel generates, and stays absent until something reads the event — nothing
asks for it at `./init`, because until then it has no answer.

Not asked on the event-sourced rung, where the log is the publication, and invisible to `make chart`: the
rendered chart of a model is the same whichever rung either of its slices is on.

**Catch-up:** nothing, unless `make check-model` now refuses a model it passed before — in which case the
refusal names the service, and the answer is the `publishes` line above once that service has the outbox.

**Adoption stops selling Event Modeling and event sourcing as one thing.** `docs/change-strategy.md`'s *Be
honest about the event model* opened by saying the generated method carries the two as a bundle, which is
exactly the claim phase 15 exists to retire. It now says the sharpened rule — the model is the same on
every rung, and the rung is a separate decision taken per service and recorded in `project.json` as
`eventSourced` — and it names the honest answer for a capability that has just moved out of a legacy
system: rung 2 of the ladder, in-process events, `--write-model state`, no genesis event, with the data
arriving by change data capture or an outbox. A genesis event is named under `--write-model events` and
only there, because it is the thing that makes a log's first entry honest rather than backfilled.

**`/strangle` asks for the freeze before the first capability moves.** A strangler fig grows beside a
system that is standing still; one that keeps gaining features is a side-car that drifts, and the
retirement ledger cannot show it. So the command now asks for the agreement — no new features in the legacy
system, bug fixes only, no schema changes — recorded on the strategy ADR as `Freeze: agreed — <who, when>`,
or recorded as `Freeze: absent — <what is done instead>` where nobody will agree to one, which is an answer
and not a failure. `/strangle` says where it stands today, refuses the first capability on silence, and
invents neither answer. `/strangle`'s *Decide the new home* now asks the rung too, before `add-service`
runs.

**A wrapped application's rung is recorded only by a person.** `slipwai adopt --confirm <name>
--write-model events` records it, with `confirmed` provenance, and `/ground` asks for it — but only of the
candidates whose own dependency manifests name an event store, which the survey now reads per buildable
directory and proposes on the candidate. A candidate the survey proposed `events` for and somebody
confirmed in silence records nothing, and `eventSourced` stays false: a log nobody vouched for is a guess
wearing a fact's clothes. `/survey`'s event-model section now says the code that was already here is an
external system *or* a state-stored service of this project, by whether anybody has modelled its behaviour
or only read what it emits.

**No persistence row joins the convergence map.** Every row on that map has one top every repository should
climb to, and a rung has none — a service that honestly is field updates is finished at `state`. The map
stays nine rows; `project.json` is the rung's record, per deployable.

**Catch-up:** nothing to run. `/survey` rewrites the pages from the record, and a repository that has
already adopted gains the questions on its next one.

**A language family can supply the browser app now, instead of the keel being the only place one can come
from.** A family that answers `npm_workspace` may also answer `browser_apps`: which browser apps it writes,
by the name `--frontend` is typed as, each one the directory its material is copied from. The keel reads the
material through that record wherever it comes from, so a frontend is no longer a directory the keel knows
the path of — and a family's own wins a name the keel also carries, because the family ships the workspace
lock that resolves the app it ships.

This is the contract, not the move: `react-vite` is still inside the keel, still the default, and generates
exactly the project it generated before. What it buys today is that somebody publishing a language package
can ship a browser app with it and find out locally whether the keel can read it — a family that reaches
outside its own directory for one, lists a record under a name it does not answer to, or offers a browser app
without declaring the workspace that holds it is refused at load, naming the package.

**Catch-up:** nothing. No project changes, and a language package that answers nothing new loads as it did.

**The order your slices run in is now something the split proposes and you confirm, rather than something
the ids happened to spell.** The order of `chart.yaml`'s `slices` block has always been the order every
captain takes them in — the ready set is in it, and so are the merges inside a fairway — but nothing ever
said so, and on the event-modelling profile the renderer sorted the rows by id, so a project whose billing
slices sorted above its ordering ones ran them in that order for no reason anybody had given.

The split now has an `## Order` step. `python3 scripts/agents/clearance.py --order` prints every slice in
the order the chart currently holds with what that position is read off — what holds it, how many siblings
steer by what it sets, and where it falls in its capability — and the stage puts an order to you with a
reason per row, the way `/chart` proposes fairways and marks. Three things are not preferences and are held
as rules: nothing goes above what sets the marks it steers by, a capability's slices stay together, and the
walking skeleton goes first. Under `/cruise` it is an ordinary decision, taken here under
`decide: recommended-first` and delegated under `decide: skipper-always`.

On the event-modelling profile the order now comes from `model.yaml`'s own list order, which is what the
split agreed, and `make check-chart` refuses a chart whose rows are in another order than the model's. The
same rows in two orders are two answers to what runs first, so a reordered model is drift now, where the
renderer's own documentation used to say it was not.

**Catch-up:** run `make chart` once on an event-modelling project, then commit the result. Your chart's
rows are in id order from the old renderer, and the gate now reads that as disagreeing with the model
wherever the model lists them differently. On the standard profile nothing changes until your next split,
which will propose an order instead of writing one in passing.

**You can say which stream goes first, and change your mind while the run is going.** A project with more
fairways than berths has always had some of them waiting, and which ones were lit was wherever each
fairway's first slice happened to fall in the chart. Now the order of `chart.yaml`'s `fairways` block is
the priority: the fairways at the top are the ones whose captains are lit, and when slots are scarce a
ready slice in an earlier fairway takes one ahead of a later fairway's. Inside a single fairway nothing
changes — the split's order is still the whole rule, which is what keeps merges predictable.

`slipwai telegraph --set fairways=billing,ordering` moves a stream up without stopping anything. It moves
the names it holds to the front and leaves every other fairway behind them in the chart's own order, so a
stream is never parked by a setting that forgot to mention it, and a name the chart has not got is refused
while you are still there to see the typo. Ringing a position does not reset it: a run you slowed down at
four o'clock has not changed its mind about which stream matters.

A captain that drops below the lit line finishes the slice it is on, writes a `yielded` line naming the
fairway that displaced it, and exits. It never abandons claimed work: a slice being carried over from an
answered park, or a fix owed to a red trunk, is finished first. The harbourmaster lights the fairway that
came above the line on its next pass, so a reorder takes effect on a run that is already going rather than
needing everything stopped and cast off again. `slipwai fleet relight` does the same by hand.

**Catch-up:** nothing, unless you want it. With no `fairways` in `harbour.json` the order is the chart's,
which is the order your split already agreed. On the event-modelling profile run `make chart` once so the
block is rendered in the model's order rather than alphabetically.

**Languages are packages, and the keel ships none.** Version 1 carried Go, Python, TypeScript, Java,
Spring and Quarkus inside the wheel, so a fix to one was a release of all of them and nobody outside the
repository could add a seventh. Each is its own repository and its own release now, installed from the
chandlery:

```sh
slipwai search              # what there is, of either kind
slipwai install go          # into ~/.slipwai/packages/
slipwai language list       # what you have, and what is offered
```

A package declares what it answers in `language.json` and answers the backend protocol in Python the keel
imports from its own directory. One that cannot load is refused **by itself**, in one line naming the
package, the directory and the fault — the others still load, and a verb still runs.

**Catch-up:** `slipwai migrate` in each project installs the languages that project's services are written
in. Until you run it, nothing changes.

**Extensions are packages too, and the three the keel carried have left it.** `codegraph`, `uipro` and
`ux-gates` lived in `catalog.json`, so every project generated carried the description of three dev tools
whether or not anybody wanted them, and a fourth meant a commit to the keel.

```sh
slipwai extension install codegraph    # or a directory, a release file, or a git URL
slipwai extension list                 # what is installed, and what each attaches to
slipwai hooks                          # the moments an extension may attach to
```

An extension's entry point is held to six obligations, each of them a failure somebody had: idempotent,
non-fatal, marker-fenced projection, a gate for state that can go stale, a recovery command on every
failure path, and merging rather than overwriting what a person hand-edited.
`python -m slipwai.conformance --extension <dir>` runs them against a scratch project.

**Catch-up:** `slipwai extension install <key>` for the ones you used, then `slipwai migrate` in each
project so `./init` offers them.

**One chandlery, several channels, and a publisher's four verbs.** An index lists packages of both kinds,
each entry declaring its kind, its publisher, a signature field, a description and tags — so
`slipwai search postgres` finds whatever will talk to Postgres for you, whichever language it is in.

`SLIPWAI_CHANDLERY` names the channels in order, comma separated: an organisation's own first, the public
one after it. **A name an earlier channel lists is that channel's**, versions and all, so an organisation
publishes its own `python` and it wins with nothing else configured. One channel being unreachable is said
and the rest are still listed; every channel being unreachable is a refusal, because "nothing available"
and "could not ask" are different answers.

Publishing is four commands, and the verb works out which kind of package it is from the manifest:

```sh
slipwai package new <name>                            # a package that already loads, TODOs where decisions go
slipwai package check .                               # the conformance suite its kind is held to
slipwai package release .                             # the file, its digest and its index entry
slipwai package register . --channel <a checkout>     # both, into a channel, and its index rebuilt
slipwai channel new|build|check                       # running a channel, public or private
```

A channel is a directory of JSON and release files served as static files, holding one entry file per
release — so two publishers releasing on one afternoon touch two files and never meet.

**Catch-up:** nothing for a consumer. A publisher: `slipwai package new` writes the whole repository.

**A package's publisher is asked about once.** Installing a package is running somebody else's code: a
language's Python is imported into the keel and an extension's entry point edits your project. The digest
the index publishes proves the file is the file the index listed; it says nothing about who listed it.

Accept a publisher and every later release of theirs installs silently. `slipwai trust list|add|remove`
does it ahead of time, which is what a container image or a CI runner needs. `ROBCOATVG` is seeded as a row
like any other and can be removed.

A release is in one of four states and `slipwai show` says which: `verified`, `unverified`, `unsigned`,
`untrusted`. `unverified` is kept apart from `verified` deliberately — the one thing a signature must never
be used to say is "signed" about a signature nobody looked at.

**Catch-up:** nothing. The first install from a named publisher asks you once.

**The runner is gone and the loop has captains.** Version 1's `/cruise` ran one iteration per checkout and
trusted what the iteration said about itself. It died at iteration two, and the seventeen iterations that
followed ran from interactive sessions and wrote nothing — so the checkpoint said "iteration 2" while
twenty slices merged.

The replacement is not a better runner. It is **no runner**:

- A **captain** per stream claims the next slice its clearance allows, dispatches the ladder, watches the
  log, and asks for the merge. It watches the *log* and not the process: a stage that has written nothing
  for its budget is ended and parked, with the reason, because a process that is alive and writing nothing
  looks identical from outside to one working hard.
- A **harbourmaster** carries the handful of lines streams need from each other, allocates workspaces, and
  holds the credentials. A captain asks it for a push, a merge, a deploy, a flag change or a publish; what
  it will never do is a closed list checked against the request's own text, and **both outcomes are
  written**, because a refusal that left no line is one somebody waits on for ever.
- `/cruise` starts them and exits. Nothing you type holds the state of a run.

A hook never costs a rung. The captain's controls depend on none of them — it reads the last line itself,
diffs the controlled files, owns the waits — so an extension that fails is a `hook` line and not a failed
stage.

**Catch-up:** `slipwai migrate`. `make cruise`, `make cruise-status` and `make cruise-stop` keep their
names and mean the new thing.

**Status is folded from lines, never stored.** The rule the whole of version 2 rests on: *a slice that
wrote no line made no progress.* A line is written by the thing that did the work at the moment it did it,
and nothing keeps a second copy of what happened.

Two logs, and the split between them is about writers: a stream's captain writes its own **deck log** and
nothing else, so no two processes ever append to one file; the **harbour log** has exactly one writer, so
the shared one never conflicts. Every line carries the format it was written in, and a reader that meets a
newer one refuses it and names the upgrade rather than guessing which fields moved.

`slipwai fleet` folds the board out of them and keeps nothing of its own. It tells a **stalled** stream
from a **finished** one — the pair that look identical in a status field, since neither is writing
anything — and where the log says nothing, the board says nothing: a stream with no lines is `not started`,
not `0%`, and a number nobody wrote is a dash, not a zero.

`slipwai bridge` is the same board as a page you can answer from. A question from a stream is a line in
that stream's log, and typing the answer on the page writes it there — so a person answers from one seat
instead of finding the right terminal.

**Catch-up:** `slipwai migrate`.

**The delivery loop has rungs, and four of them are new.** Before anything is built, a feature is charted,
its screens are drawn and approved, and the marks each slice sets and steers by are written down. After it
is built, it is reviewed and reshaped before the adversary sees it.

What falls out of the chart is the thing version 1 could not do: **a sibling unblocks a slice by having
planned, not by having merged.** A mark is set at the setting slice's first stage, in its own worktree, and
that is what clears the slice waiting on it — so streams run beside each other instead of queueing behind
every merge.

Other things a run is now held to:

- **A demo is of a capability**, not of a slice and never of a release flag. Accepting one says the work is
  right; whether the business wants it live is a separate decision and stays one.
- **Every stage has a budget**, in minutes and in tokens. A stage that reaches it does not keep going and
  does not hand its leftovers to the next slice: it **stows** into the stream's careen and says the number,
  because a budget hit every time is a budget that is wrong. Anything above the severity bar parks for a
  person instead, and nothing CRITICAL is ever stowed.
- **Messages have receipts and waits have bounds.** A message a person sent that nothing answered inside
  the bound stops the stream, and a backlog of unread decisions does too. The experiment reached 125
  decisions with 105 never reviewed, which is not a record of judgement.
- **An event is a file and the index is generated**, and the composition root's wiring comes from the
  chart — so two slices adding an event, or wiring a use case, merge without a conflict.
- **One gate is fast and one is full.** The per-increment gate leaves out what shells out or stands up a
  server, and the rule holds in generated projects as well as here.

**Catch-up:** `slipwai migrate` writes the new commands, gates and documents into an existing project.

**One lever sets every number a run is held to.** A run has a dozen numbers that all mean "go slower" in
different units, and changing one position to another by hand is eight edits that anybody in a hurry gets
some of.

```sh
slipwai telegraph                     # where it is, and every number under it
slipwai telegraph slow-ahead          # the whole group together
slipwai telegraph --set boilers=2     # one, and the board then says "slow-ahead, adjusted"
```

Five positions, fastest first: `full-ahead`, `half-ahead`, `slow-ahead`, `dead-slow`, `stop`. Ringing one
resets everything, which is what makes a hurried adjustment safe. `adjusted` is said rather than a new
position being invented, because a board reporting a position its numbers do not match is a board that is
lying.

When the day's budget is spent the harbourmaster steps the position down **one notch**, writing what it
stepped to and why. Never straight to `stop`: a run that stops dead loses whatever was in flight, and a run
that slows keeps finishing what it started.

In the experiment none of these numbers existed. 104 hours and hundreds of millions of input tokens on one
slice, and the only signals were a person noticing and the bill arriving.

**Catch-up:** `slipwai migrate` writes `harbour.json` with the defaults.

**New verbs, and the ones that moved.** `slipwai --help` lists them all; these are the ones that are new
or that mean something different:

| Verb | What it does |
| --- | --- |
| `search`, `show` | Find a package before you install it. Version 1 had no way to ask |
| `install`, `language …` | The chandlery's client: install, upgrade, remove, list |
| `extension …`, `hooks` | The other kind of package, and the moments one may attach to |
| `package …`, `channel …` | A publisher's side, and running a channel |
| `trust …` | Which publishers this machine installs from |
| `telegraph` | Every number a run is held to, under one lever |
| `fleet`, `bridge` | What every stream is doing, in the terminal or as a page |
| `adopt` | Installs the method around a repository this factory did not make — **with no language installed**, whatever that repository is written in |

`slipwai adopt` ends in `slipwai converge`, which is the verb that needs a language for each service it is
bringing up to generated.

**Catch-up:** nothing; they are new.

**What the keel is, and what it is held to.** Version 2's own source has an architecture with a gate on it:
seven tiers, no upward imports, no cycles, and a 350-line budget per module. A language package may import
exactly twenty of the keel's modules and `check-structure` refuses a twenty-first, so the surface a package
depends on is a decision rather than whatever happened to be reachable.

The keel ships with **no dependency**. Everything here is the standard library: the index client, the
release packer, the conformance suite, the board, the bridge's server.

The toolkit a project gets is written once and copied, never kept as a starter: a change under `assets/`
reaches every combination the moment it is generated. Anything a generated project runs is a toolkit
script, because a generated project has no slipwai to import — and the two modules both runtimes genuinely
need are carried into the toolkit from one source with a gate that refuses a copy that has drifted.

**Catch-up:** nothing. This is the factory's own shape.

**A package is now proved with whatever it is proved through beside it.** `java`, `java-spring` and
`java-quarkus` were red, and had been since their CI was added, each saying exactly why:

```
language java-spring (…): requires java >=1.0,<2; java is not loaded
java declares no backend of its own, and no backend of family java is loaded
beside it in …: a family is checked with a framework beside it
```

The reusable workflow checks one repository into `$PWD` and points conformance at `$PWD`, so a framework met
its own family missing and a family met no framework to be checked through. The suite was right both times;
nothing put the sibling there.

It does now, before conformance, into `$PWD` — `SLIPWAI_LANGUAGES` names the one directory the keel looks
in, so the sibling lands beside the checkout and the checkout stays the copy under test. **A framework's
family is worked out from its own `requires`** and needs no configuration. **A family names a framework**,
through a new `beside` input, because which of its frameworks proves it is the publisher's choice.

**Catch-up:** `java-spring` and `java-quarkus` need nothing — the next push fixes them. `java` needs one
line in its own `verify.yml`, beside `package:`:

```yaml
      beside: java-spring
```

**Every published package runs conformance on each push, and the matrix on `main`.** Ten repositories: six
languages, three extensions and the template `slipwai package new` copies. Three of them were red, four had
no workflow at all and read green while running nothing, and the matrix had never run anywhere.

What switching it on found, all of it in the keel:

- a package was never put beside what proves it, so a framework met its own family missing
- `--accept-publisher` was passed to a language install, which has no such flag
- installing *into* the checkout's directory was refused by the very state it was fixing
- the default chandlery index pointed at a path that has never served one
- the matrix's runner had no toolchain to build a generated project with
- an image builder a package names itself ended the run in `KeyError` rather than a skip
- three of the six obligations an extension is held to were wrong about the messages they read

**Catch-up:** nothing for a project. A package you publish yourself gains three declarations in its own
`verify.yml` — `toolchains`, `beside` and the `matrix` line — which `slipwai package new` now writes.

**The keel's reusable workflow takes a keel that is not on PyPI yet.** `keel` was a version number, so
every caller that left it empty installed `slipwai` — which is version 1 while version 2 is unpublished,
and version 1 has none of the verbs the caller needs. That failed three different ways in one morning: the
channel's own check, a package's conformance, and the publish job.

A bare version is still one on PyPI. Anything else is passed to pip as it stands, so
`git+https://github.com/owner/repo@main` works. Empty installs `slipwai`, which is where every package
ends up once the version it needs is published.

**Catch-up:** nothing. A package that pinned a version keeps working.

**The generated-variant matrix is opt-in, and there was no way to opt in.** The keel's reusable workflow
took a `matrix` input and the workflow `slipwai package new` writes passed nothing, so
`gh workflow run ... -f matrix=true` had nowhere to land — and the obvious guess, dispatching
`package.yml`, is a 404 because a reusable workflow is not dispatchable.

A package's `verify.yml` takes the input now and passes it through, off by default so a push never starts
containers. The command is written in the workflow rather than left to be remembered:

```sh
gh workflow run verify.yml -R <owner>/<repo> -f matrix=true
```

**Catch-up:** an existing package adds the input to its own workflow, or regenerates it.

**A package's generated-variant matrix now runs on `main` and on a tag, without being asked.** It was
opt-in everywhere, and the only way to opt in was a person typing `gh workflow run verify.yml -f
matrix=true` — which is the same as off. Not one package had ever run it.

This is the two-gate split a project already has for itself, applied to a package: a pull request gets
conformance, which is the fast half and the one an author runs over and over; `main` and a tag get every
generated variant of every backend as well, each held to its own native gate, because that is the
integration point.

The dispatch input stays, for a change somebody wants matrixed before it reaches `main`.

**Catch-up:** a published package's `.github/workflows/verify.yml` is its own file and does not update
itself. Replace its `matrix:` line with the one `slipwai package new` now writes:

```yaml
      matrix: ${{ inputs.matrix || github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v') }}
```

**Three faults a real run found, in the chart the event-modelling profile writes.** The first project
generated with version 2 and driven through a captain turn found all three in ten minutes:

- The renderer wrote `fairways: {}` for a project with one service and a web app, because `service` is
  optional on a slice while there is nothing to decide — and `check-chart` then refused the chart the
  renderer had just written, for naming fairways it had not got. The only *service* owns a slice that
  names none; a web app never does.
- The renderer dropped a slice it could not read and reported "0 slices" as a success. It names them now
  and writes no chart.
- The model schema had no `capability` field, and `check-chart` requires one on every slice. Three
  artefacts, two agreeing and one unable to supply it, so an event-modelling project could not produce a
  chart that passed its own gate. A slice names its capability from `planned`.

**Catch-up:** `slipwai migrate`. A model whose slices are `planned` gains a `capability` each — several
slices share one, which is the point: a demo of a single slice is a demo of a form that saves something.

**An extension can now refuse a tool call, and only that.** A hook is never fatal to the rung it runs
around — that rule is what stops an extension becoming a second control plane, and it left one thing
unbuildable: an extension that wants to say *don't grep for that, ask the index* is answering a call that
has not happened yet, not reporting after the fact. Version 1 reached it through one harness's own
`PreToolUse` hook, so it worked on Claude Code and silently did nothing everywhere else.

So there is a second closed set beside `hooks`, with three moments: `session`, `before-search`,
`after-delegate`. A guard that **exits 2** stops that one tool call and what it printed goes back to the
agent, which then does something else. Everything else a guard does — a crash, a timeout, any other exit
code — is a hook's behaviour: said, and the call goes ahead. **No guard can end a rung**, and `hooks`'s rule
is untouched.

```sh
slipwai hooks        # both sets now, and which may refuse
```

**A guard is agreed to, not just elected.** Electing an extension runs its hooks; a guard also refuses
things a person asked for, so `./init` asks once, over `/dev/tty`, saying what each extension would be able
to stop. **Silence is no** — a scripted or CI `./init` is never asked and allows nothing, which is the only
safe direction for that question. An extension that declares a guard nobody agreed to fires none.

Declared in `extension.json` beside `hooks`, in the same two forms:

```json
"guards": { "before-search": "guards/search.py" }
```

**Catch-up:** `slipwai migrate` adds `scripts/extensions/guards.py` and the `./init` question. Nothing may
refuse anything until somebody answers it.

**`slipwai package version` cuts a package's release.** It assembles `changelog.d/` into the next entry of
`CHANGELOG.md`, writes `VERSION`, and deletes the fragments — which is exactly what the conformance suite
has always demanded and what nothing could do. `VERSION` was a file to edit by hand, and editing it by hand
is precisely what the suite catches: six packages were released that way and every one of their first CI
runs failed on it.

Cutting and building stay apart. `version` rewrites the working tree and a person runs it, reads the entry,
commits and tags. `release` builds a tarball from whatever the tree says and is what CI runs from the tag —
a CI job that rewrote the changelog would be rewriting the commit its own tag points at.

The first release of a package carries no level, because it was bumped from nothing and "MINOR relative to
nothing" means nothing. `slipwai package new` now ships a `CHANGELOG.md` and a first fragment, so the whole
chain works with no hand edit: new → version → check → release → register.

**Catch-up:** a package that already has a `VERSION` ahead of its changelog runs `slipwai package version`
once to catch the two up.

**A release file lives wherever its publisher hosts it, and the channel holds the entry.** Git keeps every
version of every file for ever, so a channel that stored its own tarballs would grow a copy of every
release anybody ever made — and a contribution would arrive as a binary a reviewer cannot read. The
chandlery that opened with six packages went from 1.2 MB to 16 KB.

An entry's `file` may be any URL: a release asset on the tag that built it, an artifact store, a plain web
server, or a path relative to the index as before. **The digest is what makes somebody else's URL safe to
list.** A publisher can replace the bytes their tag hosts and nobody can stop them; what it costs them is
their own package, because the client refuses bytes that are not the bytes the index named.

`slipwai channel check --fetch` downloads each remotely hosted file and holds it to its digest. The
channel's CI does that on every pull request, which is where a contribution from somebody nobody knows is
actually decided. Without `--fetch` the check reaches no network, so a person checking a channel on a
train is not waiting on a hundred downloads.

**And a tag publishes.** A package's CI, on `v*` and only on `v*`, builds the release, attaches it to the
tag, and opens a pull request to the channel it names. A green run on `main` is a package that works; it
is not a package anybody asked for. Without a token for the channel the release is still built and
attached, and one command registers it — so a fork needs no credential and a package nobody owns can
still be proved.

**Catch-up:** nothing for a consumer. A publisher gets the tag trigger from `slipwai package new`; an
existing package adds `tags: ['v*']` and a `channel:` to its workflow.

**A channel's root was a 404.** It is a static site, and the only thing served at the top of it was the
machine's answer — `slipwai-languages/index.json` — with nothing for a person who opened the URL they were
sent to.

`slipwai channel build` writes `index.html` beside the index now: what the channel serves, one row per
package with its newest version and the one command that installs it, and the four commands for publishing
to it. Generated from the same entries as the index, so a release that changes one changes the other and
neither is edited by hand.

No script and no fetch. A page that read its own JSON at load would be blank wherever script is off, for a
list that is already known when the page is written.

**Catch-up:** `slipwai channel build` in a channel that already exists.

**The fleet stops adding to a red build.** The gate before a merge is the project's own `make verify`; CI
runs `make ci`, which adds `audit` and `test-integration`. So trunk could go red from a check `verify` never
ran, and nothing noticed while every fairway kept merging onto it.

Before granting any merge the harbourmaster reads trunk's most recent **completed** CI runs. Green, it
proceeds and the `granted` line says so. Red, it refuses, and **no fairway is granted a merge until trunk is
green** — the queue drains the moment it is. A trunk that was red and is green again is written once as
`trunk-green`, so the log says when the queue reopened.

**Every workflow of the newest commit has to be green.** One passing while another fails is a red trunk, and
reading only the first run would call it green — which is the failure this exists to stop.

**A forge it cannot reach reads *could not verify*, never *green*.** The merge still goes ahead, because a
harbour with no forge has to keep working, and the `granted` line records `ci: unverified` so nobody reads
it later as a run that was checked. `gh` is what asks by default; `harbour.json`'s `ci` takes a command for
another forge, with `{trunk}` and `{limit}` filled in, and `ci: "off"` says not to ask.

**The fix goes to the captain that broke it, not to a person.** The harbourmaster wrote the `merged` line
for the commit that went red, so it knows the fairway and the slice: `fix-trunk` names them, and that
captain takes the fix at its next turn ahead of any new slice. Every other captain keeps building, and that
work is not wasted — a sibling is cleared by a mark being set, not by a merge. A red trunk that no `merged`
line accounts for — a direct push, or a red older than any merge — parks for a person at once, because
guessing who broke it would send a captain to rewrite somebody else's work.

**Catch-up:** `slipwai migrate` is not needed. A harbour with `gh` installed and a GitHub remote starts
reading trunk on its next pass; anything else reads *unverified* until `harbour.json`'s `ci` names a command.

**A stream's own log, read from the board.** `slipwai fleet` answers *is anything stuck*, and the moment
the answer is yes the next question is always the same one — what has this stream actually been doing —
which the board cannot answer, because the answer is forty lines of one file and the board is one row.

`slipwai fleet <stream>` prints it in the terminal, and each row on the bridge opens a drawer holding the
same thing. Every line is said rather than printed: `set OrderPlaced`, not
`{"kind": "mark-set", "mark": "OrderPlaced"}`. A kind it has no sentence for is still shown, with its
fields, because the log grows and a reader meeting an unfamiliar line should see that there was one.

A log that goes bad part way keeps what came before it and says where it broke — a log that breaks at line
90 has 89 lines somebody still wants, and the whole reason for looking at one stream is that something has
gone wrong with it.

**Catch-up:** nothing; both read logs a project already writes.

**The run drawn on the event model, in two bands.** The browsable page badges every slice with
`model.yaml`'s `status` — written by a person at plan time, and the field that failed: MANDA's model said
`planned` for eight slices that were built and merged, because nobody went back.

So the page now shows that badge **and**, beside it, what the logs say happened: not started, claimed,
marks set, demoed, merged, parked. Written by nobody, folded at render time, and never written back. A
slice badged `implemented` with `not started` next to it is that same drift, drawn on the page where
somebody would see it.

`make run-state` writes the fold; `make model` runs it first. Absent, the page renders exactly as before —
an overlay that was required would be a model nobody could draw before driving it. It never touches
`model.drawio`, which is committed and held current by a gate, so a heartbeat would dirty the tree.

**Also:** `.slipwai/`'s run state is gitignored at last — the logs, the pid files, the harbourmaster's
cursor, the berth records and this fold. `logs.py` has said they were ignored since slice 5.13 and nothing
ignored them. The election record, the controlled `hooks.json` and a project's own `packages/` stay
committed, each for its own reason.

**Catch-up:** `slipwai migrate`.

**The loop is tested end to end, in a project the keel generates.** Every other suite proves one link.
This one drives the chain: generate, write a two-stream model, render the chart, run its gate, run a
captain with a stand-in for `/sail`, carry the lines with the harbourmaster, and read the board back.

It holds the claim version 2 rests on — **a sibling is cleared by a mark being set, with nothing merged** —
which nothing else in the suite would notice the loss of.

**And it found a fifth fault.** The harbourmaster's cursor outlived its log: after a reset, a fresh clone
or a rotated log, the cursor sat past the end and that stream was never carried again, for ever, while
every pass reported that it ran. A log shorter than its cursor is now read from the start and said.

**Catch-up:** `slipwai migrate`.

**slipwai has a mark: a little tug whose funnel puffs a spark.** A tug is the boat that moves the big one,
which is the whole of what this does. The spark is a substitution rather than an addition — the puff a
funnel makes, made of something other than coal — because a circuit board would have said the same thing
in the way everybody else says it.

It works in one colour first: the porthole and the funnel's band are knocked out rather than painted, so
the mark holds as a favicon and anywhere `currentColor` is all there is. It sits top right of the bridge
and is that page's icon.

**And the bridge has a theme toggle** — Auto, Light, Dark. Three states, because two can only mean "the
system's, or the other one", which is the setting people cannot put back. Radios and `:has()`, so the
published copy keeps it with no script at all; the script only remembers the choice.

**Catch-up:** nothing.

**Seven guards and ten hook points, fired from one script the captain owns.** Version 1 reached three of a
harness's own moments by having the keel write `scripts/agents/cruise.py <verb>` straight into
`.claude/settings.json`. So the control-file refusal — *a stage never edits a gate* — and the compaction
protocol were behaviours of **one harness**: they worked on Claude Code and were absent on the other
thirty-five, with nothing saying so. That is the failure both closed sets exist to end, and this is the
change that ends it.

`scripts/agents/session.py` is now the one place a harness's moments arrive. It runs the keel's own answer
and then whatever an extension declared at that point, so an extension says `before-write` once instead of
learning thirty-six spellings.

**The guards went from three to seven.** The three were the three `codegraph` needed; the four new ones are
the *shapes* they left out, each with something firing it:

- `before-write` — a path about to be written. The control-file refusal lives here now.
- `before-command` — a shell command about to run. The same refusal through the door `before-write` cannot
  see: `make verify` rewritten by a `sed` is rewritten all the same.
- `before-fetch` — a URL about to be read. Egress is its own shape; what a guard is handed is a host.
- `before-stop` — a session about to end. Refusing it carries the turn on.

Three shapes are deliberately **not** there: nothing around a rung (that is `hooks.py`, and a guard there
would let every extension end a stage), nothing that can change what a call does rather than whether it
happens, and nothing after a write — a refusal after the fact is a report, which is a hook.

**The hook points went from seven to ten.** `after-merge`, because `before-merge` had no partner and a gate
that passed on a rebased branch is not the same event as a slice being on trunk; and `before-compact` and
`after-compact`, which are the two runner verbs, now points rather than rows.

**The hold is folded from the log.** `before-stop` holds a turn whose stage has written no deck-log line
since the session opened, and lets go after three — version 1 held against a checkpoint file that had to be
remembered to be written. *A stage that wrote no line made no progress* is the loop's rule and this is the
cheap half of enforcing it; the captain's gate is the dear half, and parks.

**Catch-up:** `slipwai migrate` writes `scripts/agents/session.py` and rewrites the harness hook rows. A
project generated before this keeps working — the old rows name a script that is still there — but the new
points fire only once it has migrated.

**A captain now runs the real `/sail`.** It fell back to `scripts/agents/sail.py`, which is the *settings
reader* for `/sail` — handed a slice and a fairway it prints its table and exits 0 — and the first real run
this loop ever did was reported through on the strength of it. It starts a headless session of the installed
harness instead, and asks it for `/sail <slice> fairway=<name>`.

Which harness, and what it is asked, come from `scripts/agents/registry.json`'s `headless` column, which
carried the answer all along and which nothing but the runner read. A harness whose print mode resolves this
project's slash commands is asked `/sail`; every other is asked to read `commands/sail.md` and follow it,
which needs nothing of a harness beyond reading a file.

**No harness here is a park that says which of the three things is wrong**: one is installed and its binary
is missing, one is installed and the registry records no way to run it headless, or one is on PATH and
`./init` never ran for it — that last is named with the `./init` that would add it, and is deliberately not
driven, because a harness with no projected commands or delegate types ends a session having done nothing.

`SLIPWAI_SAIL` still replaces the whole command and still takes `<slice> <fairway>`.

**Catch-up:** nothing, on a project whose `./init` has run. One that has never been initialised now says so
by name instead of parking on a mark nobody wrote.

**Two points the keel promised and nothing called.** `after-merge` was added with 7.7b and fired by nothing;
`after-delegate` was declared in 6.1d and had no caller at all. Both now have one — the harbourmaster fires
`after-merge` once the slice is on trunk and pushed, and `scripts/agents/session.py` answers `after-delegate`
on the harness's post-tool event — and a gate holds the rule from here.

That rule is the one both closed sets exist for, and it had never been turned on itself. A point nobody
fires is the worst kind of broken thing here: an extension declares it, passes conformance, is elected, and
then never runs. The keel refuses a point an extension *invents* for exactly that reason, and a point the
keel declares and never calls is the same failure with the keel's name on it.

The gate found a third thing, which is recorded rather than fixed: **`init` and `project` are still run by
convention**, an extension's `init.py` executed by name and its `project_guidance()` called by name, so one
that declared a different script at either point would be ignored. That is the convention-not-declaration
failure `hooks.py` opens by describing, and closing it means deciding whether `init.py` becomes the point's
default declaration — a change to a closed set, and slice 6.1e. The test names the two and holds the
exemption to its size, so a third cannot be added quietly.

**The runner is gone.** `scripts/agents/cruise.py` was 1,658 lines that held the state of a run — a pid, a
checkpoint, a feed, a raw event stream, a watch cursor, two inbox files, a stop file — and re-invoked the
ladder in a fresh session each time. It died at iteration two, after which seventeen iterations ran from
interactive sessions and it knew about none of them. What replaced it is not a better runner. It is **no
runner**: the state is in the append-only logs, a captain per stream reads them, and the thing you type
starts processes and exits.

What is left of the file is 208 lines of **settings** — the answers a run gives at `/sail`'s stops, which
outlived the loop because they were never the loop's. The shape is `sail.py`'s, which does the same job for
the ladder's own settings. A verb it no longer has is refused by name, saying where that verb went.

**The seat commands read the logs now.**

- `scripts/agents/fleet.py watch` prints every stream's lines as they are written. The runner's `watch` read
  the runner's own output, so it could only ever see one machine — and when the runner died it went on
  printing nothing, which is what it printed when all was well.
- `scripts/agents/fleet.py tell <stream> <message>` writes a `told` line into that stream's deck log, which
  its captain reads at its next boundary and answers with a `read`. Nothing has to be running: a `told` is a
  line in a log, not a signal to a process, so one written while the fleet is stopped is read by whatever is
  lit next. The stream is required and the command refuses without one, naming the streams there are —
  `--everyone` is the deliberate broadcast.

**Nine settings and nine files went with it.** `stuck_after`, `max_iterations`, `max_hours` and
`poll_minutes` were budgets on a loop; what bounds a run now is the telegraph, which is one lever. The
checkpoint, the stop file, the pid, the feed, the stream, the cursor, the kept last message and the two
inbox files are no longer written or ignored.

**`commands/cruise.md` says what it now is.** Typed, it casts off and takes the watch seat. Dispatched by a
captain, it is the rules for `/sail`'s stops when nobody is at the wheel — the stop table, the skipper, the
hand, the bosun, the records — which is unchanged and is the part that mattered. What went from it is the
iteration contract: there are no four last lines, because a captain reads what a stage *wrote* rather than
what it *said* at the end.

**Catch-up:** `slipwai migrate` rewrites the six `/cruise` commands, the Makefile targets and
`.gitignore`, and takes the four dead settings out of `.specify/cruise.json`. A project that has not
migrated keeps a `cruise.py` whose verbs are gone; the new one tells you where each went.

**`wait_bound` is now a bound on the harbour going quiet, not on how long you have been waiting.** A
captain asking for a merge waits on the far side of a fetch, a rebase and your project's whole `make
verify` — all of which are a different length on a different machine — so a clock started at the request
was measuring your gate rather than the harbourmaster's health, and a fairway could be parked with
"the harbourmaster did not answer" while the merge it is naming was being gated at that moment. Any new
line in the harbour log now restarts the bound. What still parks a fairway is a harbour that has stopped
writing altogether, which is the failure the bound exists for.

**Catch-up:** nothing. `harbour.json`'s comment and `slipwai telegraph` describe the setting the new way
the next time either is written; the number itself is unchanged at every telegraph position.

**A captain no longer takes `/sail`'s word that a slice is done.** In the first real run `/sail` printed a
help message, exited 0, and the captain wrote `claimed`, then asked the harbourmaster to merge, and reported
the slice through its gate — with no `mark-set` and no `demo` written anywhere. A slice is now through its
gate only when the log holds a `mark-set` for every mark the chart says it `sets`, plus a `demo`, **all
written during that turn**; anything else parks and names what is missing. A slice that publishes no mark
still passes on its demo alone — one rule, not a special case.

**A demo sent back is a retry, not a park.** The person who sent it back is present and has just written
notes, so `/sail` is dispatched again and re-enters at the demo rung. `attempts` in `harbour.json` bounds
it — a new telegraph number, 3 at `full-ahead` down to 0 at `stop` — and when it is spent the fairway parks
naming the verdict and the count.

Three things that had to be true first:

- **`verdict` is a closed set**: `accepted`, `behaviour` or `implementation`, the same three
  `check-decisions.py` already holds the demo log to. Refused on the way in and on the way out.
- **`make check-chart` requires `sets` and `steers_by` once the split has run.** An empty list is an answer;
  an absent key is refused. It read them with `or []`, so a slice that left the key out took a demo-only
  gate by omission.
- **`slipwai telegraph --set delegate=story` and `--set cycle=rule` work.** Both are words — how much of a
  slice one delegate is handed, and how many failing tests a cycle opens with — and both were described and
  parsed as numbers, so the only values either takes were refused and `--set cycle=3` was accepted.

**Catch-up:** `slipwai migrate` adds `attempts` to `harbour.json`; without it a captain retries twice, which
is `half-ahead`'s number. A standard-profile chart written before this needs `sets: []` and `steers_by: []`
spelled out on any slice that left them off — `make check-chart` names each one.

**A slice accepted at its demo now reaches trunk, with no person in the path.** The harbourmaster wrote
`granted`, `granted` was read by nothing, and no `merged` line was written by anything — so the board said
`merged: 0` for ever while slices were being accepted. It performs the merge now.

A granted merge rebases the slice branch onto trunk **in a scratch worktree of the harbourmaster's own**,
runs the project's `make verify` there, advances trunk, and answers with the commit; the captain writes
`merged` against it in its own log. One merge at a time, in the order they were asked, so each gate runs on
a trunk that already holds the one before it.

What happens when it does not work is the part worth reading:

- **A conflict is `git rebase --abort` and a refusal naming the paths.** Nothing is left half-done, and the
  captain resolves it in its own berth — where the context is — and asks again, bounded by `attempts`. The
  harbourmaster stays credentials-and-gate only, because it is the one thing in a harbour with push rights.
- **A failed gate is a refusal with the failing check**, and the slice branch is untouched.
- **A refusal says whether a berth could fix it.** A conflict and a red gate are work on code; a missing
  branch is not. A captain reads that rather than driving a slice four more times to be told the same thing.
- **Trunk is moved by a push where there is a remote**, so nobody's working tree is touched. With no remote
  it is the local ref — and where your own checkout is sitting on trunk, that is a fast-forward when it is
  clean and a refusal naming your uncommitted changes when it is not.
- **An answer that never comes parks the fairway** at `wait_bound`, rather than waiting for ever.

**Catch-up:** nothing. A captain that asks for a merge is answered by the harbourmaster `make cruise` already
starts.

**The fork has its own release machinery again.** `make release` assembles `changelog.d/` into
`CHANGELOG.md`'s next entry, writes `VERSION`, commits and tags — in that order, and nothing is written
until everything can be, so a release cannot get as far as the tag and leave a changelog that is wrong.

The version is derived rather than typed: each fragment claims `PATCH`, `MINOR` or `MAJOR`, the entry's
level is the highest of them, and the release is the last one bumped by that. `make check-release` runs in
`make verify`, so a branch whose fragment claims more than `VERSION` does is red before it merges rather
than at the release.

`CHANGELOG.md` and `changelog.d/` are back in the wheel, the sdist and the executable, because
`slipwai upgrade` prints the entries between the version you had and the one you got and an installed keel
has no checkout to read them from.

**Catch-up:** nothing; this is the factory's own machinery.

**`slipwai migrate` crosses a version 1 project, and says what the crossing costs.** The verb kept its
name and does a different job: it reads which factory made the project, installs *that* release of slipwai
into a throwaway environment and regenerates the base there — version 2 carries none of version 1's
generator — installs the languages the project's services need, applies the declared rename table to the
base, and merges three ways against your working tree.

```sh
slipwai migrate --check          # the whole crossing prepared, and nothing written
slipwai migrate                  # one merge commit; `git reset --hard ORIG_HEAD` undoes it
slipwai migrate --with-claims    # rename open claims too, and leave each to rebase
slipwai migrate --no-install     # refuse, naming the install line, rather than install a language
```

It runs on `main`, on a clean tree, so that everything uncommitted afterwards is the migration's. A claim
branch ahead of trunk is named and refused unless `--with-claims` is given; one checked out in another
worktree is refused either way. Nothing is pushed.

**Work in flight crosses as data and is never rewritten.** Decision and adversary ids are frozen where
they are and go on resolving, ADRs keep their paths and numbers, and nothing is renumbered. Flags keep
their values and gain the `hoisted` date the strike rule counts from. Words a person said that no version
1 iteration finished acting on arrive as unanswered messages, each keeping the instant it was said, and a
run that stopped arrives as a park with its reason. Slice status is reconciled upward from trunk's own
merges only: a slice trunk cannot prove shipped keeps the status the model recorded, because unproven is
unknown rather than unstarted.

**What the merge cannot do is written down rather than left out.** `.slipwai/catch-up.md` opens with the
fairways the crossing proposed, counted — *N proposed, M slices in `unplaced`* — and nothing can be
claimed in a proposed fairway until a person confirms it. The page lists every rename once, the base that
was installed, the release mode and product state to correct, and anything a conflict stopped. `/catch-up`
stays red while a fairway is still proposed. Re-running the crossing is safe: every migrated log line
carries a key, so a second run recognises what the first wrote instead of saying the person's words twice.

**What the undo reaches, and what it does not.** `git reset --hard ORIG_HEAD` takes back the merge and the
commit after it, and nothing is pushed — but the deck logs it seeded are append-only and ignored by Git, so
a reset leaves those lines where they are (the keys above are what make the next run read them correctly).
A language the crossing installed stays installed. With `--with-claims`, each claim branch is moved to a
rename commit of its own, which resetting `main` does not move back. And a rename is substituted as text
only in the files that *declare* the thing renamed — a target in a Makefile, a command, a skill — because a
row carries a bare word, and the same characters are ordinary prose everywhere else in somebody's
repository; a reference anywhere else is left as written and listed on the catch-up page.

**Catch-up:** `slipwai migrate` in each version 1 project, once per project. Read
`docs/whats-new.md` in the factory first for what it costs and what it cannot undo.

**A keel release is refused when a published package fails against it.** The keel's own gate proves the
conformance suite works and each package proves itself against a pinned keel, and neither asks the question
a release has to answer: *does this keel still work with what is already out there?*

`backstop.yml` runs on a tag, weekly, and on request. It installs the keel from the checkout rather than
from the registry — the point is the version nobody has published yet — then every package the channel
lists, and runs each one's conformance suite. The list comes from the chandlery rather than from the
workflow, because a list in a file is wrong the day somebody publishes a seventh.

A run that checked nothing refuses the release rather than passing. A matrix job skipped because nothing
was listed is a green that means "nothing was checked", and a tag protected by that is not protected.

**Catch-up:** nothing. It is this repository's own CI.

**`slipwai upgrade` tells you what you got.** It prints the changelog entries between the version you had
and the version you landed on, there and then, rather than a number and a link. Crossing from 1.x to 2.x
gets its own page: what version 2 is in five lines, and the one command that moves a project across.

A release whose entry this copy does not carry is said to be unknown rather than printed as nothing.

**Catch-up:** nothing. It happens on your next upgrade.

**`make verify` is green on a repository nobody has written a line in, which for four stages of `/sail` it
was not.** A generated project shipped a model table naming `mockups`, `chart`, `review` and `merge`, and
its own `check-agents` called all four typos — so the first gate anyone ran failed on a project they had
not touched. The two lists are now held in step by the keel's suite rather than kept separately.

The five pages of the guide are now run rather than read: `make test-docs` generates a project, drives the
interview question by question, and asks every command the first three pages print, in the order they print
them. It found six wrong lines that had shipped — two commands that do not exist, three outputs nothing
prints, and a board row that said `2 working` where the board never says that. All six are corrected, and a
command added to one of those pages now fails the gate until something checks it.

**Catch-up:** `slipwai migrate` rewrites `.specify/models.json`. A project that has not migrated can also
just delete the four rows its own `make check-agents` names.

**`/sail` says what its argument narrows, and the guide leads with the form without one.** Bare `/sail`
takes the ready slices of every fairway nobody holds and goes on to the next without being invoked again —
that is what *Ready-set selection* has always said, and the command's own page never said it, so every
example anybody had seen passed a single slice id.

`commands/sail.md` now opens with the four forms and what each one narrows: bare, `fairway=<name>`, a
feature, and one slice id. `docs/guide/first-feature.md` leads with `/sail` and shows the others as the
ways to pin one; `docs/guide/a-second-person.md` gains the paragraph about two people taking different work
without agreeing anything, which was the page's whole subject and had no command in it.

`make test-docs` gained a check with them: a `key=value` a page writes after a `/command` must be an
argument that command's own `argument-hint` has. `/sail lane=booking` now fails the gate by name.

**Catch-up:** `slipwai migrate` rewrites `commands/sail.md`. Nothing behaves differently — the ready-set
rules are unchanged; what changed is that the command says what they are.

**Five skills for extending slipwai itself.** They are under `maintainer/skills/`: `add-language`,
`add-framework`, `add-extension`, `add-target` and `add-backing-service`. `make skills` copies them into `.claude/skills/`
beside the toolkit's, and not into a generated project — a project is not extending slipwai, and five
skills about doing so would be five wrong turns in it.

Each is prose around the verbs rather than a second copy of them: where `slipwai package new` writes a
file, the skill says so and moves on. Each ends on the mistake people actually make rather than on a
summary of what was just read.

**Catch-up:** nothing. They are for this repository's contributors.

**A crossing reads a backing-service block by its marker, not by the file it sits in.** The factory's own
file and a project's replacement for it both carry `# backing-service:<feature>:begin`, so one block
implemented twice is a fact the migration can simply see — and now does. A file the offering adds whose
every block this project already implements somewhere else is not taken, and is listed on the catch-up
page with the file that already holds it.

This is the general form of the fault that made a crossing restore a deleted stack. A factory *rename*
arrives as an addition, not a change: the offered path is one the project has never had, so there is no
deletion to conflict with and nothing to resolve. The rename table saves the ordinary case by moving the
project's own file to the new name first; this saves the case where the project's answer was never the
factory's file under any name.

**A crossing now reads the project's stacks when it has finished**, and says what it found. A generated
project's gate runs with no provider plugins and no cloud credential by design, so until now the first
thing to read those files for real was the deploy. The structural reading needs nothing installed — a name
two files of one stack both declare refuses the whole stack — and `tofu validate` adds to it wherever a
tool is installed and initialised. It never refuses: the merge is already committed, and a crossing that
failed over a stack it is not allowed to touch would be the worse answer.

**Pruning deletes a file it empties.** A marked file whose every region was dropped was written back as
zero bytes and stayed there for ever — invisible in a diff, carried through every replay, renamed along
with everything else.

**A crossing no longer dates flags it cannot date.** It used to stamp `# hoisted: <today>` onto every line
of every `flags.auto.tfvars`, flags that were off included. To hoist a flag is to turn it on for real
actors, so that is a claim about a product that never happened, written into a file a person owns — and
`check-flags` counts its thirty-day strike window from that date without looking at the value, so a
stamped off flag is reported a month later as having been on everywhere. The flags that are on and
undated are named on the catch-up page instead, for the person who knows when each went on.

**Catch-up:** nothing. If an earlier crossing stamped your flags, the dates are still there and still
wrong: delete the ones that were never true.

**A `check` hook has the minutes a gate takes.** A hook that named no budget had 30 seconds at every point,
and ux-gates' `check` hook runs its render gates over every screen: in hr-test-2 they took minutes, and the
hook was ended every time though every shard passed. A `check` hook now defaults to 600 seconds; other points
keep 30, and a declared `budget` still wins.

**A cloud you have not installed no longer takes the language with it.** A language package declares the
targets it has deployment answers for, and every published language names both clouds. The merge used to
refuse any package naming a target this installation had no row for — so installing `python` and no cloud
package left `slipwai list` offering `--language {}`, and `slipwai generate --target none`, which deploys
nowhere and needs no cloud at all, refused outright. All six published languages were unusable until both
cloud packages were installed.

An answer the catalogue cannot reach is now pruned from the backend's row and the rest of the package
merges: `--target` offers what is actually installed, a default pointing at a pruned option goes with it,
and nothing else about the package changes. This is what the keel already did one level up — an option no
installed target offers is dropped, which is why `auth0` sits in `catalog.json` and not in the merged
catalogue until a cloud that offers it arrives — so the two levels now agree.

The pruning is never silent. `slipwai list` names, under each installed language, what it answers that is
out of reach here and the command that shows the targets. An axis the keel does not declare is still a
refusal, because the keel declares every axis there is and one it has not got is a mistake in the package
rather than a gap in what is installed.

**Catch-up:** nothing to do. A project already generated is unaffected; a package that merged before still
merges, and one that was refused for naming an absent cloud now loads with that answer unavailable.

**A fairway in a multi-context service now owns its context's code in every language, and the gate that
refuses a slice for crossing that boundary works again.** `make chart` wrote each fairway's `owns` as
`<service>/src/<context>/**` — where a TypeScript service keeps a context, and nowhere a Go, Java, Python
or Rust one does. On every other language that pattern matched no file.

**It failed by passing, which is why it lasted.** `check-slice-scope` refuses a path another fairway owns,
and a path no fairway claims is nobody's to refuse — so with nothing owned, nothing was refused. A slice
branch could edit another fairway's code and the gate reported the branch in scope, which is the same thing
it says when the branch really is in scope, and nothing told the two apart. `check-chart` stayed green
throughout, because the chart was internally consistent; it just described directories that did not exist.

**The chart now says what `check-imports` has always said.** That gate finds a context by looking for its
name among a path's directory parts, at whatever depth the language keeps it; two files deciding where a
context lives, by different rules, was the defect and the `src/` was the symptom. A chart writes
`<service>/**/<context>/**`, and the matcher reads `**` as zero or more whole segments — so one pattern
covers `apps/x/billing/`, `apps/x/src/billing/` and `apps/x/internal/billing/`, and still refuses to see
`billings/` as `billing/`.

**Catch-up:** run `make chart` and commit the result. Every project migrated before this carries a chart
whose `owns` paths name directories that are not there, and `make check-chart` holds the committed chart to
what the renderer would write — so it will refuse the stale one until it is re-rendered. Read the new paths
before committing them: the fairway rule starts refusing things the moment they are right, and a slice
branch that was quietly out of scope will say so.

**`slipwai migrate` no longer writes anything under `infra/`.** Those files describe resources that
already exist — a Terraform resource address is state, not a name — and which of them are real is not
something a factory can know. Your stack now crosses exactly as it is, and what this version would have
changed there is listed in `.slipwai/catch-up.md` for you to take deliberately, `tofu plan` first.

This was learned from a crossing that re-added a factory Terraform file under its version 2 name, into a
project that had deleted it months earlier and written its own beside it. Nothing caught it: the rename
means the base and the offering share a path the project has never had, so "we deleted this" reads as
"the factory added a file". The next deploy stopped on a duplicate local value, which is the harmless end
of what that class of change can do — the same merge could as easily have proposed replacing a user pool.

**Catch-up:** nothing. A project already crossed keeps whatever the earlier crossing wrote; if that
included factory `infra/` files you had deleted, delete them again and the next crossing leaves them gone.

**Under `/cruise`, the skipper answers a slice's product questions, and a person sees only what it cannot decide.** A captain-dispatched session is told it is cruising and with which `decide`, so it puts an open question to `sail-decide-skipper` rather than parking it. A run that still stops on questions gets one skipper round from the captain before anything is parked, and is run again on the decisions as a retry. On a restart, every slice already parked on questions has them put to the skipper, once each, and is resumed when they are all decided; the harbourmaster clears such a park on the `decision` lines alone. A question the skipper answers `unavailable` stays parked for a person. A park of one slice that has gone past the wait bound no longer forces its siblings' boundary.

**A decision is read against what the project already does, and the record says which authority answered.**
`/cruise` named three things a question could be settled by without spending a delegate: the standing
entries, the specification, the constitution. All three are documents this method owns.

A generated project ten slices in, and an adopted repository on its first day, both hold conventions that
none of them names — how this codebase already publishes, how one handler reaches the next, how a migration
is named. A decision taken without those is how a codebase ends up with two ways of doing one thing, each
defensible on its own. So the project's own grain is the fourth authority, the host may settle a question it
answers, and the procedure says where to find it: `docs/architecture.md` and the code itself in a generated
project, `structure.md` and the survey in an adopted one.

Every decision entry's **Why** now carries `Read against:` — which of the four answered, or `the method's
default` where none did. It is a clause inside the field rather than a tenth bullet, so an entry already
written is still the right shape, and `make check-decisions` asks for it.

**Catch-up:** `slipwai migrate` brings the command and the gate. An entry written before this has no
`Read against:` and the gate will name it; add the clause, or say `the method's default` where that is the
honest answer.

**A disapproved storyboard is drawn again, from your reason.** Disapproving used to start nothing, and the
Draw the surfaces button had gone with the first drawing, so a run stopped at a person's no with no way on.
Now Disapprove starts `make surfaces` for that feature at once. The session is told it is a redraw
(`SLIPWAI_REDRAW=1`), so it redraws every surface and the storyboard in place answering the reason, rather
than reviewing its own rejected drafts as if a person had handed them over. Once it lands, the old verdicts
move to `specs/<feature>/mockups/disapproved.md` and the new storyboard waits on a verdict of its own. A
disapproved storyboard also brings the Draw button back, to retry a redraw that failed.

**The board shows a drawing it did not start.** `make surfaces` writes `.slipwai/surfaces.pid` the way
`make model-next` writes its own, so a board restarted mid-draw, or a redraw run from the terminal, shows the
storyboard as working rather than waiting on buttons that are locked.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/surfaces.py` and `commands/mockups.md`.
A storyboard already disapproved shows the Draw button again once the board is restarted.

**A Continue the build that failed can be pressed again.** The board remembered pressing it for as long as it
ran, whether `make launch` went through or not, so a failed launch hid the button for good, left no chart for
Cast off the fleet to appear from, and answered a press with "nothing to continue from here: a
specification ... is what the build continues from" — about a project that had one. A launch that exits
non-zero now brings the button back, unless a fleet is running in the project anyway. A launch that went
through is still pressed once only, which is what stops a second fleet.

**The refusal says why.** Pressing Continue the build when it cannot go now names the reason that holds:
the build already being continued, another step running on the board or in the project, nothing modelled
yet on the event-modelling profile, a step that failed, or a feature already charted.

**A model that failed has a Model again button.** On the event-modelling profile, approving the storyboard
starts `make model-next` once and locks the verdict, so a model step that failed — or an approval given while
the board was busy — left only a chip saying to go to the agent. Model again appears while the storyboard is
approved, nothing is modelled and nothing is running, and starts the model step from the board.

**Catch-up:** none. Restart the board, and a launch or a model that failed before shows its button again.

**The fleet now runs a fairway's ready slices at the same time, each in a worktree of its own.** A person who
typed `/sail fairway=<name>` had every ready slice fanned out, because rule 6 of *Ready-set selection* says to
run them concurrently. The fleet, given the same fairway, dispatched one slice per turn — so a split with a
walking skeleton and twenty-two independent slices behind it ran those twenty-two one after another. Now a
captain starts every slice that is ready and that the slice graph lets run together. Each slice runs in
`../<project>-<id>` on `slice/<id>`, with its own session, stage bound, retries and gate, and its own merge
request. As each one merges or parks, the next ready slice starts in the space it left. Merges still go one at
a time through the harbourmaster, so every slice is rebased and gated on the trunk the last one left.

**Ready now includes the slice graph's `depends_on`.** Clearance used to read marks alone. A split whose
slices steer by no mark but depend on a walking skeleton was offered all at once while the skeleton was still
being planned. `clearance.py` now reads `depends_on` where `/sail` says the graph is: each slice's entry in
`docs/event-model/model.yaml`, or `## Slice graph` in the split. A slice whose dependency has not merged reads
`blocked` and names it. The split's `parallel_ok_with` decides which ready slices may run side by side. A
slice it does not mention may run beside any other, as the page has always said.

**`boilers` now counts slice sessions across every fairway, not captains.** The harbourmaster shares them out
on every pass, and it writes the result as a `slots` line per fairway in the harbour log. Every fairway with
work gets one session before any fairway gets a second. Spare sessions then go by your fairway order, then by
the slice whose merge unblocks the most, then by the fairway with the most ready slices. A fairway waiting on
a merge answer starts nothing new, and no running slice is ever stopped to make room. A new setting,
`abreast`, caps how many slices one fairway runs at once. It defaults to 3 and is never more than `boilers`:

```sh
slipwai telegraph --set abreast=1     # one slice at a time in every fairway: the fleet as it was
```

**A park can now hold one slice and leave its siblings running.** A `parked` line that names a `slice` holds
that slice only. A park that names no slice still holds the whole fairway. A stop ends every slice in flight
and writes a `stopped` line for each one. The next captain lit carries all of them on, not only the last one
claimed. The board's slice column lists every slice in flight.

**Catch-up:** `slipwai upgrade` brings the new `scripts/agents/abreast.py` and `moorings.py` and the changed
captain, harbourmaster, clearance and fleet scripts. Check that `chart.yaml` and the slice graph are
committed, because a slice running abreast works in a worktree made from what is committed. To keep one slice
at a time, run `slipwai telegraph --set abreast=1`.

**`slipwai language install java` installs Java.** It did not: it brought the family and its default
framework, and the loader refused what it could not read — *family java's prune_rows name `spring-web`,
which is not a feature the pruner knows*. Asking for `java-spring` instead failed the same way on
`quarkus-rest`. Only naming both at once ever worked, and nothing said so.

A family's `prune_rows` are the family's, and may name a feature that any of its backends declares — and a
feature arrives with the backend declaring it. So a family whose frameworks are separate packages cannot be
loaded one framework at a time. Installing a family now brings every framework of it the index offers,
whichever half was asked for, and says which came along. Java is the only family with more than one
framework package today, so this changes nothing anywhere else.

**A session that has finished no longer keeps the stage waiting.** A Claude Code print session could write its
final `result` line, with every background task it started reported back, and then never exit: the MCP
servers it had started stayed attached, so `make surfaces` (or model, draft, launch, assess, or the captain's
`/sail`) waited for ever until a person killed the session. The stage then read the kill's exit 143 as a
failure and skipped what comes after a drawing. Every script that starts a headless session now runs it
through one helper in `scripts/agents/harness.py`. The helper passes the output through line by line as
before, and notices when the session has said it is finished with no task still out. If the session is still
there 30 seconds later, the helper stops it and every server it started, and the stage carries on with what
the session reported: 0 for a successful result, 1 for anything else. A harness that does not write
stream-json runs exactly as it did.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harness.py`, `surfaces.py`, `model.py`,
`draft.py`, `launch.py`, `assess.py` and `captain.py`. Nothing else changes.

**A further feature is handed to `/sail`, assessed, and specified only after a yes and a go.** The words of the request, or a document that session can read, are written under `docs/intake/`. Spec Kit's assess extension decides whether the idea deserves a specification. A person confirms it is a new feature first; under `/cruise` that question goes to the skipper. The voyage page shows what is waiting and can continue the earliest one.

**Catch-up:** `slipwai migrate` brings the commands and leaves `.slipwai/intake-cleanup.json`, a proposal that moves nothing until `/catch-up` confirms a row and `python3 scripts/apply-intake.py` is run. `docs/prd.md` and existing specifications stay where they are.

**A further feature stays on the profile the project already has.** `/sail`, `/draft` and assess tell Spec Kit to specify on `project.json`'s profile — event-modelling or standard — and on the one preset already enabled for it. `make check-speckit` fails when that preset is missing or the other profile's preset is enabled.

**Catch-up:** `slipwai migrate` brings the command pages and `scripts/check-speckit.py`.

**A listing of languages lists languages.** The chandlery has carried four kinds of package since version 2,
and the reader every language listing goes through asked for all of them — so a target came back as a
language. `slipwai list` offered a cloud under **Languages**, and the board's Language menu offered it too,
each with `slipwai language install <name>` beside it. The filter meant to keep a family's own row is
`family == name`, and a target's manifest names no family at all, so it passed.

**The command that was offered then failed in the worst available way.** It fetched the package, staged it,
and refused it for having no `language.json` — naming a temporary directory, at somebody who had pasted the
command the tool itself printed. The kind is known from the index before anything is fetched, so that is
where it is refused now: *`<name>` is an extension, not a language: `slipwai extension install <name>`*.

**And an empty shelf is no longer blamed on your keel.** The Packages tab said "no channel offers one this
keel can load" wherever a table was empty — including where the channel simply lists none of that kind,
which is the usual case for extensions today. Three states, three sentences: no channel could be read, the
channel lists none yet, or the channel lists some and this keel can load none of them.

**Catch-up:** nothing.

**A fairway parked because trunk was red now asks again once trunk is green.** The refusal said the queue
drains the moment trunk is green, but nothing drained it: the captain parked, and a parked fairway is never
relit, so every fairway that asked to merge during a red build waited for a person after the build was
fixed. A merge refused only because trunk was red now carries `waiting: "green-trunk"`. On any pass where
trunk is no longer red, the harbourmaster writes a `cleared` receipt for each park that refusal caused, and
the fairway asks for its merge again.

**A push that loses a race to trunk is gated again, not refused.** If someone else pushed to trunk between
the harbourmaster's fetch and its push, the forge refused the push, and the fairway parked behind a slice
that had passed its gate. The harbourmaster now fetches, rebases and gates the slice again on the new trunk,
up to three more times, all while it still holds the merge ref. A trunk that moves under every attempt is
refused as something a captain can ask for again, not as a park.

**The merge ref has a lease, so a dead machine no longer stops every merge.** `refs/slipwai/merge` had no
lease. A machine killed in the middle of a merge held it until the hour's wait ran out, and then the
fairway that asked was parked. The lease is half of `wait_bound`, which is half an hour by default. The
holder renews the ref while its gate runs, so a long `make verify` never lapses. A holder that has not
renewed within the lease is taken over, and the harbour log says so in a new `merge-taken-over` line naming
the machine it was taken from. Trunk is moved only if this machine still holds the ref once its gate is
over.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harbourmaster.py`, `claims.py` and
`logs.py`. A fairway already parked by a red trunk is cleared on the harbourmaster's first pass after the
upgrade if the refusal it parked on was written by the new harbourmaster; one parked before that is cleared
with `python3 scripts/agents/harbourmaster.py --clear <fairway> --parked <timestamp> --what 'merge again'`.

**A merge's answer says where its time went.** Every `granted` and `refused` line for a merge now carries
`waited_s` (how long the request sat before the harbourmaster took it up), `lock_s` (how long it waited on
`refs/slipwai/merge` for another machine's merge), `gate_s` (how long `make verify` ran on the rebased
branch) and `attempt` (which try at that slice this was). Integration that feels slow can now be read off the
harbour log: a long queue, a busy merge ref, a long gate, or a slice going round the berth again and again.
A refused merge also names its `slice`.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/harbourmaster.py`. Lines written before it carry
no timings, and nothing reads them as zero.

**The first push of a branch is judged against trunk, not the whole history.** Git's `pre-push` reports
forty zeros for a branch the remote has never seen. The dispatch gate treated that as every commit
reachable from here, so a project with any pre-ledger history could not push a new branch at all — the
refusal named commits already on trunk. The range is now the same one `make check-dispatch` already uses
with no arguments: trunk, up to the branch being pushed.

**Catch-up:** nothing. The next push uses the corrected range; nothing already in the repository has to
be rewritten.

**A note for the host can be put away from the board.** A session's `For the host: …` note is a `told` that
no decision or claim answers, so it stayed under *Waiting on you* until somebody wrote a `read` receipt by
hand. Each message row now has **Done**, which writes that receipt (`POST /dismiss`); a dismissal naming a
message the log does not hold is refused.

**A parked stream is left alone until somebody answers it, and telling it something is the answer.** Four
faults met on one run, and between them they parked every stream and held it there:

- **A captain no longer ends a stage that is committing.** The watch read only the deck log, and the
  implement rung commits an example at a time and writes no deck line until its mark, so a slice that
  committed fourteen times in ninety minutes was ended as having made no progress. A commit on the slice's
  branch now counts, because it is evidence in git rather than the agent's account of itself.
- **A stage that parks itself keeps its reason.** The captain then parked it again with what the gate missed
  (no `demo`, a mark not set), which is true of every stage that stops early and put a second park, hiding
  the first, at the top of the log.
- **A message to a parked stream clears the park.** The board's answer box and `/cruise-tell` write a
  `told` line, and nothing turned it into the `cleared` receipt a park is answered by, so a stream told
  `go` stayed parked. The harbourmaster now writes that receipt, with the message as the answer, for every
  open park the message came after.
- **A parked stream is not relit.** The harbourmaster lit a captain for it every fifteen seconds; the
  captain read the park, said so and exited, so a parked stream's log filled with the same line. It is lit
  again on the pass after its park is cleared.

**Catch-up:** none for the project. A stream parked before this upgrade is cleared by telling it something
after the upgrade, or with `harbourmaster.py --clear` as before.

**A product requirements document carries the files it stands on into the project.** `--prd` copied one
document's text to `docs/prd.md` and nothing else, so a PRD that embedded the wireframes somebody drew and
cited a brand sheet landed as a *Look and feel* section pointing at nothing — and the mock-up stage, whose
whole job is not inventing screens, had a direction it could read about but not see.

Two things travel now, both into `docs/design/`:

- **What the document itself names.** Its relative links and images are resolved against the directory it
  was read from, copied in, and the links rewritten to where they landed — a file carried in under a name
  the document still spells the old way is a file nobody finds.
- **`--design <dir>`**, a folder handed over whole, for the material the PRD happens not to link: a
  stylesheet, a competitor teardown, screenshots.

`commands/mockups.md` reads the directory before it draws a surface and is told to **follow a direction
somebody already settled rather than invent one**, naming the file each decision came from. The docs index
lists what arrived under *Handed over*, by name — a PNG has no first line to read, and material that is
there and unlisted is material the next reader does not know they have.

**Nothing outside the document's own directory travels.** A link to `../../.ssh/id_rsa`, a symlink out of
the tree, an absolute path: each is left exactly as it is rather than followed. A PRD is a file somebody
was handed, and a generate that copied whatever it pointed at would read anything its author could name.
A handed-over tree is bounded at 200 files and 50MB, so a home directory pointed at by mistake is a
refusal naming the size rather than a generate that appears to hang.

**An answer taken away takes its state-move blocks with it.** The internal/external identity rename of
2026-10-08 added `moved {}` blocks to five stack files so that the first apply after the rename moves state
instead of destroying it. They were written after each file's `backing-service:…:end` marker, which put them
outside the answer they belong to — so `./init --auth none` emptied the region and left behind state moves
for resources the pruned stack no longer defines.

`tofu validate` accepts them, which is why nothing had noticed: a `moved` block whose source is gone is a
no-op. What it is not is honest — a file that should be empty was carrying thirteen blocks about resources
the project had just said it did not want. They are inside their regions now, on both clouds, for the
internal, external and Auth0 answers.

**A quickstart that needs a cloud says so before you choose it, not after.** A quickstart answers
`target: aws`, and a target is a package like any other — but the check that greys an unusable quickstart
out of the interview read `languages` and `extensions` only. So a cloud quickstart was offered as usable on
a machine with no cloud installed, chosen, and then refused by the generator several questions later. The
menu now reads the target answer too, and names `slipwai target install <name>` beside it. The keel's own
`none` and `existing` are in the catalogue everywhere and are never missing.

**And each missing package is fetched by its own verb.** The refusal used to put every name behind
`slipwai install`, which is `language install` — so an extension's name arrived attached to the wrong
command, and a person pasting it was told their extension is not a language. Languages, extensions and
targets each get their own line now.

**Catch-up:** nothing.

**A slice waiting on you takes its answer on its own card.** On the voyage, a red card opens on the park that holds the slice and each of its open questions, with a box to answer in. What is sent is a `told` naming the slice, so it clears that slice's park and no sibling's, and the captain records it as the answer to the slice's questions when it carries the slice on. The page does not reload while an answer is being typed.

**A context boundary is tested three ways, and a shared noun no longer settles it.** The context step on
both profiles asked one question — does any word mean two things? — and a product whose host, player,
organiser and trust record all say *listing* and mean the same listing came out as one fairway, 39 slices
long, with two of its three berths empty because fan-out cannot cross a fairway. Now the candidates are the
slices that write one stream (the stories that change one Key Entity, on the standard profile), a stream
is never split across contexts, and every seam between two candidates is tested for language, change and
flow, with the evidence written down as a table before a person is asked. One vocabulary with one reason to
change is still one context, and the proposal now says why. On the event profile `make seams` lays the
evidence out from the model, and `make check-model` refuses a stream written from two contexts.

**Catch-up:** `slipwai upgrade` brings the step, the script and the Makefile target; a model already at
`modelled` with one context is not re-opened, but `make seams` will show what the one-question rule missed.

**A slice run abreast is not charged with the run's own files.** `check-slice-scope` counts untracked files
as the slice's change, and a project made before its `.gitignore` named `.slipwai/preflight.json` and
`.slipwai/logs.unread-*/` saw every berth go red on files `make preflight` and the berth's linking had
written. Untracked run state under `.slipwai/` — the same names the generated `.gitignore` carries — is no
longer read as the slice's. Anything else untracked still is. A slice's own dispatch ledger file and the
feature's `decisions.md` were already allowed.

**A slice already on trunk is never driven again.** A session may ask for its own merge, and in hr-test-2
one did: the captain then judged the run by its gate, found no mark set that turn, and drove a slice that was
already on trunk three more times before parking on it. A `merged` line, or a `granted` merge answering a
`request` in the fairway's own log, now ends the slice — checked before the claim, after every run and before
the captain asks for a merge of its own — and a grant found this way is written as the fairway's `merged`
line, so the claim closes rather than being resumed by the next captain.

**A slice's dispatch line travels in the slice's own pull request, and starting or merging a slice records
itself.** From one `/sail` run with five slices in flight on a trunk that only moves through pull requests:

- `make dispatch` writes each slice its own ledger file, `.slipwai/dispatch/<feature>/<slice>.jsonl`, into
  the slice's worktree as well as here where the worktree exists, and `check-slice-scope` lets a
  `slice/<id>` branch commit its own file and no other. A line no longer has to reach trunk in a records
  pull request before the slice that names it can pass `check-dispatch`, and five branches no longer append
  to one file that conflicts at its last line.
- `make dispatch` writes the `claimed` deck-log line for every slice it starts, and takes
  `DISPATCH_FLAGS="--slice <id>[,<id>]"` to start only the slices `/sail <slice-id>` names, saying
  clearance's reason for any named slice that may not start.
- Clearance counts a slice with a `dispatched` or `taken-here` ledger line as running even with no `claimed`
  line, and reads a slice as done when a first-parent merge on trunk names its `slice/<id>` branch — the
  subject a forge writes for a pull request, which survives the branch being deleted — so nobody writes
  `merged` lines by hand. A claim for the `prepare` band is spent once the slice's marks are set, so a
  prepared slice waiting for its implementation slot holds none.
- `disk_floor_gb` in `harbour.json` holds every slot while the checkout's disk has less free than that, and
  says how to free it.
- `check-speckit` names the integration to repair instead of `<integration>`, and says that a new worktree
  needs `make agents` first. `sail-slice-watch` says a delegate that cannot start one of its own hands the
  fresh-context diff review back to the host rather than looking for a tool it has not got.

**Catch-up:** `slipwai upgrade`, then `make agents`. Lines already in `.slipwai/dispatch/<feature>.jsonl`
keep counting; nothing moves them.

**A slice on the voyage is named.** The work columns showed `S10` and a clearance line. They now read `S10 = Appoint a moderator`, the short description from the split's Value column. The slice graph's next cell is a dependency, and it is not used as the name.

**Catch-up:** restart the board and reload the voyage. The names are already in the split; a board that is running does not re-read its own code.

**A slice run abreast starts in a berth that has what its session needs.** A worktree is the committed
tree and nothing else, so a slice's first sessions in hr-test-2 exited 1 three times in six seconds: the
harness passed `--mcp-config .mcp.json`, and the branch had been cut before the file was committed. The MCP
file is now passed by the project's absolute path. A berth is also given the projected commands and
delegates under `.claude/` — without which `/drive` is not a command — and a link to the project's `.env`.
A berth whose `.slipwai/logs` a session had already written into keeps those lines at
`.slipwai/logs.unread-<time>` and is linked to the shared log, where before every later line missed the
gate.

**Catch-up:** `slipwai migrate` (or `slipwai replay` and a merge, on 2.x) brings the corrected
`scripts/agents/harness.py`, `registry.json` and `moorings.py`. A fairway parked by this, with "`/sail`
exited 1", is cleared with `/cruise-tell` or `harbourmaster.py --clear` once they are in.

**A slice the captain runs in its own berth can pass `check-dispatch`.** The captain wrote `claimed` before it
started the slice's session, so clearance read the slice as running, and `make dispatch` refused to write the
ledger line for it — every commit on the slice was then refused as work no dispatch accounts for. The captain now
writes the slice's line into its berth and commits it on `slice/<id>`, and `make dispatch` in a session the
captain started writes the line for that slice rather than refusing it. Request (`R3`) and question (`Q7`) ids in
a commit subject are no longer read as slices.

**A stage's name now says who runs it, and that is how you can tell it has a delegate at all.** `/sail`'s
ladder has twenty-one stages and ten of them are sent to a fresh context with a scope the harness enforces;
the other eleven stay with you. Nothing in the name said which was which. `writes` and `commands` said it,
two columns further along, in a table nobody reads at three in the morning — and the only part of it a
person editing `.specify/models.json` ever sees is the key.

So every delegable stage is named for its purpose and then for the crew member who does it, and every stage
that stays on the host keeps the work's own name:

| Was | Is | Its delegate |
|---|---|---|
| `gaps` | `gaps-lookout` | reports what is missing and touches nothing |
| `tasks` | `tasks-quartermaster` | issues the stores in order |
| `implement` | `implement-shipwright` | builds to a plan that is already complete |
| `converge` | `converge-navigator` | says whether the course was held |
| `review` | `review-mate` | reads the work and signs nothing off |
| `adversary` | `adversary-privateer` | attacks under letters of marque, never repairs |
| `mutation` | `mutation-shipworm` | bores holes on purpose to see whether the hull leaks |
| `skipper` | `decide-skipper` | decides one product question as the owner would |
| `hand` | `demo-hand` | runs the demo as the actor |
| `bosun` | `unblock-bosun` | gets a blocked run moving |

The types in `agents/` take the same names (`sail-implement-shipwright`), and the whole-slice delegate is
`sail-slice-watch`. The purpose leads rather than the crew member, for two reasons: a delegate reads its own
job in the first word of its name, and the name a stage had before is still the start of the name it has now
— so `/sail`'s rungs still match the words the method uses for them.

Rung titles are untouched. **Implementation** is still **Implementation**; a title names the work and the key
now names who does it. The commands are untouched too: `/gaps`, `/adversary` and `/mutation` are what you
type, and Spec Kit still owns the plan, tasks and implement commands the ladder runs.

**Catch-up:** nothing you must do. A `.specify/models.json` still keyed `implement` is read under that name
and says so, `scripts/agents/models.py --set implement=fast` resolves to the new key, and a benchmark record
written before today is counted as the stage it was. `slipwai migrate` rewrites the table and the agent
files; the roles you mapped survive it, as every edit to a generated file does.

**A slice in flight is carried on whatever stopped its captain.** A captain killed, stopped or rebooted and
relit on the same machine took its own claim back, found no park and no takeover, stepped past the slice it
had claimed and said *nothing to start* for ever. A slice claimed and not merged is now resumed whenever it
is not parked, unless another captain on the same machine is working it at that moment.

**`fleet stop` ends the running stage and writes `stopped`.** The captain had no handler for the signal, so
it died where it stood: its `/sail` went on running with nothing watching it, the claim stayed taken and the
log said nothing. Now the stage's whole process group is ended, a `stopped` line names the slice, the claim
is given back once that line has travelled, and `fleet stop` says this instead of promising a boundary. The
board shows such a stream as `stopped` rather than, after a while, `stalled`.

**A dead harbourmaster is started again.** Nothing restarted one while any captain was alive, so a captain
waiting on a merge sat out the wait bound and parked a slice that had passed its gate. Each captain now
checks at the top of its turn and while it waits on an answer. Where the harbourmaster's pid file names a
process that has gone, the captain starts a new one and says so. It holds a lock while it does, so that
two captains start only one. A harbourmaster with no pid file, which is one a person started by hand, is
never doubled.

**A run that falls over is retried before it parks.** A missed mark, no demo, a stage ended because its log
went quiet and a `/sail` that exited non-zero all parked on the first run. Only a demo sent back was
retried. They now all count against `attempts`. Each retry is told why the last run did not close, in its
prompt and in `SLIPWAI_RETRY`. When `attempts` is spent, the park gives the last reason and how many runs it
took.

**Catch-up:** none needed. Fairways stuck on *nothing to start* with a slice claimed and not merged pick it up
on their next turn once this version is installed.

**A storyboard on the voyage keeps its formatting.** The window's seat is part of the mock-up's address, so the stylesheet, the script and the next frame load from the project that window is looking at. A query on the frame was dropped by every one of those.

**Catch-up:** nothing. The next voyage this board serves is the new page.

**A storyboard on the voyage now shows its styles and its screens when it links `docs/design/`.** The
mock-up stage is told to follow what the project was handed under `docs/design/`, so a storyboard often
links that stylesheet and those drawings, and its specification, by their place on disk
(`../../../docs/design/mockups/styles.css`, `../spec.md`). The board served the storyboard one directory
shallower than it sits, so every one of those links missed: no styles, empty frames. A mock-up is now served
at its own path in the project, under the window's seat (`/mockups/by/<seat>/specs/<feature>/mockups/…`),
and that route also serves the feature's `spec.md` and anything under `docs/design/`. The rest of the
project stays refused. The older `/mockups/<feature>/<name>` addresses still work.

**Catch-up:** none for the project. Restart a running `slipwai bridge --serve` after upgrading.

**The eleven agent briefs are assets now, and the scope they are held to is still generated.** Each type's
standing brief was a Python string literal, so `agents.py` reached its 350-line budget and was cut at a
paragraph boundary: `cruise_agents.py` exists because three more briefs would not fit, and the bosun's words
have been living in a file named for the cruise, where nobody reading about the bosun would look. They are
`assets/toolkit/agents/sail-*.md` now — one file per type, beside the skills and the commands, edited like
any other prose this repository ships.

What did not move is the frontmatter. `name`, `stage`, `writes` and `commands` are still generated from
`stage_models.STAGES`, because they are the scope every harness projection enforces: a brief that wrote
`writes: none` for itself could disagree with the table, and the harness would enforce whichever it was
handed. A brief that names one of those four fields is refused rather than merged.

This is also the first templated asset the keel has — everything else under `assets/` is copied byte for
byte — so it comes with the gate for that. A brief interpolates eleven named values and no others
(`{{make}}`, the paths the `/cruise` delegates read, two passages the ladder owns), the substitution is a
closed set rather than `str.format` so that a `${VAR}` or a JSON example in a brief is never an escaping
question for the person writing it, and `make verify` holds both directions: every token an asset names is
provided, and every value provided is named by some asset. An unresolved `{{make}}` shipped into somebody's
repository would read as a typo in the method, in a file that is valid markdown either way.

Nothing a project receives changed. The eleven generated files are byte-for-byte what they were, proved
against digests taken from the generator at the commit before the move and kept in
`tests/fixtures/agent-briefs.sha256`.

**Catch-up:** nothing. `agents/sail-*.md` in a generated project is the same text it was; regenerate or
not, as you like.

**A delegate's standing brief now names the skills its stage reads.** The implementer is sent to `tdd`,
`testing` and `refactoring` before its first RED, and to the skills that shape the code it writes; the
reviewers to `acceptance-review`, `test-design-reviewer` and `hexagonal-architecture`; the lookout and the
privateer to the same skills the `/gaps` and `/adversary` commands already named; the bosun to the hexagon it
stubs behind and the ADR shape it writes. Until now only the demo hand and the skipper named one, and the
other briefs restated a digest of the discipline instead — a fresh context read the digest and never opened
the skill. A skill the catalogue withholds from projects without its capability is named *where shipped* — including
in the quartermaster's styling passage, which a project with no browser app received with two names it had no
skill for — and the keel's suite holds every name a brief uses, as rendered, to a skill the toolkit has.

**Catch-up:** `slipwai migrate` brings the briefs.

**A project that elected no extension is no longer handed one extension's tool name.**
`scripts/agents/registry.json` is the keel's catalogue of coding agents and it travels into every generated
project. Claude Code's headless row carried `--allowedTools 'Bash,Skill,Agent,WebFetch,WebSearch,mcp__codegraph__*'`,
so every project ran its sessions under an allow-list naming the code index whether it had elected the
index or not — and a reader finding it there had every reason to think the keel brought it.

An `extension.json` now declares `tools` beside `hooks` and `guards`: the names a headless session must be
allowed to call to reach that extension, as a list of strings in the harness's own spelling. The generator
writes them to `scripts/extensions/available-tools.json` the way it already writes the other two,
`hooks.py --elect` records the elected ones in `.slipwai/hooks.json`, and a harness row says where they go
with a `{tools}` placeholder **inside** the allow-list it already has — a second `--allowedTools` flag is
not a merge on every harness that has one. A row with no placeholder is left exactly as recorded rather
than handed a flag nobody has checked it accepts.

Nothing is validated against a harness. A tool pattern is the harness's spelling, and a keel that checked
them would be a keel that has to be released before an extension can use a tool it invented. What is held
is the shape, and `tests/test_extension_reach.py` holds the registry to carrying no extension's name in any
value a session runs under — `permissions`, `command`, `env` and the rest, as against a `source` or a
`projectMcpReason`, which are dated evidence and stay as recorded.

**The keel says *the code index* for the thing.** Twenty-nine notes in the registry and the architecture
view's own prose named the product where they meant the capability. The product is still named where the
keel is naming a file format or quoting what a file says wrote it: `slipwai survey` opens
`.codegraph/codegraph.db` if it is there, the way it reads `.git`, and `./init --extension codegraph` is
still the command a refusal gives you.

**Catch-up:** a project that elected codegraph before this generates the identical session command, because
the election now supplies the name the registry used to. One that elected nothing loses a tool name from
its allow-list that nothing in it could reach.

**`slipwai migrate` works in an installed copy.** It applies the committed rename table to a version 1
project, and read that table from beside the keel — where the wheel, the source distribution and the
executable had never carried it. In a checkout the file is at the repository root and every gate was
green; everywhere else the verb ended in a `FileNotFoundError` naming a path inside the installed package.
All three distributions carry it now, and a copy that somehow has not got it refuses in one line saying
nothing has been changed, rather than raising a traceback at somebody halfway through a migration.

**What a distribution carries is now said once.** `assets.BUNDLED` names it, and `tests/test_bundled.py`
holds the wheel, the source distribution and the executable's spec to that list — the gate that was missing,
since the one thing no checkout can notice is a file it has and an installed copy does not.

**Catch-up:** `slipwai upgrade`, or reinstall, if `migrate` ended in a traceback for you.

**`slipwai list` stops calling an installed target a language.** The four kinds of package share one
directory and are told apart by the manifest each carries; the installed half of the Languages listing read
every directory in it, so a target installed beside a language appeared under **Languages**, with its
version, as though a project could be generated in it.

The offered half had the same fault from the other end and was fixed first — this is the half on disk, and
the two are now the same rule: a language is a directory holding a `language.json`.

**Catch-up:** nothing.

**Approve or disapprove a storyboard from the voyage.** Approving marks every drawn state approved and starts the next step: the model on an event-modelling project, the chart on a standard one. Disapproving parks the states, asks why, and leaves the storyboard where it is. Either press locks both buttons, and a locked button looks locked. A model session that is still running stays on the voyage after the board restarts; that window has not got the lines from before.

**Catch-up:** `slipwai migrate` brings `make model-next`. Until then, approving on an event-modelling project says the target is missing.

**The voyage tells "something wants you" from "everything has stopped".** The Slices step is amber, with `!`, while something waits on a person and slices are still at work — a park on one slice, a question, a note for the host, decisions past the ceiling — and red only when nothing is at work until a person acts. Its line names what wants you rather than counting it.

**The two identity questions are now `Internal authentication` and `External authentication`.** They were
*Staff* and *Customer*, which read as a guess about who uses the product: plenty of projects authenticate
operators, partners or agents rather than staff, and plenty have members or citizens rather than customers.
Internal and external say the thing that actually differs — which side of the organisation the account is on
— and that is the distinction the two axes have always been about.

Everything the keel says follows: the interview's two questions, every option's description, the generated
`README.md` and the cloud architecture pages, the Keycloak notes, `.env.example`, and the browser app's own
comments.

**The two cloud stacks are renamed too, and this is the part to read before you deploy.** A terraform
resource address is state, not a name: `aws_cognito_user_pool.staff` becoming `.internal` is, to terraform,
one resource destroyed and another created — which for a user pool is every account in it gone. So every
renamed address ships with a `moved` block, which tells `tofu plan` to move the state instead. The files are
renamed with them: `cognito_staff.tf` → `cognito_internal.tf`, `cognito_customers.tf` →
`cognito_external.tf`, `entra_staff.tf` → `entra_internal.tf`.

**What did not change.** The axis keys are still `auth` and `users`, the capabilities are still `auth-*` and
`users-*`, the Keycloak realms are still `app` and `customers`, and `OIDC_*` / `USERS_OIDC_*` are untouched.
Those are identifiers a running service and a generated project already read, and renaming one is a
migration rather than a rename.

**Catch-up — do not apply before you have read a plan.** On a project with an AWS or Azure stack that has
already been applied:

```sh
slipwai migrate          # brings the renamed files and their `moved` blocks in
cd infra/service && tofu plan
```

**Read that plan and do not apply until it says no resource will be destroyed.** The `moved` blocks are
what make it say that; a plan that still shows a destroy means one address was missed, and applying it would
take the pool, the app registration or the connection with it. Report the address and nothing is lost.

Your `*.tfvars` need the two renamed variables: `staff_callback_urls` is `internal_callback_urls`,
`customer_callback_urls` is `external_callback_urls`, and the `auth0_` forms of both the same way. A
variable is not state, so that is a rename and not a migration — but `tofu plan` refuses an undeclared one,
which is the gate that stops you missing it.

A project with no cloud target has nothing to do.

**A whole capability now gets six readings in one Capability gates rung, and a slice keeps only what it can answer alone.**
The rung replaces the *Mutation gate*. It runs when a capability's last slice has merged and before the
person's demo, in this order:

1. converge over the capability's whole diff, against the specification and every slice's tasks
2. `/gaps` over that diff
3. the design review from screenshots
4. one `/adversary` pass, only where a slice widened a trigger
5. `/mutation`
6. `sail-demo-hand` walking every example of every slice

**Convergence no longer runs per slice.** It asks whether the code does what the specification requires, and
that has its answer only once the slices sharing a requirement are all built. Its two-pass limit, its
re-open rules, the clean-tree rule and the "close the class, not the instance" rule govern the capability
gate unchanged.

**No slice is attacked.** The *Adversary* rung is now *Attack surface*. It writes the slice's trigger table
(identity and money rows added) under a heading ending `trigger record`, and `make check-decisions` accepts
that as the slice's row. The capability is attacked only where at least one slice widened a trigger, or with
`--full`. Otherwise the gate writes a skip naming the tables it relied on, and the skip clears the gate.
**The full pass the slice closing a feature's split used to take is gone.**

**What stays per slice is scoped to what the slice added or changed.** Screen design covers only its own
screens and the elements it changes. The review reads the diff against the merge base, and its findings point
only at added or changed lines. Anything about untouched code is noted for the capability or stowed, never
fixed in the slice, and the reshape refactors only the slice's own lines. The *Demo* rung no longer opens a
browser. Each example is recorded under `## Examples proven` in `tasks.md` against the test that proves it,
and that record gates the push.

The record is `specs/<feature>/capabilities/<capability>/gates.md`. It holds `## Convergence`, `Reviewed:`
lines and a final `Cleared:` line. `scripts/agents/capabilities.py --gates` lists capabilities owed their
gates, and `--due` lists a demo only once they clear. Findings and open convergence tasks at or above the bar
are fixed in a follow-up slice in the same fairway before the demo. Those below it go to the careen.

**Under the `open` release mode**, where a merge reaches the actor at once, converge, the gaps trace, the design
review and the hand's walk run per slice as well. A slice that widened authorisation, identity or money is
attacked before its push, because anything not covered would be live rather than dark. The capability's
converge, adversary pass and mutation still run. Under `keystone` the gates run on the capability's last slice
before its merge.

**Catch-up:** `slipwai migrate` brings the ladder in `commands/sail.md`, `commands/adversary.md`,
`commands/gaps.md`, the hand, lookout, privateer, navigator, mate, slice-watch and quartermaster briefs,
`.specify/extensions.yml`, `scripts/agents/capabilities.py`, `scripts/check-decisions.py` and the tasks
template. Then run `make agents` so the harness gets the new command and brief text. A slice already past
implementation finishes the old way. From the next slice on, skip its convergence, record its examples
proven, and write its adversary row as a trigger record. A capability whose last slice merged before you
upgraded owes its gates before its demo: run `python3 scripts/agents/capabilities.py --gates` to see which.

**The catch-up notes now open with the way from a merge to a project your coding agent can work in, whether
or not the migration stopped at conflicts.** A migration that stopped at conflicts used to leave the rest of
the way — `slipwai migrate` again, `make agents`, a new agent session — in a report that scrolled off, so a
project could be merged with its agent still running the old ladder and only a failing `check-agents` to
say so. `.slipwai/catch-up.md` now opens with *First: set the project up* on every migration, the crossing
from version 1 included. It names the files the merge stopped at and walks seven steps in order: resolve
each file (take the factory's side of `commands/sail.md` and the other generated pages, then re-apply your
own edits), commit, `slipwai migrate` again, `make agents`, `make check-agents`, start a new session, and
confirm with `make crossing` and `make verify`. A clean migration did the first four steps itself, and the
section says where to start. The stop report points at the section rather than repeating it, and `/catch-up`
will not go on while a merge is in progress or `check-agents` fails.

**A catch-up page is archived, never deleted or overwritten.** The page used to be thrown away when the work
was done and overwritten by the next migration, losing the one record of what that upgrade asked. Now each
page ends naming its own archive path, `.slipwai/catch-up/archive/<from>-to-<to>-<UTC time>.md`. `/catch-up`
moves it there when the work is done. Before writing a new page, `slipwai migrate` moves whatever page it
finds there too, the crossing from version 1 included. A page from before this change is named from the
versions in its title and the time it was last written. A page already archived is never archived twice, and
an archived page is never overwritten: a different page under the same name takes the next free suffix. The
archive stays on the machine and is git-ignored, like the page.

**Catch-up:** `slipwai migrate` brings the new `/catch-up` page and the `.gitignore` line for
`.slipwai/catch-up/`. A `.slipwai/catch-up.md` left by an earlier upgrade is moved into the archive by that
same migration, so there is nothing to do by hand.

Step 4 of that section says `make agents` installs a coding agent the project has moved to since `./init`,
where that agent names itself in its environment, and that `./init --integration <agent>` is for the case it
could not tell — rather than sending everyone to `./init`.

**Four faults that only CI could see, and one of them was a real bug on Windows.** The keel's gate had been
red on every push for a day while it was green on a laptop every time — which is the failure mode the two
gates exist to prevent, so each is now checked where it broke.

- **`fleet list` and a second `fleet start` killed what they asked about on Windows.** `os.kill(pid, 0)` is
  a signal on Unix and `TerminateProcess` on Windows, where the signal number is the exit code and 0 is as
  fatal as any other. So the liveness check ended every process it was asked about and then reported that
  nothing was running. Windows is asked through the process handle now, and a test that starts a real
  process and asks twice runs on every platform.
- **The harbourmaster could not merge in a repository with no `user.name`.** A rebase that replays a commit
  writes one, and writing one needs a committer. It now says exactly that, with the `git config` that fixes
  it, instead of relaying nine lines of git's advice inside a refusal about something else.
- **PyYAML was never pinned.** Four tests read workflow YAML and three more read a chart or a model; they
  passed on a laptop that happened to have it and errored in CI. It is in `requirements-dev.txt`, and
  `make test` puts the pinned tooling on the path beside `src`.
- **`make model` needs a Chromium that will start.** The renderer's own sandbox cannot initialise on a
  runner, so `make test-docs` now *skips that one command with the reason* rather than failing — and CI
  passes `MERMAID_PUPPETEER_CONFIG` so it is checked rather than skipped.

**Catch-up:** `slipwai migrate` carries the Windows fix into a project's `scripts/agents/fleet.py`. On
Windows, `slipwai fleet` was reporting a run it had just stopped.

**The specification is clarified and checked, and a slice is analysed before it is implemented.** After `/speckit-specify`, `/sail` runs `/speckit-clarify`. It then runs `/speckit-checklist` and the read-only find-gaps survey in parallel against the clarified specification; after both return, the host runs the find-gaps conversation and writes confirmed answers back. After tasks, and before implementation, it runs `/speckit-analyze`: a read of the spec, the plan and the tasks, writing nothing. A finding goes back to the plan or the tasks. `/speckit-taskstoissues` is not part of the loop.

**Catch-up:** `slipwai migrate` brings the command pages, the workflow page and `docs/intake/README.md`.

**A decision can be marked read from the board, and a person's own answer is never owed a read.** The
decision ceiling counts decisions with no `read` receipt, and nothing but a hand-written line could make
one: hr-test-2 parked over its ceiling with a board that showed every decision and could take none off.
*Waiting on you* now lists a stream's unread decisions with **Mark read** on each and one for all of them,
which writes the receipt the ceiling counts. A decision the captain recorded as `decided_by: human` —
a person's answer to a park, `decide for me` among them — no longer counts toward the ceiling.

**Slices worked abreast no longer mint the same decision number.** Each delegating session took the next
`D<n>` after the last entry it could see, so two slices came back with D28 to D30 apiece.
`scripts/agents/ids.py reserve decision <count> <slice>` hands out numbers under a lock shared by every
berth, past every number on trunk and on every `slice/*` branch, and `/cruise` now allocates with it.
`check-decisions.py` refuses a number used twice and no longer asks for contiguous, in-order numbering,
which slices merging in their own order could not meet.

**Catch-up:** `slipwai migrate` (or `slipwai replay` and a merge, on 2.x) brings the corrected
`scripts/agents/inbox.py`, `ids.py`, `check-decisions.py` and `commands/cruise.md`. A fairway parked over
the ceiling is let go by marking its decisions read on the board.

**The dispatch ledger lives under `.slipwai/dispatch/`, not in `specs/`.** `make dispatch` now writes
`.slipwai/dispatch/<feature>.jsonl`, committed beside the run's other records, rather than
`specs/<feature>/dispatch-ledger.jsonl`, which sat in the feature's specification as though it were part of
it. A feature folder is what the product is to do; the ledger is evidence about how a run worked it. `/sail`
now also says how the ledger reaches trunk: in the merge that lands the first slice it names, never as a
commit of its own, because a push to `main` may be a deploy and one line of evidence is not a change.
`check-dispatch` and the `pre-push` hook read both homes, so nothing goes red between upgrading and
migrating.
The `pre-push` hook now judges the ledger in the commit being pushed rather than the working tree, so a
ledger written and never committed is refused before the push rather than by CI on a clean checkout.

**Catch-up:** `slipwai migrate` moves every committed `specs/<feature>/dispatch-ledger.jsonl` to
`.slipwai/dispatch/<feature>.jsonl` with `git mv`, in the commit it makes after the merge. Where a file is
already at the new home it is left alone and named in the report; append one to the other and remove the old
one when convenient.

**Everything a run is set to is one box with a tab each, and two of the settings now have a control at
all.** Speed and Fine tune were two cards; who answers at each stop was a third; and the two files the
ladder actually reads had nowhere to be seen — `.specify/sail.json`, how much one implementation delegate
is handed and how many failing tests a cycle opens with, and `.specify/models.json`, which role each stage
runs under. Both were a command typed into an agent by somebody with the board open in front of them.
Asking "what is this run set to" was asking four questions in four places.

The Settings card carries all five: **Speed**, **Fine tune**, **Who answers** (`/cruise-settings`),
**Delegation** (`/sail-settings`) and **Models** (`/model-delegation-settings`). Each panel names the file
it writes. The telegraph's two tabs are the board's own and are always there; the other three appear only
where the project has that file, because a tab offering to set a file that is not there would be a control
that refuses every press.

**Written by the project's own scripts, never by the board** — the rule the stops already followed, now
also for `scripts/agents/sail.py --set` and `scripts/agents/models.py --set`. Each validates against the
same table the board renders from and `make check-agents` holds both files' shape, so there is no second
writer to drift from the project's own checker. Which roles a stage is offered is read from the project
too: `models.py` accepts any role name, so offering one this project has not mapped would be offering a
fall-through dressed up as a choice.

**The tabs are radio buttons and a stylesheet.** The published copy of a board is one file with nothing to
press and therefore no JavaScript, and a box whose tabs only worked on the served copy would be the two
copies disagreeing.

**Three checks an extension is held to were wrong about the thing they were reading.** The three published
extensions had never run conformance — no CI at all — so nothing had said so.

- **`recovers` read line by line.** Every real message is written the other way: the trouble, then
  `Install it:`, then the command, indented. So the first line of every one of them failed and the command
  two lines below was never seen. It reads a message now — a problem line and the lines under it — and a
  problem with nothing after it still fails.
- **`./init` could never be recognised as a remedy.** The pattern had a word boundary before it, and the
  character before `.` in `  ./init --extension uipro` is a space, so `\b\./init` matched nothing. It is the
  one command every extension names.
- **`projects` only excused a stop for a missing tool**, recognised by words like *not found*. The scratch
  project it runs in is deliberately bare, so an extension that acts on a browser app correctly does nothing
  there and says `this project has no browser app for it to design` — no such words, failed for doing the
  right thing. What makes a stop legitimate is that it names the way on, which is what obligation 6 already
  asks of it.

**Catch-up:** nothing. Three packages that were conforming all along now say so.

**`generate` now finishes the project it makes: it runs `./init` in it, and the board lands there.** Until
now both faces stopped at `created: <path>`. The next step — `cd` into it and run `./init`, which installs
Spec Kit, projects the skills and commands into your coding agent, and is the one step that reaches the
network — was a sentence in the guide, and nothing in the new tree works until it has run.

In the terminal, the interview ends by running it, with your standard input, so Spec Kit can ask which agent
it is for. A scripted `slipwai generate` is unchanged: it is left with the next step unless it is given
`--init`, and `--no-init` declines it in the interview.

On the board, the interview now asks one question the terminal cannot ask well — which coding agent, from
the thirty-six the registry knows — and when the project is made the board **attaches to it**: it is that
project's board from that moment, with a card naming what was made and tailing `./init` as it runs. The
run is a child that outlives the request, so the page never hangs waiting for Spec Kit to install.

`./init` runs through a pseudo-terminal, so the card fills line by line as it happens: the script shells
out to pip, to uv and to Spec Kit, every one of which line-buffers to a terminal and block-buffers to a
pipe, and down a pipe the card showed two lines for two minutes and then everything at once. The chip
beside the project's path carries a running clock.

**Every log on the board is a scrolling tail now** — a stream's own log, the event feed, and the two logs
a generate leaves. Each is bounded, opens on its newest line, and scrolls for the rest; the event feed
shows every line the fold carries rather than the last fifteen.

The board's interview asks for the **repository to push to** as well, whatever the target is. `./init` asks
for that one over `/dev/tty` — the terminal, not standard input — and so does the extension menu, so a
child of the board inherited whoever started it: the question printed into the card while the read blocked
on a terminal nobody was looking at. The child now runs in a session of its own, which has no terminal to
reach, so both questions do what they already do for a scripted run: nothing. The answer given here is
handed to `./init` where the target has a pipeline to configure.

The board also gained a **Looking at** card: the directory it is a view of, and a box that points it at
another one. Moving the board no longer means stopping it and starting it again with `--root`, which is
also how you watch a `/sail` or `make cruise` that is already running somewhere else — the board is a fold
of that project's logs, so attaching to it is all there is to it.

**Catch-up:** nothing. This is the factory's own behaviour, not a project's; an existing project's `./init`
is unchanged.

**A project can be started from a product requirements document, and the board takes it to a specification
a person reads before anything is built.** The interview's last question is a file picker on the board and a
path in the terminal; `slipwai generate --prd <file>` copies it into the project as `docs/prd.md`, listed in
the docs index, before the first commit. After `./init`, the board runs `make draft`: one headless session of
the coding agent, with the new `commands/draft.md` as its rules, that ratifies the constitution and writes
the first `specs/<feature>/spec.md` from the document — every call the document does not settle recorded
under its own `## Assumptions` heading — and stops. The board then shows **Continue the build**, which runs
`make launch` (`commands/launch.md`): the chart and the split in a second session answering stops as
`/cruise` does, `/cruise` enabled, and the fleet cast off. Nothing runs unattended until a person has had
the specification in front of them and pressed the button. Both `make draft` and `make launch` are typeable
in a terminal, and `/draft` and `/launch` are commands in every installed harness.

**Catch-up:** `slipwai migrate` carries `commands/draft.md`, `commands/launch.md`,
`scripts/agents/draft.py`, `scripts/agents/launch.py` and the two Makefile targets into an existing project.
A project that already has a PRD puts it at `docs/prd.md` and runs `make draft`.

**`./init` started from the board is given the login shell's environment.** A board started at login has
`PATH=/usr/bin:/bin`, and the `./init` it started with that found neither brew, uv, Spec Kit nor the
cloud's own tools on a machine that had every one of them, then fell through to the system pip and a
Python too old for Spec Kit. The generate child already got the login shell's `PATH` and exports; now the
handover child does too.

**Catch-up:** nothing — rerun `./init` from the board, or in a terminal, where it stopped.

**The board has a Voyage tab: what stage this project is on, read off the tree.** A strip of eight stages —
PRD, init, constitution, specification, event model, chart and split, slices, accepted — each done, working,
waiting on you or still to do, with the file that proves it and the command that moves it. Nothing on it is a
status field anybody typed: a stage is done when the thing that proves it exists, working while the board's
own child or a captain is on it, and waiting when a park or a failed step asks for a person. Under the strip,
the committed `docs/event-model/model.drawio` in draw.io's own read-only viewer with each slice's caption
stroked by where the slice stands, and the slices in four columns folded from the deck logs. A generate
lands here, with `./init` and the draft saying their lines on the same page, and **Continue the build** lives
on the current stage.

Two smaller things with it. Claude Code's print mode writes one JSON event per line, and the card now says
the assistant's words, the tools it reaches for and the result with its cost, rather than the JSON. And
draw.io's viewer is fetched once from viewer.diagrams.net into `~/.slipwai/` and served from there after,
rather than carried in the wheel at four and a half megabytes.

**Catch-up:** nothing. The viewer arrives the first time the tab is opened with a network.

**The Board tab is the landing, and everything live is on the Voyage tab beside the stages and the
model.** The Board now says what directory it is looking at, where that project stands in one line, and
offers the two ways in — start a project, adopt a repository. The streams, the inbox and its answer boxes,
the speed, the fine tune and the last lines moved to Voyage with their controls, under the model and the
work, so how the work is going is read on the page that says what the work is. The published copy is
unchanged: the live cards alone, with nothing to press.

**Mock-ups are on the Voyage too.** Every wireframe the mock-up stage wrote under `specs/<feature>/mockups/`
is shown small, by its own title, with the whole page a click away — served by the board from the project,
with its stylesheet, and nothing outside that directory.

**The model has its own controls, and a slice is called what the split calls it.** The model's bar carries
nudge, zoom, actual size, fit and full screen; the canvas is dragged to pan and wheeled to zoom, and it opens
with the lanes fitted to its height at the left edge rather than the whole timeline squeezed into its width.
A slice card says `S01 · Set up an account`, read off the split's table, rather than the id alone. And where
the split is written and no captain is running — a launch whose fleet never lit, a machine restarted — the
Slices stage says so and a **Cast off the fleet** button runs `make cruise` with its lines on the page.

**Catch-up:** nothing.

**The board proposes the directory it is looking at as the output parent, not the directory its process
happens to hold.** A board started at login holds `/`, so **Start a new project** proposed `/`, and
pressing Generate on any target ended in a traceback from a read-only filesystem. The proposal is now the
board's own root — the harbour it serves, or wherever it was last attached — and the login service is also
started in that directory on all three platforms. `slipwai generate` itself now refuses an output parent it
cannot write in, naming the directory and the flag, instead of tracing back.

**Catch-up:** `slipwai bridge install` again, once, so the service file carries its working directory.
Until then, type the output parent on the form.

**The README's passphrase row says where a target keeps it.** The row that told a person to keep the state
passphrase somewhere now says that a target which can keeps it in the account it bootstrapped and reads it
back, and that the printed copy is for the day that account is gone — which is what the aws and azure
packages do from their next release.

**Catch-up:** nothing; a regenerated README carries the new row.

**GitHub is where slipwai lives and where it is published from.** `ROBCOATVG/slipwai` on GitHub is the
canonical repository; its standard runners are free for a public repository on Linux, macOS and Windows,
which is the three-platform gate this keel promises. A `v*` tag pushed there runs the gate on the tagged
commit, then builds and smokes the wheel and the executable on each platform, then publishes: the wheel and
source distribution to PyPI by trusted publishing, with no token stored anywhere, and a GitHub release for
the tag carrying each platform's executable and its `.sha256`. Nothing is published from a fork, from a pull
request or from `main` without a tag.

The project's links, the presets' `repository` and the upgrade message for the executable now name
GitHub, and the README carries the gate's badge and the Python versions beside the PyPI one.

**Catch-up:** none for a project. A copy of the executable installed earlier is replaced from
`https://github.com/ROBCOATVG/slipwai/releases`.

**Hand over the whole folder your brief is in, and it is sorted for you — on the board as well as in a
terminal.** Carrying what a PRD stands on arrived as two flags and no way to use either from the generate
form, which is where most people start a project.

**Everything else** on the form is a folder picker, and `--brief <dir>` is the same thing typed. Whichever
file in it reads as the requirements document becomes `docs/prd.md`; everything else lands under
`docs/design/`. The document is found three ways, in order of how much each proves: the name a PRD usually
has, a name that says what it is, and the document's own first heading — which survives a file somebody
called `v2-final.md`. A folder with no requirements document in it is an answer rather than a failure: it
is all design material, and the specification is written in the agent the way it always could be. What was
decided is printed, so a wrong guess is visible rather than silent. `--prd` and `--design` still name
either half exactly, and win where both are given.

**A document's links are resolved against the document and contained by the brief**, which are two
different directories and were one. A PRD sitting in `docs/` inside a brief folder may point at
`../wireframes/` and have it carried, and still reach nothing outside the folder handed over.

**`--design` on its own is no longer refused.** `commands/mockups.md` reads `docs/design/` whether or not
a PRD exists, so a brand sheet handed over with the specification written in the agent afterwards is a
direction the mock-up stage follows just the same — the refusal was the keel insisting on a dependency its
own stage does not have.

**On the board the brief is a path, not an upload.** The board binds this machine only and generates on
it, so the folder is already somewhere the verb can read: carrying its bytes up through a browser and
writing them back out would be a copy nobody asked for, with a size limit nobody needs.

**And a quickstart no longer collides with the board's own flags.** `--backend` is the one-word spelling
of `--language` with `--framework`, and the verb refuses the two spellings mixed — so a quickstart filling
in either half for somebody who had typed `--backend` *was* that refusal. The board always passes
`--backend`, which made every quickstart that answers a language fail from it: all six of the ones this
keel carries.

**A project opened in a different coding agent from the one `./init` chose now sets itself up there.** Before,
a project set up under Cursor and opened in Claude Code (or under any harness and opened in another) followed
none of its rules: Claude Code reads `CLAUDE.md`, which only existed where Claude had been installed, and the
commands, skills and delegate types are generated per harness and git ignores them. Now:

- every generated project commits `CLAUDE.md` with its `@AGENTS.md` include, whichever harness was chosen, and
  `make agents` keeps that include in step for every harness that reads one;
- `AGENTS.md` opens with one instruction: if `python3 scripts/agents/harness.py --can-delegate` says this
  harness is not set up, run `make agents` and start a new session;
- `make agents` adds the harness the session runs in where it is not installed, through `specify integration
  install <key>`, so Spec Kit's commands arrive with the project's own. Where Spec Kit will not install it
  beside the others, the line says so and leaves `--force` or `specify integration switch` to you. Either way
  the project's own material is projected into it. `make arrive` and `make preflight` do the same, but only
  where the harness is missing or unprojected. Which harness is running is read from its own session variable
  (Claude Code and Codex set one) and never guessed;
- `make agents` removes a projected command, skill or agent type whose canonical file has gone, but only files
  carrying its stamp. `check-agents` reports such a file as drift;
- `make agents` warns when the slipwai installed here is newer than the one that last wrote the project, and
  names `slipwai migrate`, which is what brings a newer ladder, command or agent type in;
- Cursor is recorded as reading `AGENTS.md` natively (its documentation, read 2026-10-17), so it no longer gets
  extension blocks copied into `.cursor/rules/specify-rules.mdc`.

**Catch-up:** `slipwai migrate`, then `make agents`. Migrate brings `CLAUDE.md`, the new `AGENTS.md` opening,
the projector and the `arrive`/`preflight` targets. Commit `CLAUDE.md`.

**`./init` installs what the target needs, through the target's own hook.** A target package may now answer
`setup`: the project path, from its `scripts`, of a script `./init` runs before anything else production
needs. The keel runs it and reads nothing from it — what a region is, which package manager a tool comes
from, or what a sensible default looks like is the target's to know, never the keel's. `aws` and `azure` ship
`scripts/setup.py`: each installs OpenTofu and its CLI with whatever the machine has (`brew`, `apt`, `dnf`,
`winget`, or the tool's own installer), and settles the region or location with a default on offer. `./init`
installs and signs in `gh` the same way, as the keel's own need; `./init --no-install` only looks. A target
with no hook is checked exactly as before.

**`generate` notices rather than refuses where `./init` will install.** A machine short a tool that the
target's hook puts there is told so and what `./init` will do, and generation goes on. A target without a
hook is still refused, and the refusal now names the `PATH` it searched — a sandbox or an agent's shell with
a trimmed one reads exactly like a machine with nothing on it, and the line is what tells them apart.

**`slipwai package new --kind target` starts a package with a `scripts/setup.py` to fill in.**

**The in-tree copies of `aws` and `azure` are gone.** `packages/aws` and `packages/azure` were byte-for-byte
mirrors of `slipwai-target-aws` and `slipwai-target-azure`, which are where those targets are written and
released from; two sources for one package is how a fix lands in one and not the other. `packages/toy`
stays — it is the suite's fixture, not a published package. The suites that need a cloud skip, as they
always did on a checkout without one; the skiff migration test moved to the aws repository with the script
it exercises.

**Catch-up:** `slipwai migrate` carries each target's `scripts/setup.py` in and rewrites `./init`.

**An implementation delegate's return is a commit, named by its hash — the session integrates that and never
files copied out of a working tree.** `sail-implement-shipwright`'s brief always said to commit each green
increment locally; returns still came back as edited trees, a host copied one sibling's files while its next
rule was RED, and a verification run sampled the mixture and was thrown away. The brief now says the report
opens with `commit <hash>`, or `no commit` and why; *Who runs each stage* says the session takes that commit
(`git cherry-pick`, or a merge from the delegate's worktree) and nothing else; and the `after-delegate` guard
in `scripts/agents/session.py` refuses a shipwright's return that names neither, sending it back for the hash.

**Catch-up:** `slipwai migrate` brings the brief, the paragraph and the guard; `make agents` re-projects the
hook on a harness that fires a post-tool event.

**A project with more than one deployable gets a fast target per deployable, and a mutation sandbox is
never discovered as tests.** `make unit` is one target over every deployable, which is right for the merge
and wrong for the increment: on one project every Go domain increment paid about ninety seconds of Vitest
for a browser suite it had not touched. The generated `Makefile` now writes `unit-<name>` per service and
per browser app, running that application's own fast checks and nothing else; the *Implementation* rung and
`sail-implement-shipwright`'s brief name it as the increment's gate, with `make unit` over all of them
still the slice's before its demo. And the generated `vite.config.ts` excludes `**/.stryker-tmp/**` from
Vitest's discovery, because a `make unit` that started while a mutation run was copying the app found 1,104
test files where there were 514 and failed every copied fixture on ENOENT.

**Catch-up:** `slipwai migrate` rewrites the `Makefile` and merges the Vite config; a project that edited
either resolves the merge as usual.

**Mutation testing runs once per capability, bounded, before the person's demo of it.** Per slice it took
hours apiece — one project's owner took it out of the loop by hand — and measured a fraction of what a person
accepts. The *Mutation gate* rung, *After the hand's verdict*, *What the demo stop has to contain* and
`commands/mutation.md` now say the run is the capability's: when its last slice has merged and before the
demo stop walks it, over every production file the capability's slices changed since the first of them
branched, delegated to `sail-mutation-shipworm` under its `harbour.json` budget. The brief holds the budget
rather than hoping for it — the scope and the likely cost said first, the harness started in the background
with a root-readable log and report, and at the budget its own process tree killed and nothing beside it —
and a capped run leaves a qualified receipt naming what it covered and what it did not, never a score. A
score under the threshold still holds the capability back, and nothing is carried.

**Catch-up:** `slipwai migrate` brings the rung, the sections, the page and the brief. A project that
recorded mutation as N/A per slice records it per capability from the next demo stop on.

**A worktree is checked once before anything is dispatched into it.** One run's delegates discovered the
same environment in series — Go's build cache not writable, then Staticcheck's, then a test refused a local
socket, then the browser harness was missing and a suite crashed while trying to skip, then several delegates
in unindexed checkouts tried the code index route that was not there — a dispatch, a return and a host repair
apiece, none of it about the product. `make preflight` (`scripts/agents/preflight.py`) asks those questions
once, read off `project.json` and the elected extensions: a Python the gate scripts can run on and PyYAML in
it, a localhost socket a test may bind, each deployable's toolchain on PATH and its caches writable, Node's
dependencies installed, the index present where one is elected. One line per check, the fix on a failing
one, a language nobody has a check for said as such rather than passed, and exit 1 on any failure. *Running
ready slices concurrently* runs it in every new worktree before the slice's delegate is dispatched.

**Catch-up:** `slipwai migrate` brings the script, the target and the paragraph.

**A slice is reviewed once, over its whole diff — a delegate's return is spot-checked, never sent to a
reviewer.** The *Review and reshape* rung always said the reviewer reads the slice's whole diff; a run that
also sent every implementation return to a fresh reviewer paid eight reviews and eight fix rounds for nine
pieces of coding and delivered no more for it. The rung, the batch paragraph of *Who runs each stage* and
`sail-review-mate`'s own brief now say the cadence outright: the session that dispatched a delegate verifies
its return against the tree; the reviewer is sent the converged diff once, or — for one story that touches
identity, authority or money, where the slice's brief says so — that story's pinned commit once before the
rest is built on it. `make check-benchmark` warns of a slice whose record holds a third `review` bracket.

**Catch-up:** `slipwai migrate` brings the rung, the paragraph and the brief. Guidance of the project's own
that asks for a review per delegate return, or a dispatch plan per refill, now contradicts the ladder: delete
it, or trim it to what the ladder does not say — the exact-manifest rule and the recorded reason for any
host-imposed delegate limit.

**A stage's token budget counts the work, and the benchmark reads it at every bracket.** `harbour.json`'s
`tokens`, `bunker_per_slice` and `bunker_per_day` were thousands of input tokens, and on a host whose context
is re-read every turn that measured the context and not the work: one 81-minute implement pass recorded
19.67M input against a 1,200k budget, 19.43M of it cache reads, and the console then added the cache reads
again and said 39.1M. The unit is now **work tokens** — uncached input plus output — on every harness:
`scripts/agents/benchmark.py` normalises a Codex read, whose `input_tokens` includes its cache reads, so
`input` means the uncached part as it already did on Claude Code, and reads an older Codex record the same way.
`benchmark.py start` prints the stage's budget and what the slice has spent of its bunker; `end` says *over
budget* on stderr and writes it on the entry when the stage passed either number; the summary line carries
`work` beside `in` and `out`. The *When a stage reaches its budget* section says the lines are the control
under `/sail`, where no captain is ending stages by their silence.

**Catch-up:** `slipwai migrate` brings the script and the section. The numbers in `harbour.json` are not
changed; they were sized for input and are now generous for work, so a project that wants the old pressure
lowers them, and `slipwai telegraph` says what they mean.

**Clearance prints both concurrency numbers and says which bounds what.** `boilers` bounds the slices that
run at once and `fanout` bounds the delegates inside one slice; a run read the first as the second,
dispatched two implementers where it had room for three, and recorded that the harness disagreed with the
configuration. `python3 scripts/agents/clearance.py` now prints a second line — the slots left, the fanout
inside each slice, and the tree they add up to — and its `--json` carries the same under `numbers`. The
ladder's *Count the whole tree* paragraph reads the numbers from there, and extends the idle-slot duty to the
boundaries inside a running slice: a `[P]` task or disjoint-manifest sibling left undispatched while `fanout`
has room has a reason from a short list, said in the stage line.

**Catch-up:** `slipwai migrate` brings the script and the paragraph. Nothing in `harbour.json` changes.

**`make openapi` writes the service's document where it means to.** The recipe passed a path from the
repository root to `npm --workspace apps/service`, which runs the script inside `apps/service`, so the
document was written nowhere the client build reads — in every berth of hr-test-2. It now passes
`$(CURDIR)/apps/service/openapi.json`.

**Only a person's message answers a park, and the decision ceiling waits for a reading.** Every `told`
line used to clear whatever park was open, including a slice's own note to the host, so parks cleared each
other and a fairway parked on nineteen unread decisions was cleared by the next slice's note. The board,
the MCP server and `fleet.py tell` now write `by: person` on a person's message, or `by: session` under a
dispatched session, and only a person's clears a park. While more decisions stand unread than
`decision_ceiling` allows, no message clears a park. The park the captain writes at the ceiling says
`waiting: decision-review` and is cleared once the decisions are read or the ceiling is raised.

**`/sail` schedules in two bands, and clearance says which.** The page said *run every ready slice whose
contract is settled*, and a slice settles its contract by preparing — so a host following the rule waited
on the one thing the wait was stopping, and two cleared slices with HTTP shapes still to decide sat idle
while their example maps, route drafts and gap reviews could all have run. Preparation (the example map,
the contract files, the gaps pass — the stages that write the slice's own `mark-set` lines) now needs
clearance alone; implementation (the plan onward) needs those lines written and no open question. The
`sail-slice-watch` delegate is handed a band — `prepare`, `implement` or `whole` — and returns at its end.

**Clearance is a state with a reason, not a yes.** `scripts/agents/clearance.py` answers for every slice
with one of eight states — `blocked`, `migration-evidence-required`, `awaiting-decision`,
`preparation-ready`, `implementation-ready`, `running`, `awaiting-demo`, `done` — and the sentence that
says why, and with a schedule: which slices start now and in which band, and for every eligible slice that
does not, the reason — no slot, claimed elsewhere, or *claims could not be read*, which starts nothing.
`--json` is still query version 1 — `ready` is there and means what it meant — with `states`, `schedule`,
`slots` and `claims` beside it, so a board built before this reads it as before.

**The ready set is recomputed at every boundary.** A delegate returning, a mark landing, a decision, a demo
verdict, a merge, a refused claim: each refills the free slots from a fresh read, and a host with a slot free
and eligible work waiting owes the reason in the line that names the ready set. A product question is a
`question` line in the deck log (`fairway`, `slice`, `id`, `what`), open until a `decision` carries the same
`id`; under `/sail` it is put to the person while the independent siblings keep running, and the sentence
says which slices the answer unblocks. A demo wait is the slice's own and never a sibling's.

**The captain parks on a question and writes the decision on resume.** Under `/cruise` a session that
ends on an open `question` used to read as *wrote no `mark-set`*, which sent a person to look for a slice
that was never built. The park now carries the question and names `/cruise-tell`; when the answer clears
the park, the captain writes the `decision` line carrying the question's `id` (and `decided_by: human`)
before re-dispatching, so the resumed `/sail` finds it in the log and clearance stops saying *awaiting
decision*.

**Nested agents and browser runs are counted.** A whole-slice delegate carrying `[P]` tasks is `1 + fanout`
agents, so the fan-out asks for up to `boilers × (1 + fanout)`, held to what the harness can actually run.
`browsers` is a new telegraph number — browser-driven test runs at once on this machine, 2 at `full-ahead`
and 1 below — because several worktrees are still one machine's CPU.

**A prerequisite that shipped before marks were logged is not *blocked*.** It is
`migration-evidence-required`, and `clearance.py --baseline-marks` records, once, a `mark-set` line for each
of its marks carrying `provenance: baseline` and what it was read from — distinguishable from an earned
mark by any reader, and refused a second time, exactly as `check-decisions.py --adversary-baseline` is.

**Catch-up:** `slipwai upgrade` carries the new `clearance.py`, `logs.py` and `telegraph.py` into
`scripts/agents/`, and `slipwai migrate` rewrites `commands/sail.md`, `commands/cruise.md` and
`agents/sail-slice-watch.md`. A project whose `harbour.json` predates `browsers` reads as *adjusted* until
`slipwai telegraph <position>` is rung once. A project whose shipped slices predate the mark log runs
`python3 scripts/agents/clearance.py --baseline-marks` once.

**The board asks which extensions to elect, and the answer reaches `./init`.** It asked nothing, and the
omission was invisible rather than visible: `./init`'s extension menu reads `/dev/tty` and **prints nothing
where there is none**, so every `./init` the board has ever run elected nothing — silently, because an
empty capture is indistinguishable from a person checking no boxes. A project generated from the board came
out with no extensions and no sign that any had been offered. The only way to get one was to pick a
quickstart that named it, or to run `./init --extension <key>` afterwards in a terminal.

**Dev tooling** now sits beside the `./init` question on the generate form: one checkbox per extension
installed on this machine, each saying what it is for rather than only its key, and the chosen keys are
passed to `./init` as explicit `--extension` flags — which it never second-guesses. The card's first line
is the whole command, so an election is something a person watches happen. Nothing is checked by default,
and the question is not asked at all where the machine has no extensions installed: a question whose every
answer is unavailable is a question not worth asking, and the keel ships none of them.

`interview_page` is split at the seam its own budget note names — the rows and the page script are now
`interview_form`, leaving the questions and the flags they become, which is the pairing that note defends.

**A package installed from the board can be used without restarting it.** The catalogue is read once when a
process starts, which is right for a command — a verb runs in a process of its own and nothing moves
underneath it — and wrong for the board, which is one process that installs packages into the directory it
read. A language installed from the Packages tab was on disk, listed by that tab, and missing from the
interview's menus until the server was restarted, which is the one thing the person the board is for cannot
do. The board now reads the directory again after an install, so the language is on the next tab you open.

**And a board with no language installed says so instead of going quiet.** Asking the interview's questions
of a catalogue with no backend in it raised a refusal that reached the web server, which closed the
connection without a word — so the first thing somebody saw on the first machine they ever installed this
on, where no language is installed by definition, was a browser saying the page could not be reached. The
tab now says there is nothing to generate with yet and links to the one that installs a language, and no
page on the board can close a connection instead of answering.

**Catch-up:** nothing.

**The board says what a headless session is doing, not only which tool it reached for.** A session redrawing
eleven screens read as a column of `→ Write`, `→ Write`, `→ Bash`. Each line now says what it acted on: the
file, relative to the project, with a run of writes listed under one name; a shell command's own
description; the task a delegate was given, with that delegate's own calls indented beneath it; the page a
browser opened; the workflow by name. A delegate or a shell left running in the background says when it
finishes, the todo list shows as a count and the item in hand, and the harness's own plumbing — finding a
tool, scheduling a wake-up — is left out.

**Catch-up:** nothing to do; the board does this for every step it runs. A board kept running by the login
service is restarted by `slipwai bridge install`.

**The board stops saying a running fleet is waiting on you.** A `told` left *Waiting on you* only when a `read`
receipt named it, and nothing wrote one — so every `go` and `decide for me` a person ever sent stayed there, the
Slices step went red, and it said "make cruise-tell answers a park" while the fleet ran and nothing was parked. A
`told` is now answered by a later `decision`, or — sent while the fairway was parked — by the captain claiming
work again; a note a session leaves for the host while the fairway works still waits for a person. The step also
read a fleet at work as `todo`: it looked for a berth `running`, a state the board never gives. And with the
fleet running, the step says so instead of telling you to cast off.

**A slice run abreast no longer fails `check-slice-scope` on files the run wrote.** `.slipwai/preflight.json`
and `.slipwai/logs.unread-*/` are ignored in every generated project.

**A skill's script no longer stops `make agents`.** The projection read every file under `skills/` as text,
and the `__pycache__/` a skill's own Python leaves behind is not; it is skipped.

**Catch-up:** add `.slipwai/preflight.json` and `.slipwai/logs.unread-*/` to `.gitignore`; `slipwai replay`
and a merge bring the rest.

**A button that is waiting on something slow says so in itself.** Installing a package and generating a
project both reach the network and take their time, and both wrote only to a log a card below the button —
which on a long form is off the bottom of the screen. A press with nothing happening *at the button* reads
as a press that did not land, which is a press somebody makes again. Both now spin and say what they are
doing, and go back to what they said whether the work succeeded, failed, or could not reach the board at
all.

**The preset box says what it is.** *Start from* offered *ask me every question — the interview as it has
always been*, which described the terminal, where that menu decides how many prompts follow. On a form it
read as nonsense: every question is already on the page. It is **Preset** now, the first row is **No
preset**, and the note under it says a preset fills the questions below in and that every answer it fills
stays yours — and that none is picked for you.

**And a quickstart that cannot be carried out here says why before it says what to type.** The line was
the install command followed by *installs what it names*, which told a reader something they knew and left
out the thing they did not: it now names the packages that are missing.

**The board serves a window each, so two projects at once is a thing a person can do.** It kept `root` on
its handler class, so a second window opened on the same board looked wherever the first one had pointed it,
and a generate in one tab moved every other tab with it. A window now carries a seat — minted on its first
load and held in its own address, because a cookie is one per browser and not one per window — and where it
is looking is the seat's. What is *under way* in a project stays keyed by the project: two windows on one
tree share its `./init` and its cast-off, which is what has always stopped a fleet being cast off twice.
`slipwai --root <directory>` reaches the window now too; typed at a board that was already serving, it was
dropped.

**A run is watched in a window of its own.** The Voyage has left the tab bar. The board is where a person
points somewhere, starts a project, adopts a repository and installs a language; a run is the one product
they are watching, which is a thing to leave open on another screen rather than a tab to lose by pressing
Packages. The project's card opens it, named, so it arrives pointed at the right tree, and the window is
titled for the project so two runs are told apart in a dock.

**The strip says what to expect of the stage it is on, and whether that stage stops for you.** A stage that
waits for a person by design looked exactly like one that had hung, and nothing on the page said which it
was. Every stage now carries that sentence — roughly how long, and who it waits on — with the stage being
worked given its own space above the rest.

**The mock-up review is a stage of the strip.** It was running in the ladder and the strip never named it,
so a person waiting on a storyboard was waiting on something the page did not mention. It stands between
the specification and the event model, where `project/ladder.py` has it and for its reason — the screens
are what the modelling conversation is held over — and it is read from the states a person marked in
`specs/<feature>/mockups/mock-states.md`: amber while one is parked, with the count of what is approved. A
stage this profile has not got no longer prints a file the project will never have.

**Who answers at each stop of a run is on the page, and can be changed while it runs.** `/sail` and
`/cruise` were never one switch: `/cruise` runs the same ladder and differs only at the stops, and
`.specify/cruise.json` already answered each separately — `park` on one *is* `/sail` for that stop. The
Voyage shows all four with what each answer means, says in a line which of them this run will stop for you
at, and writes a change through the project's own `scripts/agents/cruise.py`, which is what
`/cruise-settings` runs and what `make check-agents` holds. A captain reads it at its next boundary.

**The specification can be read from the page that asks you to agree to it.** Continue the build is a
person's word that the specification is good to build from, and the page asked for that word while giving
no way to open the file. It is beside the button now, quiet and in its own tab, served as the text the
agent wrote — the keel has no markdown renderer and does not grow one to show somebody a document they are
about to agree to.

**And the fleet can be stopped from the page it is watched on.** `make cruise-stop`, beside Cast off: it
asks rather than kills, so a captain finishes the stage it is on and leaves its worktree, its branch and its
deck log in a state the next cast-off picks up.

**`slipwai bridge install` puts the board on this machine: running, and in your dock.** A
browser will not let an installed page start a server, which is why the window shows "nothing is serving
the board on this machine" whenever nobody has typed the command. The other end of that problem is the one
that can be solved: this writes your own account's login service — a launchd agent on macOS, a systemd user
unit on Linux, a file in the Startup folder on Windows — and starts it, so the board is simply up — then opens the
board so the browser can put it in your dock, which is the half no command may do for you: an installed
page is a person's own gesture. No root, no daemon, no installer, and `slipwai bridge uninstall` removes
the service.

It obeys the one-board rule like everything else here: finding a board already serving, the service ends
rather than binding a rival, and says so at install time rather than leaving you to find out. `slipwai
bridge --serve` is what it runs — serve, open nothing, and do not insist the directory is a project yet,
because a login service starts before there is one and the page attaches anywhere.

**Catch-up:** nothing, and nothing is installed unless you ask for it.

**`slipwai upgrade` on Windows offered a project the release it already had.** The catch-up notes are read
from `CHANGELOG.md`, whose entries are headed `## 2.0.0 — MINOR` — with an em-dash. The file was read in
the machine's locale encoding rather than as UTF-8, so on Windows that heading arrived as
`## 2.0.0 â€" MINOR`, no entry matched, every released version looked unreleased, and the release in flight
was offered a second time on top of the entry already in the changelog.

Nothing was lost and nothing was skipped — the notes were duplicated, not dropped. The read names its
encoding now, and the test that holds it forces a non-UTF-8 locale in a subprocess, so it is proved on
every platform rather than only on the one runner that happened to say so.

**Catch-up:** nothing. Run `slipwai upgrade` again if the last run's notes repeated themselves.

**`/drive` is `/sail`.** One command runs the whole ladder, and the word for it is now the word the rest of
the vocabulary is in: a harbour, fairways, marks, berths, a captain, a telegraph — and a car.

```
/sail                     every ready slice of every fairway nobody holds
/sail fairway=booking     one lane
/sail BOK-01              one slice
```

`/sail` and `/cruise` are a pair, and the pair is the point: somebody is at the wheel, or nobody is.
Everything named for the old word follows it — `commands/sail.md`, `commands/sail-settings.md`,
`.specify/sail.json`, `scripts/agents/sail.py`, the eleven standing briefs (`sail-decide-skipper` and the
rest), and `SLIPWAI_SAIL`, which still replaces the whole command and still takes `<slice> <fairway>`.

The guide page about running unattended was called *Let it sail*, which would now name the mode it is not
about. It is **Let it cruise**, after the command it actually opens with.

There is no alias. A command with two names is two things to keep in step, and the whole of version 2 is a
break anyway — the one release where a rename costs nothing beyond reading this line.

**Catch-up:** `slipwai migrate` writes the renamed files and removes the old ones. A project that scripted
`SLIPWAI_DRIVE` renames the variable; nothing else in a generated project refers to the old name.

**The context answer is always written down, one context included.** A headless `/launch` once charted a
31-slice feature as one fairway with no seam test, no seam table and no decision entry. It wrote "one
context, so one fairway" into the split, and every slice queued behind one captain. The chart's pass one,
and Step 9 of the event model, now always record their answer as the next entry of
`specs/<feature>/decisions.md`. The entry is headed *Which bounded contexts does <feature> touch?* and
carries the seam table under its `Options`. A context of more than twelve slices also gets a `Why not
split:` line that cites, by requirement, the invariant spanning its groups. The count asks for that reason
to be written. It never asks for a split.

**With nobody present, the run proceeds and asks.** A session a script dispatched (`SLIPWAI_STAGE` set) no
longer takes its own proposal as confirmed. It proceeds on it, records it as `Decided by: host (stage
recommendation)` with the new `Status: awaiting human confirmation`, and posts a `question` line carrying the
entry's `D<n>`. The board's *Waiting on you* now shows open questions, so the question appears there. A
person confirms by setting the entry to `confirmed by human <date>`, which `check-decisions` accepts.

**`check-chart` refuses fairways nobody explained.** A chart with fairways and no context decision is
refused, and so is a decision with no seam table, or a fairway over twelve slices with no `Why not split`.
Each refusal says what to write.

**A stream states its invariant.** A stream is one expected-version check, and naming it after the spec's
noun ("one record per leaver") decided the feature's shape before any seam test ran. The model's new
`streams` block gives each stream a `because`, by requirement. `check-model` refuses a state-change slice
at `modelled` or later whose stream has none (`stream-states-its-invariant`). `nine-steps.md` now
interrogates every stream before naming it. It looks first for invariants that span groups of slices, which
keep them on one stream, and treats "one record per X" as uniqueness or a view rather than a boundary.
`scripts/agents/model.py` tells its headless session to run all of Step 9.

**Catch-up:** `slipwai migrate` brings the new gates and pages. After it, `make verify` refuses any feature
whose chart has fairways but no context decision, and any placed stream with no `because`. Before
upgrading a run in flight, add a `## D<n> — Which bounded contexts does <feature> touch?` entry with its
seam table to each charted feature's `decisions.md`, and a `streams:` block to `docs/event-model/model.yaml`.
Each refusal names exactly what is missing.

**After a migration, the crossing report asks for the one chart `make chart` writes.** That command writes
a single `chart.yaml`, into the first feature directory that holds a slice record, and the chart covers
the whole model. The report used to owe a chart for every feature directory, which no project with more
than one feature can satisfy, and the command it named will never write those files. It now asks whether
the feature in flight has its chart.

**Catch-up:** nothing. Run `python3 scripts/check-crossing.py` again; a feature other than the one in
flight no longer owes a chart.

**`slipwai migrate` crosses a version 1 project instead of ending in a traceback.** Two faults, both of
them only reachable on a real repository, and both of them raised after the crossing had already done its
work — which is the worst moment to say nothing useful.

**A project with its own design system.** The style checker resolves every path it returns, and the crossing
replays inside a staging directory under the system temporary directory — which on macOS is reached through
a symlink, `/var` being `/private/var`. So a token file the project imports was "not in the subpath of" the
project it is in, and the verb ended in a `ValueError`. Both sides of that comparison are resolved now, and
the page the crossing writes names the file the way the repository spells it rather than where the disk
keeps it.

**A model table the merge left conflicted.** The crossing carries version 1's model roles over by rewriting
`.specify/models.json`, and read the merged file to do it — including when the three-way merge had left
conflict markers in it, which ended the migration in a `JSONDecodeError` naming no file. A conflicted table
is now a line on the catch-up page saying what was not carried and what to set by hand, the way a conflicted
`project.json` already was: one unreadable file does not take the rest of the settings with it.

**Catch-up:** nothing, beyond running `slipwai migrate` again if it stopped on either of these. It changes
nothing until it reaches the end, so a crossing that ended in a traceback left your repository alone.

**`slipwai search` and `slipwai install` work without being told where the chandlery is.** The default index
was derived from the keel's own forge URL, which produced a path that has never served an index — so every
command that reads the chandlery failed with *it is not a chandlery index* unless `SLIPWAI_INDEX` was set.

```console
$ slipwai search
  go            language  1.0.0  available  backends: go
  typescript    language  1.0.0  available  backends: typescript
  …
```

Where the keel lives and where the chandlery is published are two different things, and deriving one from
the other is what broke it. The default is written out now, and a test refuses one derived from the forge
again.

This is also what stopped the package repositories' CI fetching the family a framework is proved beside.

**Catch-up:** unset `SLIPWAI_INDEX` if you set it to work around this. A private channel still goes in
`SLIPWAI_CHANDLERY`, which is unchanged.

**The plan's gate holds its ticks and no longer its totals, so a slice branch can be green.** Two things of
different natures live in `docs/slipwai-2-plan.md` and only one of them survives concurrency.

A **Status cell** is per slice and disjoint: the branch that lands `10.1` ticks row `10.1` and no other
branch touches it. That is the same shape `check-slice-scope.py` already grants a slice over its own block
of `docs/event-model/model.yaml` — *every other slice's block reads exactly as on `main`* — and it merges
cleanly however many fairways are open.

The **`**Progress:` line** is one shared line every branch rewrites, because its totals count every slice
in the plan. That is exactly the conflict `changelog.d` was created to eliminate. Worse than conflicting,
it made the gate unpassable: a branch carrying one new `Slice-done:` trailer computes a different total
from trunk's, so `progress.py --check` went red, and the only way to green was to edit the one file every
other fairway was also holding.

So the totals stop being gated. They are rendered — like `docs/event-model/model.drawio`, which the host
regenerates after each merge. `make progress` still writes them. What is *held* to the history is the
ticks, which is what the plan is read for.

Found by running five fairways at once and watching every one of them go red on a line none of them was
allowed to own.

**Catch-up:** nothing. `make progress` is unchanged; only what `--check` refuses has narrowed.

**The guide has two map pages: the workflow and the board.** *The workflow* lists every step from a
requirements document to an accepted capability on one page. For each step it says who does it, what
starts it, what file it writes, and whether it stops for a person. It also describes the `upstream`
setting and how a message clears a park. *The board* describes every tab, card and control of
`slipwai bridge --serve`, and the file each control writes. *Let it cruise*, *the deck log and the harbour
log*, and *the fairway, the captain, the harbourmaster* now say what counts as progress for a captain, and
that the harbourmaster writes a park's receipt when a person tells the fairway something.

**Catch-up:** none.

**The hand reads the screens against what the project decided, and a design finding is now a verdict.** The
demo delegate looked at every screen already, but only for four named defects and only as a note: the brief
said a label, a colour or a layout was "never a reason to withhold acceptance". So the one rung that reads
`skills/web-interface-guidelines` was *Design review*, which is the session reviewing what it just built —
and under `/cruise` no person sees the screen before the next slice is built on it.

Where a slice has a screen and the hand reached it in a browser, it now puts each screen into every state it
can be in, screenshots each, and reads the screenshots against the approved mock state, `docs/design.md` and
the constitution's design notes, and `skills/web-interface-guidelines` — the project's own decisions winning
wherever they and a general rule disagree. A finding one of those covers is a `behaviour` verdict re-entering
at *Design review* with the screenshot. Two things are not: a finding the slice's `## Design review` record
already names with the reason it was left, which stands as recorded, and taste none of them speaks to, which
is still a `design:` note for the next slice. Where it could not drive a browser it says the screens were not
read, rather than letting the verdict imply they were.

Nothing else moved: the three verdict words, the demo log's shape and what `check-decisions` holds it to are
unchanged, and the hand still edits nothing.

**Catch-up:** regenerate to get the reworded brief — `slipwai upgrade`, or copy
`agents/sail-demo-hand.md`.

**The loop's memory travels, and `/sail` is what makes it.** `travel.py` has carried the deck logs, the
harbour logs and the in-flight slice branches between machines since it was written — one ref per writer,
nothing ever merged, a push that is not an append refused — and only `captain.py` ever called it. So a
person's `/sail`, a cloud session and a second machine each read the plans out of git and none of the
history, which is a project where nothing has been started: one run saw six slices as unstarted that
another machine had prepared that morning, rebuilt their work on trunk, and left eight worktrees nobody
could reach. `make arrive` lands what other machines wrote and `make depart` pushes what this one
did; the ladder runs the first beside its own `git fetch` and the second at every boundary it already has.
The harbourmaster now calls the same two functions, so the credentialled process and a plain session
cannot travel by two different rules.

**A session is told when it cannot run the method, instead of discovering it.** The delegate types are
derived from `agents/` into each harness's own directory, and git ignores those — correctly, since they
are a second copy of a committed source — so a fresh clone has none and a session there reads a ladder
built on delegates with nothing to call. `scripts/agents/project.py --check` passes on that by design, and
cannot do otherwise: it cannot tell a clone nobody will run `/sail` in from one somebody is about to.
`make preflight` can, because it runs when a slice is about to start, so it now asks two more
questions — are this harness's delegate types projected here, and does this harness have sub-agents at all
— and `scripts/agents/harness.py --can-delegate` answers the second from the registry. Thirty of its
thirty-six rows cannot delegate, so that answer is recorded and never failed; a missing projection is
failed, and names `make agents`.

**What was dispatched is written down at the moment of dispatch.** `make dispatch` records one line
per slice in `.slipwai/dispatch/<feature>.jsonl` — the slot, the worktree and the delegate, or
*taken-here* and *left-named* with the recorded reason this session could not delegate. Committed, unlike
the deck logs, because it is evidence about a commit and the gate that reads it runs on a checkout holding
only what git carries. It will not write a line without a current `preflight --record`, so a run that
skipped the check has nothing to dispatch with rather than a judgement to record.

**The crossing's own catch-up is taken, not asked for.** A slice that shipped before the mark log existed
set nothing in it, so everything steering by its marks reads as blocked for ever —
`clearance.py` calls that `migration-evidence-required` rather than `blocked` for exactly that reason.
`make dispatch` now takes the baseline when it sees that state, re-reads clearance, and records a
`baselined` line in the ledger so the run says what it stood on. Safe to automate for the reason it was
safe to write down: it derives from the done markers already in the tree, stamps every line
`provenance: baseline`, and refuses a second baseline outright, so automating it cannot turn it into a way
past the gate. `make hooks` is the same shape — idempotent, never takes a path somebody else owns — so
`make dispatch` depends on it and every clone, worktree and cloud runner gets it without being asked.

**And one gate holds whoever is driving.** `scripts/check-dispatch.py` reads commit subjects up to their
first colon and refuses two things: a slice-shaped token no chart, event model or `slices/` directory
knows, and a planned slice no dispatch ledger accounts for. It is on `verify` and in a `pre-push` hook
that `make hooks` installs, because every other rule in the method is one a session has to choose to
read — the command page is prose, `verify` runs when something runs it, and the session-start guards reach
three of the registry's thirty-six harnesses. Git reaches all of them. Decision ids (`D49`) and task ids
(`T018`) are excluded by shape, and a project with no plan at all — an adopted repository before its first
chart — is not held.

**The hook path is set by the thing that makes the checkout.** `core.hooksPath` is per-checkout git
config, so it travels with no clone, worktree or cloud runner — which would have left the one rule that
holds whoever is driving installed nowhere, the same shape as the bug it catches. Generation sets it, and
`slipwai migrate` sets it for a project that predates the hook. A path somebody else owns — husky,
lefthook, an adopted repository's own — is reported and never taken.

**And `make crossing` asks what a migration could not carry.** The merge carries the files; it cannot
carry the state those files are about. One project migrated cleanly and twenty minutes later had a chart
covering the first of its two features, eleven slices still `modelled` that were built and merged, a log
ref the design names and nothing had ever created, and no hook path — and had passed every gate it had.
`scripts/check-crossing.py` asks the six questions out loud: a chart per feature, every slice folder named
in one, statuses against trunk, a mark recorded for what already shipped, somewhere for the logs to
travel, and this checkout's hooks. A report by default, `--strict` to fail, because a project mid-crossing
is not a broken project and a command that refused to run is one nobody runs twice.

**Clearance refuses a feature it cannot answer for.** It takes the first feature with a chart, so a
project with two features and one chart answered for the charted one *whatever it was asked about* — and
a `/sail` on the uncharted one read every slice of the other feature as queued or blocked and took that
for *nothing may start*. A named feature with no chart is now `cannot schedule`, naming what is charted;
answering for one feature of several says which it is not about.

**Catch-up:** `slipwai migrate` carries `travel.py`, `preflight.py`, `harness.py`, the new
`scripts/agents/dispatch.py`, `scripts/check-dispatch.py` and `scripts/check-crossing.py`, rewrites
`commands/sail.md`, adds `check-dispatch` to `verify`, and points this checkout at `.githooks`. **Run
`make crossing` after it** for what no command can take for you — a chart per feature, statuses against
trunk. CI holds the push rule for every push a local hook never sees. A project whose
shipped slices predate the ledger will have `check-dispatch` refuse a commit naming one: either the slice
is already merged and the commit is prose about it (no slice-shaped token before the colon), or record
what was dispatched. A feature with no `chart.yaml` is unknown to both gates — `make chart` first, or its
slices read as work no plan knows.

**The matrix no longer plans a row that generation will refuse.** Its store, identity and production rows
were written out for every backend, and every real language implements both stores, Keycloak and a cloud
target — so nothing noticed. A package that implements none of them had four rows planned against it whose
own refusals read *a half-ported version is deliberately not emitted*.

A row is planned only where every answer it names is implemented for that backend and offered under that
target — the same two questions generation already asks before it refuses. A row that cannot generate is
not a failing matrix; it is a matrix written down wrong, and the two look identical in a CI log.

Also: an image builder whose tool a package names itself — `image_builder`'s `tool` is the package's own
word — is skipped with the tool named, rather than ending the run in `KeyError`.

**Catch-up:** nothing. A package that implements fewer options than the published six now gets a shorter
matrix instead of a red one.

**The first drawing of the surfaces is styled.** Plain unstyled wireframes were turned down for having no
style, on two projects out of two, and the redraw that bought cost ten times the drawing. Where
`docs/design/` hands over no direction, the drawing now sets a short one first — a few tokens, one shared
`mockups.css`, only the components the surfaces use — and `research.md` says it is a proposed look for
reviewing the flow, not a brand. Where `docs/design/` has a direction, it is followed as before.

**A storyboard is checked as a sketch, not as the product.** In the mock-up stage each surface is rendered
at most once per pass, in one theme, to catch a broken layout; there is no render-and-tweak loop, no light
and dark pair and no phone-width sweep unless the specification makes mobile primary. The storyboard embeds
or links the surfaces and makes no screenshots or thumbnails. Production-grade visual review still happens
where it always did, before a slice that builds the surface is demonstrated.

**The drawing has a budget, and is ended at it.** Fifteen minutes for a first drawing and ten for a redraw,
scaled by the telegraph's `stage_scale` (a `surfaces` or `surfaces-redraw` row in `harbour.json` overrides
either). The session is told its minutes and when they run out, so it plans to them; at the end of them
`make surfaces` ends it and every delegate it started, keeps what it drew, and says so in one line. Something
drawn is a storyboard to review, so that run exits 0; nothing drawn still exits 1. While it draws, the
board's Storyboard step says how far in it is: *drawing: 6 of about 15 min*.

**A redraw answers its reason and nothing else.** It reuses the design direction and stylesheet it has,
changes only what the reason concerns — a reason about the look is a change to the stylesheet — and is held
to the same checking and budget. A redraw that only restyles now counts as a redraw.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/surfaces.py`, `scripts/agents/harness.py`,
`commands/mockups.md` and `skills/storyboard/SKILL.md`. Nothing to change in `harbour.json`: the defaults
apply where it has no row for the drawing.

**The event-model stage says it is a modelling conversation, event first.** That is the line under Event model on the voyage, before a slice has been named.

**Catch-up:** nothing. The next voyage this board serves says it.

**Every generated page now describes the rung each service is actually on, and a mixed project's pages
carry both.** The last change made the keel *give* each service the files its write model names. This is the
other half: what the pages then say, which is the half a person and an agent act on. A service handed a
repository port and a versioned state table was no better off while `AGENTS.md` told whoever worked in it
that the event store is a driven port, `docs/architecture.md` promised a replay, and
`docs/event-modeling-to-code.md` showed one table — the first service's — for the whole project.

`docs/event-modeling-to-code.md` is now a section per service. The event-sourced one keeps the table it
had, with a Decider row made explicit; the state-stored one says a load through the repository port, a pure
decide over current state and a save at the version that was read, gives `stream` as the row one
transaction locks, and refuses `guard` and `folds` by name with the reason, so the first slice written
against that service finds out here rather than at a gate. `README.md`, `AGENTS.md`,
`docs/architecture.md`, `docs/whats-included.md`, `docs/gates.md`, the `/gaps`, `/adversary` and
`/constitution-coverage` command pages, `/sail`'s event-model rung and the pull-request template all read
the same way, and the store's own sections say which race their project's Postgres can actually lose — a
`(stream_id, version)` constraint on the log, a save at the version the state was read at on a row.

**Catch-up:** `slipwai migrate` rewrites these pages, and a project whose services are all event-sourced —
which is every modelled project generated before `write-model` existed — gets back what it had, bar two
sentences that stopped being true when the profile stopped deciding the rung. A project on the standard
profile gains nothing here: it has no model and therefore none of these pages.

**A language now answers both rungs, and the suite makes it prove it.** The keel has been giving a
state-stored service the rows under a backend's `state` key since the rung became an axis; what was missing
was the other half — the page that says what a backend owes, and the check that says when it has not paid.

- `write_side_files` and `read_side_files` are contracted with their `state` block: the repository port,
  its adapters per store, and the migration for a versioned state table, keyed by the same features as the
  rows above them, because the rung does not settle which store was chosen.
- `event_store_directory` is now `persistence_directory`. The store on the state rung holds current state,
  so the old name sent a reader of the generated prose looking for a log. Both names are read, the new one
  first, until 2.1 — a package answering only the old one loads, generates and passes its suite.
- `event_model_paths` answers `repository` beside `events`, `domain`, `usecase` and `test`: the port a
  state-stored service loads and saves through. Unanswered, the keel fills it from the decision's own path
  for one MINOR rather than leaving a hole in `docs/event-modeling-to-code.md`.
- `service_files`'s `event` parameter is deprecated. It says the project is on the modelled profile, which
  was all a backend had to go on when Event Modeling and event sourcing were one answer; the write model is
  per service and is `selection.option("write-model")`. The signature does not change.

`slipwai package check` generates the richest profile once more at `--write-model state`, so a `state` block
naming an asset the package never committed is a finding rather than a project with a hole in it, and names
the gap per store where a backend has written no block at all.

**Catch-up:** nothing to do in a project. For a language: rename the one answer, add the `state` rows and the
`repository` path, and run the suite — it names each of the three if you miss one.

**The six worked quickstarts are carried by the keel, so every copy has them.** They were published in
`docs/reference/` — a manifest, the page explaining its answers, and a version each — and they were in no
channel's index and in nobody's `~/.slipwai/quickstarts`, so the only way to meet one was to know the path
to it inside a checkout. `slipwai quickstart list` said *no quickstart is saved here*, the terminal
interview asked nothing at all, and the board's Packages tab showed a Quickstarts table with no rows in it,
on every machine in the world. They are now read from beside the keel, which is where a wheel, a source
distribution and the frozen command can all find them.

So `slipwai quickstart list` names all six, `slipwai quickstart show <name>` and
`slipwai generate <name> --quickstart <name>` take any of them by name with nothing installed first, and
both interviews offer them before their first question — greying out the ones this machine cannot carry
out yet, with the line that fetches what each wants. On the Packages tab they are rows marked `built in`,
each with its own sentence about the product it suits. A quickstart you save under one of those names is
still yours: a saved one wins over a carried one.

**And the board's own interview offers them too.** The page asked every question from the catalogue and had
no row for a quickstart at all; it has one now, in the place the terminal puts it, from the same menu. The
answers a chosen quickstart gives are filled into the questions below it and every one of them is still
yours to change — a quickstart is a default, which is the same thing it has always been at the prompt.

**Catch-up:** nothing. The quickstarts arrive with the keel.

**Whether a service's truth is its log is now that service's own answer.** `project.json` has recorded
`eventSourced` per deployable since it was written, but the keel set it from the profile — so every
service of a modelled project claimed the log and no service of a standard one could, however the product
was actually built. `write-model` became an axis in the last change; this is the keel reading it.
`eventSourced` is now `write-model: events` for the service that was asked, `state` for one that never was,
and `false` for a browser app and for an application the keel did not make — never `events` by detection
alone, because a log nobody vouched for is a guess wearing a fact's clothes.

What a service is *given* follows the same answer. A backend declares its event-store rows as it always
has, and the state-stored rung's rows — the repository port, its adapters, the migration for a versioned
state table — under one `state` key beside them, so a service answered `state` is given those instead. A
backend that has written no `state` block answers such a service with nothing, which `slipwai package check`
is what names.

**Catch-up:** nothing for a project whose services are all on one rung, which is every project generated
before this: the default answers still generate what they generated. `slipwai migrate` rewrites
`project.json` either way, and a mixed project is a thing you can now ask for.

**`make check-model` reads the rung the slice's service is on, so a state-stored service is held to the
write model it actually has.** The gate had one reading of a slice's write side, and it was the
event-sourced one: a planned state change named `stream` *or* `guard`, `folds` was the history a Decider
rehydrates from, and a `live` state-view owed a `liveBudget`. On a service that keeps current state, two of
those describe machinery it was never given and one bounds a fold it does not do. The first slice written
against such a service found that out at a gate, or did not find it out at all.

Both halves of the gate now read `eventSourced` off `project.json` per deployable — `check.py`, which
`make check-model` runs, and `validate.ts`, which the render pipeline runs — and give identical verdicts:

- **`stream` is required at `planned` on both rungs**, and means the row or aggregate one transaction
  locks, with its version, where it meant the stream an append carries an expected version of.
- **`guard` is refused by name** (`guard-needs-a-log`): a boundary drawn over a tag query needs a log to
  query, and the refusal names `stream` as what this service's boundary is instead.
- **`folds` is refused by name** (`folds-need-a-log`): there is nothing to replay, and the refusal says
  what the decision does instead — loads what the service holds, decides, saves at the version it read.
- **`liveBudget` is not asked**, there being no fold to bound. `materialisation` keeps all three words.
- `model-matches-code` is unchanged. An event is a file on either rung.

A service the manifest says nothing about reads as state-stored, which is the `write-model` axis's own
`absent` and the honest reading of a service nobody vouched for.

**Two naming rules, on either rung.** `event-is-not-crud` refuses `Created`, `Updated`, `Deleted`,
`Changed` and `Modified` as the verb of an event — it names what the table did, not what happened, which
Dudycz calls *property sourcing* and which is the way a reverse-engineered model most often goes wrong.
The refusal proposes the shape of a better name. A frame that honestly is a field update — a CMS page, a
setting — says `crud: true` with a `because`, and the `because` is required, because unstated it is the
exemption everything gets. `event-is-not-negative` refuses `OrderNotShipped` for the failure underneath it
(`ShipmentFailed`, with a `reason` attribute), and is written to leave `UserNotified`, `AccountUnlocked`
and `ItemUnpacked` alone. The Good / Bad / Why tables behind both are in
`skills/event-modeling/references/naming.md`.

**The rung stays invisible to the division of work.** `chart.py` names none of the fields that move, and
`tests/test_rung_gate.py` holds it to that: the rendered chart of a two-slice model is the same whichever
rung either slice is on. `docs/event-model/README.md` gains the table saying which three fields those are.

**Catch-up:** a project whose every service is event-sourced is held to exactly what it was, bar the two
naming rules — which are new on both rungs, and which an existing model may fail. A failing name is a
rename of an event the model has, and on the event-sourced rung an event already raised keeps the name it
was raised under: the new name goes on new events.

**Event sourcing is the default and the recommendation, and the prompt now says so.** Phase 15 split the
model from the log so that a product wanting one without the other could be generated at all. Nothing in
that split makes the two rungs equals at the question, and the prose had drifted into presenting them as
if it did. They are not equals, and the reason is not storage: the log is the contract between slices, so
a later slice reads an event without asking the service that wrote it and without the two being planned
together — which is what makes a slice independently deliverable — and a read model nobody thought of is
a replay away rather than a migration, which is what keeps a design reversible after it turns out wrong.

So `--write-model events` is stated as the recommendation wherever the question is asked: the axis's own
prompt and both option labels, `docs/guide/start-here.md`, and `docs/event-model/README.md`. `state` is
named for what it is for — a small supporting domain, a context that honestly is field updates, a service
whose past nobody will ask about — and is to be recorded with its reason, because a rung nobody justified
is the default. The default answer itself has not moved: Enter has always given `events`.

**A state-stored project stops receiving the event-sourcing skill.** `event-sourcing/SKILL.md`,
`event-modeling/SKILL.md` and `global-event-model/SKILL.md` each declared both `event-modelling` and
`event-sourcing`, and `serves()` is any-match, so all three shipped to every modelled project. The
sourcing skill declares `event-sourcing` alone now and the two modelling skills declare `event-modelling`
alone, so a project whose every service keeps current state gets the model and not a guide to rehydrating
a Decider from a log it has not got. A mixed project still gets all three: one service on the log is
enough for the project to carry the capability.

**The `event-modelling` constitution's Principle III is about the rung.** It was *Event-Sourced Core with
the Decider Pattern* and read as though every service were on that rung; it is *The Rung Is Recorded Per
Service, and Event Sourcing Is the Default*. The recommendation is stated as the recommendation, the
exception is named and has to carry a reason, and both rungs' rules are written out — including that a
slice on a state-stored service may name no `guard` and no `folds`, which is what `make check-model`
already refuses, so the constitution and the gate say one thing rather than two. Principle II's *a
command MUST check the event stream* reads *the write model*, which is the rule it always meant.

**The Foundational tasks branch on the rung.** T017, T019 and T022–T027 are the event-sourced rung's, and
each has a state-stored twin beside it: a repository port returning the version it read, a state table
whose `version` column is the concurrency control, an adapter turning a zero-row update into a conflict,
the same shared contract suite, and the same real-store race. T023's twin is the one that is not a
mirror — there is no append-only trigger on a table updated in place, and what goes in its place is the
outbox write in the same transaction as the state write, because the events a state-stored service raises
are lost otherwise on exactly the failure that matters. The plan template names the rung in its own field
rather than assuming it in *Storage*.

**And the modelling skill writes a role catalogue.** `docs/event-model/actors.yaml`, in Phase 1, for
every project: each human role and system actor with what it does and — the part nothing else records —
what it **cannot** do. A slice's `actor` says who acts; there was nowhere to say who may not, and a
negative permission is the first thing both a security pass and an access classification ask for.

**Catch-up:** `slipwai migrate` rewrites the constitution template and the presets. A project whose every
service is event-sourced keeps every obligation it had, with Principle III saying more than it did; one
with a state-stored service gains the rules that service was always subject to and nothing had written
down.

**The board's Slices step turns red only for what actually holds a slice up.** A note one session leaves another (`For L02's captain, from L06's: …`) is no longer listed under *Waiting on you*, and unread decisions below the decision ceiling are listed for reading without turning the step red.

**Open spec shows the specification, not its markup.** The button beside Continue the build served
`specs/<feature>/spec.md` as `text/plain` — a wall of hashes and asterisks in a browser window, which is
the format for a machine. Being asked to say a document is good and handed its source is being asked to
agree to something nobody has shown you.

It is rendered now, in the board's own shell, titled by the document's own first heading. The renderer is
the keel's own and about a hundred lines: no markdown library ships with this, and what has to be rendered
is not the whole of CommonMark but what `/draft` and `/mockups` write — headings, both kinds of list and
their nesting, tables, rules, fenced code, and bold, italic, code and links inside a line. Everything the
document says is text: a tag in the source is shown, never run.

**On the state-stored rung an event is modelled always and published only where something reads it.** The
rung shipped telling every state-stored service to build an outbox in the write's own transaction, which
is real infrastructure erected to notify nobody in exactly the case the rung exists for: a small
supporting domain, a context that is genuinely field updates.

Three things were being carried under one word. An event as **notation** — a fact on the timeline — is how
a slice is found at all, costs nothing at runtime, and belongs on both rungs. An event as **truth** is the
log, which is the other rung by definition. An event as a **published contract** is machinery, and it is
earned by a subscriber: a `reads` from another service, or a read model whose `materialisation` is `async`.

So T023's state twin is now skipped until one of those exists, `docs/event-modeling-to-code.md` says the
same of `evt`, and the `pcr` row says what it always should have: with no stream to subscribe to, two
slices in one state-stored service are linked by a call the use case makes. Principle III carries both
rules. And where the project already publishes somehow — an outbox, a bus, change data capture — the slice
uses that one and records it, rather than adding a second way of doing what the codebase already does.

Nothing changes on the event-sourced rung, and nothing changes about the timeline: every `evt` is still a
fact the model names.

**Catch-up:** nothing. A project that already built an outbox has one that works; this changes what the
next slice is told to build.

**The specification, the storyboard and the event model can advance on their own.** Each of those steps ends at
a stop: the board shows what was made, and a person presses the next step's button or approves the
storyboard. A new stop on the board's Settings card, *The specification, storyboard and model*, switches
that between **stop for me at each**, which is what a project does today and stays the default, and
**advance on their own**. Advancing, the board draws the storyboard once the specification is drafted,
approves the storyboard once it is drawn, models it on an event-modelling project, and continues the build,
each as the step before it ends well. A step that failed, a disapproved storyboard, and anything the board
is already running each stop it as before.

An approval given this way says so: the first line of `mock-states.md` names the setting, so a verdict the
board gave can be told apart from one a person did. It is `upstream` in `.specify/cruise.json`, and
`python3 scripts/agents/cruise.py --set upstream=advance` sets it from a terminal.

The board advances when it is polled, which every open board window does every few seconds; with no window
open it waits until one is.

**Catch-up:** none. A project whose `.specify/cruise.json` has no `upstream` reads it as `park`, and its own
`make check-agents` still passes; setting it writes it in.

**The Voyage keeps itself current, and the stage between a specification and a model has a button.** Two
faults in one window, both found watching a real run stop with nothing to press.

**The page went stale.** Its poll repainted the strip and gave up the moment nothing the board had started
was running — and the stages that move a project on are run in the agent, by a person, which the board is
never told about. Worse, the cards are rendered once: the specification landed under an open window and the
Open spec button, the storyboard, the model and the work were all still drawn from the files that were
there when the window opened. The poll now carries a signature of what the page was built out of, slows to
every eight seconds when nothing is moving rather than stopping, and reloads the window when the signature
says the page is built from different files than the ones it was drawn with.

**Draw the surfaces**, beside Continue the build, runs the half of the mock-up review nobody has to be
present for: `make surfaces` (`scripts/agents/surfaces.py`) starts one headless session with
`commands/mockups.md` as its rules, which researches the surfaces the specification implies, draws a
wireframe for each and storyboards them — and stops there. Nothing is marked approved by a session nobody
was in: the verdicts are what the stage is for, and `/mockups <feature>` in the agent walks a person
through them with the drawings already in front of them. The button is gone once there are drawings,
because what they wait on then is a person. The strip says so too — surfaces drawn and no verdicts written
now reads **Waiting on you** rather than *to do*, which is what it said while a person was the only thing
holding the project up.

**Catch-up:** `slipwai migrate` carries `scripts/agents/surfaces.py`, the `surfaces` Makefile target and
`commands/mockups.md`'s dispatched half into an existing project. The board's own change needs no
migration — but a board kept running by the login service is still serving the code it started with, and
`slipwai bridge install` restarts it.

**The page a reader starts on now shows the two questions it always meant to ask, and says which of them
cannot be walked back.** `docs/guide/start-here.md` showed one interview with one storage question on it —
`Event store` — under a profile prompt whose own paragraph said *the first question is the one that
matters, and it is the only one that is hard to undo.* That was true while choosing Event Modeling chose
the log with it. It is not true now: `Use Event Modeling?` decides whether the workflow is drawn before it
is built and can be answered later, and `Write model` is the storage decision, asked per service, and the
one that cannot be reversed. The transcript shows both questions with the words the interview actually
prints, and the paragraph underneath names the irreversible one.

**A package built before the rung was an axis is read onto the rung it was built for.** Renaming
`event-store` to `persistence` was only half the courtesy. `write-model` has `state` as its `absent`, and
an axis no loaded backend answers falls to its absent — so a language package that knew only `event-store`
would have gone on shipping event-store adapters while every project generated with it recorded
`eventSourced: false`. It is now read as answering `write-model: events`, and only that rung; the
state-stored rows are what a package adds when it is rebuilt on the protocol that has them.

**`/run` describes the store the service was actually given.** Its *Seed it* paragraph was keyed on the
store alone, so a state-stored Postgres service was told to migrate its event store and a state-stored
SQLite one was told that deleting the file deletes the entire truth of the system. It is keyed on the store
*and* the rung now: two services on one store and one rung still say it once, two services on one store and
two rungs say it twice, and `make migrate`'s comment names no rung, because it is one target applying
whichever migrations the rung put there. The `sqlite` block of `.env.example`, `/ready`'s readiness line
and the integration-test comment in the Makefile read the same way.

**Catch-up:** `slipwai migrate` rewrites these pages. A project whose every service is event-sourced gets
back what it had, bar the sentences that stopped being true when the profile stopped deciding the rung. The
`persistence` prompt's SQLite and Postgres labels say what each store is on each rung, and
`assets/targets/{aws,azure}/service/main.tf` stop telling a reader to run `./init --event-store memory`, a
flag that was renamed with the axis.

**Uncommitted changes on trunk no longer stop a voyage.** In a harbour with no remote, a slice that had passed
its full gate was refused at the merge whenever the person's own checkout sat on trunk with any edit in it —
even an edit to a file the slice never touched. The refusal was not one a berth could fix, so the fairway
parked behind finished work and nothing told anyone. The harbourmaster now fast-forwards around the person's
changes, which git does whenever the merge does not touch the same files. Where it would, the checkout is
detached exactly where it stands, with its working tree and index untouched, and trunk moves on anyway. The
`granted` line's `note` says so, and how to get back: commit or stash, then `git switch main`.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harbourmaster.py`. A fairway already parked
by this refusal is cleared with `python3 scripts/agents/harbourmaster.py --clear <fairway> --parked <timestamp>
--what 'merge again'`.

**The voyage shows the screens a slice has actually rendered.** Photographs written under
`specs/<feature>/slices/<id>/design/` appear on the Voyage page as they land, grouped by slice and labelled
to do, working, waiting on you or done. A feature's mock-ups sit beside them, each picture opens at full
size, and where `project.json` records a browser app the page links it. The page reloads when a photograph
appears or is replaced.

**Catch-up:** nothing. The page reads the photographs the design review already writes.

**The interview asks who signs in to the product, once, instead of asking about internal and external
identity separately.** Two axes carry identity — `auth`, the people who run the product, and `users`, the
people it is for — and a product with a staff console behind one issuer and customers in front of another
genuinely has two answers. Both were nevertheless asked of everybody: two prompts a paragraph apart, worded
alike, each offering the same list of providers. Most projects have one login and one set of people, and
for them that was a question with no right answer — picking the same provider twice looked like a
formality and was in fact a request for two realms.

The question is now *Who signs in to this product?*, with three answers: **everyone**, through one identity
provider, which asks once and settles the external axis; **staff**, people who work here and nobody else,
which asks once and settles the internal one; and **separately**, which is the pair, asked exactly as
before. The provider question that follows is headed in the words the answer earned — "Authentication" for
one set of people, "Internal authentication" and "External authentication" for two. Both faces of the
interview ask it: the terminal and the board.

Nothing downstream learned a new word. `--auth` and `--users` are still the flags, still take the same
answers, and a scripted `slipwai generate` is unchanged; a quickstart still answers both axes and the
question shows which of its three shapes that pair is. What the answer settles, it settles for both — the
axis nobody was asked about is written down as having nobody on it rather than left to a default.

**Catch-up:** nothing. This is the interview only; an existing project's answers are untouched, and
`./init` changes either axis as it always did.

**On Windows, the board no longer interrupts itself when it asks whether a captain is running.** It asked
with `os.kill(pid, 0)`, and signal 0 on Windows is a Ctrl-C to every process on the console — the board,
and whatever started it, ended with a `KeyboardInterrupt` whenever the Voyage checked for a running fleet
or a model session. Both checks now ask Windows through the process handle, as `fleet.py` already did.

**Clearance prints its whole answer when its output is piped on Windows.** The `slots:` line carried a
minus sign and a `≤` that a Windows pipe's encoding has not got, so the print raised after the first line
and every slice line after it was lost — which is what a captain and the board read. It says `-` and `<=`.

**Two runsheets are back**: [generate a new project](docs/guide/runsheet-generate.md) and
[adopt an existing repository](docs/guide/runsheet-adopt.md), every step in order with where to type it
and how you know it worked. The README, the start-here and first-feature guides and what is new now
describe the board's Voyage tab, starting from a requirements document, and the interview's last two
questions.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/clearance.py`. The board's fix needs
nothing; a board kept running by the login service is restarted by `slipwai bridge install`.

**On Windows the catch-up page is UTF-8, and `make dispatch` prints its ledger lines.** `slipwai migrate`
wrote `.slipwai/catch-up.md` in the machine's own encoding, which on Windows is cp1252, while `/catch-up` and
the archive read it as UTF-8 — so the first em dash on the page stopped both. It is written as UTF-8 now.
`make dispatch` printed each worktree after a `→` a Windows console cannot show, and stopped there with the
ledger written and nothing said; it prints `->`.

**Catch-up:** a catch-up page written on Windows before this version may not read; run `slipwai migrate` again
to write it afresh.

## 1.5.1 — PATCH

**The standalone executable starts again.** 1.5.0 was tagged but never published: its release job's smoke test
found that the executable built from it stopped at `ModuleNotFoundError: No module named 'platform'`. slipwai
loads the tool installer (`scripts/install-tools.py`) from its bundled assets at run time, so PyInstaller never
saw the standard-library modules it imports; they are now named in the build, and a test holds that list to the
installer's imports. 1.5.1 is the first release with everything 1.5.0 describes.

## 1.5.0 — MINOR

**What you choose in `slipwai generate` or `slipwai adopt` is installed for you: there is no follow-up install
to run.** Where the answers need a tool the machine lacks, slipwai installs it: Git, Make, uv and Python for the
setup; the toolchain of each language the project builds in (Node, Go, a JDK); a cloud's CLIs under `--target
aws|azure`. It uses the package manager the machine has — Homebrew or MacPorts; apt, dnf, pacman, zypper or apk
through `sudo`; winget, Scoop or Chocolatey — or the publisher's own download where a distribution's package is
too old to build with (Node, Go and the JDK on Linux, uv from its GitHub release). It does this wherever the
questions are answered at a terminal; `--install` asks for it from a script, `--no-install` turns it off, and
`SLIPWAI_NO_INSTALL=1` turns it off everywhere, naming each missing tool instead. The installer is one file,
`scripts/install-tools.py`, which every project now ships and slipwai itself loads, so `./init` on a
teammate's clone installs uv the same way instead of printing the line.

**`generate` and `adopt` ask which coding agent, with nothing preselected.** Spec Kit's own list highlights
GitHub Copilot, and Enter there chose it. `generate` asks among its questions (or uses the agent it runs
inside, or `--integration`); `adopt` (experimental) asks where the tree reads for more than one agent, and
records the answer in the adoption commit.

**Extensions install what they need.** CodeGraph runs its pinned CLI through `npx`, installing Node where it is
missing, and indexes only the project: it no longer runs `codegraph install`, which rewrote every agent's
global config (`~/.claude.json`, `~/.claude/CLAUDE.md`, Cursor's, Codex's, VS Code's). UI/UX Pro Max and the
UX gates, ticked before there is a browser app — an adopted repository whose frontend is still a candidate
(experimental), or a headless project — are recorded and wait, and install themselves once a browser app is
confirmed or added; before, they refused and asked for `slipwai add-frontend` and a second `./init`. The UX
gate installs Playwright's Chromium the first time it has Playwright and no browser. On Windows, where the
checkbox list cannot be drawn, `./init` asks for the extensions as a typed question in the console instead of
skipping the choice silently.

**`slipwai generate` in an empty folder makes that folder the project.** Its name is offered and nothing is nested
beneath it, so the agent started in the same folder finds the project's commands — the first real run made
`slipwai-test/test`, and Claude Code started in `slipwai-test` found none. Elsewhere a new folder is made, as
before, and the closing line says where to start the agent.

**What a Mac ships is accounted for.** A `python3` below 3.10 — Apple's 3.9 — counts as missing and is replaced
through Homebrew's `python`, the formula that links `python3`; Node below 22.13 likewise. `./init`, Spec Kit's
scripts and a generated project's `make verify` are checked under bash 3.2 and GNU Make 3.81, what macOS
ships. On Windows, slipwai's own output is UTF-8 wherever it is redirected: a piped or logged `generate` stopped
with `UnicodeEncodeError` on the first `—`.

**Smaller:** `slipwai adopt --next` (experimental) says `make verify` once the root Makefile includes the
delivery one, not `make -f delivery/Makefile verify`; `slipwai status` and `slipwai --next` answer the same
question instead of printing usage; the event-model check installs PyYAML with uv where pip is missing.

**Catch-up.** `slipwai migrate` brings `scripts/install-tools.py` and the new extension scripts. If CodeGraph was
adopted before this release, its old installer may have written global agent config: review `~/.claude/CLAUDE.md`
(which Claude Code loads in every project) and the MCP entries it added for tools you do not use.

## 1.4.0 — MINOR

**`slipwai generate` runs the project's `./init` as its last step, and every missing tool is named with the
command that installs it on your machine.** Answering the questions at a terminal now ends the way
`slipwai adopt` does: `./init` runs from inside the new project, so Spec Kit and the agent's skills are in
place without a second command. `--integration <agent>` passes the agent through; `--init` asks for the run
from the argument form, which otherwise leaves it as the next step as before; `--no-init` skips it anywhere.

The machine is now detected — macOS, Linux, WSL or Windows, and which of Homebrew, MacPorts, apt, dnf,
pacman, zypper, apk, winget, Scoop or Chocolatey it has — so a production target's refusal says
`brew install opentofu` or `winget install --exact --id OpenTofu.Tofu` beside the install page, and
`./init` without uv or Python says the line that installs uv there. On native Windows, where a `/bin/sh`
script cannot run as it is, `generate` and `adopt` (experimental) run `./init` through Git for Windows' `sh`
when it is installed and otherwise say to use WSL or Git Bash; neither starts `./init` on a machine with no
`python3`, and both name the command that installs it.

**`./init` has uv make PyYAML importable by the `python3` Spec Kit's scripts call, with nothing to
activate.** Spec Kit's scripts need PyYAML on the bare `python3` they take off the PATH. On a Python that
refuses pip outside a venv (PEP 668: Homebrew's on macOS, Debian's and Ubuntu's), `./init` used to build a
venv at `.delivery-tools/venv` and ask you to `export PATH="$PWD/.delivery-tools/venv/bin:$PATH"` before
starting the agent — in every shell, and in no agent session unless it was started from one. It now runs
`uv pip install --python python3`, into that `python3`'s venv if it is a venv's and otherwise `--target`
its user site, which it already reads: uv is what slipwai is installed with, needs no pip on that Python,
and writes a directory rather than the managed environment, so PEP 668 has nothing to refuse and the
system's packages are never touched. Without uv, `./init` says the line that installs it on that machine.
No venv is made, and no `PATH` line is printed.

**Catch-up.** If `./init` gave you the `export PATH=…/.delivery-tools/venv/bin…` line, run `./init` once
more — with no arguments it leaves Spec Kit alone and only repeats this step — then drop that line from
your shell profile and `rm -rf .delivery-tools/venv`.

**`slipwai generate` works in PowerShell, and a generated repository's scripts stay runnable in a Windows
clone.** Every file slipwai reads or writes, and every one the Python scripts a project ships read or write,
is now opened as UTF-8 by name. Before, they took the locale's encoding, which is cp1252 on Windows, so the
first `slipwai generate` there stopped with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`
reading slipwai's own skill files; setting `PYTHONUTF8=1` was the workaround, and is no longer needed. A
test now holds every text-mode `open`, `read_text` and `write_text` to it. Every text file they *write*
is also written with LF (`newline="\n"`): on Windows a write without it turns each line ending into CRLF,
so the pruner `generate` runs left the new project's files, `./init` among them, CRLF on disk.

A generated repository gets a root `.gitattributes`: `* text=auto eol=lf`, with CRLF kept for `.bat` and
`.cmd`. Git for Windows defaults `core.autocrlf` to `true`, which checked every file out with CRLF, and a
`#!/bin/sh` script with CRLF does not run (`/bin/sh^M: bad interpreter`), which made `./init` and the gate
unrunnable under Git Bash and printed an "LF will be replaced by CRLF" warning per file on every commit. An
adopted repository keeps its own root `.gitattributes` untouched and gets one scoped to the delivery
directory (experimental), which decides only for the files under it.

A generated project's `make verify` also runs on native Windows now (from Git Bash, with GNU Make and Node
installed). It failed at one recipe, `check-drawio`, which called `node_modules/.bin/tsx`: npm's POSIX shim,
which a Windows `make` cannot run. The event-model recipes now run tsx's entry point with `node`.

**Catch-up.** `slipwai migrate` brings the `.gitattributes`. In a Windows clone whose files were already
checked out with CRLF, re-check them out once so they take it: with a clean tree,
`git rm -r --cached -q . && git reset --hard`.

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

