# Extensions — optional dev-tooling hooks, and what a second one owes

An **extension** is an opt-in developer-tooling integration a generated project can adopt with `./init
--extension <key>` (repeatable, alongside `--integration <agent>`). It is not an axis: it never changes the
generated skeleton's code, and it is answered later than generation — at `./init` time, the same moment a
Spec Kit agent integration is chosen — rather than baked into `apps`/`Selection` when `./slipwai generate` runs.
CodeGraph (a local MCP code-knowledge graph, https://github.com/colbymchenry/codegraph) is the first one.

## What ships where

- **`catalog.json`**'s `extensions` object declares the public contract per key: `name`, `description`, and
  an optional `ignore` string — gitignore lines the extension's local state needs (e.g. `.codegraph/`).
  `ignore` is applied unconditionally in every generated `.gitignore`, whether or not the extension is ever
  adopted: an ignored path that does not exist yet costs nothing, and it means adopting the extension later
  never needs a second edit to `.gitignore`.
- **`assets/toolkit/scripts/extensions/<key>/init.py`** is the executable half, copied into every generated
  project like the rest of `assets/toolkit/` and run as `python3 scripts/extensions/<key>/init.py` by
  `./init --extension <key>`.

## Asking for it

`./init` prompts for extensions at a real terminal when none were named on the command line: a checkbox
menu lists every catalog entry's `name`/`description` — arrow keys (or j/k) move, Enter or Space checks
the highlighted row, a letter jumps to the first row starting with it, a Confirm row at the bottom
finishes with whatever is checked, Escape skips. The list is
framed by a one-line explanation of what is being asked and a key-hint footer, since the prompt appears
unannounced in the middle of `./init`. It reads and writes `/dev/tty`
directly rather than stdin/stdout, so a scripted or CI `./init` (no controlling terminal, or `--extension`
already given) gets silence and no extensions, never a hang and never a silent default-adopt. Nothing here
is specific to `codegraph`: the menu's options come from `catalog.json["extensions"]`, so a second entry
appears in it automatically.

Adopting an extension later is the same command again — `./init --extension <key>` — and such a rerun
leaves Spec Kit alone: once `.specify/integration.json` records an installed integration, `./init` skips
the bootstrap whenever the argument scan leaves nothing to forward to `specify`, so an extension add (or a
re-answered axis, or a deferred `--repository` push) finishes without the network reach that installing
Spec Kit needs.

The menu itself is `assets/toolkit/scripts/extensions/menu.py` — standalone and dependency-free on purpose,
since it ships *inside* a generated project rather than running from the factory's own package. It is the
multi-select sibling of the single-select arrow-key menu `cli_prompts.py` asks `./slipwai generate`'s own
questions with (same termios/tty raw-mode, ANSI-redraw technique); the two never share code because they
run in different processes with different questions. `./init` feeds it the candidate list as JSON on
stdin — keeping the interactive keys free to come from `/dev/tty`, which `./init` may already have
redirected stdin away from by the time this runs — and captures the chosen keys (one per line) from its
stdout. See `prompt_extensions` in `src/slipwai/project/init_script.py` for the wiring.

## What `init.py` owes

1. **Replaceably idempotent.** Running it twice must not duplicate anything it writes, and newer factory
   guidance must replace the content inside its existing markers without touching text around them.
2. **Non-fatal.** By the time it runs, Spec Kit and the agent projection are already in place — an
   extension whose own CLI is missing, or whose setup step fails, must report that and exit 0, not fail the
   rest of `./init`. `scripts/extensions/codegraph/init.py` is the reference: it prints an install command
   and returns cleanly when `codegraph` is not on `PATH`.
3. **Point the agent at it.** An extension that only gets installed and never queried is dead weight. Project
   a marker-fenced block into `AGENTS.md` (`<!-- extension:<key>:begin -->` / `:end`) — short enough to read in
   one go: what the tool is for, how to tell whether this environment can reach it at all, and that the agent
   should query it through the best route its own session offers. `AGENTS.md` is the one place a pointer can
   reach every agent, rather than a per-skill edit repeated across the shared skill catalogue.

   **Write the block for a checkout that travels.** A repository is opened in places its author never saw — a
   container, a sandbox, a CI runner, a colleague's laptop — and a block that assumes the tool is installed
   because `./init` once installed it is wrong in every one of them where it is not. `codegraph`'s block is
   the reference: it probes MCP, an installed CLI, then `npx`, says what to do only when all routes are
   unavailable, and asks for the route actually used to be named in the answer.

   **`AGENTS.md` is where the pointer goes; it is not where the whole job is done.** An agent working is inside a
   skill's steps, and a specific instruction there beats standing advice read once at the start, so a
   skill that asks for exactly the operation an index performs and does not say to use one sends the reader
   to `grep` by omission.

   So the factory carries its own half, in the two places it owns and regenerates:
   `project/rules.py`'s `CODE_INDEX` puts a *Finding your way around this codebase* section near the top of
   every generated `AGENTS.md`, and the two skills whose instructions name that operation —
   `skills/debugging` ("search every caller") and `skills/refactoring` ("inspect every caller and
   reachability path") — say where to get the answer. All of it is phrased conditionally ("where `AGENTS.md`
   names one"), because an extension is adopted at `./init`, after those files are written: the text is
   identical for every project and true whether or not one was ever adopted.

   The line to hold is *which* skills. Ten of the skills under `assets/toolkit/skills/` are vendored
   third-party at pinned upstream commits with their own `LICENSE` and `references/source-notes.md`
   (`REFERENCES.md` records each one's provenance); an edit there is a conflict on every refresh, for a
   pointer `AGENTS.md` already carries. `tests/test_code_index.py` holds both halves: that the two skills
   the generated section names still say what it claims they say, and that no licensed skill has acquired a
   mention of the index.

   Projecting into `AGENTS.md` is enough, whatever harness is installed. A `canonical` one reads that file
   itself; Claude's `import` mode reads it through an `@AGENTS.md` region that `project.py` owns in
   `CLAUDE.md`; and a `copy` harness (Gemini, Copilot, Cursor and a dozen more in
   `scripts/agents/registry.json`) receives this marker-fenced block in the context file `specify init`
   wrote *before* the extension hooks ran. So `./init` makes one more projection pass after them. `make
   agents` and `slipwai migrate` refresh elected extension blocks before refreshing agent contexts, and
   `make check-extensions` plus `make check-agents` report stale source and copied regions.

   The markers around your own block are still load-bearing: they make the region replaceable. Successful
   adoption records its key in committed `.slipwai/extensions.json`; migration infers that record once from
   markers in older projects. `scripts/extensions/<key>/init.py` must expose a side-effect-free
   `project_guidance()` using `scripts/extensions/guidance.py`, so migration never reruns installation or
   the interactive election.

4. **Gate whatever can go silently stale.** Local state an extension leaves in the tree — an index, a cache,
   a fingerprint — keeps answering after it stops being true, and a wrong answer that arrives confidently is
   worse than no answer. Where that is possible, ship a `scripts/check-<key>.py` and put it in `make verify`
   through the Makefile's `verify` dependencies: standard library only, a clear no-op line when the extension
   was never adopted, and a failure that says what went out of date and how to catch it up.
   `scripts/check-codegraph.py` is the reference — it compares the index's `files` table against the tracked
   source by content hash and reports when the index's own daemon has stopped writing to it.

5. **Say how to finish when you cannot.** A tool that is missing or an install that fails means no pointer
   was written, and the reader is now one command short of an adopted extension. Say which command:
   `./init --extension <key>` again, after the tool is there. `scripts/extensions/codegraph/init.py` is the
   reference for both halves — it names the recovery in each of its two failure paths.

6. **A file the user must hand-edit is a merge target, never a write target.** Where an extension generates a
   file it cannot complete from `project.json` — a scanner's properties file whose organisation key only the
   user knows — read the existing file, rewrite only the keys the extension owns, and leave every other line
   as it was; where that cannot be done, own a fragment the user's file includes rather than the file. A
   `write_text` over such a file deleted a required hand-added key silently, on every `./init`, only on
   machines where the tool happened to be installed, and surfaced weeks later as a failed analysis somewhere
   else. `./init` already declines to touch the shared Spec Kit paths it reports as not updated; an extension
   follows the same pattern.

Nothing else routes through this file's name specially: it reaches a generated project purely because
`assets/toolkit/` is copied as a tree (see `assets/README.md`), the same way a new skill or script does.

## Adding a second extension

1. Add its entry to `catalog.json["extensions"]`.
2. Add `assets/toolkit/scripts/extensions/<key>/init.py` meeting the obligations above, and the gate of
   its own that the fourth asks for where the extension leaves state that can go stale.
3. That's it — `./init --extension <key>` picks it up automatically; nothing in
   `src/slipwai/project/init_script.py` needs to change for a key it does not already know about
   by name.

`.claude/skills/add-extension/` is the procedure that walks these three steps, the tests they need, and the
verification pass — the same relationship `docs/backend-obligations.md` has to `add-language`/
`add-framework`: this file is the contract, that skill is how a maintainer works through it.
