#!/usr/bin/env python3
"""Check the ratified constitution still carries the principles this project cannot ship without.

`/speckit-constitution` fills a template, and a template is only a starting position: the phase that
writes `.specify/memory/constitution.md` can water a principle down, summarise five obligations into one
sentence, or drop a section that felt like boilerplate at the time. Nothing downstream notices. Every
later phase — plan, tasks, implement, review — reads that file as the authority it claims to be, so a
principle missing from it is not a documentation gap, it is a gate that silently stopped existing.

This gate states the floor. Three groups of requirements, and which apply is read from `project.json`
rather than guessed:

* **Minimum CD** — trunk-based integration, one automated path to production, build-once with deploy
  separated from release, feedback budgets, and the same bar for agent-generated change. Required in
  every profile, because these are what make the rest of the document enforced rather than asserted.
  These follow [MinimumCD](https://minimumcd.org/minimumcd/) — the industry-agreed floor for calling a
  practice continuous delivery, maintained by the MinimumCD working group. The requirements below
  restate it in this repository's terms and add the fifth, on agent-generated change, which the
  original predates; see `skills/REFERENCES.md` for what was taken and what was added.
* **The practices this repository's skills teach** — strict typing at the boundaries, ubiquitous language
  and domain types, the hexagonal boundary, acceptance-driven testing, observability, security and
  privacy, compatibility, ADRs, and a governance clause. Also required in every profile: a skill that
  contradicts the constitution loses, so a practice the team depends on has to be *in* the constitution.
* **The event-sourced obligations** — only where `project.json` claims the `event-sourcing` and
  `event-modelling` capabilities. A standard project is not asked for them, and
  `scripts/check-speckit.py` separately rejects a standard-profile constitution that mandates them
  anyway. The two gates are the same boundary read from both directions.

**What this can and cannot prove.** It reads for the vocabulary an obligation cannot be expressed
without, needing several independent signals before a requirement counts as covered. That catches the
failure that actually happens — a principle dropped, truncated, or replaced by a heading with nothing
under it — and it cannot judge whether what remains is *good*. Reviewers still do that. Wording is free:
paste `--requirements` output to start from the normative text, or write your own and keep the terms.

**When it applies.** `./init` installs the constitution *template* as `.specify/memory/constitution.md`,
placeholders and all, and the commit it pushes is meant to reach production: in a project with a
production target that push is the first deploy, and a gate that failed it would hold the walking
skeleton hostage to a document nobody has started writing. So while the file is still, byte for byte,
the template Spec Kit installed — recognised by the hash Spec Kit records beside it in
`.constitution-template.json`, or failing that by comparison with the templates the repository ships —
this gate reports that nothing has been drafted and passes. It applies in full from the first edit: a
placeholder left behind then is a constitution drafted and not ratified, which is the failure the
after-constitution hook and `make verify` exist to catch. And it applies regardless once any feature
exists under `specs/`, because a plan written against the template is a plan written against nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
CONSTITUTION = ROOT / ".specify/memory/constitution.md"
# Written by `specify init` beside the constitution: the sha256 of the template it installed and where the
# template came from. While the constitution still hashes to it, nobody has drafted anything.
TEMPLATE_RECORD = ROOT / ".specify/memory/.constitution-template.json"
# The templates the constitution can have been installed from, for a Spec Kit that wrote no record: a
# preset's override wins when one is enabled, and core's is the fallback.
PRESET_TEMPLATES = ROOT / ".specify/presets"
CORE_TEMPLATE = ROOT / ".specify/templates/constitution-template.md"
# Where Spec Kit's later phases write: one directory per feature, `spec.md` first.
SPECS = ROOT / "specs"
METADATA = ROOT / "project.json"

# `[LIKE_THIS]` and `[LIKE_THIS, e.g. a hint]` are the template's own fill-me markers, recognised by the
# run of uppercase, digits and underscores after the first character.
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]{2,}[^\]]*\]")
# The constitution as a journey (brownfield adoption; experimental). In a repository the method was installed
# around, a principle whose axis on the convergence map (`project.json`'s `convergence`) stands below the rung it
# comes into force at is a *target*: the constitution carries a marker naming the rung the repository stands on,
# and the gate holds the marker to the map instead of asking for the principle in full. Requirement key ->
# (axis, the rung the principle comes into force at). The same table lives in the factory, which writes the
# template these markers come from; a test there holds the two equal.
JOURNEY = {
    "trunk-based-integration": ("integration", "trunk"),
    "one-path-to-production": ("path-to-production", "one-path"),
    "build-once-deploy-is-not-release": ("path-to-production", "pipeline-decides"),
    "fast-feedback": ("safety-net", "fast"),
    "acceptance-driven-testing": ("safety-net", "tests-pass"),
    "hexagonal-boundary": ("structure", "hexagonal"),
    "ubiquitous-language-and-domain-types": ("structure", "typed"),
    "strict-typing": ("structure", "typed"),
}
RUNGS = {
    "path-to-production": ("unknown", "manual", "scripted", "pipeline", "one-path", "pipeline-decides"),
    "integration": ("unknown", "branches", "trunk", "continuous"),
    "safety-net": ("none", "tests-exist", "tests-pass", "fast", "pinned", "mutation-measured"),
    "structure": ("as-found", "named", "laid-out", "hexagonal", "typed"),
}
MARKER = re.compile(r"<!--\s*journey:\s*([a-z-]+)\s+at\s+([a-z-]+)\s*-->")
# The template also leaves instructions in brackets — "[Replace with the one invariant your domain cannot
# violate…]", "[Sensitive data class, e.g. …]". Those sit under the principles only this project can write,
# so missing them would mean passing a constitution whose most important clause is still a prompt. A
# markdown link is excluded by the lookahead rather than by length: `[Some Text](url)` is followed by `(`.
INSTRUCTION = re.compile(r"\[[^\]\n]{25,}\](?!\()")


@dataclass(frozen=True)
class Requirement:
    """One obligation the constitution has to carry, and how to recognise it.

    `signals` are alternative phrasings of the *same* obligation, and `needs` of them must match before
    it counts as covered. Two independent signals rather than one is what keeps a passing mark from being
    bought with a heading: "Continuous Integration on Trunk" as a title matches `trunk`, and matches
    nothing else, so the section has to actually say something.
    """

    key: str
    title: str
    signals: tuple[str, ...]
    statement: str
    capability: str | None = None
    needs: int = 2
    practice: tuple[str, ...] = field(default_factory=tuple)

    def matched(self, text: str) -> int:
        return sum(1 for signal in self.signals if re.search(signal, text, re.IGNORECASE))


# ── Minimum CD ────────────────────────────────────────────────────────────────────────────────────────
#
# Source: https://minimumcd.org/minimumcd/ (MinimumCD working group, CC BY-SA 4.0). Four of the five
# requirements below are that document's obligations restated — trunk-based integration in small batches,
# one immutable artifact through one automated pipeline, deploy separated from release, and a pipeline
# whose verdict is the release authority. `agent-change-same-bar` is this repository's addition: the
# source predates agentic delivery, and the whole point of it is that no new route to production opens.
#
# Restated rather than quoted, because a gate that reads for one wording is a gate that fails on a
# constitution phrased for its own domain. `signals` are alternative phrasings of the same obligation.

MINIMUM_CD = (
    Requirement(
        key="trunk-based-integration",
        title="Continuous integration on trunk, in small batches",
        signals=(
            r"integrate to (?:trunk|mainline)|reach(?:ed)? trunk|trunk at least once",
            r"(?:branch(?:es)?|work|item)[^.]{0,140}(?:less than a day|within a day|once per day|at least daily)",
            r"long-lived (?:develop|integration|per-feature|branch)|per-feature branch(?:es)? MUST NOT",
            r"trunk MUST be releasable|releasable at every commit",
            r"red trunk|trunk is (?:red|failing)|while the build is failing",
            r"cherry-pick",
        ),
        needs=3,
        practice=("skills/story-splitting/SKILL.md", "skills/planning/SKILL.md"),
        statement="""### Continuous Integration on Trunk (NON-NEGOTIABLE)

- Every engineer MUST integrate to trunk at least once per day. Work that has not reached trunk is
  unintegrated no matter how often a build ran against the branch it sits on.
- Where branches are used they MUST be cut from trunk, MUST re-integrate to trunk, and MUST live less
  than a day. Long-lived `develop`, integration, or per-feature branches MUST NOT exist.
- Trunk MUST be releasable at every commit, and a red trunk stops the line: while the build is failing
  the only permitted work is restoring it.
- A work item MUST be codeable, testable, reviewable, and integrable within two days. An item that is
  not MUST be split before it is started.
- Fixes MUST travel forward through trunk. Cherry-picking onto a release branch MUST NOT be the route to
  production.""",
    ),
    Requirement(
        key="one-path-to-production",
        title="One automated path to production, and the pipeline decides",
        signals=(
            r"one (?:automated )?pipeline|single pipeline|one path to production|same pipeline",
            r"pipeline (?:is|MUST be) the (?:release )?authority|pipeline decides|release authority",
            r"MUST NOT be able to override|without a commit|manual (?:step|gate|deploy|approval)",
            r"in version control|checked in(?:to)? version control|everything the pipeline (?:reads|consumes)",
            r"runnable locally|the same command CI runs|flaky test",
        ),
        needs=3,
        practice=("skills/ci-debugging/SKILL.md", "skills/twelve-factor/SKILL.md"),
        statement="""### One Path to Production, and the Pipeline Decides (NON-NEGOTIABLE)

- Exactly one automated pipeline MUST deliver every change to every environment. Hotfixes, rollbacks,
  configuration changes, and schema migrations use it too; a second route invalidates every claim the
  first route makes.
- The pipeline is the release authority. A human MUST NOT be able to override its verdict, and a passing
  pipeline MUST NOT require a further sign-off.
- The Definition of Deployable MUST be automated in full and identical for every environment. In this
  project it is what `make ci` runs — adding a quality criterion means adding a gate.
- Everything the pipeline consumes MUST be in version control: source, pipeline definition,
  infrastructure, migrations, alert definitions, tool versions, and a dependency lockfile. Floating
  versions MUST NOT appear anywhere it reads. If a change can be made to a running environment without a
  commit, that thing is not managed.
- Every pipeline step MUST be runnable locally by the same command CI runs. Flaky tests MUST be fixed,
  quarantined, or deleted the day they are noticed; re-running a build to obtain a pass is prohibited.""",
    ),
    Requirement(
        key="build-once-deploy-is-not-release",
        title="Build once, promote the same artifact, and separate deploy from release",
        signals=(
            r"built once|build once|promoted unchanged|same artifact",
            r"immutable|mutable tag|snapshot version",
            r"deploy(?:ment)?(?: and| is not)[^.]{0,40}release|separate decisions|behind a flag|dark",
            r"configuration[^.]{0,60}from the environment|environment-supplied",
            r"rollback|expand/contract|backward compatible",
        ),
        needs=3,
        practice=("skills/twelve-factor/SKILL.md",),
        statement="""### Build Once, Deploy Anywhere; Deploy Is Not Release

- One artifact MUST be built once per commit and promoted unchanged through every environment.
  Rebuilding per environment discards the evidence the pipeline produced and MUST NOT happen.
- Artifact identity MUST be unique and immutable. Snapshot versions and mutable tags MUST NOT be
  deployed.
- Configuration that varies between environments MUST come from the environment; configuration that does
  not vary MUST ship inside the artifact and be tested with it.
- Deployment and release are separate decisions. Incomplete work reaches production dark, behind a flag,
  and every release flag MUST have an owner, a removal date, tests on both paths, and an expiry.
- Rollback MUST be a single automated action, executable without approval, and exercised on a schedule.
- Schema change MUST follow expand/contract across separate deployments; an additive and a destructive
  step MUST NOT ship in the same deployment.""",
    ),
    Requirement(
        key="fast-feedback",
        title="Feedback budgets, and a deterministic suite that earns them",
        signals=(
            r"feedback budget|under (?:one|two|five|ten|1|2|5|10) (?:second|minute)|within \[?[A-Z_0-9]*\s*e\.g\.[^\]]*minutes",
            r"deterministic suite|deterministic set|deterministic pre-merge",
            r"MUST NOT depend on any system|no live third-party|shared mutable environment|wall-clock sleep",
            r"test double|contract test",
            r"same commit as the code|MUST NOT gate merge|after deploy",
        ),
        needs=3,
        practice=(
            "skills/testing/SKILL.md",
            "skills/tdd/SKILL.md",
            "skills/characterisation-tests/SKILL.md",
        ),
        statement="""### Fast Feedback, or It Is Not Feedback

- Feedback budgets are gates on the suite, not aspirations: unit tests in watch under one second, the
  pre-push deterministic set under two minutes, the full deterministic pre-merge suite under ten
  minutes. Exceeding a budget is a defect in the suite — fix the suite. Extending the budget or moving
  tests out of the gate to meet it is prohibited.
- The deterministic suite MUST NOT depend on any system the team does not control: no live third-party
  calls, no shared mutable environment, no ordering between tests, no wall-clock sleeps.
- Test doubles used in the deterministic suite MUST be validated against the real system by contract
  tests that run outside it.
- Test changes MUST ship in the same commit as the code they cover.
- Non-deterministic checks — end-to-end smoke, load, resilience, exploratory testing — run after deploy
  and MUST NOT gate merge.""",
    ),
    Requirement(
        key="agent-change-same-bar",
        title="Agent-generated change meets the same bar",
        signals=(
            r"agent-generated|agent-written|agent output|an agent MUST",
            r"same pipeline|same Definition of Deployable|same bar|fast lane",
            r"humans own intent|human-authored|MUST NOT edit (?:them|the specification|this constitution)",
            r"MUST stop and ask|outside its constraints|guessing",
            r"one scenario|single acceptance scenario|end at a green commit",
        ),
        needs=3,
        practice=(
            "skills/specification/SKILL.md",
            "skills/acceptance-review/SKILL.md",
            "skills/find-gaps/SKILL.md",
        ),
        statement="""### Agent-Generated Change Meets the Same Bar (NON-NEGOTIABLE)

- An agent-generated change MUST clear the same pipeline and the same Definition of Deployable as a
  human-generated one. There MUST NOT be a fast lane for agent output, and there MUST NOT be an extra
  manual gate applied to it because of its origin.
- Humans own intent. The specification, the acceptance criteria, the architectural constraints, and this
  constitution are human-authored and human-amended; an agent MUST NOT edit them to make its own change
  pass.
- Every change MUST carry its intent as versioned artifacts delivered in the same commit as the code:
  the problem, the observable behaviour as Given/When/Then, the constraints, and the acceptance
  criteria.
- One scenario, one session, one commit. An agent session MUST be scoped to a single acceptance scenario
  and MUST end at a green commit.
- An agent MUST stop and ask when a decision falls outside its constraints — a name in the domain
  vocabulary, a new dependency, or a change to a published contract. Guessing to keep moving is
  prohibited.""",
    ),
)

# ── The practices this repository's skills teach ──────────────────────────────────────────────────────

PRACTICES = (
    Requirement(
        key="strict-typing",
        title="Strict typing, and untrusted data parsed at the boundary",
        signals=(
            r"strict type|type check(?:ing)? MUST|maximum practical setting|strict mode",
            r"escape hatch|\bany\b MUST NOT|interface\{\}|unsafe|type: ignore|@ts-",
            r"\bunknown\b|runtime schema|schema-first|parsed at the edge",
            r"trust boundar|inbound request|third-party response",
        ),
        needs=3,
        practice=("skills/typescript-strict/SKILL.md", "skills/api-design/SKILL.md"),
        statement="""- Strict type checking MUST be enabled at its maximum practical setting from the first commit.
  Retrofitting strictness is expensive; enabling it on an empty codebase is free.
- Escape hatches (`any` and its equivalents) MUST NOT appear in domain or application code. Untyped
  external data enters as `unknown` and is narrowed by a runtime schema.
- Schema-first at trust boundaries: every crossing MUST be validated by a runtime schema — inbound
  requests, third-party responses, and anything read back out of storage, because stored data outlives
  the code that wrote it.
- The language and runtime MUST be pinned in the repository and identical across local, CI, and
  production.""",
    ),
    Requirement(
        key="ubiquitous-language-and-domain-types",
        title="Ubiquitous language and domain types that make illegal states unrepresentable",
        signals=(
            r"ubiquitous language|domain vocabulary|vocabulary is agreed",
            r"one term MUST have|exactly one meaning|technical synonym|renamed with it",
            r"illegal states unrepresentable|invalid states unrepresentable",
            r"branded or wrapped|modelled as types rather than primitives|value object",
            r"parsed into a valid domain type|MUST NOT re-validate|primitive obsession",
        ),
        needs=3,
        practice=(
            "skills/ubiquitous-language/SKILL.md",
            "skills/domain-driven-design/SKILL.md",
            "skills/functional/SKILL.md",
        ),
        statement="""### Ubiquitous Language and Domain Types

- The domain vocabulary is agreed with the people who own the domain, and one term MUST have exactly one
  meaning inside a bounded context. Where the business renames something, the code is renamed with it —
  a translation layer in people's heads is a defect.
- Types, functions, modules, tests, events, and user-facing copy MUST use that vocabulary. A technical
  synonym for a domain term MUST NOT be introduced.
- Domain concepts MUST be modelled as types rather than primitives: identifiers, quantities, and
  monetary values are branded or wrapped so one cannot be passed where another is required, and
  monetary amounts are integer minor units with an explicit currency.
- Constructors MUST make illegal states unrepresentable — parse untrusted input into a valid domain type
  once, at the boundary, rather than re-validating a primitive at every use.""",
    ),
    Requirement(
        key="hexagonal-boundary",
        title="Hexagonal boundary, enforced by an automated check",
        signals=(
            r"domain code MUST NOT import|MUST NOT import a framework|independent of (?:adapters|infrastructure)",
            r"driving adapter|driven adapter|driven port|\bport\b",
            r"named for the business|survive an adapter swap|role interface",
            r"usable fake|fake for (?:each|every) port",
            r"automated check|import check|dependency direction",
        ),
        needs=3,
        practice=(
            "skills/hexagonal-architecture/SKILL.md",
            "skills/finding-seams/SKILL.md",
            "skills/structure-codebase/SKILL.md",
        ),
        statement="""### Hexagonal Architecture — Domain Isolated from Infrastructure

- Domain code MUST NOT import a framework, transport, persistence implementation, clock, identifier
  generator, vendor SDK, or UI concern. Time and identifiers arrive as typed inputs.
- Driving adapters parse untrusted input into typed commands and call use cases; they hold no business
  rules and make no authorisation decision.
- Driven adapters implement ports owned by their innermost consumer and are injected as parameters.
- Ports MUST be named for the business conversation, never the technology, MUST survive an adapter swap,
  and MUST expose only what the consumer needs.
- Every driven port MUST have a usable fake, so domain and application code is testable with no
  infrastructure running.
- The dependency direction MUST be enforced by an automated check — in this project `make check-imports`
  — not by reviewer vigilance.""",
    ),
    Requirement(
        key="acceptance-driven-testing",
        title="Acceptance-driven development, tests written first",
        signals=(
            r"(?:every|each) slice MUST have at least one|at least one (?:GWT|Given|acceptance) ",
            r"(?:When|scenario)[^.]{0,120}(?:enters|entering|through)[^.]{0,120}(?:driving port|use case)",
            r"RED-GREEN-REFACTOR|one failing test|failing test (?:comes|MUST be observed) ",
            r"unit specification|not a slice acceptance criterion",
            r"tests/edge|delivery adapter MUST carry a test|parse, delegate",
            r"reproduc(?:e|ing) the reported behaviour|bug fix(?:es)? MUST begin",
        ),
        needs=3,
        practice=(
            "skills/tdd/SKILL.md",
            "skills/expectations/SKILL.md",
            "skills/test-design-reviewer/SKILL.md",
            "skills/adversarial-testing/SKILL.md",
        ),
        statement="""### Acceptance-Driven Development from Given-When-Then

- Every slice MUST have at least one Given/When/Then scenario whose **When** enters through the
  application's own driving port — the use case — and whose **Then** is observable there. A scenario
  satisfiable by calling an internal function is a unit specification, not a slice acceptance criterion.
- Each increment MUST be RED-GREEN-REFACTOR: the failing test comes first and states the behaviour, not
  the implementation.
- A delivery adapter — HTTP route, CLI command, queue consumer — MUST carry a test covering parse,
  delegate, and the mapping of every outcome, and that level MUST NOT be where a business rule is
  proved.
- A defect MUST be reproduced by a failing test at the level the rule lives before it is fixed.""",
    ),
    Requirement(
        key="observability-and-audit",
        title="Observability and auditability",
        signals=(
            r"structured log|log[^.]{0,40}structured",
            r"correlation (?:id|identifier)|causation",
            r"alert|detect(?:ion|ed) (?:target|within)|heartbeat",
            r"audit (?:record|trail|log)|retention|retained for",
            r"personally identifying|personal data MUST NOT be (?:written|logged)|MUST NOT be logged",
        ),
        needs=3,
        practice=("skills/observability/SKILL.md",),
        statement="""### Observability and Auditability

- Logs MUST be structured and carry a correlation identifier propagated across every hop, projection,
  and background job.
- Every recorded fact MUST carry the actor that caused it plus causation and correlation identifiers,
  both of them UUIDs, and audit records MUST be queryable without restoring a backup.
- A read model is not detection: where a criterion promises a problem is surfaced within a time bound,
  an alert satisfies it. Background jobs MUST emit a heartbeat and a missing heartbeat MUST be
  alertable.
- A production problem MUST be detected by alerting rather than by a customer.
- Personally identifying data MUST NOT be written to application logs.""",
    ),
    Requirement(
        key="security-and-privacy",
        title="Security, privacy, and compliance",
        signals=(
            r"secrets? MUST come from|secret manager|committed secret",
            r"authoris(?:ation|ed) MUST be enforced|authorization MUST be enforced|enforced server-side",
            r"MUST NOT (?:enter, transit|be logged)|sensitive payloads? MUST NOT|MUST NOT be placed in a domain event",
            r"right to erasure|erasable without|crypto-shred",
            r"dependencies MUST be scanned|known-exploitable|blocks release",
            r"cross-tenant access MUST",
        ),
        needs=3,
        practice=("skills/secure-oauth-oidc/SKILL.md", "skills/api-design/SKILL.md"),
        statement="""### Security, Privacy, and Compliance

- The sensitive data classes this system MUST NOT store, transit, or log are named here, and capture is
  delegated so the compliance scope stays minimal.
- Personal data MUST be erasable, and where storage is append-only that mechanism MUST be designed
  before the first record carrying personal data is persisted.
- Secrets MUST come from the environment or a secret manager. A committed secret is a build-breaking
  failure.
- Authorisation MUST be enforced server-side on every request, inside the application rather than in a
  driving adapter alone. Cross-tenant access MUST return not-found, not forbidden.
- Dependencies MUST be scanned in CI; a known-exploitable critical finding blocks release.""",
    ),
    Requirement(
        key="versioning-and-compatibility",
        title="Versioning and breaking changes",
        signals=(
            r"MAJOR\.MINOR\.PATCH|semantic version|versioned MAJOR",
            r"breaking (?:api )?change|deprecation|keep the prior version",
            r"additive|tolerate unknown fields|tolerant reader",
            r"backward compatible|forward compatib|two versions concurrently",
        ),
        needs=3,
        practice=("skills/api-design/SKILL.md", "skills/architecture-decisions/SKILL.md"),
        statement="""### Versioning and Breaking Changes

- Published artifacts and APIs MUST be versioned MAJOR.MINOR.PATCH.
- A breaking API change MUST ship as a new version and keep the prior version serving for the announced
  deprecation window.
- Stored contracts MUST change additively and readers MUST tolerate unknown fields.
- Migrations MUST be backward compatible with the previously deployed application version, and where a
  deployment runs two versions concurrently the previous version MUST also tolerate what the new one
  writes.""",
    ),
    Requirement(
        key="architecture-decision-records",
        title="Irreversible decisions recorded as ADRs",
        signals=(
            r"\bADR\b|architecture decision record",
            r"docs/adr|Nygard|Context, Decision, Consequences",
            r"reversal cost|would cost a migration|expensive to reverse|permanent",
            r"MUST NOT be edited|supersede",
            r"Proposed|accept(?:ing|ed)[^.]{0,40}human",
        ),
        needs=3,
        practice=("skills/architecture-decisions/SKILL.md",),
        statement="""- A decision that would cost a migration to reverse MUST be recorded as an ADR in `docs/adr/`, using
  Nygard's five sections (Title, Status, Context, Decision, Consequences). The test is reversal cost,
  not importance: stored data must change shape, another team must coordinate, a contract must be
  versioned, or history would have to be rewritten.
- An accepted ADR MUST NOT be edited; a decision is changed by a new ADR that supersedes it, with links
  resolving in both directions.
- An ADR drafted by an agent MUST start at `Proposed` — accepting an architecture decision is a human
  act.
- A slice-scoped design decision stays in that slice's `research.md`, and MUST be promoted to an ADR
  when it turns out to outlive its slice.""",
    ),
    Requirement(
        key="quality-gates",
        title="Pull-request gates, review, and recorded deviation",
        signals=(
            r"MUST pass|every pull request|quality gate",
            r"review(?:ed)? by (?:an|a second) engineer|pair or ensemble|review latency|review SLA",
            r"MUST NOT be merged|disabling a gate|while the pipeline is red",
            r"fewer than \d+ lines|smaller than|diff size",
            r"deviation|complexity[^.]{0,20}deviation|silent deviation",
        ),
        needs=3,
        practice=("skills/double-check/SKILL.md", "skills/acceptance-review/SKILL.md"),
        statement="""## Development Workflow and Quality Gates

- Every plan MUST include a Constitution Check naming which principles the feature touches and how it
  complies.
- Every pull request MUST pass automated tests including at least one boundary-level scenario per slice,
  linting, a dependency vulnerability scan, the architecture import check, and review by an engineer who
  did not write the change.
- A pull request MUST NOT be merged while the pipeline is red, and MUST NOT be merged by disabling a
  gate.
- Review is a flow constraint, not a queue: a change MUST be reviewed within the agreed SLA and an
  older-than-a-day pull request MUST be escalated. Pair or ensemble programming satisfies the review
  obligation without a separate step.
- A pull request SHOULD change fewer than 200 lines; beyond that reviewer defect detection falls off.
- Deviations from a principle MUST be recorded in the pull request under a "Complexity / Deviation"
  heading, naming the principle and the reason. Silent deviation is a defect.""",
    ),
    Requirement(
        key="governance",
        title="Governance: supersession, amendment, versioning, and review",
        signals=(
            r"constitution supersedes|supersedes other development practices|this document wins",
            r"amendment procedure|amendments? MUST (?:be proposed|state|include)",
            r"versioning policy|MAJOR (?:—|-|:)",
            r"compliance review|review this constitution|left as decoration",
            r"Ratified:|Last Amended",
        ),
        needs=3,
        practice=(),
        statement="""## Governance

This constitution supersedes other development practices in this project. Where a style guide, template,
skill, or prior decision conflicts with it, this document wins.

**Amendment procedure.** Amendments MUST be proposed as a pull request modifying this file, MUST state
the rationale and the version bump with its justification, and MUST be approved by the maintainers.
Amendments invalidating existing code MUST include a migration plan.

**Versioning policy.** MAJOR — a principle removed or redefined such that compliant work would now
violate it. MINOR — a principle or section added, or guidance materially expanded. PATCH —
clarification changing no obligation.

**Compliance review.** Every review MUST verify compliance with the principles the change touches, and
maintainers MUST review this constitution against actual practice at least quarterly; a principle
routinely ignored MUST be enforced or amended away, never left as decoration.

**Version**: 1.0.0 | **Ratified**: YYYY-MM-DD | **Last Amended**: YYYY-MM-DD""",
    ),
)

# ── Event Modeling and event sourcing, only where the project claims them ─────────────────────────────

EVENT = (
    Requirement(
        key="event-sourced-core",
        title="Event-sourced core with a pure Decider",
        capability="event-sourcing",
        signals=(
            r"events (?:are|MUST be) the source of truth|append-only[^.]{0,40}(?:log|event)",
            r"state is a left fold|state = events|reduce\(evolve|no stored current state",
            r"decide\(command|Decider (?:is|MUST be) pure|Decider [Pp]attern",
            r"evolve\(state|returns the next state|returns accepted events",
            r"complexity ladder|MUST NOT be event-sourced|merely for consistency",
        ),
        needs=3,
        practice=("skills/event-sourcing/SKILL.md", "skills/functional/SKILL.md"),
        statement="""### Event-Sourced Core with the Decider Pattern

- Events are the source of truth: immutable, past-tense facts in business language, appended and never
  updated or deleted. Corrections are new compensating events.
- State is a left fold — `state = events.reduce(evolve, initialState)`. There is no stored current state
  for the write model.
- The Decider is pure: `decide(command, state)` returns accepted events **or** a rejection with a
  business reason, never both and never partial; `evolve(state, event)` returns the next state. Both are
  free of I/O, clocks, identifier generation, randomness, and framework imports.
- Commands read user input and the event stream only. A read-model-to-command dependency MUST NOT exist.
- Event sourcing is the top of the complexity ladder, not a default. A peripheral context with no
  meaningful history MUST NOT be event-sourced merely for consistency, and the rung chosen is recorded
  with its reason.""",
    ),
    Requirement(
        key="stream-identity-and-concurrency",
        title="Stream identity as the consistency boundary",
        capability="event-sourcing",
        signals=(
            r"consistency boundary|one stream|stream per",
            r"stream identity|stream_id|stream identifier",
            r"expected version|optimistic concurrency|concurrency (?:control|ceiling)",
            r"process manager|distributed transaction|cross-stream",
            r"replay from position zero|ordered single-stream|append-with-expected-version",
        ),
        needs=3,
        practice=("skills/event-sourcing/SKILL.md", "skills/global-event-model/SKILL.md"),
        statement="""- The stream is the consistency boundary: one aggregate instance maps to one stream, and cross-stream
  work is a process manager rather than a distributed transaction.
- Stream identity MUST be documented explicitly, because it determines the concurrency ceiling, and it
  is a permanent decision — an ADR, not a code comment.
- Appends MUST carry an expected version, and a conflict MUST be resolved by re-deciding against the
  reloaded stream rather than by overwriting.
- Whatever product backs the event store, the port MUST provide append-with-expected-version, ordered
  single-stream reads, and replay from position zero. A store that cannot offer all three MUST NOT be
  adopted.""",
    ),
    Requirement(
        key="read-models-are-derivations",
        title="Read models are disposable derivations",
        capability="event-sourcing",
        signals=(
            r"read model",
            r"disposable|rebuild(?:able|ing)|from position zero",
            r"snapshot[^.]{0,40}optimisation|never truth",
            r"trace to a (?:source )?event|every event MUST have a trigger",
            r"projection",
        ),
        needs=3,
        practice=("skills/event-sourcing/SKILL.md",),
        statement="""- Read models are disposable derivations, rebuildable from position zero. Snapshots are an
  optimisation, never truth.
- Where each read model lives is a written answer — folded per query, written inline with the append, or
  maintained by a catch-up subscription — and a per-query fold carries the ceiling it holds inside. An
  automation's todo list is persisted: losing it loses work nothing else records.
- Every event MUST have a trigger — a command, an automation, or a translation — and every read-model
  field MUST trace to a source event.
- Rebuilding a projection is the preferred migration; altering one in place is the exception.""",
    ),
    Requirement(
        key="event-schema-permanence",
        title="Event schemas as permanent contracts",
        capability="event-sourcing",
        signals=(
            r"event schema",
            r"permanent|MUST be additive|additive",
            r"upcaster|schema version|maps old events forward",
            r"rewrites stored events|prohibited|MUST NOT be (?:updated|rewritten)",
            r"validated (?:on|both) (?:read and write|write and read)|on read from the store",
        ),
        needs=3,
        practice=("skills/event-sourcing/SKILL.md", "skills/architecture-decisions/SKILL.md"),
        statement="""- Event schemas are permanent contracts. Changes MUST be additive and readers MUST tolerate unknown
  fields; removing or retyping a field requires a new schema version plus an upcaster that maps old
  events forward on read.
- A migration that rewrites stored events is prohibited.
- Events MUST be validated by a runtime schema on write **and** on read, because stored events outlive
  the code that wrote them.
- Event names, event fields, and stream identity always qualify as ADR decisions — they are permanent.""",
    ),
    Requirement(
        key="idempotency-and-replay",
        title="Idempotency and replay safety",
        capability="event-sourcing",
        signals=(
            r"idempotency key",
            r"repeated key|the original result|same result for",
            r"at-least-once|safe to replay|reprocessing",
            r"MUST NOT be able to duplicate|MUST NOT produce a second|deduplicate",
        ),
        needs=3,
        practice=("skills/event-sourcing/SKILL.md", "skills/api-design/SKILL.md"),
        statement="""### Idempotency and Replay Safety (NON-NEGOTIABLE)

- Public write endpoints MUST accept a caller-supplied idempotency key and MUST return the original
  result for a repeated key rather than performing the work again.
- Every consumer MUST assume at-least-once delivery and MUST be safe to replay: reprocessing an event
  MUST NOT produce a second effect.
- A retry MUST NOT be able to duplicate a non-idempotent side effect. Where a provider offers an
  idempotency mechanism the adapter MUST use it, and a test MUST prove the key reaches the provider.""",
    ),
    Requirement(
        key="event-modelling-precedes-planning",
        title="Event Modeling precedes planning, and the model stays current",
        capability="event-modelling",
        signals=(
            r"event model(?:ling|ing)?",
            r"precede[s]? (?:planning|tasks)|before tasks are generated|before a plan",
            r"docs/event-model|model\.yaml|one global event model",
            r"status MUST track|planned|implemented",
            r"check-model|build gate|regenerated diagram",
        ),
        needs=3,
        practice=(
            "skills/event-modeling/SKILL.md",
            "skills/global-event-model/SKILL.md",
            "skills/storyboard/SKILL.md",
        ),
        statement="""- Event modelling precedes planning for any new workflow: slices, events, commands, read models, and
  Given/When/Then scenarios are modelled with domain experts before tasks are generated.
- One global event model, kept current. `docs/event-model/model.yaml` holds every slice on a single
  timeline and its status MUST track reality — `planned` before a plan is approved, `implemented` when
  the slice ships.
- A pull request changing events, commands, read models, or stream identity MUST include the regenerated
  diagram, and correctness here is a build gate (`make check-model`) rather than a convention.""",
    ),
)

REQUIREMENTS = MINIMUM_CD + PRACTICES + EVENT
GROUPS = (
    ("Minimum CD", MINIMUM_CD),
    ("Practices this repository's skills teach", PRACTICES),
    ("Event Modeling and event sourcing", EVENT),
)


def targets() -> dict[str, tuple[str, str, str]]:
    """The requirements that are targets here rather than principles in force, from the convergence map of an
    adopted repository: key -> (axis, the rung it stands on, the rung the principle comes into force at). Empty
    for a generated project, and for an adopted one with no map yet — there every principle is in force."""
    if not METADATA.is_file():
        return {}
    try:
        metadata = json.loads(METADATA.read_text())
    except json.JSONDecodeError:
        return {}
    if metadata.get("origin") != "adopted":
        return {}
    standing = {
        row.get("axis"): row.get("rung") for row in metadata.get("convergence") or [] if isinstance(row, dict)
    }
    found = {}
    for key, (axis, in_force) in JOURNEY.items():
        rungs = RUNGS[axis]
        rung = standing.get(axis, rungs[0])
        if rung in rungs and rungs.index(rung) < rungs.index(in_force):
            found[key] = (axis, rung, in_force)
    return found


def journey_statement(requirement: Requirement, axis: str, rung: str, in_force: str) -> str:
    """The text a target principle carries in place of the principle in full: the marker, where the repository
    stands, and the principle itself quoted for the day it comes into force."""
    heading, _, body = requirement.statement.partition("\n")
    quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in body.strip("\n").splitlines())
    return f"""{heading}

<!-- journey: {requirement.key} at {rung} -->
**A target, not yet in force.** On the *{axis}* ladder this repository stands at `{rung}` (docs/convergence.md).
This principle comes into force at `{in_force}`. Until it does, what holds here is written below, and the map's
*planned* column names the slice that climbs.

- [What holds here today for this principle, in a sentence or two: the practice as it is, not as it should be.]
- [The next rung, and what has to be true for it: name the slice planned to reach it, or say none is planned yet.]

When in force, this principle reads:

{quoted}"""


def capabilities() -> set[str] | None:
    """This project's capabilities, or None when `project.json` cannot be read.

    None rather than an empty set: "the metadata is unreadable" and "this project claims no capability"
    are different, and only the second one should narrow the requirement set.
    """
    if not METADATA.is_file():
        return None
    try:
        metadata = json.loads(METADATA.read_text())
    except json.JSONDecodeError:
        return None
    declared = metadata.get("capabilities")
    return set(declared) if isinstance(declared, list) else None


def applicable(available: set[str] | None) -> list[Requirement]:
    if available is None:
        # Without metadata, only the requirements that hold for every project are asked for. Demanding
        # the event-sourced ones from a project that may not be event-sourced would be a gate inventing
        # a decision nobody made.
        return [requirement for requirement in REQUIREMENTS if requirement.capability is None]
    return [
        requirement
        for requirement in REQUIREMENTS
        if requirement.capability is None or requirement.capability in available
    ]


def flatten(text: str) -> str:
    """One line per document, so a placeholder the template wrapped over three lines is still one
    placeholder — and still named as written, underscores included."""
    return re.sub(r"\s+", " ", text)


def normalise(text: str) -> str:
    """Flatten the document so a signal can match a sentence the source wrapped over three lines.

    Markdown emphasis and code ticks are dropped for the same reason: `**MUST NOT** be logged` and
    `MUST NOT be logged` are the same obligation, and a pattern that has to anticipate which one was
    typed is a pattern that fails on the other.
    """
    return flatten(re.sub(r"[*_`]", "", text))


def untouched_template(raw: bytes) -> bool:
    """Whether the constitution is still exactly the template `./init` installed.

    Spec Kit's own record is the authority where it exists: the hash it wrote is of the file it wrote, so
    a match is proof and a mismatch is an edit, whichever template resolved at the time. Without a record,
    the file is compared with every constitution template the repository carries — each preset's and
    core's — on whitespace-flattened text, so a checkout that rewrote line endings still compares equal.
    """
    if TEMPLATE_RECORD.is_file():
        try:
            recorded = json.loads(TEMPLATE_RECORD.read_text()).get("sha256")
        except json.JSONDecodeError:
            recorded = None
        if isinstance(recorded, str) and recorded == hashlib.sha256(raw).hexdigest():
            return True
    candidates = [CORE_TEMPLATE, *PRESET_TEMPLATES.glob("*/templates/constitution-template.md")]
    text = flatten(raw.decode(errors="replace")).strip()
    return any(
        candidate.is_file() and flatten(candidate.read_text(errors="replace")).strip() == text
        for candidate in candidates
    )


def workflow_started() -> bool:
    """Whether a Spec Kit phase after the constitution has run here: any feature with a `spec.md`."""
    return SPECS.is_dir() and any(SPECS.glob("*/spec.md"))


def report_requirements(selected: list[Requirement], keys: list[str]) -> int:
    journey = targets()
    wanted = [item for item in selected if not keys or item.key in keys]
    if keys:
        unknown = sorted(set(keys) - {item.key for item in selected})
        for key in unknown:
            print(f"# no applicable requirement named {key!r}", file=sys.stderr)
        if not wanted:
            return 1
    print("# Required constitution coverage for this project")
    print("#")
    print("# Paste what is missing into .specify/memory/constitution.md and adapt the wording to this")
    print("# domain. The gate reads for the obligation, not for this phrasing.")
    for group, members in GROUPS:
        included = [item for item in members if item in wanted]
        if not included:
            continue
        print(f"\n\n<!-- ── {group} ─{'─' * max(0, 78 - len(group))} -->")
        for requirement in included:
            if requirement.key in journey:
                axis, rung, in_force = journey[requirement.key]
                print(
                    f"\n<!-- {requirement.key}: {requirement.title} — A TARGET here, not yet in force: this repository "
                    f"stands at `{rung}` on the {axis} ladder; in force at `{in_force}` -->"
                )
                print(journey_statement(requirement, axis, rung, in_force))
                continue
            print(f"\n<!-- {requirement.key}: {requirement.title} -->")
            shipped = present_practice(requirement)
            if shipped:
                print(f"<!-- Practice: {', '.join(shipped)} -->")
            print(requirement.statement)
    return 0


def present_practice(requirement: Requirement) -> tuple[str, ...]:
    """The supporting skills this project actually has.

    `skills/` carries the part of the delivery catalogue this project can use — a skill about a capability
    it has no answer for is not shipped, and `docs/skills-and-commands.md` names those and says what each
    was waiting for — so a pointer at one of them would send the reader to a file that is not here. The
    catalogue sits beside this script, wherever that tree lives.
    """
    beside = Path(__file__).resolve().parents[1]
    return tuple(one for one in requirement.practice if (beside / one).is_file())


def abbreviate(placeholder: str, limit: int = 44) -> str:
    return placeholder if len(placeholder) <= limit else placeholder[: limit - 1] + "…]"


def findings(text: str, selected: list[Requirement]) -> list[str]:
    results: list[str] = []
    # Placeholders are read off the text flattened but otherwise as written, so the report names
    # `[COMPLIANCE_SCOPE]` and not a version with the underscores stripped as emphasis; the requirement
    # signals are read off the normalised text, where emphasis is noise.
    flat = flatten(text)
    flattened = normalise(text)
    placeholders = sorted(
        {match.group(0) for match in PLACEHOLDER.finditer(flat)}
        | {match.group(0) for match in INSTRUCTION.finditer(flat)}
    )
    if placeholders:
        shown = ", ".join(abbreviate(item) for item in placeholders[:3])
        remaining = f", and {len(placeholders) - 3} more" if len(placeholders) > 3 else ""
        results.append(
            f"{len(placeholders)} template placeholder(s) still unfilled ({shown}{remaining}); a "
            "constitution with placeholders is drafted, not ratified"
        )
    journey = targets()
    markers = {key: rung for key, rung in MARKER.findall(flat)}
    for requirement in selected:
        found = requirement.matched(flattened)
        marked = markers.get(requirement.key)
        if requirement.key in journey:
            axis, rung, in_force = journey[requirement.key]
            if marked == rung:
                continue
            if marked is not None:
                results.append(
                    f"{requirement.key} — {requirement.title}: the constitution says this repository stands at "
                    f"`{marked}`, and the map (project.json's convergence) says `{rung}`; amend the marker — or, if "
                    "the rung is reached, record it on the map first"
                )
            elif found >= requirement.needs:
                results.append(
                    f"{requirement.key} — {requirement.title}: written as in force, but the map says this repository "
                    f"stands at `{rung}` on the {axis} ladder and the principle comes into force at `{in_force}`; "
                    "either record the rung on the map, or mark the principle a target: "
                    f"`<!-- journey: {requirement.key} at {rung} -->`"
                )
            else:
                results.append(
                    f"{requirement.key} — {requirement.title}: neither in force nor written as a target "
                    f"(`<!-- journey: {requirement.key} at {rung} -->` with what holds here today)"
                )
            continue
        if marked is not None:
            results.append(
                f"{requirement.key} — {requirement.title}: marked as a journey at `{marked}`, but the map says the "
                "principle is in force here; write it in full and drop the marker"
            )
            continue
        if found < requirement.needs:
            shipped = present_practice(requirement)
            practice = f"; see {', '.join(shipped)}" if shipped else ""
            results.append(
                f"{requirement.key} — {requirement.title}: {found} of {requirement.needs} required "
                f"signals present{practice}"
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--requirements",
        nargs="*",
        metavar="KEY",
        help="print the normative text this project's constitution must cover, then exit",
    )
    parser.add_argument(
        "--journey", action="store_true",
        help="print the requirement-to-axis table the constitution-as-a-journey reads, then exit",
    )
    arguments = parser.parse_args()

    if arguments.journey:
        print(json.dumps(JOURNEY, indent=2, sort_keys=True))
        return 0
    selected = applicable(capabilities())
    if arguments.requirements is not None:
        return report_requirements(selected, arguments.requirements)

    if not CONSTITUTION.is_file():
        print(
            "check-constitution: no constitution ratified yet; run /speckit-constitution "
            "(scripts/check-constitution.py --requirements prints what it must cover)"
        )
        return 0

    raw = CONSTITUTION.read_bytes()
    if untouched_template(raw):
        if workflow_started():
            print(
                ".specify/memory/constitution.md is still the template ./init installed, but specs/ already "
                "has a feature:\n  - run /speckit-constitution before planning against it; every later "
                "phase reads that file as the authority it claims to be",
                file=sys.stderr,
            )
            return 1
        print(
            "check-constitution: nothing drafted yet (the constitution is the template ./init installed); "
            "the gate applies once /speckit-constitution has written it "
            "(scripts/check-constitution.py --requirements prints what it must cover)"
        )
        return 0

    results = findings(raw.decode(errors="replace"), selected)
    if results:
        print(".specify/memory/constitution.md is missing principles this project depends on:", file=sys.stderr)
        print("\n".join(f"  - {finding}" for finding in results), file=sys.stderr)
        print(
            "\nPrint the normative text with: python3 scripts/check-constitution.py --requirements "
            "[key ...]\nAmend the constitution rather than the gate — a principle removed here is a gate "
            "that stopped existing.",
            file=sys.stderr,
        )
        return 1
    journey = targets()
    held = f", {len(journey)} of them as targets held to the convergence map" if journey else ""
    print(f"check-constitution: {len(selected)} required principle(s) covered{held}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as error:
        print(f"check-constitution failed: {error}", file=sys.stderr)
        raise SystemExit(1)
