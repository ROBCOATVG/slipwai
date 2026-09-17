# The factory's own local and CI entry points. `make verify` is the gate, and it is the same command here
# and in .github/workflows/verify.yml — the rule this factory writes into every project it generates.
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the available targets
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{ printf "  %-18s %s\n", $$1, $$2 }'

.PHONY: install
install: ## Install the pinned development tooling into .python-tools
	./scripts/verify --install-only

.PHONY: lint
lint: ## Run ruff over the factory's own source, scripts and tests
	./scripts/verify --lint-only

.PHONY: typecheck
typecheck: ## Byte-compile everything, then type-check it with mypy
	python3 -m compileall -q src scripts tests
	./scripts/verify --typecheck-only

.PHONY: check-structure
check-structure: ## Fail when a module imports against the declared direction, cycles, or outgrows its budget
	python3 scripts/check-structure.py

# The suite, or a slice of it: `TESTS="test_matrix test_add_service"` runs those modules, `SKIP="test_matrix"`
# every module but those. CI holds the gate in parallel jobs this way; `make verify` still runs the whole suite.
ALL_TESTS := $(patsubst tests/%.py,%,$(wildcard tests/test_*.py))
TESTS ?= $(if $(SKIP),$(filter-out $(SKIP),$(ALL_TESTS)),)
.PHONY: test
test: ## Run the factory's test suite, or a slice: TESTS="test_a test_b", or SKIP="test_a"
	$(if $(TESTS),PYTHONPATH=src:tests python3 -m unittest -v $(TESTS),PYTHONPATH=src python3 -m unittest discover -s tests -v)

.PHONY: verify
verify: lint typecheck check-structure test ## Full local gate — the same one CI runs
	@echo
	@echo 'verify: all gates passed'

.PHONY: changelog
changelog: ## List the commits since the last VERSION bump, for the changelog.d/ fragment they owe
	@python3 scripts/changelog-draft.py $(VERSION)

.PHONY: release
release: ## Turn the snapshot on main into a release: commit, tag v<release>, open the next snapshot, push
	python3 scripts/tag-release.py $(RELEASE_ARGS)

.PHONY: test-migration
test-migration: ## Generate at the last release tag, replay at HEAD, merge, and hold the result to its own gate
	python3 scripts/test-migration.py $(MIGRATION_ARGS)

.PHONY: test-adoption
test-adoption: ## Adopt each fixture repository, re-survey, verify, migrate from a newer factory, verify again (experimental)
	python3 scripts/test-adoption.py $(ADOPTION_ARGS)

.PHONY: starters
starters: ## Materialize every starter combination under build/ for inspection
	python3 scripts/regenerate-starters.py

.PHONY: locks
locks: ## Rebuild every committed dependency lock (needs network)
	python3 scripts/regenerate-locks.py

.PHONY: check-locks
check-locks: ## Report a stale committed lock, changing nothing (needs network)
	python3 scripts/regenerate-locks.py --check

.PHONY: executable
executable: ## Build the standalone slipwai executable
	./scripts/build-executable

.PHONY: test-executable
test-executable: executable ## Build it, then prove it scaffolds with Git alone
	python3 scripts/smoke-executable.py dist/slipwai$(if $(filter Windows_NT,$(OS)),.exe,)

.PHONY: package-executable
package-executable: test-executable ## Build, prove, and package it for release
	python3 scripts/package-executable.py dist/slipwai$(if $(filter Windows_NT,$(OS)),.exe,)

.PHONY: wheel
wheel: ## Build the pip-installable package (wheel and sdist) into dist/
	./scripts/build-wheel

.PHONY: test-wheel
test-wheel: wheel ## Build it, install it into a throwaway venv, then prove it scaffolds with Git alone
	./scripts/smoke-wheel

.PHONY: publish-wheel
publish-wheel: test-wheel ## Build, prove, and upload it: PYPI_URL, PYPI_INDEX and PYPI_USER; PYPI_TOKEN from the environment
	PYTHONPATH=.build-tools/publish python3 scripts/publish-wheel.py --url "$(PYPI_URL)" --index-url "$(PYPI_INDEX)" --user "$(PYPI_USER)"

.PHONY: publish-release
publish-release: ## Attach release/* to a tag's release: FORGE_URL, FORGE_REPO and TAG; GITEA_TOKEN from the environment
	python3 scripts/publish-release.py --api "$(FORGE_URL)/api/v1" --repository "$(FORGE_REPO)" --tag "$(TAG)" release/*
