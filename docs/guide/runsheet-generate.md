# Runsheet: generate a new project

**The whole life of a generated repository as one list of steps, in order** — from an empty machine to a
fleet cruising, and on through every slipwai release after it. Each step says where you type it and how
you know it worked. The reasoning is on the guide pages each phase links to; this page is the sequence.

Where you type each command:

- **terminal** — a shell at the repository root
- **agent** — a session of your coding agent (Claude Code, Codex, Cursor, …) opened at the repository root
- **board** — the page `slipwai` opens, served from this machine only

Slash commands are written the way Claude Code spells them. Codex takes them as skills, so `/sail` is
`$sail` there.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.10 or newer |
| 0.3 | terminal | `slipwai install typescript` (or `python`, `go`, `java-spring`, …) | it names the package, its version and its publisher; `slipwai search` lists it as `installed` |
| 0.4 | terminal | `slipwai bridge install` — optional | the board is up whenever you log in, and your browser offers to put it in the dock |

- **0.1.** `pipx install slipwai` and `pip install --user slipwai` work too, and the releases page has a
  standalone executable that needs only Git.
- **0.3.** The keel knows no languages; the chandlery has them. The first install from a publisher you have
  not met asks once. `slipwai search postgres` searches what packages *answer*, not their names.
  [Start here](start-here.md#2-get-a-language).
- **0.4.** A login service for your own account — launchd, systemd user unit, or the Startup folder — and
  no root. `slipwai bridge uninstall` removes it.

---

## Phase 1: create the repository

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal *or* board | `slipwai generate` — or `slipwai`, then *Start a project* | it prints `created: <path>` and runs `./init` in the new project |
| 1.2 | terminal | `cd <name>` | you are at the project's root; start your coding agent here |
| 1.3 | terminal | `./init`, only if 1.1 did not run it | Spec Kit, the skills and the commands are installed for your agent |
| 1.4 | terminal | `make verify` | it ends with `verify: all gates passed` |
| 1.5 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.1: the questions.** A quickstart first — six are carried, `slipwai quickstart list` names them —
  then Event Modeling, the production target, the language, the service and its contexts, the browser
  app, the write model, persistence, who signs in, and where the project goes. Enter takes every default.
  [Start here](start-here.md#3-generate-the-repository) has the whole transcript and what each answer
  costs to change later; **the write model is the one that cannot be walked back**.
- **1.1: from a document.** The last two questions take a requirements document, or the folder it sits in
  (`--prd <file>`, `--brief <dir>`). It is copied in as `docs/prd.md`, and on the board the first
  specification is drafted from it for you — Phase 2 then starts at 2.3.
- **1.1: for scripts and CI.** Every answer is a flag: `slipwai generate bookings --quickstart
  laptop-trial`, or the axes one by one. `slipwai generate --help` lists them. The flag form does not run
  `./init` unless given `--init`.
- **1.3: extensions.** `./init` offers the extensions installed on this machine; the board asks the same
  thing as *Dev tooling* checkboxes. `./init --extension <key>` adds one later. [Extensions](../extensions.md).
- **1.5.** `./init` writes its files and does not commit them.

---

## Phase 2: the first feature

| # | Where | Command | Done when |
|---|---|---|---|
| 2.1 | agent | `/sail` | it has asked you to ratify the constitution, and `make check-constitution` passes |
| 2.2 | agent | `/speckit-specify <the feature, in a sentence or two>` | `specs/<feature>/spec.md` exists |
| 2.3 | agent *or* board | `/sail` — or **Open spec**, then read it | the specification is clarified, checked and its gaps answered |
| 2.4 | agent *or* board | `/mockups` — or **Draw the surfaces**, then **Approve storyboard** | every surface state is approved, parked with its question, or `n/a` with a reason |
| 2.5 | agent *or* board | the event-modeling skill, then `make model` | `docs/event-model/model.yaml` names the commands, events and read models; standard profile: skip |
| 2.6 | terminal *or* board | `make chart && make check-chart` — or **Continue the build** | `check-chart` passes: every mark typed, one setter each |
| 2.7 | agent | `/sail` | the first slice reaches its demo and asks you to accept it |

- **2.1: why it starts here.** `/sail` works out the stage from what is on disk, and an unratified
  constitution is the first thing missing. Everything later is judged against it.
- **2.3: what `/sail` runs.** `/speckit-clarify`, then `/speckit-checklist` beside the find-gaps survey,
  then `/gaps` with you. Each question answered now costs a sentence; later it costs a slice.
- **2.6: standard profile.** There is no model to render from, so `/chart` writes the chart with you.
- **2.7: per slice.** Clearance, the claim, the example map, plan and tasks, `/speckit-analyze`, then
  RED-GREEN-REFACTOR one increment at a time, convergence, the examples proven by tests, review, the
  adversary where identity, authority or money widened, and the merge. Once a capability's last slice has
  merged, its gates — converge, gaps, design review, adversary, mutation, the hand's walk — run once, then its
  demo.
  [Your first feature](first-feature.md) walks every stage, and
  [from the board](first-feature.md#from-the-board) is the same ladder from the Voyage tab.

**Where am I?** None of these changes anything:

- `/where-are-we` in the agent, or the board's **Voyage** tab — which stage, and what proves it
- `python3 scripts/agents/clearance.py` — which slices may start now, and what each blocked one waits on
- `slipwai fleet` — every fairway's state, folded from the logs

---

## Phase 3: a further feature

| # | Where | Command | Done when |
|---|---|---|---|
| 3.1 | agent | `/sail <the request, or a path to a document>` | it is written under `docs/intake/` and you are asked whether it is really a new feature |
| 3.2 | agent | answer yes, then go | Spec Kit's assessment has run and the next `specs/<feature>/spec.md` exists |
| 3.3 | agent *or* board | `/sail` — or **Continue the next feature** | the new feature is on the ladder at Phase 2's step 2.3 |

A further feature stays on the profile the project already has.

---

## Phase 4: more than one of you

| # | Where | Command | Done when |
|---|---|---|---|
| 4.1 | terminal | `git pull`, then `make arrive` | every deck log and in-flight branch from other machines is here |
| 4.2 | agent | `/sail fairway=<name>` | you hold one fairway, and the others' ready slices are named and left |
| 4.3 | terminal | `slipwai fleet` | both fairways are listed, each with its own slice |

A slice is cleared the moment the mark it steers by is **set** — at the setting slice's first stage, in
its own worktree — not when it merges. [A second person joins](a-second-person.md).

---

## Phase 5: let it cruise

| # | Where | Command | Done when |
|---|---|---|---|
| 5.1 | agent | `/cruise-settings enabled=true` | `.specify/cruise.json` says `enabled: true` |
| 5.2 | terminal | `slipwai telegraph slow-ahead` | `slipwai telegraph` shows the position; start slow |
| 5.3 | terminal *or* board | `make cruise` — or **Cast off the fleet** | a harbourmaster and a captain per fairway are running, and the command has exited |
| 5.4 | terminal *or* board | `slipwai fleet`, `make cruise-watch` — or the Voyage tab | lines arrive in the deck logs |
| 5.5 | terminal *or* board | `make cruise-tell MSG="…"` — or the answer box on the waiting line | the captain writes a `read` line at its next boundary |
| 5.6 | terminal *or* board | `make cruise-stop` — or **Stop the fleet** | every captain parks at the end of the stage it is in |

Three things still stop for a person: mock-up approval, the demo, and the decision ceiling. Speed, fine
tune, who answers at each stop, delegation and models are the tabs of the board's **Settings** box, each
written by the project's own scripts. [Let it cruise](let-it-cruise.md).

---

## Phase 6: keeping the repository in tune with slipwai

| # | Where | Command | Done when |
|---|---|---|---|
| 6.1 | terminal | `slipwai upgrade --check` | it says whether a newer version is published, and changes nothing |
| 6.2 | terminal | `slipwai upgrade` | `slipwai --version` shows the new version; installed languages moved with it |
| 6.3 | terminal | `git status` | the tree is clean — `migrate` refuses otherwise |
| 6.4 | terminal | `slipwai migrate` | one merge commit, and `.slipwai/catch-up.md` written |
| 6.5 | agent | `/catch-up` | it has worked through the catch-up and `make verify` passes |
| 6.6 | terminal | `git push` | the gate in CI is green |

- **6.4.** Every file slipwai wrote becomes what the new version writes for your answers; a file you
  edited too meets the change in a three-way merge. `slipwai migrate --check` says what would happen, and
  `slipwai replay` writes the new version beside the project instead of merging it.
- **6.5: the upgrade is not done without it.** A merge moves files. `/catch-up` does what a merge cannot:
  a gate that now judges older code, or a question the project still has to answer.
- **From version 1.** The same steps. [What is new since version 1](../whats-new.md#crossing-a-project-slipwai-migrate)
  says what the crossing costs.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai generate` | Delete the directory. Nothing else was touched |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
| `make cruise` | `make cruise-stop` — captains finish the stage they are in |
| `slipwai bridge install` | `slipwai bridge uninstall` |
| A decision a cruising run took | Change its `Status` in `specs/<feature>/decisions.md` and write your answer into the artefact it names |

---

## Next

[Start here](start-here.md) · [your first feature](first-feature.md) · [a second person joins](a-second-person.md) ·
[let it cruise](let-it-cruise.md) · [runsheet: adopt an existing repository](runsheet-adopt.md) ·
[the vocabulary](../../GLOSSARY.md)
