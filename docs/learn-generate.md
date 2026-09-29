# Runsheet: generate a new project

The whole life of a generated repository, as one list of steps in order: from an empty directory to
`/cruise`, and on through every slipwai release after it. Each step says where you type it, what it leaves
behind and how you know it worked, and the transcripts show what you will see. You do **not** clone this
factory to scaffold a product: the installed `slipwai` carries everything it needs. The reasoning behind each
step is in the pages linked from it; this page is the sequence.

Where you type each command:

- **terminal**: a shell at the repository root
- **agent**: a session of your coding agent (Claude Code, Codex, Cursor, …), opened at the repository root

Commands are written the way Claude Code spells them: `/ground`, `/drive`. Other agents differ. Codex takes
them as skills, so you type `$ground` and `$drive`. Codex also runs commands in a sandbox that cannot rewrite
its own skills, so when slipwai reports that *the harness projections could not be re-derived*, run
`make agents` in a terminal.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |

```text
$ slipwai --version
slipwai 1.4.0
```

- **0.1: why uv.** It is the recommended installer, and a generated project's `./init` uses it too: to fetch
  Spec Kit, and to give the `python3` on your PATH the PyYAML that Spec Kit's scripts need. Alternatives,
  `pip` or a standalone executable that needs only Git, are in [Install the command](executable.md).
- **The project's own toolchain** (Node, Python, Go or a JDK, whichever language you pick) is installed for you
  where it is missing, as are Git, Make and uv: with Homebrew on macOS, apt, dnf, pacman, zypper or apk on Linux
  (through `sudo`), winget, Scoop or Chocolatey on Windows, or the publisher's own download where the packaged
  version is too old. `--no-install` turns that off. **Docker is the exception:** it needs a system service and
  your user in its group, so if you choose Postgres or Keycloak, install Docker yourself.
  [Tools required](requirements.md) lists everything.

---

## Phase 1: create the repository

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `slipwai generate` | among its questions it has asked which coding agent to use (nothing preselected); it prints `created: <path>`, installs any missing tools, and runs `./init`, which offers the optional extensions and installs the ones you tick |
| 1.2 | terminal | `cd <name>`, only if you did not run 1.1 in an empty folder | you are in the project's root: start your coding agent here, or it will not find the project's commands |
| 1.3 | terminal | `./init`, only if 1.1 did not run it | as 1.1 |
| 1.4 | terminal | `make verify` | it ends with `verify: all gates passed` |
| 1.5 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

**1.1: answering the questions.** Run it in an empty folder to make that folder the project — its name is offered, and nothing is nested beneath it — or from wherever a new folder for it should appear. In a terminal each
fixed list is an arrow-key menu (↑/↓ or `j`/`k`; Enter chooses). The transcript below is the typed form of
the same questions: what you see when stdin is not a terminal, and on Windows. Press Enter to accept a shown
default:

```text
Create a new product monorepo. Press Enter to accept a shown default.
Project name: ledger

Delivery foundation:
  event-modelling — Event Modeling — everything above, plus events as the source of truth, …
  standard — Standard — walking skeleton, executable test and the CD gate, …
Use Event Modeling? [Y/n]: Y

Production target:
  none — Local only — nothing is deployed anywhere; `make verify` is the end of the road
  aws — AWS — …
  azure — Azure — …
  existing — Existing — … (experimental, with brownfield adoption)
Choose (none/aws/azure/existing) [none]:

Language (typescript/python/go/java) [typescript]:
Service name [service]:
What does service own? (a sentence or two; Enter to decide later):
Bounded contexts service holds, comma-separated [service]:
Frontend (none/react-vite) [react-vite]:

Event store:
  memory — In-memory — …
  sqlite — SQLite — …
  postgres — Postgres — …
Choose (memory/sqlite/postgres) [postgres]:

HTTP transport:
  none — None — library or worker only, no inbound HTTP
  fastify — Fastify — …
Choose (none/fastify) [fastify]:

Staff authentication:
  none — None — …
  keycloak — Keycloak — …
Choose (none/keycloak) [none]:

Customer authentication:
  none — None — …
  keycloak — Keycloak — …
Choose (none/keycloak) [none]:
Output parent [/Users/you/dev]:
created: /Users/you/dev/ledger

Running ./init — it installs Spec Kit, which needs the network.
```

To skip the questions, give every answer as a flag. This is the form for scripts and CI:

```sh
slipwai generate ledger \
  --profile event-modelling \
  --target none \
  --language typescript \
  --frontend react-vite \
  --event-store postgres \
  --http fastify
```

```text
created: /Users/you/dev/ledger
```

The new directory is a Git repository on `main` with one commit. The target must not already exist, and
`--output` names a different **parent** directory. [Project shape](axes.md) says what each answer brings.

- **1.1 and 1.3: when `./init` runs.** Answering the questions at a terminal runs `./init` for you, from
  inside the new project, as the last step. The flag form does not unless given `--init`, and `--no-init`
  skips it either way; 1.3 is then yours to run. `--integration <agent>` names the coding agent so it is not
  asked; run from inside an agent, `generate` uses that one.
- **1.1 on Windows.** `./init` is a shell script. `generate` runs it through Git Bash when Git for Windows
  is installed, and otherwise tells you to run it from WSL or Git Bash.
- **1.3: agent and extensions.** `./init` installs Spec Kit, then copies the commands and skills into the
  agent you name, then offers the optional extensions as a checkbox menu:

  ```text
  Optional dev tooling — check any to adopt now, or none;
  `./init --extension <key>` adds one later just the same.

    ❯ [ ] CodeGraph — Indexes the codebase into a local knowledge graph your
          coding agent can query over MCP, so it can trace callers, dependencies,
          and the blast radius of a change across files.

      [ Confirm ]

    ↑/↓ move · Enter or Space checks · Enter on Confirm finishes · Esc skips
  ```

  Space or Enter on a row checks it, Confirm finishes with whatever is checked, and Escape skips. Nothing is
  adopted by default, and `./init --extension <key>` adds one at any later time. [Extensions](extensions.md).
- **1.5: commit.** `./init` writes its files and does not commit them, which is what 1.5 is for.

[What you get](what-you-get.md) is the tour of the tree.

---

## Phase 2: the first feature

Every command in this phase is typed in the **agent**, except where a row says otherwise.

| # | Command | What it does | Done when |
|---|---|---|---|
| 2.1 | `/speckit-constitution` | Writes the project's principles, which the gate then holds every change to | `make check-constitution` passes and `constitution.md` has no placeholders left |
| 2.2 | `/speckit-specify <the feature, in a sentence or two>` | Writes the first feature as a specification | `specs/<feature>/spec.md` exists |
| 2.3 | `/drive` | Takes one slice of that feature from wherever it stands to a demo | it stops at the demo and asks you a question only you can answer |
| 2.4 | `/drive` again | Continues from the artifacts on disk, whatever the conversation has forgotten | the next slice reaches its demo |

- **2.1: do it first.** `/drive` sends you to 2.1 by itself if you skip it. Do it before 2.2 all the same:
  once `specs/` exists over the template constitution, `check-constitution` fails, and `verify` and `/drive`
  fail with it.
- **2.3: what `/drive` does.** It works out which stage is missing and runs it: the split into slices, gaps,
  plan and tasks, then RED, GREEN, REFACTOR, converge and the demo. A question that needs a product decision
  stops it, and so does every demo. [The delivery loop](delivery-loop.md) has the stages.
- **Where am I?** Three commands answer that at any point, and none of them changes anything:
  - `/whats-next`: one line saying what to do next
  - `/where-are-we`: the progress board
  - `/gaps`: an adversarial read of whatever was written last

---

## Phase 3: the development loop

Work arrives as a **feature**, written as a specification, and is delivered as **slices**: thin, vertical,
one-demo-each pieces of it. The loop below runs once per feature for the upstream stages and once per slice
for the rest. `/drive` knows where it is from the files on disk, so it can stop and resume anywhere, in a new
session, on another day.

```text
once per feature   constitution → specify → gaps → (event model) → split into slices
once per slice     (example map) → gaps → plan and tasks → implement: RED, GREEN, REFACTOR
                   → converge → gaps → demo → next slice
now and then       /adversary when a slice changed attack surface · /mutation on every accepted slice
```

The bracketed stages exist in the `event-modelling` profile only. Every implementation step starts from a
green `make verify` and ends on one.

A day with it looks like this:

| When | Where | Command |
|---|---|---|
| Starting a session | agent | `/whats-next`: one line saying what to do next, and why |
| Doing the work | agent | `/drive`, and answer what it asks |
| Checking where things stand | agent | `/where-are-we`: the progress board, slices done, in progress and blocked |
| A new feature | agent | `/speckit-specify <feature>`, then `/drive` |
| Before every push | terminal | `make verify` |
| Another service or frontend | agent | `/add-service`, `/add-frontend` |

---

## Phase 4: `/drive` or `/cruise`

They run the same ladder and produce the same artifacts. The difference is who answers when the ladder needs
a person.

| | `/drive` | `/cruise` |
|---|---|---|
| **Who answers a product question** | you | the agent, as product owner: it reads the spec, the constitution and the owner brief, decides, and writes the decision down with its reason |
| **Who judges a demo** | you: every slice stops at its demo | the agent, as the actor, driving the app through a browser, HTTP or the CLI; each acceptance is marked `accepted-by: drive-hand` so you can tell |
| **How far it goes** | one slice, to its demo | slice after slice, until the whole specification is satisfied |
| **Sessions** | the one you are typing in | a fresh session per iteration, started by a runner in the background |
| **When it stops** | at every question and every demo | only for a human, a budget, or something it cannot get past (below) |
| **What you review** | each demo as it happens | the report, the decision log, the ADRs and the demos afterwards |
| **Use it when** | the product is still being discovered, the questions matter, or you are learning how the loop behaves | the spec is settled enough that you would accept the agent's recommended answer most of the time |

Start with `/drive`. Run it by hand until you have seen where it stops and agreed with how it decides; then
hand the settled specs to `/cruise`. The two mix freely: `/drive` a slice that needs you, `/cruise` the rest.

---

## Phase 5: setting `/cruise` goals, and letting it run

`/cruise` pursues **goals you write down**, and it works on them until they are met or a person stops it.
It never invents what to build: it refuses to start without a specification.

### What a goal is

| What you want | Where you write it | What `/cruise` does with it |
|---|---|---|
| **What to build** | `specs/<feature>/spec.md`, through `/speckit-specify` | splits it into slices and delivers every one. At the end, a completion audit checks the whole spec against what shipped: anything unbuilt becomes a new slice, or a recorded out-of-scope decision. Only an audit with nothing left ends the run |
| **What matters most, and what is out of scope** | `.specify/product-owner.md`, the owner brief: who the user is, what the product is for, priorities, tie-breakers, taste, what is out of scope | reads it before every product decision. Edit it at any time to steer a run without stopping it |
| **What this particular run is for** | the words after `/cruise`: `/cruise build the reporting feature; payments is out of scope` | the first iteration writes it down where it outlives the session (a scope becomes a decision entry, a preference goes into the owner brief) before it does anything else. Later iterations never see the text itself |
| **A change of course mid-run** | `/cruise-tell <message>` | the next iteration carries it. `--now` ends the iteration in flight so it is heard sooner |
| **How long it may run** | `/cruise-settings max_iterations=<n> max_hours=<n>` | stops when either budget is spent |

A spec's user stories carry priorities (P1, P2, P3), and the owner brief says what matters. The split uses
both, and orders slices by value and risk: the product's core capability before infrastructure that only
feels foundational, and the slice that retires the most risk early.

### A series of goals

**Several goals that belong together** go in one spec, as separate user stories. One run delivers all of
them, in the order the split chooses, and ends when the audit finds nothing left.

**Several separate features** are several specs. Write each one first; `/cruise` needs the spec to exist.
Then run them one at a time, scoping each run to its feature:

```sh
make cruise FEATURE=001-reporting
make cruise FEATURE=002-exports
```

or queue them in one line and walk away:

```sh
make cruise FEATURE=001-reporting && make cruise FEATURE=002-exports && make cruise FEATURE=003-billing
```

Each run ends on its own `done` and the next begins. What else moves the queue on:

- **A park** holds the queue. `make cruise` runs in the foreground, so a parked run waits for you (see below),
  and the queue waits with it.
- **A spent budget** moves it on. `max_iterations` and `max_hours` are per run, and a run that spends one ends
  normally, so the next feature starts with a fresh budget and the unfinished one is left for later. Leave the
  budgets unset (`null`) for a queue that should finish each feature before the next, or set them knowing
  that.
- **A stop** (`/cruise-stop` or `make cruise-stop`) ends the whole queue: every later run sees the stop file
  and ends on its first iteration.

In the agent, `/cruise --feature 001-reporting` starts the same scoped run for one feature.

### When it stops

| It stops because | What you do |
|---|---|
| **Done**: the audit of the spec found nothing left | read what it did (below), then start the next feature |
| **A person stopped it**: `/cruise-stop`, `make cruise-stop`, or Ctrl-C | nothing. To go again, `rm .specify/cruise.stop` (the stop commands leave it, and `/cruise` refuses while it is there), then `/cruise`: it resumes from the files on disk |
| **A budget ran out**: `max_iterations` or `max_hours`, counted per run | run `/cruise` again for another budget's worth, or raise it with `/cruise-settings` |
| **It parked**: something it cannot decide or get past — a fact nobody has given it, such as a credential, where the bosun delegate could not work around it; or three iterations with nothing changed | `/cruise-status` says why. Answer it by changing the artifact it names, or with `/cruise-tell`; the parked run looks again every `poll_minutes` (10) and resumes itself |

A product *decision* never stops it: it decides, and writes the decision where you can overturn it. A missing
*fact* never makes it guess: the slice is marked blocked, it moves to the next ready slice, and the bosun
works around the block where it can, recording what it did.

### Running it

| # | Where | Command | What it does |
|---|---|---|---|
| 5.1 | agent | `/cruise-settings enabled=true max_iterations=3` | Turns cruise on, with a small budget for the first run. This commits `.specify/cruise.json` |
| 5.2 | agent | edit `.specify/product-owner.md` | Says what matters, what breaks ties and what is out of scope |
| 5.3 | agent | `/cruise <what this run is for>` | Starts the runner in the background and shows its feed in this session |
| 5.4 | agent | `/cruise-status` · `/cruise-watch` · `/cruise-tell <a steer>` | Check on it, sit back down at the feed, steer it |
| 5.5 | agent | `/cruise-stop` (or `/cruise-stop now`) | Ends it after the iteration in flight, or at once |
| — | terminal | `make cruise` · `make cruise-status` · `make cruise-stop` | The same controls from a shell; `make cruise` runs in the foreground |

When a run ends, read these in order:

1. `specs/<feature>/cruise-report.md`: what shipped, what was ruled out of scope, and every decision not yet
   reviewed.
2. `specs/<feature>/decisions.md`: to overturn a decision, change its `Status` and write the answer you want
   into the artifact it names. The next iteration picks it up from there.
3. The ADRs it left at `Proposed`: accept each one, or write the one that supersedes it. It never accepts its
   own.
4. Each slice's `demo-log.md` and `demo/`: the evidence behind every `accepted-by: drive-hand`.
5. The constitution, if it ratified one: the line `pending human review` is yours to remove.
6. The flags: nothing a run merges is visible to a real user until you turn its flag on.

[Cruise](cruise.md) has every setting.

---

## Phase 6: keeping the repository in tune with slipwai

Each slipwai release can change the files it generated for you: the gates, the commands, the skills and CI.
Taking those changes is three steps, on a clean tree, as often as releases come out. Checking weekly, or
whenever the changelog says something you want, is a good rhythm.

| # | Where | Command | Done when |
|---|---|---|---|
| 6.1 | terminal | `slipwai upgrade --check` | it says whether a newer version is published. It changes nothing |
| 6.2 | terminal | `slipwai upgrade` | `slipwai --version` shows the new version |
| 6.3 | terminal | `git status` | the tree is clean. Commit or stash first, because `migrate` refuses otherwise |
| 6.4 | terminal | `slipwai migrate` | it prints `migrated <name> from <old> to slipwai <new>`, as one merge commit |
| 6.5 | agent | `/catch-up` | it has worked through `.slipwai/catch-up.md` and `make verify` passes |
| 6.6 | terminal | `git push` | the gate in CI is green |

**6.1 and 6.2: upgrade the command.** This moves the *installed* `slipwai`, not a checkout of this factory.
`slipwai upgrade --pre` counts the snapshot of `main` as well.

```text
$ slipwai upgrade --check
slipwai 1.3.0, installed as: uv tool
newest published: 1.4.0
this is not the newest published version.
would run: uv tool upgrade slipwai

$ slipwai upgrade
slipwai 1.3.0, installed as: uv tool
newest published: 1.4.0
running: uv tool upgrade slipwai
```

An installation configured for a private mirror may still need that mirror's credentials; public PyPI
installs need none. [Upgrade it](executable.md#upgrade-it) has the detail.

**6.4: migrate the project.** `upgrade` moved the command on your PATH; `migrate`, run **inside** the
project, brings its files forward to match:

```text
$ slipwai migrate
migrated ledger from 1.3.0 to slipwai 1.4.0: 47 files
One merge commit. The files this project had changed itself were kept; the rest are what the
factory now generates for its answers.
Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.
What the versions crossed ask of code already here — which no merge can do — is written to
.slipwai/catch-up.md, git-ignored and disposable.
Next: /catch-up, which reads .slipwai/catch-up.md — what these versions ask of code already here — and
runs make verify against it.
```

- **What the merge does.** Every file slipwai wrote becomes what the new version writes for your answers. A
  file you edited as well meets slipwai's change in a normal three-way merge. A clean merge is one commit, or
  two when the harness projections had to be re-derived.
  - On a conflict, the merge is left in progress with each file named. Resolve the files, then run `git add`
    and `git commit`. Or run `git merge --abort` to leave everything as it was.
  - After a clean merge, `git reset --hard ORIG_HEAD` undoes the whole thing.
  - To see what would change before merging anything, run `slipwai replay`, which writes the new version
    beside the project instead of merging it.
- **6.5: the upgrade is not done without it.** A merge can only move files. `/catch-up` does what a merge
  cannot: a gate that now judges older code, or a question the project still has to answer. Skipping it
  leaves the repository on a newer factory with obligations nobody has worked through.
- **Not taking a change.** To keep a file of slipwai's as your own for good, delete its line from `.written`.
  `migrate` then leaves it to you.

[Bring a generated project forward](upgrading.md) is the full recipe.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai generate` | Delete the directory. Nothing else was touched |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
| A `/cruise` decision | Change its `Status` in `decisions.md`, and write your answer into the artifact it names |

---

## Next

| | |
|---|---|
| [Scaffold a new project](generating.md) | Every flag, the interactive form in full, layout, adding a second service |
| [Project shape](axes.md) | What each answer brings, and which combinations are refused |
| [The delivery loop](delivery-loop.md) | `/drive` and the seventeen workflow commands |
| [Cruise](cruise.md) | `/cruise`: `/drive` run on its own until the specification is satisfied |
| [Runsheet: adopt an existing repository](learn-adopt.md) | The other runsheet: the method around code that already exists |
