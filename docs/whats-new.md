# What is new since version 1

**Version 2 is a different factory, not a bigger one.** Twelve things are not where you left them, and one
command moves a project across. This page is for somebody who has a version 1 project; it is everything
that affects you and nothing else.

Nothing is migrated behind your back. **Your version 1 projects keep working until you run
[`slipwai migrate`](#crossing-a-project-slipwai-migrate)**, and that command is the last section here.

Where version 2 has a new word for something version 1 already had, version 1's own word is named beside
it, the way [the vocabulary](../GLOSSARY.md) names it.

---

## The twelve changes

| What changed | What it is for | Where it is shown working |
| --- | --- | --- |
| Languages are packages, and the keel ships none | A language is released on its own day, and a seventh one needs nobody's permission | [Start here](guide/start-here.md#2-get-a-language) |
| The clouds are packages too | Somewhere to deploy to is published rather than branched into `generate` | [The deployment question](guide/start-here.md#3-generate-the-repository) |
| One chandlery, several channels | You can ask what there is before you install it | [Start here](guide/start-here.md#2-get-a-language) |
| A publisher is asked about once | Installing a package runs somebody else's code, so who published it is a question with an answer | [Start here](guide/start-here.md#2-get-a-language) |
| Extensions are packages | Dev tooling is elected per project instead of carried by every one | [Extensions](extensions.md) |
| The chart and the mark | One typed contract, one owner, written before the work is cut up | [Your first feature](guide/first-feature.md#5-the-fairways-charted-from-the-model) |
| A sibling is cleared by a mark being *set* | Two people deliver at once without either waiting on the other's branch | [Why neither of you is waiting](guide/a-second-person.md#why-neither-of-you-is-waiting) |
| Captains and the harbourmaster | Nothing holds the state of a run, so nothing can die holding it | [The captain](guide/let-it-cruise.md#the-captain) |
| Status is folded from the logs, and stored nowhere | A stage that wrote no line made no progress | [The board](guide/a-second-person.md#the-board) |
| The fleet board and the bridge | One board, folded from the logs, that a person can answer from | [Answering from one seat](guide/a-second-person.md#answering-from-one-seat) |
| One lever: the telegraph | Every number a run is held to moves together | [The telegraph](guide/let-it-cruise.md#the-telegraph-one-lever-for-the-whole-run) |
| Two gates, not one | An increment stops paying for the whole suite | [Start here](guide/start-here.md#4-start-the-repository) |

Each one again, in a paragraph.

### Languages are packages, and the keel ships none

Version 1 carried Go, Python, TypeScript, Java, Spring and Quarkus inside the wheel, so a fix to one was a
release of all of them and nobody outside the repository could add a seventh. Each is its own repository
and its own release now, installed into `~/.slipwai/packages/`. A package that cannot load is refused by
itself, naming the package, the directory and the fault; the others still load and a verb still runs.
`slipwai install go`, and [start here](guide/start-here.md#2-get-a-language) shows the whole of it.

### The clouds are packages too

AWS and Azure left the keel the same way, and the keel now names neither. Until `slipwai target install
aws` has been run, the production-target question offers `none` and `existing` and nothing else — the
answers only a cloud can provision are not in the menu, because nothing there could provision them.
Everything a project going to a cloud is given travels with that cloud: both stacks, the bootstrap and
deploy scripts, the drawing, the decision record, and the pipeline parts that are its own. A project
already generated on either cloud is unchanged and needs nothing.

### One chandlery, several channels

The index lists packages of both kinds, each with a version, a compatibility range, a checksum, a
publisher and a description — so `slipwai search postgres` finds whatever will talk to Postgres for you,
whichever language it is in. `SLIPWAI_CHANDLERY` names the channels in order, and a name an earlier
channel lists is that channel's, versions and all, which is how an organisation publishes its own
`python` and wins with nothing else configured. One channel being unreachable is said and the rest are
still listed; every channel being unreachable is a refusal, because "nothing available" and "could not
ask" are different answers. Version 1 had [no way to ask](guide/start-here.md#2-get-a-language) at all.

The board asks it too: its **Packages** tab lists what is installed here and what the channels offer —
languages, extensions, targets and quickstarts, a table each — and installs one where you press it, by
the same function the verb calls. A publisher this machine has not accepted is a tick-box on the row,
which is `--accept-publisher` asked where you already are.

### A publisher is asked about once

A language's Python is imported into the keel and an extension's entry point edits your project, so the
digest — which proves the file is the file the index listed — is not the whole question. Accept a
publisher and every later release of theirs installs silently; `slipwai trust list|add|remove` does it
ahead of time, which is what a container image needs. A release is `verified`, `unverified`, `unsigned`
or `untrusted`, and `slipwai show` says which. [Start here](guide/start-here.md#2-get-a-language) is where
you meet the question.

### Extensions are packages

`codegraph`, `uipro` and `ux-gates` lived in the keel's catalogue, so every project generated carried the
description of three dev tools whether or not anybody wanted them. They are packages now, elected at
`./init`, and an entry point is held to six obligations — each of them a failure somebody had. See
[extensions](extensions.md), and `slipwai hooks` for the moments one may attach to.

### The chart and the mark

A **chart** (version 1 called it a contract map) is written before the feature is cut up: it names the
fairways, and for every slice the marks it sets and the marks it steers by. A **mark** (version 1's
contract entry) is one published contract — an event, a route, a schema or a port — typed, set once,
never moved. On the event-modelling profile the chart is rendered from the model; on the standard profile
a stage writes it with a person present. Either way the gate refuses the two mistakes that cost the most:
a mark nobody typed, and a mark two slices both set.
[Your first feature](guide/first-feature.md#5-the-fairways-charted-from-the-model) does it in six lines.

### A sibling is cleared by a mark being *set*

This is the change the rest of them hold up. A slice is cleared to start when every mark it steers by has
been set — and a mark is set at the setting slice's **first stage, in its own worktree**, before anything
merges anywhere. So a fairway (version 1 called this a value stream, or a workstream) runs beside another
instead of queueing behind its merges.
[Why neither of you is waiting](guide/a-second-person.md#why-neither-of-you-is-waiting) shows the mark
being set one second after the slice was claimed, and the other fairway starting on it.

### Captains and the harbourmaster

Version 1's runner ran one iteration per checkout and trusted what the iteration said about itself. It
died at iteration two; seventeen iterations ran from interactive sessions afterwards and wrote nothing, so
the checkpoint said "iteration 2" while twenty slices merged. What replaced it is not a better runner — it
is **no runner**. A **captain** per fairway claims the next slice its clearance allows, dispatches the
ladder and asks for the merge, and it watches the log rather than the process: a stage that has written
nothing for its budget is ended and parked, with the reason. A **harbourmaster** (version 1's integrator),
one per machine, carries the few lines fairways need from each other, allocates berths (version 1 called
one a workstation, or a lane) and holds the credentials; what it will never do is a closed list, and both
outcomes are written. The thing you type starts them and exits.
[The captain](guide/let-it-cruise.md#the-captain) and
[the harbourmaster](guide/let-it-cruise.md#the-harbourmaster) are a page each.

### Status is folded from the logs, and stored nowhere

*A slice that wrote no line made no progress.* A fairway's captain writes its own **deck log** (version 1:
the stream log) and nothing else, so no two processes append to one file; the **harbour log** has one
writer per machine, so the shared one never conflicts. `slipwai fleet` folds the board out of them and
keeps nothing of its own — it tells a stalled fairway from a finished one, which look identical in a
status field, and where the log says nothing the board says nothing: no lines is `not started`, not `0%`,
and a number nobody wrote is a dash rather than a zero. In version 1 a model file said `planned` for eight
slices that had shipped. [The board](guide/a-second-person.md#the-board) and
[one fairway's log](guide/a-second-person.md#one-streams-log) show the fold.

### The fleet board and the bridge

The board is the harbour's view of the agents at work; the **bridge** is the same thing as a page you can
answer from, and a question from a fairway is a line in that fairway's log, so typing the answer on the
page writes it there. One server, one port, one page: `slipwai bridge` opens it at the board, `slipwai
fleet --page` does the same without giving up the printed board, and `slipwai` on its own opens it too —
and none of them starts a second one. Its tabs are the board, starting a project, adopting a repository
and the packages this copy can be given.

Your browser will also install it: press **Install this board**, and it opens in its own window from the
dock with no address bar. Installing a window cannot start a server, so when nothing is listening that
window says so and names the command that starts it, rather than showing a connection error — and names
the better answer beside it. `slipwai bridge install` writes this machine's own login service (a launchd
agent, a systemd user unit, or a file in the Startup folder) so the board is simply up, then opens it for
the browser to put in your dock — the two halves of having the board on a machine, in one word. `slipwai
bridge uninstall` removes the service.
[Answering from one seat](guide/a-second-person.md#answering-from-one-seat) is the picture.

### One lever: the telegraph

A run has a dozen numbers that all mean "go slower" in different units, and in version 1 none of them
existed — 104 hours and hundreds of millions of input tokens on one slice, with a person noticing and the
bill arriving as the only signals. `slipwai telegraph half-ahead` sets the group: how many boilers are lit,
how many delegates a captain may run at once, the budget per slice and per day, and five more. Which model
runs each stage is a separate choice, `/model-delegation-settings`, versioned with the project. Five positions, fastest first: `full-ahead`, `half-ahead`, `slow-ahead`, `dead-slow`, `stop`.
Set one number alone and the board says "adjusted" rather than inventing a position. When the day's budget
is spent the harbourmaster steps down one notch and writes why — never straight to `stop`, because a run
that stops dead loses what was in flight.
[The telegraph](guide/let-it-cruise.md#the-telegraph-one-lever-for-the-whole-run) rings it.

### Two gates, not one

In version 1 one `make verify` did everything, so every increment paid for lint, types, structure and the
whole suite — and the honest result was a gate nobody ran. It is split: the fast checks inside a slice
(`make unit`, lint, types), and the full gate once, on the rebased branch, before the merge. The
per-increment gate leaves out what shells out or stands up a server, and the rule holds in generated
projects as well as in the keel. [`make verify`](guide/start-here.md#4-start-the-repository) is still the
whole gate, and still what CI runs.

---

## The two doors

| Verb | For | Page |
| --- | --- | --- |
| `slipwai adopt` | A repository this factory did not make: the method installed around it, with **no language installed**, whatever it is written in | [Bring an existing codebase](guide/adopt.md) |
| `slipwai migrate` | A project version 1 generated or adopted: brought across to version 2, as one merge | Below |

`slipwai adopt` is new. It is two halves — a survey that writes down what it found rather than what it
would have chosen, then the wrap that installs the gate, CI, the skills, the commands and the agent
projections — and it ends in `slipwai converge`, which is the verb that needs a language for each service
it is bringing up to generated.

---

## Crossing a project: `slipwai migrate`

Run it inside the project, on `main`, with a clean tree. It is one command and three flags.

```console
$ slipwai migrate --check      # prepares the whole crossing and writes nothing
$ slipwai migrate              # the crossing: one merge commit
```

| Flag | What it does |
| --- | --- |
| `--check` | Prepares a crossing and reports it without changing the project: the catch-up page it would write, the conflicts there would be to resolve, and anything that would refuse. No project file and no claim branch changes |
| `--with-claims` | Applies the rename table to claim branches that are ahead of trunk and leaves each to rebase, instead of refusing while they are open |
| `--no-install` | Refuses, naming the install line, where a language the project needs is not installed — instead of installing it first |

**What it does, in order.** It reads which factory made the project from `project.json`, installs *that*
release of slipwai into a throwaway environment and regenerates the base there — version 2 carries none of
version 1's generator. A recorded snapshot falls to the nearest stable release below it, and the
difference is reported. It installs the languages the project's services need, or refuses before writing
anything if one has no compatible package. It applies the rename table to the base, takes `infra/` out of
both factory sides, merges three ways against your working tree, and leaves one merge commit.

**What it does not touch: `infra/`.** Those files describe resources that already exist — a Terraform
resource address is state, not a name — and which of them are real is not something a factory can know. So
the crossing neither writes nor removes anything under `infra/`, and your stack crosses exactly as it is.
What this version would have changed there is listed in the catch-up page instead, for you to take
deliberately, reading `tofu plan` before you apply. This is the rule that was learned the hard way: a
crossing re-added a factory Terraform file under its version 2 name, into a project that had deleted it
months before and written its own beside it, and the next deploy stopped on a duplicate definition. The
same merge could as easily have offered a plan that destroyed every account in a user pool.

**What it will not take.** A block is read by its marker — `# backing-service:<feature>:begin` — and never
by the file it sits in, so a file the factory offers whose every block this project already implements
somewhere else is left where it is and named on the catch-up page. That is the general form of the
`infra/` rule above: a factory *rename* arrives as an addition, with no deletion to conflict with, so
without this the project's own answer and the factory's end up side by side.

**What it checks when it has finished.** It reads the stacks under `infra/` and says what it found — a
name two files of one stack both declare refuses the whole stack, and `tofu validate` runs as well
wherever a tool is installed and initialised. It never refuses over any of it: the merge is already
committed, and this is the only moment between a tree being rewritten and a runner finding out, because
`make verify` has no provider plugins and no credential by design.

**What it preserves.** Existing decision and adversary ids are frozen where they are, under
`fairways/main/<feature>/`, and go on resolving; ADRs keep their paths and numbers; nothing is renumbered,
including by the migration. Flags keep their values. A flag that is on and carries no
`hoisted:` date is named on the catch-up page for you to date: to hoist a flag is to turn it on for real
actors, and the day a crossing happened to run is not that day — the strike rule would otherwise count
thirty days from a date nobody chose. Words a person said that version 1's run never finished acting on cross as unanswered messages, each
keeping the instant it was said; a run that stopped crosses as a park with its reason. Slice status is
reconciled upward from trunk's own merges only.

**What it costs.**

- **Fairways are proposed, not decided.** The catch-up page's first task is confirming them, counted
  rather than described — *N fairways proposed, M slices in `unplaced`* — and nothing can be claimed in a
  proposed fairway until you confirm. A project whose slices all landed in one context finds the task
  already satisfied.
- **The tree has to be clean, and you have to be on `main`**, so that everything uncommitted afterwards is
  the migration's and the way back is one command.
- **An open claim stops it.** A `slice/<id>` branch ahead of trunk is named and refused: finish it, merge
  it, or pass `--with-claims`. A claim checked out in another worktree is refused either way.
- **Conflicts leave the merge in progress**, exactly as `git` leaves it, with each conflicting file named
  and both ways out spelled out — resolve and commit, or `git merge --abort`.
- **The catch-up page is the part no merge can do.** `.slipwai/catch-up.md` lists every rename once, the
  base that was installed, the release mode and state to confirm, every `infra/` path it left alone, and
  what the crossing could not do.
  `/catch-up` finishes it, and stays red while any fairway is still proposed.

**What it cannot undo.**

- `git reset --hard ORIG_HEAD` undoes the merge and the commit after it — **until you push**. Nothing is
  pushed by the migration itself.
- It does not undo the deck logs. What version 1 left behind is appended to logs that are append-only by
  design and ignored by Git, so resetting the tree leaves those lines where they are. Re-running is safe:
  each migrated line carries a key, and a second crossing recognises what the first wrote rather than
  saying the person's words twice.
- With `--with-claims`, each claim branch is moved to a rename commit of its own. Resetting `main` does
  not move the claims back.
- A language the crossing installed stays installed.
- A rename is substituted as text only in the files that *declare* the thing renamed — a target in a
  Makefile, a command, a skill. A reference anywhere else in your repository is left exactly as written
  and read off the catch-up page, because a bare word in somebody's prose is not a declaration.
- A slice trunk cannot prove shipped keeps the status the model recorded for it. Unproven is unknown, not
  unstarted.

When the merge is clean, a second commit re-derives the factory-owned projections the merge cannot reach;
after a conflict, that is `make agents` once the resolving commit is in, and then `slipwai migrate` again.
A green `make verify` on the migrated tree is the end of it.

---

## The words that changed

Version 2's names come from the slipway and the harbour. [The vocabulary](../GLOSSARY.md) is the whole
table, with version 1's own word for each in the last column; these are the ones a version 1 user meets
first.

| Version 1 | Version 2 |
| --- | --- |
| core, core driver | the **keel** |
| marketplace, index | the **chandlery** |
| value stream, workstream | a **fairway** |
| workstation, lane | a **berth** |
| runner, `cruise.py run` | a **captain** |
| integrator | the **harbourmaster** |
| stream log, cross-stream log | the **deck log** and the **harbour log** |
| contract map, streams manifest | the **chart** |
| contract entry | a **mark** |
| consumption gate | **clearance** |
| concurrency setting, cost cap | the **telegraph** |
| hardening slice | the **careen** |
| backload | **stow** |
| `/drive` | `/sail`, and `/cruise` when nobody is at the wheel |

`slipwai migrate` applies this table to your project for you, so an edit of yours to a renamed file lands
in the file that replaced it.

---

→ **[Start here](guide/start-here.md)** if you would rather see version 2 from the beginning ·
[your first feature](guide/first-feature.md) · [a second person joins](guide/a-second-person.md) ·
[let it cruise](guide/let-it-cruise.md) · [bring an existing codebase](guide/adopt.md) ·
[the vocabulary](../GLOSSARY.md) · [the changelog](../CHANGELOG.md)
