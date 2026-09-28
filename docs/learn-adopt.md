# Runsheet: adopt an existing repository

> **Experimental.** As [AGENTS.md](../AGENTS.md#versioning-is-not-optional) defines the word: the files
> `adopt` writes, the facts `project.json` records and the questions it asks may change in a MINOR release.
> Every place this reaches you says so until it stops being true. Report surprises on the issue tracker.

The whole life of an adopted repository, as one list of steps in order: from `slipwai adopt` to `/cruise`,
and on through every slipwai release after it. Each step says where you type it, what it leaves behind and
how you know it worked, and the transcripts show what you will see. This is **adopt the method**, not
**generate the skeleton**: nothing about strangler-versus-rewrite has to be decided first.
[Adopt an existing repository](adopting.md) has the reasoning; this page is the sequence.

Where you type each command:

- **terminal**: a shell at the repository root
- **agent**: a session of your coding agent (Claude Code, Codex, Cursor, …), opened at the repository root

Commands are written the way Claude Code spells them: `/ground`, `/drive`. Other agents differ. Codex takes
them as skills, so you type `$ground` and `$drive`. Codex also runs commands in a sandbox that cannot rewrite
its own skills, so when slipwai reports that *the harness projections could not be re-derived*, run
`make agents` in a terminal.

**Lost your place?** Run `slipwai adopt --next` in the terminal. It works out where the repository is in
this sequence from the files on disk, and says which step is done, which is now, and which come next. Use
it whenever you come back to a repository.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |

- **0.1: why uv.** It is the recommended installer, and `./delivery/init` uses it too: to fetch Spec Kit,
  and to give the `python3` on your PATH the PyYAML that Spec Kit's scripts need. Alternatives are in
  [Install the command](executable.md).
- **Your repository's own toolchain** has to be installed as well: its Node, PHP, JDK or whatever its build
  runs. The gate runs the commands your build already has, so it needs what those commands need.

---

## Phase 1: install the method

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `git status` | nothing to commit. `adopt` refuses a tree that is not clean |
| 1.2 | terminal | `slipwai adopt --integration claude` | it prints the list of directories that build, asks the one question about your CI, commits, and runs `./delivery/init` |
| 1.3 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

**1.2: what you see.** Start at the **root** of the repository. `adopt` surveys the tree, shows every
directory that builds, and asks one question: where your CI runs, which is a fact about your forge rather
than your code. In the list, ↑/↓ move and Enter chooses:

```text
Adopt the delivery method here (experimental). The survey read the tree; what it
found is below. Nothing here is recorded as an application yet: which of these the gate should hold,
what each is called and what it owns are questions the code answers, and the agent asks them with the
code in front of it. This asks the one thing the tree cannot settle on its own.

2 directories that build:
  .   python      from requirements.txt  (2 of 8 targets have a command)
  ui  javascript  from ui/package.json  (3 of 8 targets have a command)

Where does this repository's CI run? (decides what shape the gate's CI
configuration can take, which is a fact about your forge and not about your
code)
    github — GitHub — the gate is an Actions workflow under .github/workflows
    gitea — Gitea or Forgejo — the same Actions workflow, which they run too
    gitlab — GitLab — the gate is a job to include from .gitlab-ci.yml
    other — Jenkins, Azure, Bitbucket, CircleCI or another — nothing is written;
    your CI runs the gate's command
  ❯ none — no CI runs this repository — nothing is written until one does
CI forge: none
adopted legacy-worker with slipwai 1.4.0 — experimental: this path is new, its shape may change in a MINOR, …
291 files written under delivery/ and beside it; nothing of the repository's own was written over. One
commit by the factory; `git reset --hard HEAD^` undoes all of it.
  2 buildable directories, none of them recorded as an application yet — what each is, what it is called
  and what it owns are questions the code answers:
    . (python, from requirements.txt), 2 of 8 targets have a command
    ui (javascript, from ui/package.json), 3 of 8 targets have a command
  Until one is confirmed, `verify` refuses rather than passing over nothing: /ground asks about each with
  the code in front of it, and `slipwai adopt --confirm <name>` records the answer.
…

Running ./delivery/init --integration claude — it installs Spec Kit, which needs the network.
```

- **1.2: the flags.**
  - `--integration claude` names your coding agent; use the key for yours. Without it, the agent is taken
    from the one you ran `adopt` inside, where there is one, and otherwise `./delivery/init` asks.
  - In a terminal, `adopt` runs `./delivery/init` for you once the adoption is committed. It needs the
    network, and `--no-init` leaves it to you. It asks the same questions as a generated project's `./init`:
    the agent, then the optional extensions as a checkbox menu (Escape skips; `--extension <key>` adds one
    later).
  - On native Windows it runs through Git Bash when that is installed, and otherwise says to use WSL or Git
    Bash. Without `python3` it names the command that installs it on your machine and does not start.
  - `--delivery <dir>` puts the method somewhere other than `delivery/`.
  - `--yes` is the unattended path: nothing is asked, `./delivery/init` is left for you, and every directory
    that builds is confirmed as an application unlooked-at, each fact recorded `detected`. Outside a terminal
    without `--yes`, `adopt` refuses rather than guessing.
- **1.2: what it writes.** The adoption is one commit, and `git reset --hard HEAD^` undoes exactly that
  commit.
  - The method lives under `delivery/`.
  - Your `README.md` is left alone. Your `AGENTS.md` and `.gitignore` each get one marked block, added once.
  - Your root `.gitattributes`, if you have one, is left alone; `delivery/.gitattributes` keeps the method's
    own scripts LF in a Windows clone.
  - Your code is never touched.
  - Without `--yes`, nothing is recorded as an application yet. The directories that build are only
    *candidates*, and which of them is an application — a directory whose build the gate holds — is
    `/ground`'s first question ([ADR 0003](adr/0003-a-wrapped-application-begins-as-a-candidate.md)).
- **1.3: commit.** `./delivery/init` writes Spec Kit and the agent's commands and skills, and does not commit
  them. Committing is optional: nothing in Phase 2 refuses to run over it. A clean starting point makes
  Phase 2 one change you can read on its own.

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

- **3.1: which command.** Where your repository had no root `Makefile`, `adopt` wrote one, and `make verify`
  works from the start. Where it had one, `adopt` left it alone, and until 3.3 is done the gate is
  `make -f delivery/Makefile verify`.
- **3.1: the first run.** It records the lint and typecheck findings already in the code as the baseline,
  and only new findings fail after that. A failing test suite stops the run and says so. Read the
  failures, then either fix them or quarantine them on purpose with `make ratchet-tighten`.
- **3.4: the strategy.** `/ground` writes the ADR at `Proposed`, recommending one of five strategies
  (`leave-it`, `in-place`, `modular-monolith`, `strangler-fig`, `rewrite`). `leave-it` is as real an answer
  as the others. A recommendation is not a decision: you accept the ADR, and an agent never does. To change
  your mind later, write an ADR that supersedes it.

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

The loop is the one a generated project runs, stage for stage:
[the generate runsheet's Phase 3](learn-generate.md#phase-3-the-development-loop) has it. On an adopted
repository the same ladder has three more stages, and they are the difference between changing code that
already exists and writing new code:

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

## Phase 6: `/drive` or `/cruise`, and `/cruise` goals

These are the same as for a generated project, so they are written once:
[`/drive` or `/cruise`](learn-generate.md#phase-4-drive-or-cruise) says which to use when, and
[setting `/cruise` goals](learn-generate.md#phase-5-setting-cruise-goals-and-letting-it-run) says what a goal
is, how to queue several features, when a run stops and what to read when it ends. `/cruise` runs the same
ladder as `/drive`, so on an adopted repository it runs the three extra stages above as well.

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

**7.1: upgrade the command**, the same as for a generated project:

```text
$ slipwai upgrade
slipwai 1.3.0, installed as: uv tool
newest published: 1.4.0
running: uv tool upgrade slipwai
```

`slipwai upgrade --pre` counts the snapshot of `main` as well. An installation configured for a private
mirror may still need that mirror's credentials; [Upgrade it](executable.md#upgrade-it) has the detail.

**7.3: migrate, from the repository root:**

```text
$ slipwai migrate
migrated legacy-worker from 1.3.0 to slipwai 1.4.0: 32 files
One merge commit. The files this project had changed itself were kept; the rest are what the
factory now generates for its answers.
Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.
What the versions crossed ask of code already here — which no merge can do — is written to
.slipwai/catch-up.md, git-ignored and disposable.
Next: /catch-up, which reads .slipwai/catch-up.md — what these versions ask of code already here — and
runs make verify against it.
```

- **7.3: what the merge touches.** Only the files listed in `delivery/.written`. Your code and your answers
  in `project.json` carry forward, and a file of slipwai's that you edited meets its change in a normal
  three-way merge.
  - On a conflict, resolve the files and commit, or run `git merge --abort`.
  - After a clean merge, `git reset --hard ORIG_HEAD` undoes it.
  - To keep a file of slipwai's as your own, delete its line from `delivery/.written`.
- **7.4: the upgrade is not done without it.** While adoption is experimental, a MINOR release can change
  what it writes. The catch-up note says what each change asks of you, and `/catch-up` is where you deal
  with it. Skipping it leaves the method on a newer factory with obligations nobody has worked through.
- **`/survey` is not `migrate`.** `migrate` brings slipwai's new material in. `/survey` re-reads *your*
  code. Run `/survey` when your code changed, and `migrate` when slipwai did.

[Bring a generated project forward](upgrading.md) is the full recipe; adoption-specific notes stay in
[Adopt an existing repository](adopting.md).

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

---

## Next

| | |
|---|---|
| [Adopt an existing repository](adopting.md) | Survey, flags, convergence map, ratchet, what it forfeits |
| [The two workflows](two-workflows.md) | Generated and adopted side by side |
| [Gates](verification.md) | The ratchet and day-one green |
| [Runsheet: generate a new project](learn-generate.md) | The other runsheet: a fresh skeleton from answers |
