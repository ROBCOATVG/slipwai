"""The Makefile's agent block: projections, the settings checks, the models table, the benchmark, and `/cruise`'s loop.

Its own module because `makefile.py` sits at the line budget `scripts/check-structure.py` holds every module
to, and because these targets are about the method rather than any service's toolchain: nothing here is per
backend. `check-python` comes first on `verify` because every gate is a `python3 scripts/…` line, and which
interpreter a shell finds first decides whether they run: one older than the scripts is named once, rather than
as whichever gate first uses a newer feature. `check-agents` is where every settings file the ladder reads is held to its shape — the models table,
`sail.json` and `cruise.json` — so a hand edit that would leave `/sail` or `/cruise` reading nonsense fails
the gate rather than the run. `check-decisions` holds the decision log and demo log `/cruise` writes to their
shape, and sits on `verify` because a person overrides a decision by editing that file.
"""
from __future__ import annotations


def agent_targets() -> str:
    """The `.PHONY` block between the npm workspace targets and the native gate targets."""
    return """.PHONY: check-python preflight arrive depart dispatch hooks crossing agents agents-list check-extensions check-agents models check-benchmark benchmark cruise cruise-watch cruise-status cruise-stop cruise-tell draft assess surfaces model-next launch check-decisions
check-python: ## Fail, first, when python3 is older than the 3.10 every gate script is written for
\t@python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 'check-python: ' + sys.executable + ' is Python ' + sys.version.split()[0] + ', and the gate scripts need 3.10 or newer; put a newer python3 first on PATH (a non-interactive macOS shell finds /usr/bin/python3, which is 3.9, before Homebrew)')"
preflight: ## Check once, in a fresh worktree, that an increment can run here: toolchains, caches, a socket, the index
	python3 scripts/agents/preflight.py
arrive: ## Land what other machines wrote: every deck log and in-flight branch pushed since this checkout last looked
\tpython3 scripts/agents/travel.py --arrive
depart: ## Push what this machine wrote, so the next machine — or the cloud — reads the same loop state
\tpython3 scripts/agents/travel.py --depart
dispatch: hooks ## Record what starts now and with what — or that this session could not delegate, and why
\tpython3 scripts/agents/preflight.py --record
\tpython3 scripts/agents/dispatch.py $(DISPATCH_FLAGS)
hooks: ## Point this checkout at .githooks, so a push naming unplanned or undispatched work is refused here
\tpython3 scripts/check-crossing.py --fix-hooks
crossing: ## What a migration could not carry: charts, marks, statuses, log refs, hooks. CROSSING_FLAGS="--strict" to fail
\tpython3 scripts/check-crossing.py $(CROSSING_FLAGS)
agents: ## Refresh elected extensions, then skills, commands and agent types in every installed agent harness
\tpython3 scripts/extensions/project.py
\tpython3 scripts/agents/project.py
agents-list: ## Show every supported harness and which integrations are installed
\tpython3 scripts/agents/project.py --list
check-extensions: ## Fail when elected extension guidance has drifted, or an extension's own gate says no
\tpython3 scripts/extensions/project.py --check
\tpython3 scripts/extensions/hooks.py check --fatal
check-agents: ## Fail when an initialized agent projection has drifted, or .specify/models.json, sail.json or cruise.json is malformed
\tpython3 scripts/agents/project.py --check
\tpython3 scripts/agents/models.py --check && python3 scripts/agents/sail.py --check && python3 scripts/agents/cruise.py --check
models: ## Show which model runs each stage of /sail for the installed harness, and why
\tpython3 scripts/agents/models.py
check-benchmark: ## Fail when the benchmark script's own behaviour regresses; warn of an entry left open or a done slice with no record
\tpython3 scripts/test_benchmark.py && python3 scripts/agents/benchmark.py check
benchmark: ## Show what each slice cost and how each stage of /sail did, from the records under specs/
\tpython3 scripts/agents/benchmark.py
cruise: ## Cast off: start the harbourmaster and a captain per fairway, and exit. Nothing is left holding the state of the run
\tpython3 scripts/agents/fleet.py start
cruise-watch: ## Watch the fleet from here: every stream's lines as they are written, returning after a minute and a half (CRUISE_FLAGS=\"--minutes 10\" to sit longer)
\tpython3 scripts/agents/fleet.py watch $(CRUISE_FLAGS)
cruise-status: ## What is running: the harbourmaster and each captain, with their pids. `slipwai fleet` is what they are doing
\tpython3 scripts/agents/fleet.py list
cruise-stop: ## Ask the harbourmaster and every captain to stop. A captain stops at its next boundary
\tpython3 scripts/agents/fleet.py stop
cruise-tell: ## Tell one stream something; its captain reads it at the next boundary (STREAM=<name> MSG=\"…\"; CRUISE_FLAGS=--everyone tells them all)
\tpython3 scripts/agents/fleet.py tell $(CRUISE_FLAGS) $(STREAM) $(MSG)
draft: ## Draft the constitution and the first specification from a PRD in a headless session, and stop for a person to read it (PRD=<path>; default docs/prd.md)
\tpython3 scripts/agents/draft.py $(PRD)
assess: ## Assess one idea /sail captured, and specify it only after a yes and a go (SLUG=<name>)
\tpython3 scripts/agents/assess.py $(SLUG)
surfaces: ## Research, draft and storyboard this feature's surfaces in a headless session, and stop for a person to approve each state (FEATURE=<name>; default the first specified)
\tpython3 scripts/agents/surfaces.py $(FEATURE)
model-next: ## Model the product from an approved storyboard, and stop before the chart
\tpython3 scripts/agents/model.py
launch: ## Continue the build from a drafted specification: chart and split it in a headless session, enable /cruise and cast off (CRUISE_FLAGS="--boilers <n>")
\tpython3 scripts/agents/launch.py $(CRUISE_FLAGS)
check-decisions: ## Fail when a decision log or demo log /cruise wrote has lost its shape
\tpython3 scripts/check-decisions.py
"""
