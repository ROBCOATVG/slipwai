"""What `make mutation` does per backend, and why — the prose the generated Makefile carries, and the command.

Read only by the two modules that build the Makefile and the one that writes `commands/mutation.md`. The answers
are the backends' own (`mutation_note`, `mutation_tool`), and they are per backend rather than per family where
that is load-bearing: `make mutation` is run by no gate in a generated project, and by the keel's only for Go
(docs/backend-obligations.md section 2), so a note is most of what stands between the next reader and a score
they should not trust — and the two Java backends genuinely disagree, because PIT works under Spring Boot's test
harness and times out under Quarkus's. Each language's `mutation_note` answer holds its note.
"""
from __future__ import annotations

import re

from ..backends import APP
from ..registry import MUTATION_NOTE, MUTATION_SCOPING, MUTATION_TOOL, registry
from ..services import App, backends_of, services_of

# A file a note names, spelled with `APP` where the service's path goes — PIT's scope is in the pom, Gremlins'
# threshold is in its yaml — which a project with two services of one backend has two of.
NAMED_FILE = re.compile(rf"`{re.escape(APP)}/([^`]+)`")


def mutation_notes(apps: list[App]) -> str:
    """Each present backend's note once, naming that backend's own services where a note names a file. Looked up
    with a default: most backends have nothing to say about `make mutation`, and absence is that answer."""
    notes = []
    for backend in backends_of(apps):
        paths = [s.path for s in services_of(apps) if s.backend == backend]
        notes.append(named(registry().answer_or(backend, MUTATION_NOTE, ""), paths))
    return "".join(dict.fromkeys(notes))


def named(note: str, paths: list[str]) -> str:
    """Every file the note names under `APP`, as that file in each of these services, joined by "and"."""
    return NAMED_FILE.sub(lambda match: " and ".join(f"`{path}/{match[1]}`" for path in paths), note)


def mutation_command(backends: list[str]) -> str:
    answer = registry().answer
    # Each backend's `mutation_scoping` paragraph once, where it has one: how its own target narrows a run to a
    # change. Absent, nothing — most backends reach for their own tool's way of doing it.
    scoping = "".join(dict.fromkeys(registry().answer_or(b, MUTATION_SCOPING, "") for b in backends))
    return f"""---
description: Evaluate test effectiveness with mutation testing
argument-hint: [changed-production-paths]
---

# Mutation

Read `skills/mutation-testing/SKILL.md`. Target changed production code and use {" or ".join(dict.fromkeys(answer(b, MUTATION_TOOL) for b in backends)) or "the ecosystem's mutation tool"} when the
project has configured it. Mutation tooling is intentionally not part of the mandatory repository gate: if it
is absent, report the exact setup decision needed instead of pretending mutations ran. Classify survivors,
add tests only for meaningful behavioural gaps, then finish with `make verify`.

## It is a gate, not a report

A slice merges at its threshold or it does not merge. In the first attempt the score was a number in a
report and the gaps moved on: 18 from S08 to S09, 31 from S09 to S13, 46 from S12 to S13, until two whole
slices existed only to collect the debt. A slice that inherits a gap pays for it without having chosen to,
and the slice that made it has already been accepted.

So nothing is carried. A survivor is one of three things, said out loud and in this order: a behavioural
gap, which is a test written now; an equivalent mutant, which is recorded as one with its reason; or a
decision that this code does not warrant the test, which goes to the fairway's careen as a stowed row with
the slice that stowed it. What is not available is a fourth answer where the number is noted and the slice
merges anyway.

A run that cannot happen at all — no tooling configured — is the setup decision above, reported as a stop
rather than passed as a score. A gate that is green because it did not run is the one failure mode worse
than a red one.

## Once per capability, bounded

The run is the capability's, not the slice's: it runs when a capability's last slice has merged and before
the person's demo stop walks it (`commands/sail.md`, *What the demo stop has to contain*), over every
production file the capability's slices changed since the first of them branched. Per slice it took hours
apiece — one project's owner took it out of the loop by hand — and measured a fraction of what a person
accepts.

It is bounded by the `mutation-shipworm` row of `harbour.json`, and the bound is enforced rather than hoped
for: before the run, estimate the work from the scope and say whether the scope is file-level or
changed-line; run it in the background with a root-readable log and report, so the session that delegated
it can read and stop the job without waking the delegate; at the budget, kill the task's own process tree
and nothing beside it. A capped or incomplete run leaves a **qualified receipt** — the scope covered, the
scope not, the mutants tested and surviving so far — and never a score, and the gate reads that receipt as
*not run* for the scope it missed. Scope, score and completion come from the tool's own completed report,
never from the scrollback.
{scoping}"""
