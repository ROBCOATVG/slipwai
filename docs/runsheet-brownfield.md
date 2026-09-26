# Runsheet: an existing repository (brownfield)

> **Experimental.** As [AGENTS.md](../AGENTS.md#versioning-is-not-optional) defines the word: the files
> `adopt` writes, the facts `project.json` records and the questions it asks may change in a MINOR release.
> Every place this reaches you says so until it stops being true. Report surprises on the issue tracker.

The whole life of an adopted repository as one list of commands, in order, from `slipwai adopt` to
`/cruise` and then on through every slipwai release after it. Each step says where you type it, what it
leaves behind, and how you know it worked. [Adopt an existing repository](adopting.md) has the reasoning;
this page is the sequence.

Where you type each command:

- **terminal**: a shell at the repository root
- **agent**: a session of your coding agent (Claude Code, Codex, Cursor, …), opened at the repository root

**Lost your place?** Run `slipwai adopt --next` in the terminal. It works out where the repository is in
this sequence from the files on disk, and says which step is done, which is now, and which come next. Use
it whenever you come back to a repository.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |

Your repository's own toolchain has to be installed as well: its Node, PHP, JDK or whatever its build
runs. The gate runs the commands your build already has, so it needs what those commands need.

---

## Phase 1: install the method

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `git status` | nothing to commit. `adopt` refuses a tree that is not clean |
| 1.2 | terminal | `slipwai adopt --integration claude` | it prints the list of directories that build, and asks the one question about your CI |
| 1.3 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.2: the flags.**
  - `--integration claude` names your coding agent. Use the key for yours.
  - It then runs `./delivery/init` for you, which needs the network. `--no-init` leaves that to you.
- **1.2: what it writes.** The adoption is one commit, and `git reset --hard HEAD^` undoes exactly that
  commit.
  - The method lives under `delivery/`.
  - Your `AGENTS.md` and `.gitignore` each get one marked block, added once.
  - Your code is never touched.
  - Nothing is recorded as an application yet. The directories that build are only *candidates*.
- **1.3: commit.** `./init` writes Spec Kit and the agent's commands and skills, and does not commit them.
  Committing is optional: nothing in Phase 2 refuses to run over it. A clean starting point makes Phase 2
  one change you can read on its own.

---

## Phase 2: ground it, in the agent

`/ground` asks what the code cannot tell a survey. It reads the code before each question, says what it
thinks and why, and records your answer along with who gave it.

| # | Where | Command | Done when |
|---|---|---|---|
| 2.1 | agent | `/ground` | every candidate is confirmed, declined or deliberately left open. Each row of the map has been asked about, and so has `smoke` for each application |
| 2.2 | terminal | `git add -A && git commit -m "Ground: what the code could not say"` | `git status` is clean |

What `/ground` asks, in this order:

1. **How much to explain.** Pick the long form the first time. It says what each answer commits you to.
2. **Which directories are applications.** An application here means *a directory whose build the gate
   holds*, which is not the same thing as a directory that gets deployed.
   - **Confirm:** its lint, typecheck and test join `make verify`, which every change has to pass: yours,
     `/drive`'s and `/cruise`'s.
   - **Decline:** nothing is recorded, and the gate ignores that directory.
   - **Leave it open:** it is asked again next time. This is the right answer when you are unsure, because
     neither a confirm nor a decline can be taken back by a command yet.
3. **The nine rows of the convergence map.** These are path to production, integration, safety net,
   structure, platform, constitution, data, infrastructure and strategy.
4. **`smoke` for each application.** This is the command that starts it and proves it answers. `/drive`
   will not change an application until one is recorded.

`/ground` records answers one at a time, then runs `/survey` so the generated pages follow, and asks you to
commit **once**, at step 2.2. Don't commit between answers. Once you have committed, `/ground <axis>` asks
about one row again.

---

## Phase 3: prove the gate and settle the strategy

| # | Where | Command | Done when |
|---|---|---|---|
| 3.1 | terminal | `make verify` | it ends with `verify: all gates passed` |
| 3.2 | terminal | `git add delivery/baseline.json && git commit -m "Gate baseline"` | the baseline is committed |
| 3.3 | terminal | add `-include delivery/Makefile` to your root `Makefile` | `make verify` works as one word. Skip this if `adopt` wrote the root `Makefile` itself |
| 3.4 | agent | accept the strategy ADR: change its `Status` to `Accepted` and commit it | `slipwai adopt --next` shows the strategy as decided |

- **3.1: which command.** Until 3.3 is done, the gate is `make -f delivery/Makefile verify`.
- **3.1: the first run.** It records the lint and typecheck findings already in the code as the baseline,
  and only new findings fail after that. A failing test suite stops the run and says so. Read the
  failures, then either fix them or quarantine them on purpose with `make ratchet-tighten`.
- **3.4: the strategy.** `/ground` writes the ADR at `Proposed`, recommending one of five strategies
  (`leave-it`, `in-place`, `modular-monolith`, `strangler-fig`, `rewrite`). `leave-it` is as real an answer
  as the others. A recommendation is not a
  decision: you accept the ADR, and an agent never does. To change your mind later, write an ADR that
  supersedes it.

---

## Phase 4: the first feature

Every command in this phase is typed in the **agent**.

| # | Command | What it does | Done when |
|---|---|---|---|
| 4.1 | `/speckit-constitution` | Writes the principles. On an adopted repository, a principle the map says is not reachable yet is written as a *journey* target | `make check-constitution` passes |
| 4.2 | `/speckit-specify <the feature>` | Writes the first feature as a specification | `specs/<feature>/spec.md` exists |
| 4.3 | `/drive` | Takes one slice from wherever it stands to a demo | it stops at the demo and asks you a question only you can answer |

- **4.1: do it before 4.2.** `check-constitution` fails as soon as `specs/` exists over the template.
- **4.3: what an adopted repository adds to `/drive`.** Three stages — Ground, Pin and Convergence —
  described with the loop in Phase 5.

---

## Phase 5: the development loop

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

On an adopted repository the same ladder has three more stages, and they are the difference between changing
code that already exists and writing new code:

- **Ground**, before everything: an open row of the map that this slice touches is asked about first.
- **Pin**, before implementation: `/characterise` records what the existing code does at the seam the slice
  will change, as tests, so that the change is measured against what the code did rather than what somebody
  remembers. It refuses "full coverage first", which is where these programmes stall.
- **Convergence**, after the slice: the map is re-checked, a row moves up a rung when the slice reached it,
  and the next row nobody has planned is offered as a *method slice* — work on the delivery method itself,
  such as getting a test suite green in CI, which goes into the split like any other slice.

Where the strategy is `strangler-fig`, a slice can be `/strangle`: one capability moved out of the old code
into a new home behind a routing seam, with a row in `retirement.md`.

A day with it looks like this:

| When | Where | Command |
|---|---|---|
| Coming back to the repository | terminal | `slipwai adopt --next` |
| Starting a session | agent | `/whats-next`: one line saying what to do next, and why |
| Doing the work | agent | `/drive`, and answer what it asks |
| Checking where things stand | agent | `/where-are-we`: the progress board, slices done, in progress and blocked |
| A new feature | agent | `/speckit-specify <feature>`, then `/drive` |
| The code's shape changed (a new directory that builds, a runtime version bump) | agent | `/survey`. This is `slipwai adopt --refresh` |
| A row of the map was answered wrongly | agent | `/ground <axis>`, for example `/ground safety-net` |
| A fact about an application was wrong (its commands, purpose or kind) | agent | ask for it to be corrected in `project.json` with `overridden` provenance, then `/survey` |
| Before every push | terminal | `make verify` |
| Another service or frontend | agent | `/add-service`, `/add-frontend` |

---

## Phase 6: `/drive` or `/cruise`

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

## Phase 7: setting `/cruise` goals, and letting it run

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
| 7.1 | agent | `/cruise-settings enabled=true max_iterations=3` | Turns cruise on, with a small budget for the first run. This commits `.specify/cruise.json` |
| 7.2 | agent | edit `.specify/product-owner.md` | Says what matters, what breaks ties and what is out of scope |
| 7.3 | agent | `/cruise <what this run is for>` | Starts the runner in the background and shows its feed in this session |
| 7.4 | agent | `/cruise-status` · `/cruise-watch` · `/cruise-tell <a steer>` | Check on it, sit back down at the feed, steer it |
| 7.5 | agent | `/cruise-stop` (or `/cruise-stop now`) | Ends it after the iteration in flight, or at once |
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

## Phase 8: keeping the repository in tune with slipwai

Each slipwai release can change the material it wrote under `delivery/`: the gates, the commands, the skills
and the CI job. Taking those changes is the same three steps as for a generated project, on a clean tree.

| # | Where | Command | Done when |
|---|---|---|---|
| 8.1 | terminal | `slipwai upgrade --check`, then `slipwai upgrade` | `slipwai --version` shows the new version |
| 8.2 | terminal | `git status` | the tree is clean |
| 8.3 | terminal | `slipwai migrate` | one merge commit |
| 8.4 | agent | `/catch-up` | it has worked through `.slipwai/catch-up.md` and `make verify` passes |
| 8.5 | terminal | `slipwai adopt --next` | nothing new is `now`. A release can add a step, and this is where it shows up |
| 8.6 | terminal | `git push` | the gate in CI is green |

- **8.3: what the merge touches.** Only the files listed in `delivery/.written`. Your code and your answers
  in `project.json` carry forward, and a file of slipwai's that you edited meets its change in a normal
  three-way merge.
  - On a conflict, resolve the files and commit, or run `git merge --abort`.
  - After a clean merge, `git reset --hard ORIG_HEAD` undoes it.
  - To keep a file of slipwai's as your own, delete its line from `delivery/.written`.
- **8.4: experimental changes.** While adoption is experimental, a MINOR release can change what it writes.
  The catch-up note says what each change asks of you, and `/catch-up` is where you deal with it.
- **`/survey` is not `migrate`.** `migrate` brings slipwai's new material in. `/survey` re-reads *your*
  code. Run `/survey` when your code changed, and `migrate` when slipwai did.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai adopt` | `git reset --hard HEAD^`. The adoption is exactly one commit |
| An answer in `/ground`, not yet committed | `git checkout -- project.json`, then `/survey` |
| A row of the map, already committed | `/ground <axis>` asks it again |
| A confirmed or declined candidate, already committed | No command yet: revert the commit that recorded it |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
