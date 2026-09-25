---
name: add-language
description: Factory-maintenance skill for adding a new backend language to slipwai (catalog.json, src/slipwai/ touchpoints, assets/languages/<language>/, example snippets, tests, CI, README). Use when asked to add, restore, or scaffold support for a new backend language in this factory.
---

# Add a backend language

This factory generates product monorepos for a matrix of `profile x language x frontend`
combinations from `catalog.json` and `assets/`. Adding a language means touching a fixed set of
per-language dictionaries under `src/slipwai/`, writing the one module that produces its
walking skeleton, committing that skeleton under `assets/languages/<language>/`, adding an idiomatic
example snippet for every marker any canonical skill already uses, and updating the tests/CI/README
that assert the language matrix. Follow this list top to bottom; skipping a step fails `make verify`
at a predictable point (noted below) rather than silently.

Java was removed from this factory specifically so this skill could be proven by re-adding it, and it has
now been re-added as `java-quarkus`. So the fastest concrete reference is no longer the deletion commits
but the live backend: **read `java-quarkus` for anything below you are unsure of.** It is the only backend
here whose framework owns startup, so it is the one that shows what sections 0, 4 and 5 actually produce —
per-backend tables keyed `java-quarkus` while its assets and examples split between
`assets/languages/java-quarkus/` (the skeleton, which a framework decides) and `assets/languages/java/`
(the example snippets, which a family shares).

**Read [`docs/backend-obligations.md`](../../../docs/backend-obligations.md) first.** It is the
checklist this document is a procedure for: every axis, every Make target, every per-backend table,
every choice that belongs to the ecosystem rather than to this repository, and what a framework that
owns startup is expected to provide instead of a hand-written adapter.
`tests/test_backend_obligations.py` holds that file to the catalog and the generator, so it is the one
inventory here that cannot quietly go stale — and when an axis or a target is added later, it is what
tells you the obligation now applies to *your* backend too.

**Three failure modes are worth naming before you start, because following this document faithfully caused
them.**

**One: spending the framework answer only on the backend's name.** Section 0 asks whether a framework owns
the ecosystem's startup — and a first run of this skill spent that answer only on naming and keying the
backend. The sections that write adapters
(4 and 5) describe the adapter set by pointing at the three existing backends, and all three are
framework-free, so mirroring their shape produced a framework-owned backend that hand-rolled a
datasource, a migration runner, a health endpoint and an OIDC placeholder — each one beside a
first-party extension of the very framework that had just been chosen. Mirroring those three is the
right instinct for the *ports and the contract suite* and the wrong one for the adapters behind them.
Section 0's "what does the framework already provide?" step exists to carry the verdict forward; do not
skip it on the grounds that the framework question is already answered.

**Two: assuming the ecosystem's container image can run `make`.** `compose.py` runs `make dev` inside
`ci_image` and the generated CI's integration job runs `make migrate test-integration` there, so a backend
whose image ships no GNU Make has *two* broken paths and neither is exercised by `make verify` — the demo
fails with `exec: make: not found` and CI fails the same way later. `node:`, `python:` and `golang:` all
carry it; no official Maven or JDK image does. Check with
`docker run --rm --entrypoint sh <image> -c 'command -v make'` before believing the demo works, and put
whatever is missing in `BACKEND_TOOLING`'s `container_setup` so Compose and CI install it from one place.

**Three: leaving the container's build output in the mounted checkout.** `COMPOSE_CACHES` masks a path with
an anonymous volume, which keeps the *contents* out of the host tree — but Docker still creates the mount
point on the host, owned by root, and the next host-side build then fails with a permission error nowhere
near its cause. That is why the `http` row of `docs/backend-obligations.md` names "the environment that
redirects it" as the alternative: point the toolchain's output somewhere outside the mount instead of
masking a path inside it. `make demo` followed by `make verify` in the same checkout is the test, and
`find . -user root` afterwards is the proof.

Pick a concrete language before starting (this doc uses `<language>` as a placeholder, e.g. `rust`,
`java`). Use its lowercase ecosystem name as the catalog key — it becomes a Python dict key, a CLI
`--language` choice, and a directory name under `assets/languages/`.

## 0. Decide the scope — ask, do not assume

### Before every question below: search for the answers, do not copy them from here

This document names products — Spring Boot, Quarkus, Fastify, Rails — and every one of them is there to
**illustrate a rule**, never to be offered to the user as the menu. Two different kinds of claim get made
in a skill like this one, and they have opposite sources of truth:

| A claim about | Source of truth | Example |
|---|---|---|
| **the ecosystem** — which frameworks own startup, what teams actually reach for, what a transport is called, which version is current, whether a project is still maintained | **a web search, every time** | "ASP.NET Core owns startup for C#", "Minimal APIs are the mainstream in 2026", "SDK 10.0.100" |
| **this factory** — which tables are keyed by backend, what `make verify` runs, what `validate_backends` refuses | **the code, read now** | `BACKEND_TOOLING`, `verify_dependencies`, `catalog.py` |

So: **run `WebSearch` before presenting any option to the user, and build the option list out of what it
returns.** Then apply this document's *tests* — "do you call it, or does it call you?", "does it need a
container?" — to those results. The rule is the durable part; the examples beside it were true when
somebody wrote them down and have been ageing since.

The failure mode this prevents is specific and quiet. A list copied out of a skill looks authoritative to
the person answering, so a stale entry is not read as stale — it is chosen. A framework that has since gone
unmaintained, a version that is two LTS releases behind, a library that has announced bugfix-only mode:
none of that is visible from in here, and all of it changes the answer, because whatever is chosen gets
pinned into every project this factory generates from then on.

The same applies past this section, and to more than versions. Wherever a version or an image name is
written down — the `actions/setup-*` step in section 2 item 5, `BACKEND_TOOLING`'s `ci_image` in item 13,
the toolchain row in `docs/requirements.md` — search for the current LTS rather than recalling one.

But **the choice of tool is an ecosystem claim too, not only its version**, and that is the more expensive
one to get wrong: a stale version is a one-line bump, while the wrong tool is baked into every project
generated from then on. Every one of these is a decision this factory makes *per backend*, and every one
of them has an answer that belongs to the ecosystem rather than to this document:

| Decision | Where it lands | What to search for |
|---|---|---|
| formatter, linter, static analysis | section 2 item 3 (`native["lint"]`, `["typecheck"]`) | what that ecosystem's teams actually gate on |
| test runner and coverage | section 2 item 3 (`native["test"]`) | the runner the chosen framework's own test harness expects |
| mutation testing tool | section 2 items 3 and 8 | the tool, **and its support matrix for your framework** |
| dependency audit | section 2 item 3 (`native["audit"]`) | whether the ecosystem has a first-party one |
| schema migrations | section 4 | the framework's migration integration before any standalone tool |
| datasource, pooling, transactions | section 4 | the framework's own datasource extension |
| health / readiness endpoint | section 4, `http` axis | whether the framework ships a health endpoint |
| OIDC client | section 4, `auth` axis | the framework's OIDC extension — never a hand-rolled flow |
| build-output and cache paths | section 2 item 2, section 4's `COMPOSE_CACHES` | where that toolchain actually writes |

The "search, do not copy" rule above governs this table exactly as it governs the framework question. What
is written in the right-hand column is the *question*; none of it is an answer.

**And every row of it is confirmed with the user before it is pinned — searching is half the job.** Put
the whole set to them in one pass with `AskUserQuestion`, each option carrying the fact that decided it:
the version, the release date, the maintenance signal, the support constraint a search turned up. This is
not the same instruction as the one above, and the difference is what a first run of this skill got wrong:
it searched all nine rows faithfully, decided all nine alone, and reported them afterwards — because the
sections below say "search this" and never say "then ask". The framework and the axes were confirmed; the
toolchain was not.

The reason to confirm is that the two kinds of decision are equally permanent. A generated project has no
update relationship with this factory, so a linter, a mutation plugin or an audit tool chosen here is
chosen for every project generated from now on, exactly as the framework is — and unlike the framework,
nobody is asked about it later. Three of these choices also cost real money to get wrong in a way a
`WebSearch` alone will not reveal:

- **the mutation tool**, whose support matrix for the chosen framework is a separate question from whether
  the tool is current, and which **no gate at either level ever runs** (`docs/backend-obligations.md`
  section 2) — so a wrong answer here is committed green and stays green;
- **the dependency audit**, because the honest options differ in what they *require* rather than in
  quality — an API key, or a committed lockfile the ecosystem may not otherwise need, which pulls
  `scripts/regenerate-locks.py` into scope;
- **static analysis depth**, which every generated project's gate then enforces on code nobody here will
  write.

Recommend one option per row and say why, so this is a confirmation rather than an interrogation. A user
who wants to defer to the recommendation can do it in one click; a user who has a house style, an internal
mirror, or a licence constraint gets the chance to say so before it is committed — and that chance is
exactly what a search cannot provide.

### First: is this a language, a framework, or an axis option?

Three different things get asked for in the same words ("add Java", "add Spring", "add Axum"), and they
are not the same job. One question separates them:

> **Do you call it, or does it call you?**

- **You call it** — you still own `main()`, and it is a dependency you hand a request to (`net/http`,
  `chi`, Fastify, Express, FastAPI). That is an **option on the `http` axis**, not a backend: use
  `.claude/skills/add-backing-service/` instead, and stop reading this one.
- **It calls you** — it owns startup, dependency injection, configuration, transactions and the test
  harness (Spring Boot, Quarkus, Nest, Django). That is a **new backend in an existing family**: a
  framework that owns the composition root owns how every adapter behind every other axis is written, so
  it multiplies with the language rather than combining with it. Use
  `.claude/skills/add-framework/` instead, and stop reading this one — a framework added beside one the
  family already has is a sibling, and that skill is the whole job.
- **Neither, because the language is new** — that is a **new family**, and the whole of this document
  applies. Keep reading, but do not skip the next section: a new family still has to answer "and what owns
  its startup?", and for most languages the answer is not "nothing".

The borderline cases resolve by asking the same question honestly. Ktor is the awkward one: you write
`embeddedServer(...)`, so you call it — but its DI plugin pulls the other way. The tiebreaker is whether
you would still hand-write the composition root `skills/hexagonal-architecture/` teaches. If yes, it is an
`http` option.

### Then: does anything own startup in this ecosystem? Probe, do not default to "nothing"

The question above sorts the **words the user typed**. It cannot catch the case that matters most here:
somebody types a bare language name for an ecosystem where nobody starts a service without a framework.
"Add Java" is a new family, so the triage above routes it to this document — and if you then follow this
document to the letter you will build a framework-free Java backend, which is a thing approximately no
Java team would start a product from. The request was almost certainly "add Java", meaning Spring Boot or
Quarkus.

So the moment you know the language is new, **ask which framework owns its startup, before touching
`catalog.json`.** Three steps, in this order:

1. **Search** for what owns startup in that ecosystem now — and for what it is used *instead of*, so the
   list has real alternatives in it rather than one answer and a straw man. A second search for adoption
   or maintenance status is worth it: "actively developed", "moved to bugfix-only", "last release" all
   change a recommendation, and none of them can be known from in here.
2. **Filter what came back through "do you call it, or does it call you?"** Search results will not make
   this distinction for you — they list "frameworks" and mean both kinds. Anything that runs *inside*
   another framework's host is an `http` axis option, however framework-shaped it looks. The tell is
   usually in its own documentation: a library that describes itself as building on, or hosting inside,
   the ecosystem's standard host is not the startup owner.
3. **Then `AskUserQuestion`**, offering what survived plus framework-free, with the fact that decided each
   one attached — the version, the maintenance signal, the adoption claim. Recommend the one a team would
   actually reach for. `none` is a legitimate answer, but it has to be chosen rather than arrived at by
   omission.

A worked example of steps 1–2, from the C# probe this section was written for: search returned ASP.NET
Core, ABP, Orleans, Minimal APIs, MVC controllers, FastEndpoints and Wolverine.HTTP as "C# frameworks". The
test cut that list in half — ASP.NET Core, ABP and Orleans own startup; the other four run inside the .NET
generic host, so they are candidate `http` options for an ASP.NET Core backend, and offering them as
frameworks would have produced a backend keyed for a thing that does not own its own startup.

Which way an ecosystem tends to fall is worth knowing as a *prior*, and no more than that. When this was
written, languages whose normal answer was a framework included Java, Kotlin, C#, Scala, Ruby, PHP and
Elixir — startup, DI, configuration, transactions and the test harness belong to the framework there, and a
framework-free backend is a teaching exercise rather than a starting point. Languages whose normal answer
was framework-free included Go, Rust, C and Zig, where the standard library or a thin router is idiomatic
and the composition root stays hand-written — which is exactly what `skills/hexagonal-architecture/`
teaches. TypeScript and Python have both routes, and this factory already chose the library route for both,
which is why their transports are `http` options and their backends carry bare language names; a Nest or
Django backend is a *sibling*, which is `add-framework`.

Treat that paragraph as a hypothesis to check, not a lookup table. It is the one part of this section with
a shelf life, and a search costs less than a wrongly-keyed backend.

**What the answer changes:** exactly one thing in section 1, and it is the catalog key. A backend that has
a framework is named for it from the start — `java-spring`, not `java` — because
`assets/languages/<family>/` holds what a family shares and a framework-built backend is not that shared
material. `validate_backends` refuses the other spelling in both directions, so this is mechanical rather
than a matter of taste. Getting it right on day one also means a second framework later is purely
additive: a sibling, with no rename of anything already generated.

Everything else in this document is unchanged by the answer. The skeleton, the thirteen tables of section
2, the axis assets and the example snippets of section 6 are the same work either way — a framework changes
what is *inside* those files, not which files there are.

### Then: what does the framework already provide? — the verdict has to carry

Answering "it calls you" is not only a naming decision. A framework that owns startup, DI, configuration
and the test harness also owns **the integration for each backing service behind it**, and that is where
the previous section's answer has to be spent. Ask it once per axis, before writing a single adapter:

> **Does the framework already ship an integration for this backing service?**

If it does, that integration *is* the adapter's implementation. Hand-writing one instead is not a neutral
stylistic choice — it means the generated project carries connection handling, migration bookkeeping,
health-probe wiring or a security protocol that the framework maintains, tests and patches for free, and
that this factory would then own forever.

Three steps, the same shape as the framework probe above:

1. **Search `<framework> <backing service>` for each axis you are answering** — the event store, the
   transport, identity. Frameworks in this class publish an extension, starter or module index; that
   index is the source of truth, not this document.
2. **Check what the integration brings with it that you were about to hand-write.** Pooling,
   configuration binding, a readiness probe, dev/test profiles, native-image support, metrics. A
   framework datasource extension usually also registers the database health check, so two axes get
   answered by one dependency.
3. **Then decide, and record the decision** in `docs/axes.md` beside the coverage row (section 9). "The
   framework's own extension" and "hand-written, because …" are both legitimate; an unexamined
   hand-written adapter is not.

**What stays hand-written regardless** — and this is why using the framework's extension does not
compromise the architecture `skills/hexagonal-architecture/` teaches:

- the **port** — an interface owned by the application, naming no framework type;
- the **domain** and its tests, which is the part the extension must never reach into;
- the **in-memory adapter**, so the contract has something infrastructure-free to run against;
- the **contract suite** run against every adapter, framework-backed ones included.

The framework's extension sits *behind* the port, in the driven adapter, exactly where a hand-rolled
driver would have. The port is what makes the swap invisible to the application — so "use the
framework's integration" and "keep the hexagon" are the same instruction, not competing ones.

**What must not be hand-written when the framework provides it:** connection pooling and datasource
configuration; the schema-migration runner and its ledger; the health and readiness endpoints; and above
all the OIDC protocol flow, where a hand-rolled implementation is a security defect rather than a style
one.

**Two traps that follow from adopting an integration**, both worth checking before you commit to it:

- **Automatic dev/test infrastructure.** Frameworks in this class increasingly start a throwaway
  container for a datasource when one is not configured. That is a direct conflict with this factory's
  rule that the default gate runs with no Docker and only `make test-integration` touches a real service.
  Find the switch that disables it and set it explicitly, then prove the gate still runs with the Docker
  daemon stopped.
- **A cross-backend contract the integration does not match by default.** The generated Compose
  healthcheck, `make demo`'s printed URL and the run skill all name one path, and the other backends'
  probe bodies agree on a shape. All of it lives in `probes.py`: `HEALTH_PATH` as a constant, because a
  liveness probe's path is configurable and every backend is pointed at the same one; the per-language
  table `READY_PATHS`, read through `ready_path`, which is keyed by backend and says where this one
  answers "send me traffic"; and `HEALTH_BODIES`, read through `health_body` and keyed by backend too,
  because a specification can fix the body and MicroProfile Health does. So an integration serving its own
  liveness path is *configured* onto `HEALTH_PATH`; one whose readiness endpoint is its own — SmallRye
  Health, Actuator — *adds a row* to `READY_PATHS` naming the path it serves, rather than growing a
  hand-written `/ready` beside a maintained probe; and one answering in its own shape *adds a row* to
  `HEALTH_BODIES`. Read `compose.py`, `infra.py`, `makefile.py` and `run_skill.py` for what is actually
  promised before assuming any of them.
- **A health check that is red while the service works.** A framework datasource extension usually
  registers a readiness check per datasource, which is a real benefit and the wrong default here: nothing
  in a freshly generated project reads the event store, so the check reports DOWN wherever the database is
  unreachable — which is `make verify` by design, and `make demo` too, since Compose cannot hand the
  service the store's address (that line would sit inside the transport's marked region, and the pruner
  refuses a nested marker). Ship it off, with the note that says to turn it on in the same change that
  wires the store into a use case.

### Then: which axes should it answer?

Adding a backend is not one decision. It is the walking skeleton, plus one independent decision per
**axis**: where events live, what accepts inbound HTTP, who issues staff identities. The skeleton is
always in scope; the axes are not, and which ones you take changes how much of this document applies —
section 4 and half the tables in section 2 exist only for an axis you are actually implementing.

**Ask the user before writing anything.** Use `AskUserQuestion` with one multi-select question — "Which
axes should the `<language>` backend answer?" — offering the three below with these recommendations. Do
not infer the answer from the bare request: axis coverage is the difference between a backend that can be
demonstrated and one that can only be verified, and it is not a detail to settle by omission.

These three options need no search: which axes exist, and what each one costs a backend that skips it, are
facts about this factory. Read them from `catalog.json` and from the call sites named below rather than
from this list, which is the same reason — the code is the source of truth that is *here*, so use it.

- **`event-store` — recommend it.** `event-modelling` is the default profile and the event-store port is
  its whole subject. Without an adapter the project still gets the port and a contract test asserting a
  version conflict is a returned value, but nothing implements the port, so the contract runs against
  nothing. Take `memory`, `sqlite` and `postgres` together rather than one of them: the value is one
  contract suite running against all three, and a fake with no real adapter beside it has nothing keeping
  it honest (see section 4).
- **`http` — recommend it.** A backend with no transport has no `make dev`, no `docker-compose.yml` and
  no `make demo` — verified, not assumed: `transport_feature(selection)` is `None`, so `makefile.py` emits
  no `dev` target and `composed()` is false. The project passes its gate and can never be shown running,
  which is the one outcome this factory's own generated guidance calls out ("a green gate is not a
  demonstration"). This is a new `http` option naming that ecosystem's own transport, not this language
  added to an existing one — and **which** transport is an ecosystem question, so search it and ask, the
  same way the framework was decided. The candidates are usually exactly the libraries the framework
  question rejected for running inside somebody else's host: that is what an `http` option is. Weigh
  maintenance status heavily here, because this option gets pinned into every project generated with it.
- **`auth` — optional, and never first.** `keycloak` ships its realm, container and group mapping with the
  protocol flow deliberately unimplemented, and every backend defaults to `none`, so a language without it
  sits exactly where the others' default does. It also `requires` the `http` axis, so it cannot be added
  before a transport exists.

**Answering none of them is legitimate** — but as a stated choice, not a silent one. Such a backend ships
the whole toolkit, its walking skeleton and the event-store port with nothing behind it, and ships nothing
that needs an adapter. Say that back to the user in those terms before you start, so "add Rust" and "add a
Rust backend we can run" are not quietly treated as the same request.

Whatever they choose, record it in `docs/axes.md`'s coverage table (section 9) — a row of dashes is how a
gap stays visible, and `tests/test_catalog.py::test_the_documented_axis_coverage_is_the_catalog_s` fails if
the table and the catalog disagree.

## 1. catalog.json

Add the backend to the `backends` object. A backend is a language, plus the framework that owns startup
where the ecosystem has one — flattened into a single key, because the two do not combine independently
(see section 0):

```json
"backends": {
  "go": { "family": "go", "label": "Go — modules, gofmt, `go vet`, `go test`" },
  "java-spring": {
    "family": "java",
    "framework": "spring-boot",
    "label": "Java — Spring Boot owns startup; Maven, Checkstyle, JUnit"
  }
}
```

`family` is the language itself, and it is what `snippet`/`resolve_examples_for` and the pseudocode disclaimer read —
so the snippets in section 6 are shared by every backend in the family, and only the ones a framework
actually changes are overridden per backend. `label` is what the framework prompt shows.

**The naming rule, which section 0 already made you decide.** The key is the bare language name **exactly
when nothing owns startup** (`go`, `python`, `typescript`); a backend that has a framework is suffixed with
it (`java-spring`) whether or not it has a sibling yet. `assets/languages/<family>/` holds the material a
family shares, and a backend built around a framework is not that material even while it is the only one.
`validate_backends` enforces both directions, so the wrong spelling is a refusal rather than a style
disagreement:

- `java-spring` alone → fine. This is a new framework-first language on day one.
- `java` declaring `"framework": "spring-boot"` → refused: *"must be named for that too"*.
- `go-plain` alone with no framework → refused: *"must be named for the language itself"*.

A `default.framework` entry is **not** wanted while the family has one member, however that member is
spelled — one answer is not a choice, and `validate_backends` refuses it too. It arrives with the second
member, which is `.claude/skills/add-framework/`:

```json
"default": { "framework": { "<language>": "<the one a team would keep>" } }
```

Nothing in `cli.py` or `cli_prompts.py` needs touching either way: `prompt_framework` asks the language, then asks the framework only where the
family has more than one member — the same "something with one answer is not a choice" rule the axes
follow — and `resolve_backend` turns the pair into the key everything downstream is keyed by. A lone
`java-spring` is reachable as `--language java`, as `--backend java-spring`, and as `--language java
--framework spring-boot`; any other `--framework` is refused naming the one it does have.

Then decide, per **axis**, whether your backend can answer it. `catalog.json` has one entry per axis —
`event-store`, `http`, `auth` — and every option under it declares the backends it is implemented for:

```json
"postgres": {
  "capabilities": ["event-store-postgres"],
  "backends": ["typescript", "python", "go"],
  "containers": ["postgres"],
  "features": ["postgres"]
}
```

Doing nothing is a safe answer: your backend is simply absent from those `backends` arrays, so
`--event-store postgres` with it is refused at the command line with the reason, and no half-ported adapter
is emitted. It is safe, but it is the answer section 0 asked the user for rather than one to take by
default — a backend that answers no axis cannot be run, and that is a decision, not an omission. Add your
backend to an option's `backends` array only once you have actually written that option's assets for it —
see section 4.

**The `default` block, once you do add an option.** `catalog.json` carries a recommended answer per axis,
and `--event-store` and `--http` both recommend something real. A backend an axis has nothing for falls
back to that axis's no-infrastructure answer automatically, so a language absent from every `languages`
array needs no entry here at all. The moment you add your backend to an option, though, `validate_catalog`
requires the default to name an answer for it — a backend that *can* be given a transport and is left
defaulting to `none` is a recommendation that quietly stopped being made. For a per-backend axis that means
one line:

```json
"default": { "http": { "typescript": "fastify", "python": "fastapi", "go": "net-http", "<backend>": "<its option>" } }
```

`event-store` recommends `postgres` for every backend as one string, so adding your backend to that
option's `backends` array is what makes the recommendation apply to it — no `default` edit needed. If your
backend gets some stores but not that one, the string has to become a map naming what each backend can
actually be given; the validation error says so, and names the options yours has.

Two things about the axis data are worth understanding before you touch it:

- **`always` versus an option's `features`.** The `event-store` axis declares `"always": ["memory"]`. That
  is what makes the in-memory adapter un-prunable: every answer ships it, because it is what the port's
  contract runs against in `make verify`. A feature listed in an option's `features` is one a generated
  project can later drop; a feature in `always` is not, and the catalog refuses to have it in both.
- **The transport axis is one option per backend.** `fastify` is TypeScript, `fastapi` is Python,
  `net-http` is Go. A new backend means a new `http` option naming its own transport, not adding your
  backend to an existing one — and the refusal message then points at *your* option, because it is
  computed from `axis_options(axis, language)` rather than from the catalog's first entry.

## 2. src/slipwai/ — per-language dictionaries

Every one of these is a literal collection keyed by language name — a `dict[str, ...]` in all but the
last case. Add a `"<language>": ...` entry to each. Each item below names the module that owns it, and
paths are relative to `src/slipwai/` except for item 12, which is the pruner the generated
project runs and lives under `assets/`.

This list is the inventory — do not substitute a grep for it. `grep -rn '}\[language\]'` finds the
ones indexed inline and misses every one bound to a name first, and two of the sites it *does* find
belong to section 4 rather than here, because a backend that answers no axis never reaches them.

The same inventory, with the conditional entries marked and each one's module beside it, is section 3 of
[`docs/backend-obligations.md`](../../../docs/backend-obligations.md) — and unlike this list, that one is
asserted against the modules it names. If the two ever disagree, that file is right and this one has
rotted.

1. **`catalog.py`** — `validate_catalog`'s `expected_backends` set gains `"<backend>"`; update
   the count in the adjacent `ValueError` message (currently "three supported backends").
2. **`project/gitignore.py`** — `build_artifacts`'s `language_artifacts` dict: the `.gitignore`
   fragment for this language's build output and caches (e.g. `target/\n` for a Maven-like build,
   `__pycache__/\n...` for Python).
3. **`project/native_commands.py`** — the `native` dict in `service_commands`: one entry with keys
   `install`, `typecheck`, `lint`, `test`, `integration`, `adversarial`, `audit`, `mutation`, each a shell
   snippet run from the repository root for **one service**, spelling that service's directory as `{APP}`
   (most `cd {APP}` first — never `apps/service`, because a project may have several services and the
   table is stamped per service; `docs/services.md`). Match the other languages' shape — the generated `make verify`
   runs `check-python lint typecheck check-imports check-migrations check-slice-scope check-extensions check-agents check-speckit check-codegraph check-ux-gates
   check-constitution check-benchmark check-decisions test [check-model] [check-drawio]` (see `verify_dependencies` in `project/makefile.py`, the table's only reader) and
   `make ci` adds
   `audit test-integration`, so every key must produce a working command with no project-level
   config beyond what sections 3 and 5 provide. If the ecosystem needs a separate frontend-aware
   toolchain step (like the `if frontend == "react-vite": ...` block below the table in
   `native_commands`),
   confirm it triggers for `language != "typescript"` as the existing block already does — no
   per-language change needed there unless the new language needs bespoke wiring.
4. **`project/agent_settings.py`** — the `native` dict: the `Bash(...)` permission globs this
   language's toolchain needs (e.g. `["go test *", "go vet *", "gofmt *"]`). If the toolchain is driven
   through one entry point rather than several binaries (a build tool, a task runner), add that
   invocation pattern here — see item 10 for what such an entry point may and may not be.
5. **`project/ci_workflows.py`** — the dict in `toolchain_setup`, keyed by family: the `actions/setup-<language>@vN` GitHub
   Actions step (`with:` block included) run before `make verify` in the generated repo's own CI.
6. **`project/docs.py`** — `documentation_files`'s `gate` dict: a short human-readable description
   of this language's native verification stack (e.g. `"gofmt, \`go vet\`, and \`go test -cover\`"`),
   used in the generated `docs/gates.md`.
7. **`project/event_model.py`** — `event_documentation`'s `paths` dict: illustrative file paths
   for `events`, `domain`, `usecase`, and `test` responsibilities, used in the generated
   `docs/event-modeling-to-code.md` and
   `docs/first-slice.md`. If the language needs a derived package/namespace segment from the
   project name (Python does this with `documented_python_package`, sanitizing to
   `[a-z0-9_]` and prefixing a leading digit), add the same sanitize-and-prefix pattern here and
   reference it in the path strings — see `dde1b7f`'s reverse diff for the Java version
   (`documented_java_segment`/`documented_java_path`) as a second worked template.
8. **`project/mutation.py`** — `mutation_command`'s `tools` dict: the mutation-testing tool name
   for this ecosystem (only used in generated prose; the mutation Make target itself lives in item 3
   above).
9. **`project/languages/__init__.py`** — the `BACKENDS` dispatch: `"<language>": <language>`,
   naming the module you write in section 3 below. The facade does one thing per service — prefix every
   path `service_files` returned with that service's directory and hand it to your `name_service` — and
   then delegates the repository root to your `repository_files`. There is no per-language branch to add
   here beyond the dispatch entry.
10. **`BACKEND_EXECUTABLES` in `backends.py`** — every backend needs an entry, an empty `set()` where the
    skeleton ships no script of its own. It names the generated paths (`{APP}/...`, stamped per service)
    that have to arrive at `0o755`; `executable_paths(profile, language, apps)` in `toolkit.py` unions it with the toolkit's
    own, whose bit is read off disk instead because those land where they are committed. A lost `chmod +x`
    is the difference between a working gate and a fresh clone reporting "permission denied", and
    `tests/test_matrix.py` asserts the mode from this table rather than naming any file.

    **A build wrapper can go here, but only the script-only kind.** The default `gradlew`/`mvnw` needs a
    `.jar` beside it and this factory cannot emit a jar at all: `assets/` is text or it is nothing, which
    `tests/test_factory_repository.py::test_every_asset_is_text_because_the_pipeline_can_carry_nothing_else`
    pins. Maven's `wrapper:wrapper -Dtype=only-script` emits three text files and no jar, which is how
    `java-quarkus` commits one — see `MAVEN` in `backends.py`. Check two things before following it:

    - **Line endings are load-bearing here and nowhere else.** `mvnw.cmd` is CRLF throughout and is a
      batch/PowerShell polyglot that re-reads itself, so `asset_tree` reads and `write_project` writes with
      `newline=""` and the skeleton ships a `.gitattributes` declaring `eol=lf`/`eol=crlf`. A wrapper added
      without those arrives flattened and passes a character-level check while being unrunnable on Windows.
    - **What the download costs, and whether anything caches it.** The script fetches a whole distribution
      on first use. For Maven, `actions/setup-java@v5` caches `~/.m2/wrapper/dists` under a key derived from
      the wrapper properties alone, and `COMPOSE_CACHES` covers the containers — so it is one fetch per
      pinned version. An ecosystem with no such cache is one where taking the tool from the PATH is still
      the better answer. Do not pin a `distributionSha256Sum`: the script swaps to `.tar.gz` when `unzip` is
      missing, which the Java images here do, and one sum cannot match both archives.

    Whichever way it goes, pin the version somewhere the repository holds — the wrapper properties, or the
    CI setup step (item 5) and `BACKEND_TOOLING`'s `ci_image` (item 13) — and state what a contributor must
    already have in `docs/requirements.md` (section 9).
11. **`project/makefile.py`** — the `service_variables` / `integration_targets` block, which is where the
    Makefile is assembled from the recipes item 3 wrote. It derives the
    Postgres-free `INTEGRATION_TEST ?=` fallback from your `native["integration"]` entry by splitting on
    `"\n\t"` and taking the last line, so a multi-line integration recipe works as long as the *last*
    line is the command that differs.
12. **`prune.py`** — `LANGUAGES`, the language families the generated project's own pruner knows the
    layout of. Required whether or not you answer an axis: `validate_catalog` asserts that tuple
    against the catalog's families, so a new family missing from it refuses every generation, not just
    the ones with something to prune. Families rather than backends, because `project_language` reads
    `project.json`'s `language`.
12b. **`images.py`** — `IMAGE_BUILDERS`: how a service on this backend becomes a production image with the
    ecosystem's own builder (a `pack` invocation with the right buildpack environment, `ko`, a Maven goal),
    and the `tool` the deploy workflow has to install for it; `MIGRATIONS_IN_PRODUCTION`: how its
    migrations run once it is an image — a `command` in the service's own image, a second `image` from
    another entry point, or an `environment` that makes the framework migrate at start-up. Both are keyed
    by backend and read only under the `aws` target, so a backend can arrive with a row that is honest
    about what is unproven. Prove the build by hand: `make build smoke-image PLATFORM=<yours>` in a project
    generated with `--target aws`; `docs/aws-target.md` says what is and is not gate-tested.
13. **`backends.py`** — `BACKEND_TOOLING`, the one table the Makefile, the CI workflow and the
    README all read for "how does this backend install, migrate, run its integration suite, and
    which container image does its CI job use". Add an entry even if you answer no axis yet: the
    `migrate` and `integration`
    values are only reached once Postgres is offered for your language, but `install` and the CI image
    are not. `app_tooling` in `tooling.py` is how the Makefile and the CI workflow read this table — once
    per service, with the service's own path stamped in — so it needs nothing from you beyond the entry.

## 3. src/slipwai/project/languages/<language>.py

Create the module beside `typescript.py`, `python.py` and `go.py`. It owns three functions, and nothing
outside it needs to know how your ecosystem names things. A project may have several services
(`docs/services.md`), so the first two are called once per service and the third once for the list:

- `service_files(event: bool, selection: Selection) -> dict[str, str]` — the initial contents of one
  service's directory, keyed by path *relative to* it (the facade in section 2, item 9 prefixes that).
  Start it with `asset_tree(LANGUAGE_ROOT / "<language>/app")`, which copies your committed skeleton
  (section 5) verbatim, then add only the files whose *content* the selection decides — a manifest with
  per-feature dependencies, a config with a marked region.
- `name_service(project_name, service: App, files) -> dict[str, str]` — that service's files under this
  project's own names. Rewrite the paths that embed a placeholder package or module name, then replace
  that placeholder inside each rewritten file's content, touching only paths under `service.path`. Name the
  package after `service_qualifier(project_name, service.name)` — the project alone for the first service,
  `<project>-<service>` after — so the first service is named exactly as it always was. `python.py` is the
  template when your language needs a project-derived package name; `go.py` is the template when one
  module path is enough — and note that `go.py` rewrites the module path in **every** `.go` file, not only
  in `go.mod`, because every import of the service's own packages names it. A version that rewrote only
  the manifest would produce a project that does not compile.
- `repository_files(project_name, files, selection, services: list[App]) -> dict[str, str]` — whatever
  manifests your ecosystem puts at the repository root above the services (npm's workspace `package.json`
  and lockfile, Go's `go.work`), and `files["scripts/verify"]`, each iterating over `services`. Decide
  here what a second service *is* in your ecosystem — a second workspace, a second module in one
  workspace, a second build with no aggregator — and say why in the docstring, as `go.py` and `java.py`
  do.

The factory's own gate has two requirements for the file itself: a module docstring saying which part
it is, and under 350 lines. `scripts/check-structure.py` enforces both, and it also enforces the import
direction — your module sits in the `parts` tier, so it may read `assets`, `backends`, `catalog`,
`selection` and its sibling `project/` modules, and may not read `scaffold` or `cli`. Keeping the file
content in `assets/` (section 5) is what keeps it comfortably inside the budget.

Copy the shape from the three existing modules, not their syntax. Two things in them are load-bearing
and easy to miss:

- **The event-sourcing fallback is conditional on the axis, not on the profile.** `go.py` and
  `python.py` read `if event and not selection.has("memory")`, then merge
  `asset_tree(LANGUAGE_ROOT / "<language>/event-port")` — a port with a shape and nothing behind it,
  emitted *only* for a backend whose event-store axis is not offered yet. Once that axis is asked, the
  port and its adapters arrive together from section 4 instead, and emitting both would define the port
  twice. Write the same guard, and commit the same shape under `event-port/`: `DomainEvent`, an
  `AppendResult`-shaped outcome type, an `EventStore`-shaped port, and one contract test asserting a
  version-conflict is a returned value, never a thrown/raised error.
  `tests/test_language_skeletons.py` asserts both halves — that the port matches its asset, and that it
  is *not* what arrives once an adapter is selected.
- **A flag reader is part of the skeleton, and it is target-conditional.** `service_files` takes
  `target` and ends with `files.update(flag_reader(target, "<language>"))`, which merges the tree
  `FLAG_READERS` in `project/flags.py` names for your backend — nothing at all under `--target none`,
  which has no flag mechanism. Add the row there and commit the tree under
  `assets/languages/<language>/flags/` (see section 5): one key-to-variable transform (`checkout-v2` →
  `FLAG_CHECKOUT_V2`), on only for the exact string `on`, absent read as off rather than as an error, and
  the environment taken as a parameter so a test can drive both paths. Read the existing four first —
  they are one file each and the reasoning is in their comments — and note that both Java backends share
  `java/flags` because the class names no framework type. Without this row, generation raises `KeyError`
  the moment somebody asks for your language with a production target, and a slice in it has no way to
  reach production dark.
- **End `service_files` with `files.update(backing_service_service_files(selection, "<language>"))`,**
  as all three existing modules do, so a selection's adapters land in the same dict. That function
  indexes its layout table with `[language]`, so it raises `KeyError` for a language the table does
  not name — add a `"<language>": {}` entry there now even if you are adding no axis assets, and
  fill it in section 4 if you are.

**Do not inline file content here.** A generated file's body belongs under `assets/` (section 5) — that
is what makes `assets/` the single source rather than a claim, and `tests/test_language_skeletons.py`
fails a module that stops reading its tree. Code in `service_files` is for the files whose content
genuinely varies with the selection: `typescript.py` writes `tsconfig.json` and `vitest.config.ts`
because a marked region depends on the answer, and `python.py` writes the dependency arrays into
`pyproject.toml` — and picks the committed `uv.lock` resolved from exactly that manifest — because the
dependency list does. Everything else is a copy.

## 4. Axis assets for a new language (only if you are adding them)

Skip this section unless you added your language to an option's `languages` array, or added an `http`
option for it, in section 1. If you did, the same rule as everywhere else applies: emit nothing half-ported.

**Three more per-language tables become mandatory here**, and only here — which is why section 2
leaves them out. All three live in `backends.py`, all three are indexed with `[language]`, and all
three raise `KeyError` rather than degrading, so a missed entry fails generation for your backend the
moment the axis is answered:

- **`dev_command`** — how this backend starts the service in the foreground, read by the generated
  `make dev`. Required as soon as your language has an `http` option, because a project with a
  transport gets a `dev` target. The same string is what Compose runs inside the container, so there
  is one answer rather than a local one and a demo one.
- **`COMPOSE_CACHES`** — where this backend's toolchain writes what it installs, relative to the
  container. `make demo` mounts the checkout and gives each of these paths a volume, so a Linux
  container's installed dependencies do not land in the host's working tree and break the native
  `make verify` that ran fine an hour earlier. Required alongside `dev_command`, and read from the
  same `app_services` block.
- **`event_store_directory`** — where this backend's driven adapters live, quoted by the generated
  `AGENTS.md` when the project has an event store. Required as soon as your language answers the
  `event-store` axis.

- Assets live under `assets/backing-services/<language>/`. Look at how the three existing backends are
  shaped: a port every adapter implements, the in-memory adapter, the file-backed and real ones, **one
  contract suite run against all of them**, and the migrations. The set is the point — a fake with no real
  adapter checked against the same contract has nothing keeping it honest.
- **Mirror that set, not its plumbing.** All three of those backends are framework-free — a library
  transport and a hand-written composition root — so what their adapters do *inside* is the framework-free
  answer, and copying it into a backend whose framework owns startup is how a first run of this skill
  produced a hand-rolled datasource, migration runner and health resource beside a framework shipping a
  first-party extension for each. The port, the in-memory adapter and the contract suite transfer unchanged. The body of a real
  adapter does not: that is section 0's "what does the framework already provide?" question, and it is
  answered per axis, from a search, before this file is written.
- `backing_service_service_files` in `project/backing_services.py` maps those assets to paths relative to
  a service's directory, keyed by
  language then by feature. Add a `"<language>": {...}` block. Paths are relative to your asset directory,
  and `../sql/...` reaches the event-log schema shared with the other SQL backends — use it rather than
  copying the DDL, and `tests/test_backing_services.py` asserts the copies that do exist have not
  drifted.
- **The generated `make verify` must still run with no Docker.** Whatever you write, the port's contract
  runs against the infrastructure-free adapters in the ordinary gate, and only `make test-integration`
  touches a real service. A test that needs infrastructure goes where the default suite cannot see it: an
  excluded directory, a separate config, or a build tag.
- `PACKAGE_EDITS` in `assets/backing-services/prune.py` names the dependencies and scripts each feature
  adds, per language, so the prune can remove exactly those again. `OWNED_FILES` names the files each
  feature owns — patterns may glob, which is how the Python entries reach inside a package directory named
  after the project. `tests/test_pruning.py` asserts that what generation adds and what the prune
  removes agree, per feature.
- **Commit the dependency lock.** A manifest and its checksums have to move together, or the project's
  first install refuses to run. `scripts/regenerate-locks.py` produces every committed lock — npm
  lockfiles per dependency set, and `go.mod`/`go.sum` per Go variant, by generating a real project and
  tidying it. Add your ecosystem there rather than writing a lock by hand, and run
  `python3 scripts/regenerate-locks.py --check` to see whether one has gone stale.
- Marked regions (`backing-service:<feature>:begin` / `:end`) are how a generated project prunes a feature
  later. Pruning only ever *subtracts*, so an "and this instead when it is absent" spelling cannot be a
  second marked block — the factory already cut the other branch. Express the alternative so both states
  are valid at once; the generated `Makefile` does it with `INTEGRATION_TEST :=` inside the block and
  `INTEGRATION_TEST ?=` outside it, and `services-up` does it by testing for the Compose file the prune
  deletes. Add any new marked file to `MARKED_FILES` (or `MARKED_FILES_BY_LANGUAGE`) in `prune.py`, or its
  region is silently never pruned.
- If an option of yours needs another axis answered — the way `auth` needs `http` — declare it in the
  catalog axis's `requires` and in `REQUIRES` in `prune.py`. Both ends matter: the factory refuses the
  combination at generation time, and the pruner refuses to create it later.
## 5. assets/languages/<language>/ — the committed skeleton

Every language has files here; this is where the walking skeleton lives. Lay each subtree out at the paths
its files land on, so reading it is a copy and nothing else:

```text
assets/languages/<language>/
├── app/            the walking skeleton, at paths relative to a service's directory
│                   — the build manifest, a `health` module, its test
├── event-port/     the port with nothing behind it, emitted only for a backend whose
│                   event-store axis offers nothing yet (see section 3); omit if yours answers it
├── flags/          the feature-flag reader and its own tests, at paths relative to a
│                   service's directory — emitted only under a production target, and
│                   named in `FLAG_READERS` in `project/flags.py` (see section 3)
├── repository/     whatever your ecosystem puts *above* the services, at repository-root
│                   paths — an aggregator manifest, a workspace file. Read by
│                   `repository_files`, so those bodies are assets rather than string
│                   literals; omit it if one computed line is enough, as Go's go.work is
├── locks/          committed dependency locks, if the ecosystem has them
│                   (TypeScript: package-lock*.json; Go uses modules/<variant>/ instead).
│                   An ecosystem whose manifest already pins every version exactly needs
│                   none, and then `scripts/regenerate-locks.py` has nothing to add
└── examples/       marker snippets — a different concern entirely, see section 6
```

Everything here is **text**, and that is a hard limit rather than a convention: the asset pipeline reads
and writes with `read_text`/`write_text`, so a `.jar`, a font or an image cannot be committed under
`assets/` at all (see section 2, item 10, and the gate it names). An executable *script* is fine — mark it
executable and add its path to `executable_paths` in `toolkit.py` so the generated copy keeps the bit.

Adding a file to `app/` later needs no code change — the tree is read, not enumerated, which is the
property `tests/test_language_skeletons.py` pins.

## 6. Example snippets — required, or `make verify` fails

Canonical skills reference language examples with a `{{example: <skill>/<id>}}` marker (see
`resolve_examples` in `src/slipwai/examples.py`). At generation time every marker in every
toolkit file and
profile overlay is resolved against `assets/languages/<language>/examples/<skill>/<id>.md` for the
project's backend language; a missing snippet raises `GenerationError` and fails generation.
`tests/test_toolkit.py::test_every_example_marker_resolves_for_every_catalog_language` enforces
this statically (no generation needed) for every language in `catalog.json` — so adding a language
to the catalog before this section is done fails `make verify` immediately, with a clear
"half-translated example: missing snippet(s) ..." message naming every gap.

Find every marker that currently exists and write one snippet per marker for your new language:

```sh
grep -rhoE '\{\{example: [a-z0-9-]+/[a-z0-9-]+\}\}' assets/toolkit assets/profiles | sort -u
```

For each `{{example: <skill>/<id>}}` found, create
`assets/languages/<language>/examples/<skill>/<id>.md` containing **exactly one** fenced code block
(with its language tag, e.g. ```` ```go ````) — no surrounding prose; the marker's surrounding prose
in the skill file already carries the explanation. Write idiomatic code for your language's own
conventions (see the existing `typescript/`, `python/`, and `go/` snippets for the three ways the
same concept — e.g. an optimistic-concurrency conflict as a value, not a throw/raise — gets
expressed per ecosystem). Do not transliterate another language's snippet line-by-line.

Your snippets are also what a polyglot project shows beside the others': `resolve_examples_for` in
`src/slipwai/examples.py` expands each marker to one labelled block per language the project's
services are written in (`**Go — \`apps/ledger\`**`), in service order, and `add-service --language
<yours>` regenerates the four marker-carrying skills so they gain your language. Nothing to wire: the
label comes from the part of your catalog `label` before the ` — `.

Skills that still carry a raw ```` ```typescript ```` or ```` ```ts ```` fence (not yet converted to
a marker) need no snippet from you: `stamp_pseudocode_notes` in `src/slipwai/examples.py`
automatically
stamps a "TypeScript-as-pseudocode" disclaimer under the title of *every* file that carries such a
fence — resources and references included, not just `SKILL.md` — when generated for your new
non-TypeScript language, plus the skill's `SKILL.md` so the warning arrives before the reader is
routed into a resource. The frontend-inherent skills (`react-testing`, `front-end-testing`,
`typescript-strict`, `bff-entry-points`) stay TypeScript-only by design and are exempt from that
disclaimer — their TypeScript is the real thing rather than a stand-in, and they ship whatever the
selected frontend is. As more skills get converted to markers over time (see the
task that converted `testing`, `event-sourcing`, `hexagonal-architecture`, and
`domain-driven-design`), the marker grep above simply returns more results — there is no separate
list to keep in sync.

## 7. tests/

The suite is one module per concern, and `tests/support.py` holds the `FactoryTestCase` base every
module builds on — `self.generate(...)` and `self.refuse(...)` come from there. A new language mostly
touches `tests/test_matrix.py`.

- `tests/test_monorepos.py::test_scaffolds_complete_matrix_as_independent_monorepos` computes `len(repos)`
  from
  `CATALOG["profiles"] x CATALOG["languages"]` automatically — no count to update by hand, but add
  language-specific file-existence assertions analogous to the Go/Python ones already there (e.g.
  the equivalent of `(repos[("continuous-delivery", "go")] / "go.work").is_file()`) for any
  distinctive root-level file your language produces.
- If any test was pointed at a specific *other* language purely as a stand-in sample (grep `tests/`
  for `"go"` and `"python"` used as literal arguments to `self.generate(...)`), leave those alone —
  they are not about the new language.
- `tests/test_catalog.py` asserts the per-axis option lists per backend; a language that answers an
  axis belongs in those assertions.
- Run `make verify` (below) before considering this step done; it exercises the full matrix
  including your new language for every existing test.

## 8. The factory's own CI — two places, both held by a test

The factory's CI runs the matrix suite as one job per backend (`strategy.matrix` in
`.github/workflows/verify.yml`, sliced with `FACTORY_BACKENDS`), and every job installs its toolchains
through one local composite action. A new language touches exactly two files:

1. `.github/actions/toolchains/action.yml` — add the same `actions/setup-<language>@vN` step you wrote for
   the generated repo's own CI (section 2, item 5). Nowhere else: the workflow's jobs all `uses:` this action.
2. `.github/workflows/verify.yml` — add the backend key to the `matrix.backend` list, in catalog order.

`tests/test_factory_repository.py::test_the_ci_matrix_names_every_backend_the_catalog_has` compares that list
to `CATALOG["backends"]` and fails until they match — a backend missing from it is one CI never gates, with
every other job green. The `toolchains` job warms the shared tool cache alone before the slices start, so
the new step's first download is not raced by five jobs at once.

## 9. Documentation

`README.md` is a short overview plus a how-to-use guide; the reference material lives in `docs/` and
`assets/README.md`, so the language list appears in several files:

- `README.md` — the pitch line's language list.
- `docs/axes.md` — the coverage table under "Which backend can be given what" (one row per backend, a
  dash per axis it answers nothing for; pinned to the catalog by the test named in section 0), the
  generated-verification-conventions sentence, the "Backend language and browser frontend are independent
  choices" paragraph, the `--http` row's per-backend answers, and the dependency column of the "what
  arrives" table if the language brings its own driver.
- `docs/generating.md` — the interactive language choices example
  (`Language (typescript/python/go/<language>) [...]:`) and one CLI `--language` example.
- `docs/requirements.md` — a `make verify` in a `<language>` backend row for the toolchain it needs.
- `docs/maintaining.md` — the "eight/six/... foundations" count in "Browse the starters"
  (`len(CATALOG["profiles"]) * len(CATALOG["languages"])`).

## 10. Verify

```sh
make verify
```

This scaffolds every `profile x language x frontend` combination — plus the backing-service variants —
and runs each one's native gate,
so a gap in any step above surfaces here: a missing dict entry raises a `KeyError` from `[language]`
immediately; a missing example snippet raises `GenerationError` well before generation completes
(and is caught earlier still by the static marker test in section 6); a broken `native` Make command
in section 2, item 3 fails that generated repo's own `make verify`.

**A green `make verify` is not the whole obligation.** The factory's gate runs each generated project's
`make verify` and nothing else (`tests/test_matrix.py`), and that target is
`check-python lint typecheck check-imports check-migrations check-slice-scope check-extensions check-agents check-speckit check-codegraph check-ux-gates check-constitution check-benchmark check-decisions test`. Five of the eight
commands section 2 item 3 declares are therefore never run by this factory: `install`, `integration`,
`audit`, `adversarial` and `mutation`. Two of them (`audit`, `integration`) at least run in the generated
project's own `make ci`; **`adversarial` and `mutation` are reached by no gate at either level**, so a
command naming a tool version its framework does not support — or a tool that cannot run under that
framework's test harness at all — is committed green and stays green. A first run of this skill shipped
exactly that: a mutation-testing configuration whose plugin version had never been checked against the
chosen framework's supported range, which no gate could have caught. So before you are done, in one generated project of your backend
with every axis answered:

```sh
make mutation && make adversarial && make audit   # each one, at least once, really run
make test-integration                             # the axis adapters against real services
make demo                                         # then a host-side `make verify` in the same checkout
```

Anything you cannot run in this sandbox, say so explicitly rather than reporting the backend proved —
and if a search turned up a support constraint for a tool (a minimum version, an incompatible runner),
name the constraint and where you checked it.
