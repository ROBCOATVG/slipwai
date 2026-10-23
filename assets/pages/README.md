# {{title}}

This is an independently evolvable product monorepo scaffolded by `slipwai`. Which version scaffolded it, and which version last wrote a file here, are both recorded in `project.json`'s `generator` — the one place either number lives, so a replay cannot leave this page claiming the other. The factory's own `CHANGELOG.md`, read against that pair, says what later versions bring and what a repository already generated owes to catch up.

- Project: `{{project-name}}`
- Profile: `{{profile}}`
- Production target: `{{target}}`
- Services: {{services}}
- Frontend: `{{frontend}}`{{frontend-paths}}
- Backend capabilities: {{capabilities}}
- Frontend capabilities: {{frontend-capabilities}}
{{axes}}
<!-- section: before-init -->
## Before `./init`

`./init` installs Spec Kit for the agent you choose. It needs **Python 3**, and **`uv`** or network access
for `pip`. Nothing else has to be set up first.
<!-- end section -->
<!-- section: before-init-cloud -->
## Before `./init`

In this project `./init` does the first day's work: it installs Spec Kit, pushes this repository to your
forge, and runs `make bootstrap` against your {{cloud}} account — so the push is the first deploy. Have every row
below ready on the machine that runs it. It checks, and stops before pushing if something is missing, but
knowing first is quicker.

| | Have | Proof it is there |
|---|---|---|
| 1 | **Python 3**, and **`uv`** or network access for `pip` — Spec Kit is installed with one of them | `uv --version` |
{{prerequisites}}
| {{last-checked}} | **Access to your forge.** GitHub: `gh` signed in (`gh auth login`). Gitea: `GITEA_TOKEN` set to a token with `read:user` and `write:repository` — plus `write:organization` if the repository will belong to an organisation | `gh auth status` · `echo ${GITEA_TOKEN:+set}` |
| {{repository-row}} | **The repository's URL** — `https://github.com/<owner>/<name>`, `http://localhost:3300/<owner>/<name>` — created on the forge if it does not exist | — |
| {{passphrase-row}} | **Somewhere to keep a passphrase.** `make bootstrap` generates one, prints it once and, where the target can, keeps it in the account it bootstrapped so a later `make bootstrap` signed in there reads it back; the printed copy is for the day that account is gone | a password manager |

Whether rows 2–{{last-checked}} are on the machine is checked when the project is generated, too; who the CLI is signed
in as, `make bootstrap` checks before it applies anything. Missing a tool, `./init` still installs Spec Kit,
says which and leaves the push and bootstrap for later — `./init --repository <url>`, or push and
`make bootstrap`. `./init --skip-bootstrap` leaves them deliberately. Once the bootstrap has run, a later
`./init` — to answer an axis again, add an extension, or switch agent — sees its committed state and leaves
the account alone; re-applying the stack is `make bootstrap`, by hand.

`make bootstrap` also asks the one question that decides the bill: whether production is deployed on every
green push, or only when you say so. Answer `n` — or `./init --auto-promote false` — and the pipeline deploys
staging alone, production is never created, and `make promote` is what creates it when you want it. Either
way an environment costs money from the moment it exists;
[`docs/adr/0002-production-target.md`](docs/adr/0002-production-target.md) says how much.
<!-- end section -->

## Start here

```sh
./init{{start-here-production}}
```

`./init` installs Spec Kit for the selected agent; it is not vendored in this repository.{{init-production}} Then,
in the agent, type `/verify`. It runs `make verify`, the repository's local and CI quality gate, and reads the
result back. Add one small vertical slice at a time and keep the main branch releasable.

<!-- section: services-none -->
## Services

No service here was made by the keel. The applications this repository already had are recorded in
`project.json` as `"generated": false`, each with how its own build answers the Make targets; `apps/` is
where a service the keel adds would go. In the agent, `/add-service` runs the keel that installed this method:

```text
/add-service <name> --language python    the language is required: nothing here to inherit
```
<!-- end section -->
<!-- section: services -->
## Services

`apps/` holds one directory per service: {{services-described}}.{{browser-apps}} Each service has its own language,
framework and backing-service answers, recorded in `project.json`; every one owes the same eight Make
targets (`make help` lists them; every recipe runs for every service), answers a liveness and a readiness
probe on its own port,
and keeps the hexagonal layout `make check-imports` enforces. Which services exist is recorded once, in
`project.json`'s `deployables`; the Makefile, `docker-compose.yml`, the CI workflow,
`scripts/check-imports.py` and `scripts/backing-services.py` read that list, and none keeps a copy.

Add one in the agent, with `/add-service`. It runs the factory that generated this repository:

```text
/add-service <name>                      the first service's language and answers
/add-service <name> --language python    another language, its own answers
```

It scaffolds `apps/<name>` with the walking skeleton, adapters and tests a service of that language starts
with, on the next free port, registers it in `project.json`, and regenerates the files that list drives —
the skills' example snippets included, so a second language shows up beside the first at every example.
Say what the service is for while adding it — `--purpose "<what it owns>"` and `--context <bounded
context>`, repeated for each context it holds — because that is what the delivery loop reads when it decides
which service a slice belongs to; `describe-service <name>` takes the same flags for a service already there.
`docs/architecture.md` has the contexts as recorded, and says when a context should become a service.
`/add-frontend <name> [--api <service>]` does the same for a browser app, proxying `/api` to the service it
names. Code shared between services goes under `packages/`, and the hexagonal rule applies inside it too;
`docs/architecture.md` says what a shared package is in each language and what each service owes.
<!-- end section -->
<!-- section: run-it -->

## Run it

```sh
{{run-commands}}
```

`make demo` runs that same `make dev` inside a container over this checkout, so the two paths cannot
disagree about how this project starts, and there is no image to rebuild between an edit and a demo.
`skills/run-the-app/SKILL.md` is the full account: what it serves today, what has to be seeded first, and
how far to go before opening a browser.
<!-- end section -->
{{production}}
## Documentation

[`docs/workflow.md`](docs/workflow.md) diagrams the delivery loop each slice travels, from the constitution
through to the hardening passes. [`docs/getting-started.md`](docs/getting-started.md) walks the first slice
end to end{{documentation-production}}, and [`docs/README.md`](docs/README.md) indexes every page.
<!-- section: profile-boundary -->

## Profile boundary

This standard profile does not adopt Event Modeling or event sourcing. Native Spec Kit cannot
infer that boundary from constitution text you paste: keep the constitution architecture-neutral, or
generate the `event-modelling` profile when those capabilities are intentional. `make verify` rejects a
constitution that mandates event sourcing in this profile.
<!-- end section -->
<!-- section: event-workflow -->

## Event workflow

{{write-model}}

### One command runs the loop: `/sail`

```text
/sail          # start the loop, or resume the slice already in flight
/sail S2       # drive a named slice to its demo
```

`/sail` enters at the first incomplete stage proven by durable artifacts, and its ladder starts above the
slice loop: principles, product specification, the event model, the split, then example map, a `/gaps` pass
over it, the installed Spec Kit plan and tasks, implementation, the examples proven by tests, and — once a
capability is whole — convergence, its other gates and the actor-visible demo. Invoking it before the model exists is
a valid start rather than an error — it steps back to the stage that owes an artifact and says so. It never
reruns a completed stage merely to check. It pauses at the demo before hardening so feedback can return to the stage that owns it. Once the
demo is accepted, it runs the mutation pass — plus the adversarial pass when the slice changed attack
surface or closed the split — verifies and archives the slice, and starts the next ready slice without
another invocation. A real product question or unavailable external input is
the other stopping boundary.

`/cruise` runs the same ladder with nobody at the wheel — deciding as the owner, demoing as the actor, recording
both under `specs/` — until the specification is satisfied. It ships switched off: `/cruise-settings enabled=true`,
then `/cruise` in any session starts the runner and watches it; `/cruise-tell` steers it, `/cruise-stop` stops it.

### The browsable model

The event-model workflow renders `docs/event-model/model.yaml` into a zoomable timeline with per-slice
views and embedded wireframe mockups, and publishes it on every push to `main` that touches the model.
Your forge's pages host serves it from the `pages` branch at:

{{model-page}}

On GitHub the same workflow deploys through GitHub Pages instead; when that URL differs, update
`render.page` in `model.yaml` and the link below. Regenerate locally with `make model` (needs Node).

<!-- event-model:start -->
_Run `make model` after the first modelling session to generate this section._
<!-- event-model:end -->
<!-- end section -->
