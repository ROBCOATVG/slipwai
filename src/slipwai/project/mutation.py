"""What `make mutation` does per backend, and why — the prose the generated Makefile carries.

Split out of `backends.py` for the reason `service_layouts.py` was split out of `backing_services.py`:
this is most of the bytes and none of the behaviour, and it is read only by the two modules that build
the Makefile — `project/native_commands.py` for the recipes, `project/makefile.py` for the notes beside
them. It belongs beside those readers rather than in the per-backend contract, the same way every other
piece of generated prose in this package does.

Three notes and one placeholder, keyed per backend rather than per family, and that distinction is
load-bearing here. `make mutation` is run by no gate in a generated project, and by the factory's only for
Go (docs/backend-obligations.md section 2), so what these say is most of what stands between the next
reader and a score they should not trust — and the two Java backends genuinely disagree, because PIT works
under Spring Boot's test harness and times out under Quarkus's.
"""
from __future__ import annotations

from ..backends import APP
from ..services import App, backends_of, services_of

# Gremlins, pinned to a release and run through `go run`, so the tool is never a dependency of the module it
# mutates and the same build runs on every machine. It replaced go-mutesting, whose package loader was
# golang.org/x/tools from 2019 and crashed inside `go/types` on any package importing a module outside the
# standard library — every adapter — so `./...` never reached a project's tests and the target was a
# placeholder. Gremlins loads with a current x/tools; 0.6.0 was run against the generated service with and
# without third-party imports on Go 1.26.5 before this pin was written, and a deliberately weakened test was
# checked to leave survivors and a red target. It requires Go 1.25 or newer: an older `go` with the default
# `GOTOOLCHAIN=auto` downloads one for the run and leaves the project's own toolchain alone.
GO_GREMLINS = "github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0"

# Where a Go service's mutation gate is written, relative to the service: the threshold Gremlins reads.
GO_GREMLINS_CONFIG = ".gremlins.yaml"

# The script `make mutation` runs Gremlins through, written once per project by `languages/go.py` from the
# asset of the same name. It exists because of two things verified against 0.6.0 on 2026-09-09 (the marches
# review of the Gremlins migration raised the first):
#
#   1. Gremlins copies the module it mutates — the nearest go.mod upwards, never the workspace — to a
#      temporary directory and tests there, where no `go.work` and no `packages/<name>` exist. A service
#      that imports a shared module the way `guidance.py` tells it to cannot build in that copy, and
#      Gremlins scores the build failure as KILLED because `go test` exits 1 for a failed build and a failed
#      test alike: every mutant in the importing package "killed", 100% efficacy, exit 0, with a test that
#      could not fail. The script stages the service beside the workspace modules it imports, with an
#      absolute `replace` for each, and runs with GOWORK=off.
#   2. Gremlins passes two runs the Spring backend's `failWhenNoMutations` would fail: a module with nothing
#      to mutate ("No results to report.", exit 0), and a run whose mutants timed out — a timed-out mutant is
#      left out of the score, and at the default coefficient half the skeleton's were. The script fails both.
GO_MUTATION_SCRIPT = "scripts/go-mutation.py"


# Emitted above the `mutation:` target so the next person to read a score, or a red run, knows what was run
# and where the gate is before trusting either. Make comments do not match the `help` grep, so this stays out
# of `make help`. `__APP__/.gremlins.yaml` is rewritten to the project's own Go services by `mutation_notes`.
GO_MUTATION_NOTE = """\
# Wired up: Gremlins, pinned to a release and run through `go run` by `scripts/go-mutation.py`, so it is
# never a dependency of the module it mutates. It needs Go 1.25 or newer; an older `go` with the default
# GOTOOLCHAIN=auto downloads one for the run. It replaced go-mutesting, whose 2019 package loader crashed on
# any package importing a module outside the standard library — that is, on every adapter — so the old
# target never reached the tests.
#
# The script stages the service beside the workspace modules it imports before Gremlins runs. Gremlins
# copies only the module it mutates to a temporary directory — no `go.work` above it, no `packages/<name>`
# beside it — and scores the build failure that follows as a kill, because `go test` exits 1 for a failed
# build and a failed test alike: run naked on a service that imports shared code it reported every such
# mutant killed, 100% efficacy and a green target, with tests that could not fail. The staged copy gets a
# `require` and an absolute `replace` per imported module and runs with GOWORK=off. The shared module is
# built there and never mutated; run this against it as a service of its own if its rules need a gate.
#
# The gate is in `__APP__/.gremlins.yaml`, not on this line: a run with a surviving mutant fails. The
# value there is 99.99 and it lives in a file for two reasons the file records — in Gremlins 0.6.0 the
# `--threshold-efficacy` flag and the GREMLINS_* environment variables are read as strings and silently
# gate nothing, and a threshold of 100 fails a perfect run because the comparison is `<=`. A recipe that
# grows a `--threshold` flag here gates nothing; change the file.
#
# The scope is that file's `integration: true` — Gremlins' word for running the whole module's tests against
# every mutant and gathering coverage across packages, so domain code that only an adapter's tests reach is
# covered and mutated rather than reported "not covered". It is not Go's `-tags=integration`: no run here
# sets that tag, so a test behind it is `make test-integration`'s, and a store adapter is mutated only as far
# as its in-process tests reach. Only mutants a test reaches are run — "not covered" is reported, never
# failed — so this fails on a weak test and not on a missing one; `make test`'s coverage gate
# (`scripts/go-coverage.py`) is where the missing one fails.
#
# Two runs Gremlins passes are red here, for the reason `failWhenNoMutations` is true in the Spring
# service's pom — a silent pass on a target no gate runs is worse than a red one. A run that found nothing
# to mutate ("No results to report.", exit 0) exits 1. And a timed-out mutant, which Gremlins leaves out of
# the score, fails the run: the fix is `timeout-coefficient` in the yaml, not a lower threshold.
#
# A survivor is a test to write or an equivalent mutant. Gremlins excludes files, not mutants, so an
# equivalent mutant means lowering the threshold deliberately, named in the commit that lowers it. No gate
# in this repository runs this target (docs/backend-obligations.md section 2); the factory's own suite runs
# it once, on a service importing a workspace module, to hold the staging to what this note says.
# `/mutation` runs it after an accepted slice and classifies what it reports.
"""


# What `make mutation` does on the Quarkus backend, and why it is not PIT already wired up.
#
# Per backend rather than per family, and the Spring sibling is the reason: PIT *is* wired up there, so a
# note shared across the family would tell one of the two something flatly untrue about its own build.
#
# PIT is the ecosystem's mutation tester and pitest-junit5-plugin 1.2.3 is the first version claiming
# Quarkus support — so the tool is not in doubt. What is in doubt is running it over a `@QuarkusTest`:
# pitest issue #1287 reports tests that pass standalone timing out on every mutation under PIT, on the
# configuration that behaves fine for Spring Boot — which is the one `java-spring` in this same factory
# ships wired up. That is exactly the failure this factory could not
# catch, because `make mutation` is run by no gate at either level (docs/backend-obligations.md section 2),
# so a wired-up PIT would have been committed green and stayed green.
#
# The mitigation is real and is written down below rather than guessed at later: mutate the domain, which
# is framework-free by construction here, with its plain JUnit tests — and keep `@QuarkusTest` and `*IT`
# out of PIT's reach. That is a decision about which classes this product considers worth mutating, which
# is why it is a decision the project makes rather than one the factory pins.
JAVA_QUARKUS_MUTATION_NOTE = """\
# Not wired up, on purpose, and the reason is a support constraint rather than a missing dependency.
#
# PIT is the JVM's mutation tester, and pitest-junit5-plugin 1.2.3 is the first version that claims
# Quarkus support. But pitest issue #1287 reports `@QuarkusTest` classes that pass standalone timing out
# on every mutation once PIT runs them — the same configuration works for Spring Boot, which is why the
# `java-spring` backend here ships `make mutation` wired up and this one does not. Nothing in this
# repository's gates runs this target, so a broken configuration here would never fail a build; it would
# just quietly never have worked.
#
# So configure it deliberately, and narrowly:
#
#   1. targetClasses — the domain packages only. They are framework-free by construction, which is the
#      whole reason the hexagon puts them there, and they are where a surviving mutant means something.
#   2. targetTests — the plain JUnit tests over those packages. Exclude `@QuarkusTest` and every `*IT`.
#   3. pitest-junit5-plugin as a dependency of the pitest-maven *plugin*, not of the project. Declared as
#      a project dependency, PIT reports "0 tests found" and does nothing, which is the most common way a
#      first PIT setup silently passes.
#
# Then run it, look at the survivors, and only afterwards let anything depend on the score.
"""

# What `make mutation` does on the Spring backend, where it is a working target rather than a placeholder.
#
# Emitted above the target for the same reason its sibling's note is: the next person to read a mutation
# score needs to know what was mutated before they trust it. Make comments do not match the `help` grep, so
# this stays out of `make help`.
JAVA_SPRING_MUTATION_NOTE = """\
# Wired up and scoped, and the scope is the part to read before trusting a score.
#
# PIT mutates the packages named in `pitest-maven`'s `targetClasses` in `__APP__/pom.xml` — the
# domain, the ports, the URL parser and the group mapping — and runs the plain `*Test` classes over them.
# That is deliberate on both sides:
#
#   1. Those packages are framework-free by construction, which is the whole reason the hexagon puts them
#      there, and they are where a surviving mutant means a rule nothing checks.
#   2. `*IT` is excluded. PIT runs the tests once per mutant, so a database suite in scope would turn a
#      minutes-long run into an hours-long one, for coverage of wiring rather than of rules.
#   3. Two classes inside those packages are excluded by name — `SecurityConfig` and the
#      `EnvironmentPostProcessor`. They are how a decision gets plugged into Spring rather than the
#      decision, so their mutants survive by nature: killing one would mean asserting Spring's own wiring.
#
# The report lands in `target/pit-reports/`. It fails rather than passes when it finds nothing to mutate,
# which is deliberate: `failWhenNoMutations` is `true` in the pom because "0 mutations" here can only mean
# a misconfigured run, and a silent pass on a target no gate runs is worse than a red one.
#
# So a clean run here does NOT mean the adapters are well tested; it means the rules are. Widen
# `targetClasses` as use cases arrive, and leave the adapters out — their tests are about wiring, and
# mutating wiring mostly produces survivors nobody should act on.
#
# No threshold is set. A score nobody has looked at yet is not a gate, and this target is run by no gate at
# either level (docs/backend-obligations.md section 2) — so read the survivors, then decide.
"""

JAVA_QUARKUS_MUTATION_PLACEHOLDER = (
    "@echo 'Configure PIT for the domain packages only — see the note above this target — then run it.'; "
    "exit 2"
)


# Per backend, and this is the one place in the Java family where that distinction is load-bearing.
# Gremlins' limits are the Go toolchain's, so that note holds for the family — but PIT's do not: it works
# under Spring Boot's test harness and times out under Quarkus's, so one backend's note explains a working
# target and the other's explains why there is none. A family lookup here would print the wrong one for one
# of them, and the target it lies about is run by no gate. Looked up with a default: most backends have
# nothing to say about `make mutation`.
MUTATION_NOTES = {
    "go": GO_MUTATION_NOTE,
    "java-quarkus": JAVA_QUARKUS_MUTATION_NOTE,
    "java-spring": JAVA_SPRING_MUTATION_NOTE,
}

# The per-service files a note names, spelled with `APP` where the service's path goes: PIT's scope is in the
# pom, Gremlins' threshold is in its yaml, and a project with two services of one backend has two of each.
NAMED_FILES = ("pom.xml", GO_GREMLINS_CONFIG)


def mutation_notes(apps: list[App]) -> str:
    """Each present backend's note once, naming that backend's own services where a note names a file."""
    notes = []
    for backend in backends_of(apps):
        note = MUTATION_NOTES.get(backend, "")
        for file in NAMED_FILES:
            named = " and ".join(f"`{s.path}/{file}`" for s in services_of(apps) if s.backend == backend)
            note = note.replace(f"`{APP}/{file}`", named)
        notes.append(note)
    return "".join(dict.fromkeys(notes))


def mutation_command(backends: list[str]) -> str:
    tools = {"typescript": "Stryker", "python": "mutmut", "go": "Gremlins", "java-quarkus": "PIT (pitest)",
             "java-spring": "PIT (pitest)"}
    return f"""---
description: Evaluate test effectiveness with mutation testing
argument-hint: [changed-production-paths]
---

# Mutation

Read `skills/mutation-testing/SKILL.md`. Target changed production code and use {" or ".join(dict.fromkeys(tools[b] for b in backends)) or "the ecosystem's mutation tool"} when the
project has configured it. Mutation tooling is intentionally not part of the mandatory repository gate: if it
is absent, report the exact setup decision needed instead of pretending mutations ran. Classify survivors,
add tests only for meaningful behavioural gaps, then finish with `make verify`.
"""
