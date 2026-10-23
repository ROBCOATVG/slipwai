# Runsheet: generate a new project

**This page lists every step in the life of a generated repository, in order.** It starts from an empty
machine, goes to a fleet that cruises, and continues through every slipwai release after that. Each step
says where you type it and how you know that it worked. This page gives the sequence. The guide pages that
each phase links to give the reasons.

Where you type each command:

- **terminal** — a shell at the repository root
- **agent** — a session of your coding agent (Claude Code, Codex, Cursor, …) opened at the repository root
- **board** — the page `slipwai` opens, served from this machine only

Slash commands are written as Claude Code spells them. Codex takes them as skills, so in Codex `/sail` is
`$sail`.

**Where a step has a slash command, type that.** `/cruise`, `/cruise-tell`, `/cruise-stop`, `/launch` and the
rest run the project's `make` target for you and read the result back, so you stay in the session you are
already working in. The `make` target of the same name is what they run underneath, and is named here only
where no command covers the step.

---

## Phase 0: once per machine

| # | Where | Command | Done when |
|---|---|---|---|
| 0.1 | terminal | `uv tool install slipwai` | `slipwai --version` prints a version |
| 0.2 | terminal | `git --version`, `python3 --version` | Git is installed, and Python is 3.11 or newer |
| 0.3 | terminal | `slipwai install typescript` (or `python`, `go`, `java-spring`, …) | it names the package, its version and its publisher; `slipwai search` lists it as `installed` |
| 0.4 | terminal | `slipwai bridge install` — optional | the board is up whenever you log in, and your browser offers to put it in the dock |

- **0.1.** `pipx install slipwai` and `pip install --user slipwai` also work. The releases page also has a
  standalone executable that needs only Git.
- **0.3.** The keel knows no languages. The chandlery has them. The first time that you install from a new
  publisher, the command asks you to confirm that publisher, once. `slipwai search postgres` searches what
  packages *answer*, not their names. See [start here](start-here.md#2-get-a-language).
- **0.4.** This installs a login service for your own account: launchd, a systemd user unit, or the Startup
  folder. It does not need root. `slipwai bridge uninstall` removes it.

---

## Phase 1: create the repository

| # | Where | Command | Done when |
|---|---|---|---|
| 1.1 | terminal *or* board | `slipwai generate` — or `slipwai`, then *Start a project* | it prints `created: <path>` and runs `./init` in the new project |
| 1.2 | terminal | `cd <name>` | you are at the project's root; start your coding agent here |
| 1.3 | terminal | `./init`, only if 1.1 did not run it | Spec Kit, the skills and the commands are installed for your agent |
| 1.4 | agent | `/verify` | it says `verify: all gates passed` |
| 1.5 | terminal | `git add -A && git commit -m "Install Spec Kit"` | `git status` is clean |

- **1.1: the questions.** The questions come in this order: a quickstart (six are included, and
  `slipwai quickstart list` names them), Event Modeling, the production target, the language, the service
  and its contexts, the browser app, the write model, persistence, who signs in, and where the project
  goes. Press Enter to take every default. [Start here](start-here.md#3-generate-the-repository) has the
  whole transcript, and says what each answer costs to change later. **You cannot reverse the write
  model.**
- **1.1: from a document.** The last two questions take a requirements document, or the folder that
  contains it (`--prd <file>`, `--brief <dir>`). The command copies the document in as `docs/prd.md`. On
  the board, the first specification is then drafted from it for you, and Phase 2 starts at 2.3.
- **1.1: for scripts and CI.** Every answer is also a flag: for example,
  `slipwai generate bookings --quickstart laptop-trial`, or each axis one by one.
  `slipwai generate --help` lists the flags. The flag form does not run `./init` unless you give `--init`.
- **1.3: extensions.** `./init` offers the extensions that are installed on this machine. The board asks the
  same thing as *Dev tooling* checkboxes. `./init --extension <key>` adds an extension later. See
  [extensions](../extensions.md).
- **1.5.** `./init` writes its files, but does not commit them.

---

## Phase 2: the first feature

| # | Where | Command | Done when |
|---|---|---|---|
| 2.1 | agent | `/sail` | it has asked you to ratify the constitution, and `make check-constitution` passes |
| 2.2 | agent | `/speckit-specify <the feature, in a sentence or two>` | `specs/<feature>/spec.md` exists |
| 2.3 | agent *or* board | `/sail` — or **Open spec**, then read it | the specification is clarified, checked and its gaps answered |
| 2.4 | agent *or* board | `/mockups` — or **Draw the surfaces**, then **Approve storyboard** | every surface state is approved, parked with its question, or `n/a` with a reason |
| 2.5 | agent *or* board | the event-modeling skill | `docs/event-model/model.yaml` names the commands, events and read models; standard profile: skip |
| 2.6 | agent *or* board | `/sail` — it writes the chart on the standard profile and renders it from the model on the event-modelling profile — or **Continue the build**, which in the agent is `/launch` | `check-chart` passes: every mark typed, one setter each |
| 2.7 | agent | `/sail` | the first slice reaches its demo and asks you to accept it |

- **2.1: why it starts here.** `/sail` finds the stage from the files on disk. An unratified constitution
  is the first thing that is missing. Every later stage is judged against the constitution.
- **2.3: what `/sail` runs.** First `/speckit-clarify`. Then `/speckit-checklist` and the find-gaps survey,
  side by side. Then `/gaps`, with you. A question that you answer now costs a sentence. Later, it costs a
  slice.
- **2.4 to 2.6: on the board.** By default, the specification, the storyboard and the model each stop for
  you. On the **Who answers** settings tab, set *The specification, storyboard and model* to **advance on
  their own** to let the board start each next step itself. See [the board](the-board.md).
- **2.6: standard profile.** There is no model to render the chart from, so `/chart` writes the chart with
  you.
- **2.7: per slice.** Each slice goes through clearance, the claim, the example map, plan and tasks, and
  `/speckit-analyze`. Then it goes through RED-GREEN-REFACTOR one increment at a time, with the examples
  proven by tests, a review of the slice's own diff, its trigger record, and the merge. When a capability's
  last slice has merged, the capability's gates run once: converge, gaps, design review, adversary (where a
  slice widened a trigger), mutation, and the hand's walk. Then its demo runs.
  [Your first feature](first-feature.md) goes through every stage.
  [From the board](first-feature.md#from-the-board) shows the same ladder from the Voyage tab.

**Where am I?** None of these commands changes anything:

- `/where-are-we` in the agent, or the board's **Voyage** tab: which stage you are at, and what proves it
- `python3 scripts/agents/clearance.py`: which slices can start now, and what each blocked slice waits for
- `slipwai fleet`: the state of every fairway, calculated from the logs

---

## Phase 3: a further feature

| # | Where | Command | Done when |
|---|---|---|---|
| 3.1 | agent | `/sail <the request, or a path to a document>` | it is written under `docs/intake/` and you are asked whether it is really a new feature |
| 3.2 | agent | answer yes, then go | Spec Kit's assessment has run and the next `specs/<feature>/spec.md` exists |
| 3.3 | agent *or* board | `/sail` — or **Continue the next feature** | the new feature is on the ladder at Phase 2's step 2.3 |

A further feature uses the profile that the project already has.

---

## Phase 4: more than one of you

| # | Where | Command | Done when |
|---|---|---|---|
| 4.1 | terminal | `git pull` | the other machines' commits are here |
| 4.2 | agent | `/sail fairway=<name>` | it has landed every deck log and in-flight branch from the other machines (`make arrive`, which it runs itself), you hold one fairway, and the others' ready slices are named and left |
| 4.3 | agent | `/cruise-status` | both fairways are listed, each with its own slice |

A slice is cleared as soon as the mark that it steers by is **set**, not when that mark merges. The slice
that owns the mark sets it at its first stage, in its own worktree. See
[a second person joins](a-second-person.md).

---

## Phase 5: let it cruise

| # | Where | Command | Done when |
|---|---|---|---|
| 5.1 | agent | `/cruise-settings enabled=true` | `.specify/cruise.json` says `enabled: true` |
| 5.2 | terminal | `slipwai telegraph slow-ahead` | `slipwai telegraph` shows the position; start slow |
| 5.3 | agent *or* board | `/cruise` — or **Cast off the fleet** | a harbourmaster and a captain per fairway are running, and the command has exited |
| 5.4 | agent *or* board | `/cruise-status`, `/cruise-watch` — or the Voyage tab | lines arrive in the deck logs |
| 5.5 | agent *or* board | `/cruise-tell <fairway> <what it should know>` — or the answer box on the waiting line | the captain writes a `read` line at its next boundary. A message to a parked fairway also clears the park |
| 5.6 | agent *or* board | `/cruise-stop` — or **Stop the fleet** | every captain parks at the end of the stage it is in |

Three things still stop for a person: mock-up approval, the demo, and the decision ceiling. The board's
**Settings** box has a tab each for speed, fine tune, who answers at each stop, delegation and models. The
project's own scripts write each setting. See [let it cruise](let-it-cruise.md).

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

- **6.4.** Each file that slipwai wrote becomes what the new version writes for your answers. If you also
  edited a file, your edit meets the change in a three-way merge. `slipwai migrate --check` says what would
  happen. `slipwai replay` writes the new version beside the project, and does not merge it.
- **6.5: the upgrade is not complete without this step.** A merge moves files. `/catch-up` does what a merge
  cannot do. For example, a gate now judges older code, or the project still has a question to answer.
- **From version 1.** Use the same steps.
  [What is new since version 1](../whats-new.md#crossing-a-project-slipwai-migrate) says what the move
  costs.

---

## Undo

| You just ran | To undo it |
|---|---|
| `slipwai generate` | Delete the directory. Nothing else was touched |
| `slipwai migrate` (clean) | `git reset --hard ORIG_HEAD` |
| `slipwai migrate` (conflicted) | `git merge --abort` |
| `/cruise` | `/cruise-stop` — captains finish the stage they are in |
| `slipwai bridge install` | `slipwai bridge uninstall` |
| A decision a cruising run took | Change its `Status` in `specs/<feature>/decisions.md` and write your answer into the artefact it names |

---

## Next

[Start here](start-here.md) · [your first feature](first-feature.md) · [a second person joins](a-second-person.md) ·
[let it cruise](let-it-cruise.md) · [runsheet: adopt an existing repository](runsheet-adopt.md) ·
[the vocabulary](../../GLOSSARY.md)
