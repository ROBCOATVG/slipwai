# Runsheet: adopt an existing repository

**This page lists every step in the life of an adopted repository, in order.** It starts at
`slipwai adopt`, goes to a fleet that cruises, and continues through every slipwai release after that. This
is *adopt the method*, not *generate the skeleton*. You do not have to decide between a strangler and a
rewrite first. This page gives the sequence. [Bring an existing codebase](adopt.md) gives the reasons.

Where you type each command:

- **terminal** — a shell at the repository root
- **agent** — a session of your coding agent opened at the repository root
- **board** — the page `slipwai` opens, served from this machine only

**Lost your place?** `slipwai adopt --next` works out where the repository is in this sequence, from the
files on disk. It says which steps are done, which step is now, and which steps come next. Run it each time
that you come back to a repository.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |

You must also install your repository's own toolchain: its Node, its JDK, or whatever its build uses. The
gate runs the commands that your build already has, so the gate needs what those commands need.

---

## Phase 1: install the method

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `git status` | nothing to commit. `adopt` refuses a tree that is not clean, and a directory that is not a Git repository |
| 1.2 | terminal *or* board | `slipwai adopt --integration claude` — or `slipwai`, then *Adopt a repository* | it lists the directories that build, asks where your CI runs, commits, and runs `./delivery/init` |
| 1.3 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.2: the one question.** Where CI runs is a fact about your forge, not about your code. So it is the
  only question. Each directory that builds is recorded as a **candidate**, not as an application. Which
  candidates the gate should hold is a question that the code answers, in Phase 2.
- **1.2: the flags.** `--integration <agent>` names your coding agent. `--delivery <dir>` puts the method
  somewhere other than `delivery/`. `--yes` asks nothing, confirms every candidate without looking at it,
  and records each fact as `detected`. `--no-init` leaves `./delivery/init` for you to run.
- **1.2: what it writes.** One commit, beside your code: the method under `delivery/`, one marked block in
  each of your `AGENTS.md` and `.gitignore`, and a `project.json` that holds the record. It never touches
  your code or your `README.md`. `git reset --hard HEAD^` undoes exactly that commit.
- **1.3.** `./delivery/init` writes Spec Kit and the agent's commands and skills, but does not commit
  them.

---

## Phase 2: ground it, in the agent

| # | Where | Command | Done when |
|---|---|---|---|
| 2.1 | agent | `/ground` | every candidate is confirmed, declined or deliberately left open, and every row of the map has been asked about |
| 2.2 | terminal | `git add -A && git commit -m "Ground: what the code could not say"` | `git status` is clean |

Before each question, `/ground` reads the code and says what it thinks and why. It records your answer
with its **provenance**: `confirmed` or `overridden` mean that a person answered, and `detected` means only
that the tree was read. `/ground` asks these questions, in this order:

1. which directories are applications (an application is a directory whose build the gate holds)
2. the rows of the convergence map, one at a time
3. `smoke`, for each application

Commit once, at 2.2.

The same answers from the terminal:

```sh
slipwai adopt --confirm api
slipwai adopt --confirm worker --language worker=python --purpose "worker=overnight settlement"
slipwai adopt --decline tools
slipwai adopt --as admin=admin-ui
```

---

## Phase 3: prove the gate and settle the strategy

| # | Where | Command | Done when |
|---|---|---|---|
| 3.1 | agent | `/verify` | it says `verify: all gates passed` |
| 3.2 | terminal | `git add delivery/baseline.json && git commit -m "Gate baseline"` | the baseline is committed |
| 3.3 | terminal | add `-include delivery/Makefile` to your root `Makefile` | `make verify` works as one word. Skip it if `adopt` wrote the root `Makefile` itself |
| 3.4 | agent | accept the strategy ADR: set its `Status` to `Accepted` and commit it | `slipwai adopt --next` shows the strategy as decided |

- **3.1: the first run** records the lint and typecheck findings that are already in the code as the
  baseline. After that, only new findings fail. **A red test suite stops the run, and the run says so.**
  Fix the suite, or tell `/verify` to put it in quarantine on purpose, which it records with
  `make ratchet-tighten`. Until you do 3.3, `/verify`
  runs the gate as `make -f delivery/Makefile verify`.
- **3.4: the strategy.** `/ground` writes the ADR (architecture decision record) at `Proposed`. It
  recommends one of `leave-it`, `in-place`, `modular-monolith`, `strangler-fig` or `rewrite`. `leave-it` is
  as valid an answer as the others. You accept the ADR. An agent never accepts it.

---

## Phase 4: the first feature

An adopted repository uses the **standard profile**. `/chart` writes the chart with you. The chart is not
rendered from a model. Everything after the chart is the same as in a generated project.

| # | Where | Command | Done when |
|---|---|---|---|
| 4.1 | agent | `/sail` | it has asked you to ratify the constitution, and `make check-constitution` passes |
| 4.2 | agent | `/speckit-specify <the feature>` | `specs/<feature>/spec.md` exists |
| 4.3 | agent | `/sail` | the specification is clarified and its gaps answered, the mock-ups approved, and `/chart` has written the chart with you |
| 4.4 | agent | `/sail` | the first slice reaches its demo and asks you to accept it |

- **4.1.** If the map says that a principle cannot be reached yet, the principle is written as a
  *journey* target. It is not written as a rule that the code already breaks.
- **4.4: what adoption adds to the ladder.**
  - **Ground**, before everything: if the slice touches an open row, `/sail` asks about that row first.
  - **Pin**, before implementation: `/characterise` records, as tests, what the existing code does at the
    seam that the slice will change. The change is then measured against what the code did before.
  - **Demo**, after implementation: when the slice's examples are proven, the map is checked again. A row
    moves up a rung when the slice reached that rung.

After this, the steps are the same as for a generated project. A further feature, a second person and
cruising are [Phases 3 to 5 of the generate runsheet](runsheet-generate.md#phase-3-a-further-feature). On
an adopted repository, where a person's answer is missing, a cruising run continues on stated assumptions
and writes `Proposed` records. You confirm or reverse them afterwards.

**Fairways are useful only where your code has seams.** If one directory holds everything, you have one
fairway: a well-gated loop for a single worker. `skills/finding-seams/SKILL.md` describes how to get from
one fairway to two.

---

## Phase 5: keeping the record and the repository in tune

| # | Where | Command | Done when |
|---|---|---|---|
| 5.1 | terminal | `slipwai adopt --refresh` | it surveys again, refreshes what was only detected, and reports what now disagrees with what a person decided |
| 5.2 | terminal | `slipwai upgrade --check`, then `slipwai upgrade` | `slipwai --version` shows the new version |
| 5.3 | terminal | `git status` | the tree is clean |
| 5.4 | terminal | `slipwai migrate` | one merge commit |
| 5.5 | agent | `/catch-up` | it has worked through `.slipwai/catch-up.md` and `make verify` passes |
| 5.6 | terminal | `slipwai adopt --next` | nothing new is `now` — a release can add a step, and this is where it shows up |
| 5.7 | terminal | `git push` | the gate in CI is green |

`--refresh` never writes over a person's answer with a new guess. It says where the two now disagree.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai adopt` | `git reset --hard HEAD^` — the adoption is one commit |
| `/ground`, before 2.2 | `git checkout -- .` |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
| An accepted strategy | Write the ADR that supersedes it |

---

## Next

[Bring an existing codebase](adopt.md) · [your first feature](first-feature.md) ·
[let it cruise](let-it-cruise.md) · [runsheet: generate a new project](runsheet-generate.md) ·
[the vocabulary](../../GLOSSARY.md)
