# The keel's own local and CI entry points. There are two gates, not one, and this file is where the
# difference is spelled: `make unit` with `make lint` and `make typecheck` is what an increment inside a
# slice runs, and `make verify` is what runs once on the rebased branch before `main` and again in CI.
# Never the full gate in the inner loop — that rule cost the first attempt more than any other.
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the available targets
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{ printf "  %-18s %s\n", $$1, $$2 }'

.PHONY: install
install: ## Install the pinned development tooling into .python-tools
	./scripts/verify --install-only

.PHONY: lint
lint: ## Run ruff over the keel's own source, scripts and tests
	./scripts/verify --lint-only

.PHONY: typecheck
typecheck: ## Byte-compile everything, then type-check it with mypy
	python3 -m compileall -q src scripts tests
	./scripts/verify --typecheck-only

# `.python-tools` is on the path beside `src`, because the pinned tooling is where PyYAML is: the suite
# reads YAML that nothing in `src/` does, and a test that imports it has to find the version this
# repository pinned rather than whatever the machine happens to carry.
TEST_PATH := src:.python-tools
# The suite, or a slice of it: `TESTS="test_registry test_cli"` runs those modules, `SKIP="test_registry"`
# every module but those. CI holds the gate in parallel jobs this way; `make verify` still runs the whole
# suite.
ALL_TESTS := $(patsubst tests/%.py,%,$(wildcard tests/test_*.py))
TESTS ?= $(if $(SKIP),$(filter-out $(SKIP),$(ALL_TESTS)),)
.PHONY: test
test: ## Run the keel's test suite, or a slice: TESTS="test_a test_b", or SKIP="test_a"
	$(if $(TESTS),PYTHONPATH=$(TEST_PATH):tests python3 -m unittest -v $(TESTS),PYTHONPATH=$(TEST_PATH) python3 -m unittest discover -s tests -v)

# The fast half of the suite: everything that does not generate a project, shell out, or reach the network.
# A slice that adds a test of that kind adds its module to SLOW in the same commit, because the value of
# this target is entirely in it staying quick — an increment that waits on the full suite stops being run.
# Measured 2026-10-07, not guessed: `test_upgrade` stands up an HTTP server and shells out (6.5s) and
# `test_conformance` shells out per check (2.5s), and between them they were nine of this target's twelve
# seconds while never having been listed. The rest spawn a subprocess per case. `test_captain` runs a real
# `/drive` process and waits for a wall budget to run out (23s), which is the shape of what it proves.
SLOW := test_generated test_upgrade test_conformance test_target_conformance test_chart test_chart_render test_slice_scope test_surfaces test_captain test_captain_gate test_merge test_bridge test_loop
UNIT_TESTS := $(filter-out $(SLOW),$(ALL_TESTS))
.PHONY: unit
unit: ## The fast tests only — the per-increment gate, with the slow modules left out
	$(if $(UNIT_TESTS),PYTHONPATH=$(TEST_PATH):tests python3 -m unittest $(UNIT_TESTS),@echo 'unit: no test modules yet')

.PHONY: glossary
glossary: ## Rewrite GLOSSARY.md from the plan's vocabulary (tests/test_glossary.py holds them in step)
	python3 scripts/glossary.py

.PHONY: release check-release changelog
release: verify ## Assemble the entry, write VERSION, commit and tag. The gate first, always
	python3 scripts/tag-release.py
check-release: ## Fail when the fragments and VERSION disagree about what the next release is
	@python3 scripts/tag-release.py --check
changelog: ## Show the entry the fragments in flight would make, without writing anything
	@python3 scripts/tag-release.py --dry-run

.PHONY: shared check-shared
shared: ## Carry the modules both runtimes need from the keel into the toolkit
	python3 scripts/shared-modules.py
check-shared: ## Fail when a carried module is not what its keel source renders to
	@python3 scripts/shared-modules.py --check

.PHONY: skills
skills: ## Copy the toolkit's and the maintainer's skills into .claude/skills for this checkout (ignored by git)
	python3 -c "import pathlib, shutil; d = pathlib.Path('.claude/skills'); shutil.rmtree(d, ignore_errors=True); shutil.copytree('assets/toolkit/skills', d); [shutil.copytree(s, d / s.name) for s in sorted(pathlib.Path('maintainer/skills').iterdir()) if s.is_dir()]"
	@echo "skills: .claude/skills written from assets/toolkit/skills and maintainer/skills — edit those, never this copy"

.PHONY: progress
progress: ## Tick off in the plan the slices the history says are done
	python3 scripts/progress.py

.PHONY: next
next: ## What can be brought back next, and what each remaining module waits on
	python3 scripts/bring-back.py

.PHONY: executable
executable: ## Build the standalone slipwai executable
	./scripts/build-executable

.PHONY: test-executable
test-executable: executable ## Build it, then prove it scaffolds with Git alone
	python3 scripts/smoke-executable.py dist/slipwai$(if $(filter Windows_NT,$(OS)),.exe,)

.PHONY: starters
starters: ## Materialise every starter combination under build/ for inspection
	python3 scripts/regenerate-starters.py

# Not in `verify`, and deliberately: it generates two projects, drives the interview, renders the model
# through Node and runs the full generated gate, which is a minute or two. The inner loop stops being run
# the moment it is not quick. It runs in CI on every change, which is where a page drifts from the keel.
.PHONY: test-docs
test-docs: ## Run every command the first three guide pages print, against a fresh generation
	python3 scripts/test-docs.py

.PHONY: check-structure
check-structure: ## Fail when a module imports against the declared direction, cycles, or outgrows its budget
	python3 scripts/check-structure.py
	python3 scripts/bring-back.py --check

.PHONY: verify
verify: lint typecheck check-structure check-shared check-release test ## Full local gate — the same one CI runs
	@echo
	@echo 'verify: all gates passed'
