---
name: add-framework
description: Factory-maintenance skill for adding a second application framework to a language slipwai already has — Spring Boot or Quarkus beside plain Java, Nest beside Fastify's TypeScript, Django beside FastAPI's Python. The bare language name is reserved for a backend nothing owns the startup of, so a sibling beside an already-suffixed backend is purely additive while one beside `typescript`/`python`/`go` also renames it, and this covers both: catalog.json, the assets split, which per-backend tables become family lookups, the pruner, tests and docs. Use when asked to add, restore or scaffold a framework for a backend language this factory already supports.
---

# Add a second framework to a language family

A **backend** in this factory is a language plus, where the ecosystem has one, the framework that owns
startup — flattened into one catalog key because the two do not combine independently. A **family** is the
language itself. The key is the bare language name **exactly when nothing owns startup** (`go`, `python`,
`typescript`); a backend that has a framework is suffixed with it (`java-spring`) from the day it is added,
because `assets/languages/<family>/` holds the material a family shares and a framework-built backend is
not that shared material.

**So how much of this document you need depends on how the existing backend is named**, and that is the
first thing to check:

- **The existing backend is already suffixed** (`java-spring`, because `add-language` asked which framework
  owned startup when Java was added). Then adding Quarkus beside it is **purely additive**: a new key, new
  assets, new rows. Skip every "rename" instruction below — sections 3 and 4 still apply to the *new*
  backend, and section 2's rename list is empty. This is the cheap path, and it is the one a
  correctly-added framework-first language leaves you on.
- **The existing backend carries the bare language name** (`typescript`, `python`, `go` — a family where
  nothing owned startup and now something does). Then it must be renamed as well, because a member with a
  framework may not keep the family's name. That migration is the bulk of this document, and
  `validate_backends` in `catalog.py` enforces it from both sides, so it is mechanical rather than
  optional.

Adding a whole new language is `.claude/skills/add-language/` — and note that its section 0 now probes for
this, so a new Java or C# backend arrives already suffixed and never needs the rename path at all. Adding a
tool a project *calls* is `.claude/skills/add-backing-service/`.

## 0. Confirm it is this job, and that the family is worth splitting

### Before the questions below: search, do not copy the examples from here

Spring Boot, Quarkus, Nest, Django, Ktor and Micronaut appear throughout this document to **illustrate the
rule**, never as the menu to offer the user. Claims about the *ecosystem* — what owns startup, what a team
would reach for, which version is current, whether a project is still maintained — have one source of
truth, and it is a `WebSearch` run now. Claims about *this factory* — which tables are keyed by backend,
what `validate_backends` refuses, where the assets split — have another, and it is the code, read now.

So search first, filter the results through the test below, and only then `AskUserQuestion`. A stale name
copied out of a skill does not read as stale to whoever is answering: it reads as the recommendation, and
it gets pinned into every project generated from that backend afterwards. `.claude/skills/add-language/`
section 0 states this at length, including the version pins that carry the same shelf life — and its
table of **which decisions are ecosystem claims at all**, which is the longer list: not just the version
of a tool but the choice of tool, for the formatter, the test runner, the mutation tester, the audit, the
migration mechanism, the datasource, the health probe and the OIDC client. Read that table before section
4 of this document, not after.

One of those answers lands somewhere the table does not name: a framework that ships its own readiness
probe usually answers in its own shape and on its own path, and both are rows in `probes.py` rather than
something a sibling can configure away — the shape in `HEALTH_BODIES`, read through `health_body`, and the
path in the per-language table `READY_PATHS`, read through `ready_path`, which is keyed by backend and is
what every waiter asks for. `HEALTH_PATH` beside them stays one constant for every backend, because a
liveness path *is* configurable. Check all three before assuming the probe is free.

**Every row of that table is confirmed with the user, not merely searched** — the requirement is stated in
full beside it, and it applies here for a sharper reason. Section 4 below asks "does this framework change
this answer?" of each table, and a *yes* is a new tool choice for the sibling: its own test harness, its
own dev command, possibly its own mutation plugin and its own migration mechanism. Those are decisions the
user is entitled to make even though the language was settled long ago, and a sibling is exactly where
they are easiest to make silently, because the family already has a house answer to copy.

The search matters more here than it looks, because this skill's whole premise is that a *second*
framework is worth having. Two things it can tell you that this document cannot: whether the sibling being
asked for is still the live alternative or has been overtaken since, and whether the two frameworks are
really siblings rather than one of them running inside the other's host — which would make it an `http`
option and this the wrong skill entirely.

### Do you call it, or does it call you?

The same three words ("add Spring", "add Axum", "add Java") name three different jobs, and one question
separates them:

- **You call it** — you still own `main()` and hand it a request (`net/http`, `chi`, Fastify, Express,
  FastAPI). That is an **option on the `http` axis**: use `.claude/skills/add-backing-service/`, and stop
  reading this one. This is the common misroute, because an `http` option is also "a framework".
- **It calls you** — it owns startup, dependency injection, configuration, transactions and the test
  harness (Spring Boot, Quarkus, Nest, Django). That is **this** skill, if the language is already in the
  catalog, or `add-language`'s "new family" path if it is not.

The tiebreaker for the awkward cases (Ktor, Micronaut's functional mode) is whether you would still
hand-write the composition root `skills/hexagonal-architecture/` teaches. If yes, it is an `http` option.

### Then: does the existing backend keep its axis coverage?

The existing member is being renamed at most, never rewritten, so it keeps whatever axes it already
answered — and the new sibling starts at zero. Ask the user which axes the *new* backend should answer,
exactly as `add-language` section 0 does, and for the same reason: a backend with no `http` option gets no
`make dev`, no `docker-compose.yml` and no `make demo`, so it can be verified and never demonstrated.
Record the answer in `docs/axes.md`'s coverage table (section 8) — it gains a row per backend, not per
family, and `tests/test_catalog.py::test_the_documented_axis_coverage_is_the_catalog_s` fails if the table
and the catalog disagree.

**If a rename is involved, say it out loud before starting.** Where the existing backend carries the bare
language name, "add Spring Boot" and "rename our TypeScript backend and add Nest beside it" are the same
job, and the user should hear the second one — because every project already scaffolded with
`--language typescript` was scaffolded with a backend key that will no longer exist. Where the existing
backend is already suffixed there is nothing to say: no key changes and nothing already generated is
affected.

### And: what does the new framework already provide?

A sibling framework is a different answer to "what owns startup", so it is also a different answer to
**what each axis adapter is made of**. This is the step that is easiest to skip here, because the family
already has a working backend and its adapters are right there to copy — and copying them is usually
wrong. The existing member's adapters were written against *its* framework's integrations (or against
none, if the family is framework-free), and an adapter that hand-rolls what the new framework ships is a
defect this factory has shipped before: a hand-written datasource, migration runner and health resource
beside a framework with a first-party extension for each.

`.claude/skills/add-language/` section 0's "what does the framework already provide?" step applies here
in full — the same per-axis search, the same list of what stays hand-written (the port, the domain, the
in-memory adapter, the contract suite), the same two traps (framework-managed dev containers starting
inside a gate that must run without Docker; an integration whose default path or response shape does not
match the cross-backend contract in `compose.py`, `makefile.py` and `run_skill.py`). Do not restate the
existing member's dependency list as the new one's.

The family's *shared* material is the other half of this. Anything under `assets/languages/<family>/`
belongs to the language, not to either framework — so an example snippet or a domain type that names one
framework's extension is in the wrong tree, and section 3's split is where that gets decided.

## 1. What the factory already does for you

[`docs/backend-obligations.md`](../../../docs/backend-obligations.md) is the checklist both maintenance
skills work from: every axis, every Make target, every per-backend table, and the ecosystem choices that
must come from a search rather than from a sibling backend's answer. A new framework is a new backend, so
it owes the whole of it — and `tests/test_backend_obligations.py` fails until it does.

This mechanism was built before anything depended on it, so a large part of the job is already done and
should not be rebuilt. Read these before writing anything:

- `resolve_backend` in `catalog.py` turns a language plus a framework into the one backend key everything
  downstream is keyed by, defaults the framework from `default.framework` when nobody gives one, and — for
  a single-member family — accepts the framework that member actually has while refusing every other,
  naming the one it has.
- `prompt_framework` in `cli_prompts.py` asks the framework **only** where a family has more than one member — the
  same "something with one answer is not a choice" rule the axes follow. The CLI needs no change: it
  already offers `--language` with `--framework`, and `--backend` for the key directly, and refuses the two
  spellings mixed.
- `snippet` in `examples.py` looks a snippet up under the **backend** first and its **family**
  second. So `assets/languages/<family>/examples/` stays where it is and stays shared; the new sibling
  overrides only the snippets its framework actually changes. Without that fallback a second framework
  would mean a second copy of every snippet, and the two would drift. In a project that has both
  frameworks, `resolve_examples_for` shows a shared snippet once under both labels
  (`**Java (Spring Boot) — \`apps/service\`, Java (Quarkus) — \`apps/billing\`**`) and an overridden
  one as two blocks; `toolkit.speakers_of` adds the framework to the label only when a project has two
  frameworks of one language.
- `stamp_pseudocode_notes` is passed the list of families, so the disclaimer reads "Java-as-pseudocode"
  rather than "Java-Spring-as-pseudocode".
- `project.json` already records all three — `backend`, `language` (the family) and `framework` — so
  anything downstream that needs to tell the siblings apart has the data without a format change. See
  `metadata` in `project/readme.py`.
- `tests/test_backend_naming.py::test_a_language_with_two_frameworks_becomes_two_backends`,
  `tests/test_backend_naming.py::test_a_backend_is_named_for_its_language_only_when_nothing_owns_its_startup` and
  `tests/test_backend_naming.py::test_a_lone_framework_backend_is_reachable_and_refuses_the_others_honestly`
  already prove the rules against a synthetic catalog. **They say so in their own docstrings** — "the real
  one has no such family yet". Your migration is what turns that synthetic coverage into real coverage, so
  when it is done, delete the "synthetic because" caveat from those docstrings rather than leaving a
  comment that has stopped being true.

## 2. catalog.json — the rename and the sibling

Both members get suffixed and both must declare a distinct `framework`:

```json
"backends": {
  "java-quarkus": { "family": "java", "framework": "quarkus", "label": "Java — Quarkus owns startup, ..." },
  "java-spring":  { "family": "java", "framework": "spring-boot", "label": "Java — Spring Boot owns ..." }
},
"default": { "framework": { "java": "quarkus" } }
```

`family` stays the bare language for both — it is what `snippet`/`resolve_examples_for` and the pseudocode
disclaimer read. `framework` is the token `--framework` takes and the prompt shows; `label` is the line beside it.

`validate_backends` will refuse, with the reason, if you get any of this half-done: a sibling still named
`java`, a member without its own distinct `framework`, or a `default.framework` naming something no member
offers. It also refuses a `default.framework` entry for a family that has only one member, which matters
in the other direction — **if you ever remove a framework and leave one member, drop its
`default.framework` entry.** The survivor keeps its suffixed key: it still has a framework, and the bare
language name is reserved for a backend that has none.

Then rename the old key everywhere else in the file:

- every axis option's `backends` array that named the old key — and add the new sibling to each option you
  actually wrote assets for, and to no others;
- `default.http`, which is a map keyed by backend;
- `default.backend`, if the renamed backend was the catalog's default.

`event-store` recommends one string for every backend, so it needs no edit unless the sibling cannot be
given `postgres` — then the string has to become a map, and `validate_axes` says so and names the options
each backend actually has.

## 3. assets/languages/ — split the tree

Today `assets/languages/<language>/` is both "the family's shared material" and "this backend's skeleton",
because there is only one backend. Splitting it is the part with no code to guide you, so decide it
explicitly, file by file:

```text
assets/languages/java/                  the FAMILY — what both frameworks share
├── examples/                           marker snippets (see below)
└── event-port/                         the adapter-free port, if the family still has one

assets/languages/java-quarkus/          the BACKEND — what this framework decides
├── app/                                the walking skeleton, at paths relative to a service's directory
├── repository/                         what this ecosystem puts above the services
└── locks/                              committed dependency locks, if the ecosystem has them
```

- **`examples/` stays at the family.** That is what `resolve_examples`'s fallback is for. Move a snippet
  down to a backend only where the framework genuinely changes the answer — a composition root, a driven
  adapter's wiring, a test harness. A Decider, a value object, a projection are the same Java either way,
  and a second copy is a second thing to keep in step.
  `tests/test_toolkit.py::test_every_example_marker_resolves_for_every_catalog_language` checks both
  lookups, so a backend covered entirely by its family's snippets passes.
- **`app/`, `repository/` and `locks/` go to the backend.** The language module names these directories as
  string literals (see `LANGUAGE_ROOT / "go/app"` in `go.py`), so this is a path edit in the module, not a
  configuration change.
- **`event-port/` is a judgement.** It is emitted only for a backend whose event-store axis offers nothing
  yet, and it is a port with no adapter behind it — the same shape in both frameworks. Keep it at the
  family unless a framework's DI actually changes the port's declaration.

`tests/test_language_skeletons.py::test_each_language_reads_its_skeleton_rather_than_listing_it` and
`tests/test_language_skeletons.py::test_every_skeleton_asset_reaches_the_generated_project_unchanged` pin
that the tree is read rather than enumerated, so moving files needs no list updated anywhere.

## 4. Per-backend tables: one question per table

Every table below is indexed with the **backend** key, so after the rename each one raises `KeyError` for
both members until you deal with it. There are exactly two ways to deal with one, and the choice is per
table rather than global:

> **Does this framework change this answer?**
> **Yes** → give each backend its own entry.
> **No** → look the table up by `family_of(language)` and keep one entry for the family.

Duplicating a family-wide answer under two backend keys is the failure mode to avoid: it works on the day
you write it and it is two places to fix afterwards. `tests/test_maintenance_skills.py::test_every_language_keyed_table_is_documented`
holds this list to the code, so a table added later cannot quietly miss it.

Where the answer is **yes** and the new entry names a *tool* rather than a spelling — a test runner, a
mutation plugin, a migration mechanism, a formatter — run `WebSearch` for what that framework's own
ecosystem uses now, then put the result to the user with `AskUserQuestion`, exactly as section 0 requires.
A `yes` here is a fresh ecosystem choice being made under cover of a table edit, and it is pinned into
every project generated from the sibling. Neither half is optional: the search is what makes the options
current, and the question is what makes them the user's.

| Table or function | Module | A framework changes it? |
|---|---|---|
| `BACKEND_TOOLING` | `backends.py` | **Yes** — `install`, `migrate`, `integration`, `ci_install`; `ci_image` usually not |
| `dev_command` | `backends.py` | **Yes** — `quarkus:dev` is not `spring-boot:run` |
| `COMPOSE_CACHES` | `backends.py` | Usually **no** — one dependency cache per ecosystem |
| `IMAGE_BUILDERS` | `images.py` | **Yes** — the framework's own image build is the answer (Quarkus's Jib extension, Spring's `build-image`), and the `tool` the workflow installs |
| `MIGRATIONS_IN_PRODUCTION` | `images.py` | **Yes** where the framework migrates at start-up (an `environment` switch); the sibling's `command` where it does not |
| `BACKEND_EXECUTABLES` | `backends.py` | Usually **no** — a build wrapper belongs to the build tool, and a sibling framework normally shares it; **yes** if the sibling builds with a different one (Gradle beside Maven brings `gradlew`, not `mvnw`) |
| `event_store_directory` | `backends.py` | Usually **no** — a source layout, not a framework's |
| `native` | `project/native_commands.py` | **Yes** — the whole generated gate |
| `native` (permission globs) | `project/agent_settings.py` | **Yes** where the build or test command differs |
| `toolchain_setup` | `project/ci_workflows.py` | **No** — keyed by family; one `actions/setup-*` per ecosystem |
| `gate` | `project/docs.py` | **Yes** where the test runner differs |
| `paths` | `project/event_model.py` | Usually **no** — illustrative source paths |
| `tools` | `project/mutation.py` | Usually **no** — one mutation tester per ecosystem |
| `language_artifacts` | `project/gitignore.py` | Usually **no** — one build output per build tool |
| `BACKENDS` dispatch | `project/languages/__init__.py` | **Yes, always** — one module per backend (section 5) |
| the layout table in `backing_service_service_files` | `project/backing_services.py` | **Yes** — adapters are framework-shaped |
| `FLAG_READERS` | `project/flags.py` | **Yes, always** — one row per backend key; usually pointing at the *same* `assets/languages/<family>/flags/` tree, because a flag reader names no framework type. Both Java backends do exactly that. Give it a tree of its own only if the framework changes how a variable is read at all |

`app_services` in `project/compose.py` has no table of its own — it reads `BACKEND_TOOLING` and
`COMPOSE_CACHES`, so it follows whatever you decided for those two. So does `app_tooling` in `tooling.py`,
which is how the Makefile and the CI workflow read `BACKEND_TOOLING` per service.

Two more sites are not in the table because they are not keyed by backend *yet*, and one of them may
have to become so:

- `executable_paths` in `toolkit.py` takes only the profile, so an executable script that must stay
  executable is already awkward — `add-language` section 2 item 10 describes threading a language
  through it. If exactly one of your two frameworks ships one, that thread has to carry the backend
  rather than the family, or the sibling without it gets a `chmod +x` on a file it does not have. Note
  what such a script cannot be: `assets/` is text-only, so a build wrapper needing a `.jar` is not
  available to either sibling — both take the build tool from the PATH and the CI image.
- `resolve_backend` in `catalog.py` and `prompt_framework` in `cli_prompts.py` both index by `[language]`, and
  both are already correct: they index the *families* map, which is what a language names. They are the
  model to copy, not sites to change.

### The trap: a family question asked of a backend key

`language != "typescript"` reads correctly today, because a backend is named for its language right up
until a sibling arrives. After the rename it silently means the wrong thing, and the failure is quiet — a
generated project installs and audits the same npm workspace twice, or loses the Go mutation note, with
every test still green. So a comparison against a *family* name must go through `family_of`, and
`tests/test_factory_repository.py::test_a_family_question_is_never_asked_of_a_backend_key` fails the build
if a new call site is written the other way. Add nothing to that list; it finds them itself.

## 5. The language module and the dispatch

`cli.py` needs nothing per framework. `generate_main` (and `cli_add.py`'s `resolve_requested_backend`) turn
`--language`/`--framework` into the backend key through the catalog — `prompt_framework` asks the framework
only where a family offers more than one — and the one place `generate_main` indexes `CATALOG["backends"]`
by that key is the refusal for a backend the chosen target does not offer, which reads the new entry's
`targets` list like any other. The `add-language` skill says the same of a new language.

`src/slipwai/project/languages/` holds one module per **backend**, so the family gets two. Name
each for its backend key with the hyphen replaced — `<family>_<framework>.py` — and register both in
`BACKENDS`. Each owns the same two functions `add-language` section 3 describes — `service_files` and
`repository_files` — and each reads its own `assets/languages/<backend>/` tree.

What the two share is real but small: a manifest fragment, a package-name derivation, a source-root path.
Put it in whichever place the import direction allows and both can read — a helper in one sibling that the
other imports is a cycle waiting to happen, and `scripts/check-structure.py` enforces the direction as
well as the 350-line budget and the module docstring. If the shared part is content rather than logic,
it belongs under `assets/languages/<family>/` and neither module needs to know about the other.

Both modules must still end `service_files` with
`files.update(backing_service_service_files(selection, "<backend>"))`, and both need an entry in that
function's layout table — `{}` for a backend answering no axis yet, which is legitimate and stated rather
than silent.

## 6. The pruner

`assets/backing-services/prune.py` is the one place keyed by **family** rather than by backend:
`project_language` reads `project.json`'s `language`, so `LANGUAGES`, `OWNED_FILES`, `PACKAGE_EDITS` and
`MARKED_FILES_BY_LANGUAGE` are all family-keyed. `validate_catalog` asserts `LANGUAGES` against the
catalog's families, so a promotion inside an existing family needs **no change here at all** — the family
name is unchanged.

That is true only while the two frameworks agree about what they name and where they put it, and one of
those tables is likely to break the agreement: `PACKAGE_EDITS` names dependencies, and Quarkus and Spring
do not name the same Postgres dependency. When they disagree, rekey **only the tables that differ** to
`project.json`'s `backend` — the factory already writes it beside `language`, and `project_language` has a
sibling to model the reader on. Rekeying all of them because one of them needed it puts the family's
shared answers in two places again.

`tests/test_pruning.py::test_the_pruner_is_one_implementation_shared_with_the_generated_project` proves
the factory and the generated project run the same prune, so a change here has to satisfy both callers.

## 7. Scripts that name a backend as a literal

Two scripts pass a backend key positionally, and both were written when a backend key was always a bare
language name:

- `scripts/regenerate-starters.py` iterates `CATALOG["backends"]` and must pass each as `--backend`, not
  as `--language`. `--language` is declared with `choices=list(families())`, so a suffixed key never
  reaches `resolve_backend` at all — argparse refuses it with `invalid choice: 'java-quarkus'`, which
  reads like a typo rather than like the wrong flag.
- `scripts/regenerate-locks.py` hardcodes asset paths (`assets/languages/typescript/app`,
  `assets/languages/go/modules`) and passes a backend key straight into `write_project`, whose fourth
  positional argument is a backend and not a family. Both follow whatever section 3 decided about the
  asset split.

`scripts/smoke-executable.py` also names languages as literals, and needs no change: it passes them to
`--language`, which takes a family, and asserts against `project.json`'s `language`, which is one. Leave
it alone rather than rekeying it for symmetry.

## 8. Tests and documentation

- `tests/test_monorepos.py::test_scaffolds_complete_matrix_as_independent_monorepos` computes its count from
  the catalog, so the matrix grows by itself — but add a root-file assertion for the new sibling next to
  the existing per-language ones.
- `.github/workflows/verify.yml` — the `matrix.backend` list gets the new key (and keeps the renamed one);
  the factory's CI runs the matrix suite as one job per backend, and
  `tests/test_factory_repository.py::test_the_ci_matrix_names_every_backend_the_catalog_has` fails until the
  list is the catalog's. No toolchain step to add: the family's `setup-*` step in
  `.github/actions/toolchains/action.yml` already serves both siblings.
- `tests/test_catalog.py` asserts the per-axis option lists per backend and the default block by hand;
  both name the old key.
- The three synthetic-catalog tests in `tests/test_catalog.py` named in section 1 can now assert against
  the real catalog. Prefer moving them over rather than leaving both.
- `README.md` — the pitch line's backend list.
- `docs/axes.md` — the coverage table (a row per backend), the `--http` row's per-backend answers, and the
  "Backend language and browser frontend are independent choices" paragraph.
- `docs/generating.md` — the interactive example now shows a second question. `Language` lists families;
  the new `Application framework` prompt lists this family's members. Add one `--language X --framework Y`
  CLI example and note that `--backend` names the key directly.
- `docs/requirements.md` — a row per backend for the toolchain each one needs.
- `docs/maintaining.md` — the foundation count in "Browse the starters" is
  `len(CATALOG["profiles"]) * len(CATALOG["backends"])`, which the promotion increases; and the
  `project/languages/` line in the source-layout tree names each backend module.

## 9. Prove the surviving backend did not change

The renamed backend must generate exactly what it generated before, or the rename was a rewrite. That is
checkable, and this factory's rule is to check it rather than to assert it: snapshot the whole matrix
before you start and again at the end, and diff.

```sh
# Before any edit, and again afterwards: every variant, every file, hashed.
for profile in standard event-modelling; do
  for backend in $(python3 -c 'import json;print(" ".join(json.load(open("catalog.json"))["backends"]))'); do
    for frontend in none react-vite; do
      ./slipwai generate snap --profile "$profile" --backend "$backend" --frontend "$frontend" --output "$OUT"
    done
  done
done
```

Hash every generated file (excluding `.git`), keep the backend's own key out of the compared paths, and the
diff for the surviving backend must be empty. A non-empty one is the list of things to explain before
finishing — each entry is either a deliberate consequence of the split or a mistake, and there is no third
option.

Cover both frontends and each axis answer: several of the sites in section 4 only differ when a frontend
is present, so a `--frontend none` snapshot alone would show an empty diff for a change that broke
`react-vite`.

## 10. Verify

```sh
make verify
```

This validates the catalog, scaffolds every `profile x backend x frontend` combination plus the
backing-service variants, and runs each one's native gate. A gap above surfaces at a predictable point: a
table you neither split nor made a family lookup raises `KeyError` from `[language]`; a missing example
snippet is caught statically before any generation; a `native` entry that does not work fails that
generated repo's own `make verify`. Also run `make starters` — it is the one caller that iterates every
backend key, and section 7 is the reason it would otherwise fail.
