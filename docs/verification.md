# Gates

`make verify` is the one gate, identical locally and in CI, and it is the contract a generated repository
keeps: run it before and after each increment, and keep `main` releasable.

- [What `make verify` runs](#what-make-verify-runs)
- [What is deliberately outside it](#what-is-deliberately-outside-it)
- [Why the split is where it is](#why-the-split-is-where-it-is)

## What `make verify` runs

It **never needs Docker**, whichever event store the project was given — an event store that needs a
container is exercised by the integration targets, not by the gate every increment pays for.

| Gate | Fails when |
|---|---|
| `typecheck` | The native compiler or static type check rejects the code — `tsc`, mypy with `check_untyped_defs` over the service's `src/` and `tests/`, `go vet`, or `javac` with Error Prone and NullAway |
| `lint` | The native formatting and static-analysis gate rejects it — Biome (rules, formatting and import order in one pass, over every npm package from one `biome.jsonc` at the root), Ruff (`check` and `format --check`), gofmt + `go vet` + staticcheck, or Checkstyle + PMD + SpotBugs |
| `test` | The native suite fails — Vitest, pytest, `go test -coverpkg=./...` with its profile held to the minimum on the Makefile line by `scripts/go-coverage.py` (entry points and integration-tagged suites left out of the count), or JUnit 5 with the framework's own harness |
| `check-imports` | Domain code imports an outer architecture layer, or one bounded context reaches into another's internals |
| `check-styles` *(browser app)* | Two imported stylesheets declare the same custom property at `:root`, so bundle order silently owns the token. Absent without a frontend |
| `check-migrations` | A migration contracts the schema without naming the earlier expand it completes |
| `check-flags` *(production target)* | A feature flag is declared and read nowhere, read and declared nowhere, new and seeded anything but `off`, tested on only one of its two paths, or read by naming `FLAG_<KEY>` instead of calling the service's own reader — which loses the key-to-variable transform and the seam the two paths are driven through. Under `--target none` there is no flag mechanism to gate, so the target is absent rather than passing |
| `check-extensions` | An elected extension's marker-fenced guidance in `AGENTS.md` differs from the current factory source. `make agents` repairs it without rerunning installation or election |
| `check-agents` | An agent projection has drifted from the canonical `skills/`, `commands/` or `agents/` |
| `check-speckit` | A Spec Kit-managed file was edited in place, deleted, or a declared preset override is missing |
| `check-codegraph` *(code index adopted)* | The project has a `.codegraph/` index that no longer describes the tracked source — files it has never seen, or files whose content has changed since it read them. CodeGraph only indexes while a client is attached to its daemon, so a checkout opened where that tooling is absent keeps a database nothing writes to, and a stale index answers *nothing calls that* exactly as an accurate one answers *nothing calls that yet*. With no `.codegraph/` the check says so and passes — the index is an optional extension |
| `check-constitution` | A ratified constitution stopped carrying the floor this project depends on — or, in an adopted repository, a principle marked as a target drifted from the convergence map, or was claimed in force against it |
| `check-model` *(event profile)* | The event model and the repository disagree, or the committed diagram is stale |
| `check-convergence` *(adopted repositories)* | The convergence map claims a rung the tree contradicts, or `docs/convergence.md` was not redrawn after its rows changed |
| frontend build and component tests | The browser app fails to build, or its Testing Library tests fail |

The gate scripts a generated repository ships are deliberately dependency-free — the Python standard library
only — so `make verify` needs no `pip install` of its own in any language.

## What is deliberately outside it

One `make` away, and none of them in the gate:

| Target | Runs | Why it is outside |
|---|---|---|
| `make test-integration` | The integration suite against real backing services | Needs `services-up` and a database; an empty integration suite is a valid starting state |
| `make adversarial` | Tests named or tagged adversarial | An end-of-slice pass, after the demo is accepted, where the slice changed attack surface |
| `make mutation` | The backend's native mutation testing | Minutes, not seconds — an end-of-phase question, not a per-increment one |
| `make audit` | The ecosystem-native dependency-vulnerability audit | Needs the network, and answers a question that does not change between two commits an hour apart |
| `make sonar` *(Sonar extension)* | Runs tests with language-native coverage output, then publishes both to SonarQube or SonarCloud | Needs a remote host, token and scanner; its coverage run is optional analysis, while native lint, typecheck and tests remain the deterministic merge gate |
| `make model` *(event)* | Re-renders the model's diagrams and browsable page | Needs Node and a headless browser; `make check-model` proves the committed output is current without either, which is why *that* one is in the gate |
| `make ci` | The extended gate | Under a production target it also builds every service's production image and runs it against its probe — the half of a deploy provable without an account |
| `make format` | Each family's own formatter over this project's code — Biome over each npm package (a directory under `apps/` or `packages/` that has a `package.json`), `ruff format`, `gofmt` | `lint` already fails on formatting the project has not applied, and this is what applies it. Deliberately not a prerequisite of `verify`: a gate that rewrites the tree it is judging is a gate that always passes. A project whose languages have no formatter has no such target. Biome is not pointed at `.`: `packages/` also holds Go modules, and a formatter that rewrites JSON there is a digest change `make lint` never sees |

The Sonar extension's optional `.github/workflows/sonar.yml` is separate from `verify.yml`. It skips its
scan steps without a `SONAR_TOKEN` secret or an adopted `sonar-project.properties`, so remote availability
cannot change the result deploy and branch protection read from the native gate.

## Why the split is where it is

The gate is the thing you run dozens of times a day, so everything in it has to be fast, deterministic, and
free of infrastructure. Everything that is slow, needs a network, needs Docker, or answers a question that
only changes at the end of a phase sits outside — reachable by name, run when it is worth it, and run in CI
where the wall-clock belongs to a machine.

The one asymmetry worth knowing is the event model's: rendering needs a browser, so it is outside;
*validating* needs nothing but Python, so it is inside. The gate proves the committed diagram matches the
model without ever drawing it.

## Adopted repositories: the ratchet

> Experimental, as everything under [Adopt an existing repository](adopting.md) is.

A repository the method was installed around has a linter and a type checker of its own, and on day one they
are usually red: the rules arrived after the code. `verify` in such a repository runs each wrapped
application's recorded `lint` and `typecheck` through `scripts/ratchet.py`, which holds the command to a
committed **baseline** — `delivery/baseline.json` — and fails only on what is new. A finding is a line of the
command's output naming a file at a position; positions are dropped, so a known finding that moves down its
file is still the same finding, and a line that merely mentions a file is not one. A test runner names the test
rather than a file — `--- FAIL: TestX`, TAP's `not ok 3 - adds`, pytest's `FAILED tests/test_a.py::test_b`,
Surefire's `[ERROR]   ShopTest.adds:42` — and each is a finding too, `test: <name>`, so a second failure beside a
known one is new and named. Where a red command names neither, the exit code is compared instead, and the run
says so.

The baseline is recorded by the first local `verify` — never on CI, where a `CI` variable and a missing entry
fail with the reason, because a baseline nobody looked at is one nobody committed — and only tightens: fixing
findings never fails anything, and `make ratchet-tighten` re-records what is left once somebody has looked.
`test` runs through the same ratchet with one difference: a suite that arrives red stops the first run, which
shows the failures and says what quarantining means, and records nothing — a red suite is a fact about the
software, and whether to ship on it is a person's answer, never one the gate takes behind them. `make
ratchet-tighten`, once they have read the failures, records it as **quarantined**: the run says so every time,
passes on the recorded state, and fails on a new failure the output names — until the suite is green and
`ratchet-tighten` clears the entry; `check-convergence` reports how many tests the quarantine holds. A suite
too slow for `verify` is recorded as `test-full` and has its own target. `smoke` — the application started by
the command it recorded and proved to answer — has its own target too, run by `ci` and by a job of its own in
the gate's workflow, never by `verify` ([Adopt an existing repository](adopting.md#adopt-it) says why and how
it is recorded). `check-convergence` holds the map beside it: a row of
`docs/convergence.md` that claims a rung the tree contradicts fails by name, an `unrecorded` row passes with a
line, and a page rendered from other rows than `project.json` now holds is stale and fails until `/survey`
redraws it ([Adopt an existing repository](adopting.md#the-map)).
The import gate applies its hexagonal rule to what the factory generated, and to a wrapped application only
where its `project.json` record declares `"layout": "hexagonal"`.
