# Runsheet: adopt an existing repository

**The whole life of an adopted repository as one list of steps, in order** — from `slipwai adopt` to a
fleet cruising, and on through every slipwai release after it. This is *adopt the method*, not *generate
the skeleton*: nothing about strangler-versus-rewrite has to be decided first.
[Bring an existing codebase](adopt.md) has the reasoning; this page is the sequence.

Where you type each command:

- **terminal** — a shell at the repository root
- **agent** — a session of your coding agent opened at the repository root
- **board** — the page `slipwai` opens, served from this machine only

**Lost your place?** `slipwai adopt --next` works out where the repository is in this sequence from the
files on disk, and says which step is done, which is now, and which come next. Run it whenever you come
back to a repository.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.10 or newer |

Your repository's own toolchain has to be installed as well — its Node, JDK or whatever its build runs.
The gate runs the commands your build already has, so it needs what they need.

---

## Phase 1: install the method

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal | `git status` | nothing to commit. `adopt` refuses a tree that is not clean, and a directory that is not a Git repository |
| 1.2 | terminal *or* board | `slipwai adopt --integration claude` — or `slipwai`, then *Adopt a repository* | it lists the directories that build, asks where your CI runs, commits, and runs `./delivery/init` |
| 1.3 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.2: the one question.** Where CI runs is a fact about your forge, not your code, so it is the only
  thing asked. Every directory that builds is recorded as a **candidate**, not an application: which of
  them the gate should hold is a question the code answers, in Phase 2.
- **1.2: the flags.** `--integration <agent>` names your coding agent. `--delivery <dir>` puts the method
  somewhere other than `delivery/`. `--yes` asks nothing and confirms every candidate unlooked-at, each
  fact recorded `detected`. `--no-init` leaves `./delivery/init` for you.
- **1.2: what it writes.** One commit, beside your code: the method under `delivery/`, one marked block
  each in your `AGENTS.md` and `.gitignore`, and a `project.json` holding the record. Your code and your
  `README.md` are never touched. `git reset --hard HEAD^` undoes exactly that commit.
- **1.3.** `./delivery/init` writes Spec Kit and the agent's commands and skills, and does not commit them.

---

## Phase 2: ground it, in the agent

| # | Where | Command | Done when |
|---|---|---|---|
| 2.1 | agent | `/ground` | every candidate is confirmed, declined or deliberately left open, and every row of the map has been asked about |
| 2.2 | terminal | `git add -A && git commit -m "Ground: what the code could not say"` | `git status` is clean |

`/ground` reads the code before each question, says what it thinks and why, and records your answer with
its **provenance** — `confirmed` or `overridden` are a person's word; `detected` is only the tree's reading.
It asks which directories are applications (a directory whose build the gate holds), then the rows of the
convergence map one at a time, then `smoke` for each application. Commit once, at 2.2.

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
| 3.1 | terminal | `make verify` | it ends with `verify: all gates passed` |
| 3.2 | terminal | `git add delivery/baseline.json && git commit -m "Gate baseline"` | the baseline is committed |
| 3.3 | terminal | add `-include delivery/Makefile` to your root `Makefile` | `make verify` works as one word. Skip it if `adopt` wrote the root `Makefile` itself |
| 3.4 | agent | accept the strategy ADR: set its `Status` to `Accepted` and commit it | `slipwai adopt --next` shows the strategy as decided |

- **3.1: the first run** records the lint and typecheck findings already in the code as the baseline; only
  new ones fail after that. **A red test suite stops the run and says so** — fix it, or quarantine it on
  purpose with `make ratchet-tighten`. Until 3.3 is done the gate is `make -f delivery/Makefile verify`.
- **3.4: the strategy.** `/ground` writes the ADR at `Proposed`, recommending one of `leave-it`,
  `in-place`, `modular-monolith`, `strangler-fig` or `rewrite`. `leave-it` is as real an answer as the
  others. You accept it; an agent never does.

---

## Phase 4: the first feature

An adopted repository runs the **standard profile**: the chart is written by `/chart` with you rather than
rendered from a model, and everything downstream of it is the same as a generated project's.

| # | Where | Command | Done when |
|---|---|---|---|
| 4.1 | agent | `/sail` | it has asked you to ratify the constitution, and `make check-constitution` passes |
| 4.2 | agent | `/speckit-specify <the feature>` | `specs/<feature>/spec.md` exists |
| 4.3 | agent | `/sail` | the specification is clarified and its gaps answered, the mock-ups approved, and `/chart` has written the chart with you |
| 4.4 | agent | `/sail` | the first slice reaches its demo and asks you to accept it |

- **4.1.** A principle the map says is not reachable yet is written as a *journey* target, not a rule the
  code already breaks.
- **4.4: what adoption adds to the ladder.** **Ground** before everything — an open row the slice touches
  is asked about first. **Pin** before implementation — `/characterise` records what the existing code
  does at the seam the slice will change, as tests, so the change is measured against what the code did.
  **Demo** after it — once the slice's examples are proven the map is re-checked, and a row moves up a rung
  when the slice reached it.

From here the rest is the generated project's: a further feature, a second person, and cruising are
[Phases 3 to 5 of the generate runsheet](runsheet-generate.md#phase-3-a-further-feature). On an adopted
repository a cruising run proceeds on stated assumptions and `Proposed` records where a person's word is
missing, and you confirm or overturn them afterwards.

**Fairways are only worth drawing where your code has seams.** One directory holding everything is one
fairway — a well-gated single-worker loop. `skills/finding-seams/SKILL.md` is how to get from there to two.

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

`--refresh` never overwrites a person's answer with a fresh guess; it says where the two now disagree.

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
