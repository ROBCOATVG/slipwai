# What is new since version 1

**Version 2 is a different factory, not a bigger one.** Twelve things have moved. One command moves a
project across. This page is for a person who has a version 1 project. It covers everything that affects
that person, and nothing else.

Slipwai migrates nothing without you. **Your version 1 projects keep working until you run
[`slipwai migrate`](#crossing-a-project-slipwai-migrate).** The last main section of this page describes
that command.

Version 2 has new words for some things that version 1 already had. Where this page uses a new word, it
also gives version 1's word, as [the vocabulary](../GLOSSARY.md) does.

---

## The twelve changes

| What changed | What it is for | Where it is shown working |
| --- | --- | --- |
| Languages are packages, and the keel ships none | Each language has its own release day. Anybody can publish a seventh language without permission | [Start here](guide/start-here.md#2-get-a-language) |
| The clouds are packages too | A deployment place is published as a package. It is not a branch inside `generate` | [The deployment question](guide/start-here.md#3-generate-the-repository) |
| One chandlery, several channels | You can see what is available before you install it | [Start here](guide/start-here.md#2-get-a-language) |
| A publisher is asked about once | A package runs somebody else's code, so slipwai asks who published it | [Start here](guide/start-here.md#2-get-a-language) |
| Extensions are packages | Each project chooses its development tools. No project carries all of them | [Extensions](extensions.md) |
| The chart and the mark | One typed contract with one owner, written before the work is divided | [Your first feature](guide/first-feature.md#5-the-fairways-charted-from-the-model) |
| A sibling is cleared by a mark being *set* | Two people deliver at the same time. Neither waits for the other's branch | [Why neither of you is waiting](guide/a-second-person.md#why-neither-of-you-is-waiting) |
| Captains and the harbourmaster | No process holds the state of a run, so no process can lose it by stopping | [The captain](guide/let-it-cruise.md#the-captain) |
| Status is folded from the logs, and stored nowhere | A stage that wrote no log line made no progress | [The board](guide/a-second-person.md#the-board) |
| The fleet board and the bridge | One board, read from the logs, where a person can answer questions | [Answering from one seat](guide/a-second-person.md#answering-from-one-seat) |
| One lever: the telegraph | All the limits on a run move together | [The telegraph](guide/let-it-cruise.md#the-telegraph-one-lever-for-the-whole-run) |
| Two gates, not one | A small change no longer pays for the whole test suite | [Start here](guide/start-here.md#4-start-the-repository) |

The sections below explain each change in more detail.

### Languages are packages, and the keel ships none

The **keel** is slipwai's own core. Version 1 carried Go, Python, TypeScript, Java, Spring and Quarkus
inside its wheel. A fix to one language was a release of all of them. Nobody outside the repository could
add a seventh language.

In version 2, each language has its own repository and its own release. Slipwai installs a language into
`~/.slipwai/packages/`. If a package cannot load, slipwai refuses that package only. The refusal names
the package, the directory and the fault. The other packages still load, and the command still runs.

To install a language, run `slipwai install go`. [Start here](guide/start-here.md#2-get-a-language)
shows the full process.

### The clouds are packages too

AWS and Azure also left the keel, and the keel does not name either of them now. Until you run
`slipwai target install aws`, the production-target question offers only `none` and `existing`. The
answers that need a cloud are not in the menu, because nothing installed could provision them.

A cloud package carries everything that a project for that cloud receives:

- both stacks
- the bootstrap and deploy scripts
- the drawing
- the decision record
- the pipeline parts that belong to that cloud

A project already generated for AWS or Azure does not change and needs nothing.

### One chandlery, several channels

The **chandlery** is the index of packages. It lists packages of both kinds. Each entry has a version, a
compatibility range, a checksum, a publisher and a description. So `slipwai search postgres` finds every
package that works with Postgres, in any language.

`SLIPWAI_CHANDLERY` names the channels, in order. If an earlier channel lists a name, that name belongs
to that channel, with all its versions. An organisation uses this to publish its own `python` package.
That package wins, and nothing else needs configuring.

If one channel is unreachable, slipwai says so and still lists the others. If every channel is
unreachable, slipwai refuses, because "nothing is available" and "slipwai could not ask" are different
answers. Version 1 had [no way to ask](guide/start-here.md#2-get-a-language).

The board can also ask. Its **Packages** tab has one table each for languages, extensions, targets and
quickstarts. Each table shows what is installed on this machine and what the channels offer. Press a row
to install that package. The board uses the same function as the command. If this machine has not
accepted a publisher, the row has a tick-box. The tick-box does the same as `--accept-publisher`.

### A publisher is asked about once

The keel imports a language's Python code, and an extension's entry point edits your project. The
**digest** (the checksum) proves only that the file is the file the index listed. It does not tell you
whether you trust the person who published it.

So slipwai asks you about a publisher once. When you accept a publisher, all their later releases install
without a question. To decide in advance, use `slipwai trust list|add|remove`. A container image needs
this. Each release is `verified`, `unverified`, `unsigned` or `untrusted`, and `slipwai show` tells you
which. You first meet the question in [Start here](guide/start-here.md#2-get-a-language).

### Extensions are packages

In version 1, `codegraph`, `uipro` and `ux-gates` were in the keel's catalogue. So every generated project
carried the description of three development tools, whether anybody wanted them or not.

They are packages now. You choose them at `./init`. Every extension entry point must meet six obligations.
Each obligation exists because somebody once had that failure. See [extensions](extensions.md). Run
`slipwai hooks` to see the moments that an extension can attach to.

### The chart and the mark

A **chart** (version 1: a contract map) is written before the feature is divided into slices. It names
the fairways. For every slice, it names the marks that the slice sets and the marks that the slice steers
by.

A **mark** (version 1: a contract entry) is one published contract: an event, a route, a schema or a
port. A mark is typed, it is set once, and it never moves.

On the event-modelling profile, slipwai renders the chart from the model. On the standard profile, a stage
writes the chart while a person is present. On both profiles, the gate refuses the two most expensive
mistakes:

- a mark that nobody typed
- a mark that two slices both set

[Your first feature](guide/first-feature.md#5-the-fairways-charted-from-the-model) does this in six lines.

### A sibling is cleared by a mark being *set*

The other changes depend on this one. A slice is cleared to start when every mark that it steers by is
set. A mark is set at the first stage of the slice that sets it. That stage runs **in the slice's own
worktree**, before anything merges anywhere.

So a **fairway** (version 1: a value stream, or a workstream) runs beside another fairway. It does not
wait in a queue behind the other fairway's merges.
[Why neither of you is waiting](guide/a-second-person.md#why-neither-of-you-is-waiting) shows a mark set
one second after its slice was claimed, and the other fairway starting on that mark.

### Captains and the harbourmaster

Version 1's runner ran one iteration per checkout. It trusted what each iteration said about itself. It
stopped at iteration two. After that, seventeen iterations ran from interactive sessions and wrote
nothing. So the checkpoint said "iteration 2" while twenty slices merged.

Version 2 does not replace it with a better runner. Version 2 has **no runner**.

- A **captain** runs for each fairway. The captain claims the next slice that clearance allows. It runs
  the ladder of stages, and then it asks for the merge. The captain watches the log, not the process. If
  a stage writes no log line and makes no commit on its slice branch for its time budget, the captain ends
  the stage and parks it, with the reason.
- A **harbourmaster** (version 1: the integrator) runs once per machine. It carries the few lines that
  fairways need from each other. It allocates **berths** (version 1: a workstation, or a lane), and it
  holds the credentials. The things that it will never do are a closed list. It writes down both outcomes.

The command you type starts the captains and the harbourmaster, and then exits.
[The captain](guide/let-it-cruise.md#the-captain) and
[the harbourmaster](guide/let-it-cruise.md#the-harbourmaster) each have a page.

### Status is folded from the logs, and stored nowhere

*A slice that wrote no line made no progress.*

- Each fairway's captain writes its own **deck log** (version 1: the stream log), and nothing else. So no
  two processes append to the same file.
- The **harbour log** has one writer on each machine. So the shared log never conflicts.

`slipwai fleet` builds the board from these logs. "Folding" is the word for this: the board is calculated
from the log lines each time, and it keeps nothing of its own. The fold can tell a stalled fairway from a
finished one. A status field shows both as the same.

Where the log says nothing, the board says nothing. No lines means `not started`, not `0%`. A number that
nobody wrote shows as a dash, not a zero. In version 1, a model file said `planned` for eight slices that
had shipped. [The board](guide/a-second-person.md#the-board) and
[one fairway's log](guide/a-second-person.md#one-streams-log) show the fold.

### The fleet board and the bridge

The board is the harbour's view of the agents at work. The **bridge** is the same board as a page that
you can answer from. A question from a fairway is a line in that fairway's log. When you type the answer
on the page, the page writes it into that log.

One server serves one page on one port. Three commands open it, and none of them starts a second server:

- `slipwai bridge` opens the page at the board.
- `slipwai fleet --page` opens the page and also prints the board.
- `slipwai` with no arguments also opens the page.

The page has these tabs: the board, starting a project, adopting a repository, the packages this copy can
install, and the **Voyage**. The Voyage tab shows where this project is on the ladder, read from the
files in the project. Beside that, it shows the model, the mock-ups, the slices and the live fleet. Each
stop that waits for a person has a button:

- open and approve the specification
- draw and approve the storyboard
- continue the build
- cast off or stop the fleet

You can start a project on the Voyage tab from a requirements document, or from the whole folder that the
document is in. The board drafts the first specification from it. Then the board stops so that you can
read the specification. A project can set `upstream` to `advance` in `.specify/cruise.json`. Then the board
presses the next of these buttons itself after each step ends well. [The board](guide/the-board.md) says
how. [Your first feature](guide/first-feature.md#from-the-board) walks through the page.

Your browser can also install the page as an app. Press **Install this board**. The board then opens in
its own window from the dock, with no address bar. An installed window cannot start a server. So when no
server is listening, the window says so. It names the command that starts the server, and it names the
better option beside that command.

The better option is `slipwai bridge install`. This command writes a login service for this machine: a
launchd agent, a systemd user unit, or a file in the Startup folder. The board is then always running.
The command then opens the board, so that the browser can put it in your dock. `slipwai bridge uninstall`
removes the service. [Answering from one seat](guide/a-second-person.md#answering-from-one-seat) shows
this.

### One lever: the telegraph

A run has about a dozen limits. They all mean "go slower", each in a different unit. Version 1 had none
of them. One slice used 104 hours and hundreds of millions of input tokens. The only signals were a person
who noticed and the bill.

`slipwai telegraph half-ahead` sets the whole group of limits:

- how many boilers are lit
- how many delegates a captain can run at the same time
- the budget per slice and per day
- five more limits

The model that runs each stage is a separate choice. Set it with `/model-delegation-settings`. That choice
is versioned with the project.

The telegraph has five positions, fastest first: `full-ahead`, `half-ahead`, `slow-ahead`, `dead-slow`,
`stop`. If you set one limit alone, the board says "adjusted". It does not invent a position.

When the day's budget is spent, the harbourmaster moves down one position and writes why. It never goes
straight to `stop`, because a run that stops suddenly loses the work in progress.
[The telegraph](guide/let-it-cruise.md#the-telegraph-one-lever-for-the-whole-run) shows how to set it.

### Two gates, not one

In version 1, one `make verify` did everything. So every small change paid for lint, types, structure and
the whole test suite. In practice, nobody ran the gate.

Version 2 has two gates:

1. **The fast checks**, inside a slice: `make unit`, lint and types. This gate leaves out anything that
   runs an external process or starts a server.
2. **The full gate**, once, on the rebased branch, before the merge.

The same rule applies in generated projects and in the keel.
[`make verify`](guide/start-here.md#4-start-the-repository) is still the whole gate, and CI still runs it.

---

## The two doors

| Verb | For | Page |
| --- | --- | --- |
| `slipwai adopt` | A repository that this factory did not make. Slipwai installs the method around it, with **no language installed**, whatever language it is written in | [Bring an existing codebase](guide/adopt.md) |
| `slipwai migrate` | A project that version 1 generated or adopted. Slipwai brings it across to version 2 as one merge | Below |

`slipwai adopt` is new. It has two halves:

1. A survey. It writes down what it found, not what it would have chosen.
2. The wrap. It installs the gate, CI, the skills, the commands and the agent projections.

It ends in `slipwai converge`. That command needs a language for each service that it brings up to the
generated shape.

---

## Crossing a project: `slipwai migrate`

Before you run it, make sure of three things: you are inside the project, you are on `main`, and the
working tree is clean. The command has three flags.

```console
$ slipwai migrate --check      # prepares the whole crossing and writes nothing
$ slipwai migrate              # the crossing: one merge commit
```

| Flag | What it does |
| --- | --- |
| `--check` | Prepares a crossing and reports it. It does not change the project. It reports the catch-up page it would write, the conflicts you would have to resolve, and anything that would refuse. No project file and no claim branch changes |
| `--with-claims` | Applies the rename table to claim branches that are ahead of trunk, and leaves each one to rebase. Without this flag, the command refuses while those branches are open |
| `--no-install` | If a language that the project needs is not installed, refuses and names the install command. Without this flag, the command installs the language first |

**What it does, in order.**

1. It reads `project.json` to find which factory release made the project.
2. It installs *that* release of slipwai into a temporary environment, and regenerates the base there.
   Version 2 carries none of version 1's generator. If the project records a snapshot release, the
   command uses the nearest stable release below it, and reports the difference.
3. It installs the languages that the project's services need. If a language has no compatible package,
   it refuses before it writes anything.
4. It applies the rename table to the base.
5. It removes `infra/` from both factory sides.
6. It merges three ways against your working tree, and leaves one merge commit.

**What it does not touch: `infra/`.** The files in `infra/` describe resources that already exist. A
Terraform resource address is state, not a name. A factory cannot know which of those resources are real.
So the crossing does not write or remove anything under `infra/`, and your stack crosses exactly as it is.
The catch-up page lists what this version would have changed in `infra/`. Take those changes deliberately,
and read `tofu plan` before you apply.

This rule came from a real failure. A crossing added a factory Terraform file again, under its version 2
name. The project had deleted that file months before and written its own file beside it. The next deploy
stopped on a duplicate definition. The same merge could just as easily have offered a plan that destroyed
every account in a user pool.

**What it will not take.** The command reads a block by its marker, for example
`# backing-service:<feature>:begin`, and never by the file that the block is in. Sometimes the factory
offers a file whose every block this project already implements somewhere else. The command then leaves
that file where it is, and names it on the catch-up page. This is the general form of the `infra/` rule.
A factory *rename* arrives as an addition, with no deletion to conflict with. Without this rule, the
project's own version and the factory's version would end up side by side.

**What it checks when it has finished.** It reads the stacks under `infra/` and reports what it found. If
two files of one stack declare the same name, it refuses that whole stack. Where a tool is installed and
initialised, it also runs `tofu validate`. It never refuses the crossing because of these checks, because
the merge is already committed. This check is the only moment between the rewrite of the tree and a CI
runner finding the problem. `make verify` has no provider plugins and no credentials, by design.

**What it preserves.**

- Existing decision and adversary ids stay where they are, under `fairways/main/<feature>/`, and still
  resolve.
- ADRs keep their paths and numbers. Nothing is renumbered, including by the migration.
- Flags keep their values. If a flag is on and has no `hoisted:` date, the catch-up page names it so that
  you can date it. To hoist a flag is to turn it on for real users. The day that a crossing ran is not
  that day. Without a date that you chose, the strike rule would count thirty days from a date that nobody
  chose.
- Some words a person said were never acted on by version 1's run. Each one crosses as an unanswered
  message, and keeps the instant it was said.
- A run that stopped crosses as a park, with its reason.
- Slice status is moved forward only from trunk's own merges.

**What it costs.**

- **Fairways are proposed, not decided.** The first task on the catch-up page is to confirm them. The page
  counts them rather than describing them: *N fairways proposed, M slices in `unplaced`*. You cannot claim
  anything in a proposed fairway until you confirm it. If all of a project's slices landed in one context,
  that task is already done.
- **The tree must be clean, and you must be on `main`.** Then everything uncommitted afterwards belongs to
  the migration, and one command takes you back.
- **An open claim stops it.** If a `slice/<id>` branch is ahead of trunk, the command names it and
  refuses. Finish it, merge it, or pass `--with-claims`. If a claim is checked out in another worktree, the
  command refuses in either case.
- **Conflicts leave the merge in progress**, the same way that `git` leaves it. The command names each
  conflicting file and gives both ways out: resolve and commit, or run `git merge --abort`.
- **The catch-up page is the part that no merge can do.** `.slipwai/catch-up.md` lists:
  - every rename, once
  - the base that was installed
  - the release mode and state to confirm
  - every `infra/` path that it left alone
  - what the crossing could not do

  `/catch-up` finishes the page. `/catch-up` stays red while any fairway is still proposed.

**What it cannot undo.**

- `git reset --hard ORIG_HEAD` undoes the merge and the commit after it, **until you push**. The migration
  itself pushes nothing.
- It does not undo the deck logs. The migration appends what version 1 left to logs that are append-only
  by design and ignored by Git. So a reset of the tree leaves those lines in place. It is safe to run the
  command again: each migrated line carries a key, and a second crossing recognises what the first one
  wrote. It does not write the person's words twice.
- With `--with-claims`, each claim branch moves to its own rename commit. A reset of `main` does not move
  the claims back.
- A language that the crossing installed stays installed.
- The command substitutes a rename as text only in the files that *declare* the renamed thing: a target
  in a Makefile, a command, a skill. It leaves a reference anywhere else in your repository exactly as
  written. Read those from the catch-up page. A word in somebody's prose is not a declaration.
- If trunk cannot prove that a slice shipped, the slice keeps the status that the model recorded for it.
  Unproven means unknown, not unstarted.

If the merge is clean, a second commit regenerates the factory-owned projections that the merge cannot
reach. After a conflict, commit your resolution, run `make agents`, and then run `slipwai migrate` again.
The crossing is finished when `make verify` passes on the migrated tree.

---

## The words that changed

Version 2's names come from the slipway and the harbour. [The vocabulary](../GLOSSARY.md) has the full
table, with version 1's word for each in the last column. These are the words that a version 1 user meets
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

`slipwai migrate` applies this table to your project. So if you edited a renamed file, your edit lands in
the file that replaced it.

---

→ **[Start here](guide/start-here.md)** if you want to see version 2 from the beginning ·
[your first feature](guide/first-feature.md) · [a second person joins](guide/a-second-person.md) ·
[let it cruise](guide/let-it-cruise.md) · [bring an existing codebase](guide/adopt.md) ·
[the vocabulary](../GLOSSARY.md) · [the changelog](../CHANGELOG.md)
