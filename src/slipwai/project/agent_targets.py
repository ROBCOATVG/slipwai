"""The Makefile's agent block: projections, the settings checks, the models table, the benchmark, and `/cruise`'s loop.

Its own module because `makefile.py` sits at the line budget `scripts/check-structure.py` holds every module
to, and because these targets are about the method rather than any service's toolchain: nothing here is per
backend. `check-python` comes first on `verify` because every gate is a `python3 scripts/…` line, and which
interpreter a shell finds first decides whether they run: one older than the scripts is named once, rather than
as whichever gate first uses a newer feature. `check-agents` is where every settings file the ladder reads is held to its shape — the models table,
`drive.json` and `cruise.json` — so a hand edit that would leave `/drive` or `/cruise` reading nonsense fails
the gate rather than the run. `check-decisions` holds the decision log and demo log `/cruise` writes to their
shape, and sits on `verify` because a person overrides a decision by editing that file.
"""
from __future__ import annotations


def agent_targets() -> str:
    """The `.PHONY` block between the npm workspace targets and the native gate targets."""
    return """.PHONY: check-python agents agents-list check-extensions check-agents models check-benchmark benchmark cruise cruise-watch cruise-status cruise-stop cruise-tell check-decisions
check-python: ## Fail, first, when python3 is older than the 3.10 every gate script is written for
\t@python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 'check-python: ' + sys.executable + ' is Python ' + sys.version.split()[0] + ', and the gate scripts need 3.10 or newer; put a newer python3 first on PATH (a non-interactive macOS shell finds /usr/bin/python3, which is 3.9, before Homebrew)')"
agents: ## Refresh elected extensions, then skills, commands and agent types in every installed agent harness
\tpython3 scripts/extensions/project.py
\tpython3 scripts/agents/project.py
agents-list: ## Show every supported harness and which integrations are installed
\tpython3 scripts/agents/project.py --list
check-extensions: ## Fail when elected extension guidance differs from the factory-owned source
\tpython3 scripts/extensions/project.py --check
check-agents: ## Fail when an initialized agent projection has drifted, or .specify/models.json, drive.json or cruise.json is malformed
\tpython3 scripts/agents/project.py --check
\tpython3 scripts/agents/models.py --check && python3 scripts/agents/drive.py --check && python3 scripts/agents/cruise.py --check
models: ## Show which model runs each stage of /drive for the installed harness, and why
\tpython3 scripts/agents/models.py
check-benchmark: ## Fail when the benchmark script's own behaviour regresses; warn of an entry left open or a done slice with no record
\tpython3 scripts/test_benchmark.py && python3 scripts/agents/benchmark.py check
benchmark: ## Show what each slice cost and how each stage of /drive did, from the records under specs/
\tpython3 scripts/agents/benchmark.py
cruise: ## Run /drive with nobody at the wheel, a fresh session per iteration, until the specs are satisfied or a person stops it (FEATURE=<name> to scope it)
\tpython3 scripts/agents/cruise.py run $(if $(FEATURE),--feature $(FEATURE),) $(CRUISE_FLAGS)
cruise-watch: ## Watch a /cruise run from here: what the iteration does as it happens, returning at the iteration's end, a park, or the run's end (CRUISE_FLAGS=\"--minutes 10\" to sit longer)
	python3 scripts/agents/cruise.py watch $(CRUISE_FLAGS)
cruise-status: ## Say whether a /cruise runner is running and what its log shows: iterations run, the last line, whether it is parked and why
\tpython3 scripts/agents/cruise.py status
cruise-stop: ## End a /cruise run after the iteration in flight (CRUISE_FLAGS=--now ends that iteration too)
\tpython3 scripts/agents/cruise.py stop $(CRUISE_FLAGS)
cruise-tell: ## Queue a message for the next /cruise iteration (MSG=\"…\"; CRUISE_FLAGS=--now ends the iteration in flight so it goes at once)
\tpython3 scripts/agents/cruise.py tell $(CRUISE_FLAGS) $(MSG)
check-decisions: ## Fail when a decision log or demo log /cruise wrote has lost its shape
\tpython3 scripts/check-decisions.py
"""
