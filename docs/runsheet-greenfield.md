# Runsheet: a new project (greenfield)

The whole life of a generated repository as one list of commands, in order, from an empty directory to
`/cruise` and then on through every slipwai release after it. Each step says where you type it, what it
leaves behind, and how you know it worked. The reasoning behind each step is in the pages linked from it;
this page is the sequence.

Where you type each command:

- **terminal**: a shell at the repository root
- **agent**: a session of your coding agent (Claude Code, Codex, Cursor, …), opened at the repository root

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |

You also need the toolchain of whichever language you are going to pick (Node, Python, Go or a JDK), and
Docker if you choose Postgres or Keycloak. [Tools required](requirements.md) lists them all.

---

## Phase 1: create the repository

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `slipwai generate` | it prints `created: <path>` |
| 1.2 | terminal | `cd <name>` | |
| 1.3 | terminal | `./init` | it has asked which coding agent to use, and then offered the optional extensions |
| 1.4 | terminal | `make verify` | it ends with `verify: all gates passed` |
| 1.5 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.1: answering the questions.** This asks the profile, the production target, the language, the service
  and the frontend, one at a time, and shows each default. To skip the questions, give every answer as a
  flag: `slipwai generate ledger --profile event-modelling --target none --language typescript --frontend
  react-vite --event-store postgres --http fastify`. [Project shape](axes.md) says what each answer brings.
- **1.3: agent and extensions.** `./init` installs Spec Kit, then copies the commands and skills into the
  agent you name. `./init --integration claude` names the agent without asking. `./init --extension
  codegraph` adds the code index, now or at any later time.
- **1.5: commit.** A generated project starts as one commit. `./init` writes its files and does not commit
  them, which is what 1.5 is for.

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

## Phase 3: hand the wheel over (optional)

Run `/drive` by hand at least once and watch where it stops before you do this.

| # | Where | Command | What it does |
|---|---|---|---|
| 3.1 | agent | `/cruise-settings enabled=true max_iterations=3` | Turns cruise on, with a budget of three iterations for the first run. This commits `.specify/cruise.json` |
| 3.2 | agent | `/cruise <what the run is for, or where the PRD is>` | Starts the runner in the background and shows its feed in this session |
| 3.3 | agent | `/cruise-status` · `/cruise-watch` · `/cruise-tell <a steer>` | Check on the run, take the watch seat again, and queue a message for the next iteration |
| 3.4 | agent | `/cruise-stop` (or `/cruise-stop now`) | Ends the run after the iteration in flight, or immediately |
| — | terminal | `make cruise` · `make cruise-status` · `make cruise-stop` | The same controls from a shell |

When a run ends, read what it did in this order:

1. `specs/<feature>/cruise-report.md`
2. `specs/<feature>/decisions.md`: change a decision's `Status` to overturn it
3. the ADRs it left at `Proposed`: accept each one, or write the one that supersedes it
4. each slice's `demo-log.md`
5. the flags: nothing a run merges is visible to a real user until you turn its flag on

[Cruise](cruise.md) has every setting.

---

## Phase 4: the everyday rhythm

| When | Where | Command |
|---|---|---|
| Starting a session | agent | `/whats-next` |
| A new feature | agent | `/speckit-specify <feature>`, then `/drive` until it is done |
| A slice changed its attack surface | agent | `/adversary` (`/drive` also runs it at the end of a split) |
| Measuring the tests | agent | `/mutation` |
| Another service or frontend | agent | `/add-service`, `/add-frontend` |
| Before every push | terminal | `make verify` |

---

## Phase 5: keeping the repository in tune with slipwai

Each slipwai release can change the files it generated for you: the gates, the commands, the skills and CI.
Taking those changes is three steps, on a clean tree, as often as releases come out. Checking weekly, or
whenever the changelog says something you want, is a good rhythm.

| # | Where | Command | Done when |
|---|---|---|---|
| 5.1 | terminal | `slipwai upgrade --check` | it says whether a newer version is published. It changes nothing |
| 5.2 | terminal | `slipwai upgrade` | `slipwai --version` shows the new version |
| 5.3 | terminal | `git status` | the tree is clean. Commit or stash first, because `migrate` refuses otherwise |
| 5.4 | terminal | `slipwai migrate` | it prints `migrated <name> from <old> to slipwai <new>`, as one merge commit |
| 5.5 | agent | `/catch-up` | it has worked through `.slipwai/catch-up.md` and `make verify` passes |
| 5.6 | terminal | `git push` | the gate in CI is green |

- **5.4: what the merge does.** Every file slipwai wrote becomes what the new version writes for your
  answers. A file you edited as well meets slipwai's change in a normal three-way merge.
  - On a conflict, the merge is left in progress with each file named. Resolve the files, then run
    `git add` and `git commit`. Or run `git merge --abort` to leave everything as it was.
  - After a clean merge, `git reset --hard ORIG_HEAD` undoes the whole thing.
  - To see what would change before merging anything, run `slipwai replay`, which writes the new version
    beside the project instead of merging it.
- **5.5: the upgrade is not done without it.** A merge can only move files. `/catch-up` does what a merge
  cannot: a gate that now judges older code, or a question the project still has to answer.
- **Not taking a change.** To keep a file of slipwai's as your own for good, delete its line from
  `.written`. `migrate` then leaves it to you.

[Bring a generated project forward](upgrading.md) is the full recipe.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai generate` | Delete the directory. Nothing else was touched |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
| A `/cruise` decision | Change its `Status` in `decisions.md`, and write your answer into the artifact it names |
