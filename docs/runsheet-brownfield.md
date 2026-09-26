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
| 1.2 | terminal | `slipwai adopt --experimental-intro --integration claude --init` | it prints the list of directories that build, and asks the one question about your CI |
| 1.3 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.2: the flags.**
  - `--experimental-intro` is the adopt flow this runsheet describes. It stays needed until that flow
    becomes the default.
  - `--integration claude` names your coding agent. Use the key for yours.
  - `--init` runs `./delivery/init` once the adoption is committed. That needs the network.
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
- **4.3: what an adopted repository adds to `/drive`.** It has three extra stages:
  - **Ground:** asks any open row this slice touches
  - **Pin:** runs `/characterise` to record what the existing code does, before changing it
  - **Convergence:** moves a row of the map up when a slice reaches the next rung
- **4.3: moving a capability out.** `/strangle` is how a capability moves out of the old code into a new
  home. `/drive` offers it when the strategy says so.

---

## Phase 5: hand the wheel over (optional)

Run `/drive` by hand at least once and watch where it stops before you do this.

| # | Where | Command | What it does |
|---|---|---|---|
| 5.1 | agent | `/cruise-settings enabled=true max_iterations=3` | Turns cruise on, with a budget of three iterations for the first run |
| 5.2 | agent | `/cruise <what the run is for>` | Starts the runner in the background and shows its feed |
| 5.3 | agent | `/cruise-status` · `/cruise-watch` · `/cruise-tell <a steer>` | Check on the run, take the watch seat again, and queue a message |
| 5.4 | agent | `/cruise-stop` (or `/cruise-stop now`) | Ends the run |
| — | terminal | `make cruise` · `make cruise-status` · `make cruise-stop` | The same controls from a shell |

When a run ends, read these in order:

1. `specs/<feature>/cruise-report.md`
2. `decisions.md`
3. the ADRs it left at `Proposed`
4. each `demo-log.md`
5. the flags

[Cruise](cruise.md) has every setting.

---

## Phase 6: the everyday rhythm

| When | Where | Command |
|---|---|---|
| Coming back to the repository | terminal | `slipwai adopt --next` |
| Starting a session | agent | `/whats-next` |
| A new feature | agent | `/speckit-specify <feature>`, then `/drive` |
| The code's shape changed (a new directory that builds, a runtime version bump) | agent | `/survey`. This is `slipwai adopt --refresh` |
| A row of the map was answered wrongly | agent | `/ground <axis>`, for example `/ground safety-net` |
| A fact about an application was wrong (its commands, purpose or kind) | agent | ask for it to be corrected in `project.json` with `overridden` provenance, then `/survey` |
| Before every push | terminal | `make verify` |

---

## Phase 7: keeping the repository in tune with slipwai

Each slipwai release can change the material it wrote under `delivery/`: the gates, the commands, the skills
and the CI job. Taking those changes is the same three steps as for a generated project, on a clean tree.

| # | Where | Command | Done when |
|---|---|---|---|
| 7.1 | terminal | `slipwai upgrade --check`, then `slipwai upgrade` | `slipwai --version` shows the new version |
| 7.2 | terminal | `git status` | the tree is clean |
| 7.3 | terminal | `slipwai migrate` | one merge commit |
| 7.4 | agent | `/catch-up` | it has worked through `.slipwai/catch-up.md` and `make verify` passes |
| 7.5 | terminal | `slipwai adopt --next` | nothing new is `now`. A release can add a step, and this is where it shows up |
| 7.6 | terminal | `git push` | the gate in CI is green |

- **7.3: what the merge touches.** Only the files listed in `delivery/.written`. Your code and your answers
  in `project.json` carry forward, and a file of slipwai's that you edited meets its change in a normal
  three-way merge.
  - On a conflict, resolve the files and commit, or run `git merge --abort`.
  - After a clean merge, `git reset --hard ORIG_HEAD` undoes it.
  - To keep a file of slipwai's as your own, delete its line from `delivery/.written`.
- **7.4: experimental changes.** While adoption is experimental, a MINOR release can change what it writes.
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
