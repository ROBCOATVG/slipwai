"""The rules `AGENTS.md` puts whoever works in the project under, per answer — the prose beside `guidance.py`.

Split from `guidance.py` for the reason `native_commands.py` is split from `makefile.py`: these tables are
most of that module's bytes and none of its assembly, and it had reached the line budget. Each is keyed by
the feature that answered an axis and looked up by `guidance.agent_guidance`, so exactly one rule is emitted
per answer and nothing is tested for by product name. Where a table needs more than a lookup to become a
sentence — the contracts below are a list a project may have several of — the reading of it is here beside
it rather than back in the module whose budget this file exists to keep.
"""
from __future__ import annotations

from ..services import App, services_of, web_apps

# Where each transport publishes its service's API contract, keyed by the feature that answered the `http`
# axis; `__APP__` is the service's own directory. A transport absent from here publishes nothing this
# factory ships — Quarkus and Spring do not — so the sentence that names these simply stops after
# "contracts": a rule pointing at a path the project does not have teaches the reader to ignore the file.
API_CONTRACTS = {
    "fastify": "`GET /openapi.json`",
    "fastapi": "`GET /openapi.json` (and `/docs` for a person)",
    "net-http": "`__APP__/openapi.yaml`",
}


def api_contracts(apps: list[App]) -> str:
    """Where this project's services publish their contracts, as the sentence promising one says it."""
    published = dict.fromkeys(
        API_CONTRACTS[transport].replace("__APP__", service.path)
        for service in services_of(apps)
        for transport in (service.selection.feature_of("http"),)
        if transport in API_CONTRACTS
    )
    if not published:
        return ""
    # Broken before the path rather than after it, so the sentence wraps the same way whatever the
    # project is called and however many services it has.
    return f",\n  which this project publishes at {', '.join(published)}"


def frontend_contract(apps: list[App]) -> str:
    """The rule a project with a browser app is under: what the frontend reads, and where it is."""
    web = web_apps(apps)
    if any(service.selection.feature_of("http") in API_CONTRACTS for service in services_of(apps)):
        client = (
            "\n  `packages/api-client` is that contract as types — generated from the committed document by"
            "\n  `make build-packages`, never edited — so the browser app calls the API through it rather than"
            "\n  writing paths and shapes out a second time. `make openapi` rewrites the document from the"
            "\n  routes and `make check-openapi` fails when the committed one has fallen behind them."
        )
    else:
        # Said out loud, because the absence reads as an omission otherwise: there is no `packages/api-client`
        # here, and a reader who finds none would reasonably conclude the frontend was left half-wired.
        client = (
            "\n  This project's transport publishes none, so there is no `packages/api-client` and the one"
            "\n  route fetches by hand with a `Record<string, unknown>` response — what a shape nobody"
            "\n  declared honestly is. Publishing a document is what buys the typed client; `docs/design.md`"
            "\n  says what changes here when it does."
        )
    return f"""- The frontend consumes published API/query contracts{api_contracts(apps)}.{client}
  Frontend state is ordinary UI, server, and URL state; it is not reconstructed from backend
  persistence history.
- Read `docs/design.md` before writing anything with a browser surface. It says what this project's
  screens are made of — the design tokens in `{web[0].path}/src/styles/`, the layout shell, the element styles
  the slice inherits for free — and it is where a decision about how this project looks is recorded.
"""


# The rule each store puts whoever works here under: what it proves, and what a claim asserted against it
# is not evidence of.
EVENT_STORE_GUIDANCE = {
    "sqlite": """<!-- backing-service:sqlite:begin -->
- The SQLite adapter carries its own schema, so there is nothing to migrate and nothing to start. It cannot
  prove concurrent behaviour — SQLite serialises writers — so do not write a test that claims to race on
  it. Durability and the append-only rule are provable there, and are proved.
<!-- backing-service:sqlite:end -->
""",
    "postgres": """<!-- backing-service:postgres:begin -->
- The Postgres adapter is where the never-write-the-same-version-twice guarantee is proved: its
  `(stream_id, version)` unique constraint is the concurrency control, and the integration suite races two
  appends at one version. A concurrency claim asserted anywhere else is not evidence.
<!-- backing-service:postgres:end -->
""",
}

# The rule each identity provider puts whoever works here under, keyed by the feature that answered `auth`.
IDENTITY_GUIDANCE = {
    "keycloak": """<!-- backing-service:keycloak:begin -->
- The OIDC flow in the auth adapter is a placeholder. Load `skills/secure-oauth-oidc/SKILL.md` before
  implementing it and use a maintained client library; never hand-roll token validation. Authorisation
  decisions belong in use cases, not in the adapter.
<!-- backing-service:keycloak:end -->
""",
}

# The same, for whoever authenticates the product's users — keyed by the feature that answered `users`. A
# second table rather than a row in the one above because the two questions are answered separately and a
# project may have either realm without the other.
USERS_GUIDANCE = {
    "users-keycloak": """<!-- backing-service:users-keycloak:begin -->
- Customers sign in from the browser app, which owns the login: `apps/web/src/auth/` uses react-oidc-context
  over oidc-client-ts for the authorization-code flow with PKCE, the session and silent renewal. Do not add a
  second login path in a service, and never hand-roll any of that — load `skills/secure-oauth-oidc/SKILL.md`
  before touching it.
- A service accepts a customer only from the customers realm. The users adapter refuses any other issuer,
  because the staff realm lives in the same Keycloak and a staff token is a valid JWT that differs by one path
  segment; keep that check exact. A customer is `sub` plus a verified email — what an account may do is a
  use-case decision about ownership, not a role in an adapter.
<!-- backing-service:users-keycloak:end -->
""",
}

# The flag rule, for a project that has somewhere to deploy. The longest rule in this file, and the reason
# is that it is the only one standing between a merge and a customer: under a target every commit that
# passes `verify` on `main` is applied to production. `{readers}` and `{calls}` are filled in per project
# by `flags.py`, which also emits the reader they name.
FLAG_GUIDANCE = """- **A feature flag is what makes merging and releasing two decisions**, and here it is the only thing
  that does: every commit that passes `verify` on `main` is applied to staging and then to production, with
  nobody in between. Unfinished work therefore ships **dark**. A flag is declared in
  `infra/service/flags.auto.tfvars` under the service that reads it, seeded `off`, in the same change as
  the code that reads it; it reaches that service as `FLAG_<KEY>` — `checkout-v2` is `FLAG_CHECKOUT_V2` —
  and it is read through {readers}, asked by key ({calls}) and nowhere else. Never derive the variable
  name at the point of use and never read the environment for a flag anywhere else: a typo reads as
  absent, absent reads as off, and the feature simply never turns on. Read it where the behaviour branches
  — a use case or an adapter — never in the domain, which takes decided values as inputs the way it takes
  the clock. No service calls {cloud} for a flag.
- **A flag covers a releasable capability, not a slice.** A capability that is not coherent to an actor
  until three slices land wants one flag held off across all three, not three flags — three flags mean two
  states nobody designed, and the first one turned on shows a customer half a feature. One flag stretched
  over unrelated capabilities is the opposite failure: they can then only be released together, and the
  key never gets deleted because something behind it is always unfinished. So **before implementing a
  slice, say which flag gates it and why** — the existing key of a capability this slice continues, or a
  new key because this slice opens one. Recommend the answer with its reason rather than asking an open
  question; ask the user only where it is genuinely undecidable which capability the slice completes,
  which is a product question and never a default. Never add a second flag for a capability that has one.
- **Both paths are tested, and the off path is the one that ships.** While the flag is off, the branch
  running in production is the branch the slice's own tests miss unless they were written — and inserting
  the branch changed that path too, so "it worked before" is not evidence. The reader takes the
  environment as an argument for exactly this reason — which is also why the reader is the only place that
  touches the environment: a bare `FLAG_<KEY>` read at the point of use cannot be driven down both paths,
  so bypassing the reader quietly makes this rule unsatisfiable. `make check-flags` runs inside
  `make verify` and refuses a key declared and never read, a key read and declared nowhere, a new key
  seeded anything but `off`, a key whose tests only ever drive one path, and a read that names the variable
  instead of calling the reader.
- **Before pushing, say what holds the change back from the actor** — the flag key, and that it is `off`.
  If nothing does, because there is no flag or because the flag is already on, **stop and ask the user to
  confirm this is a release they want now**; do not push first and mention it after, and do not decide on
  their behalf that a change is small enough to be safe. There is no later gate at which somebody would
  catch it. A change with no actor-visible behaviour is not a release and needs no flag — say that it is
  one rather than saying nothing.
- `make flag ENV=… KEY=… VALUE=on` writes the value, restarts the service and smokes the environment, so a
  flip costs a rolling restart and no build, no apply and no merge; `make flags ENV=…` prints what an
  environment is set to now, with who set it and when, which is the only place that answer lives — the
  file only seeds a *new* environment, and a flip is not in the release record. A rollback does not turn a
  flag off: `docs/deployment.md` says which undo button is which.
"""

# The other half of that rule, for a project whose flags also have to reach a browser. Two things an author
# cannot work out from the service half: the spelling, and that this side is a build rather than a switch.
BROWSER_FLAG_GUIDANCE = """- The same flag reaches `{web}` as `VITE_FLAG_<KEY>`, and `{web}/src/flags.ts` is the only place that
  transform is written on this side: ask with `flagEnabled('checkout-v2')`, never by reading
  `import.meta.env` at the point of use. Vite inlines the value while the bundle is *built*, so a browser
  flag is a property of the bundle: `scripts/deploy.py` builds it with what this environment's parameters
  are set to at deploy time, and a flag flipped afterwards reaches the browser only on the next `make
  deploy ENV=…` of that environment. `make flag` says so when it flips one this app reads. A flag declared
  under a service other than the one `{web}`'s `/api` goes to does not reach the bundle at all.
- That asymmetry has a window in it, and a direction. On in the service, off in the bundle: the feature is
  invisible and nothing is at risk. Off in the service, on in the bundle: an inviting UI whose every call
  is refused. So turn a feature **on** in the service first and reveal it with the next deploy, and turn it
  **off** in the bundle first — by deploying — before the service stops honouring it. Either way the
  service is the authority: gate the surface on the flag *and* handle the endpoint refusing, because for
  the couple of minutes a restart takes it will. Locally both halves come from `.env`, `FLAG_<KEY>` and
  `VITE_FLAG_<KEY>` set to the same value unless you are deliberately reproducing that window.
"""

# The cloud a service is told never to call for a flag, per target. The rule is the same everywhere — the
# platform resolves `FLAG_<KEY>` into the environment so no image gains a cloud SDK — but naming the cloud
# is what makes it land: "no service calls AWS" is a sentence an author checks themselves against.
CLOUD = {"aws": "AWS", "azure": "Azure"}

# What a destination puts whoever works here under: the pipeline is the only path to production. Per target,
# because every noun in it is that cloud's — the workflow's steps, what a rollback re-applies, what `infra/`
# is written in — and a second cloud is a row here rather than a conditional inside the prose.
PRODUCTION_GUIDANCE = {
    "aws": """- This project deploys to AWS from `.github/workflows/deploy.yml`, and a pipeline is the only path to
  production: never `tofu apply` production by hand, and never build an image on a laptop for it — a deploy
  is the commit's own image, pushed by digest, promoted unchanged from staging. Whether that pipeline takes
  every green commit all the way is the `AUTO_PROMOTE` variable on the forge; where it reads `false` it stops
  at staging and `.github/workflows/production.yml` is what deploys production, started by `make promote` or
  from the Actions tab. `make promote` asks the forge to run it and applies nothing itself, so it is not an
  exception to the rule above — check `make -s url ENV=production` before assuming production exists at all,
  since without auto-promotion it does not until the first promotion. `make build smoke-image
  PLATFORM=linux/arm64` proves an image locally; a bad release is undone by starting
  `.github/workflows/rollback.yml` by hand with the environment to roll back; `make deploy` and `make
  rollback` are for a person with credentials, from a checkout of `main`. `infra/` is OpenTofu; edit it as code, `tofu fmt` and `tofu
  validate` before committing, and record a changed decision in `docs/adr/0002-production-target.md`. A
  renamed or moved resource gets a `moved` block and one dropped from the code a `removed` block, so the
  apply updates or forgets it rather than destroying it (`infra/README.md`). IAM the service stack declares
  beyond this project's roles is a grant in `infra/bootstrap/main.tf` and a `make bootstrap` by a person
  before it merges — `make check-deploy-role` says which.
  Never put a credential in this repository: the pipeline authenticates with OIDC and carries identifiers.
""",
    "azure": """- This project deploys to Azure from `.github/workflows/deploy.yml`, and a pipeline is the only path to
  production: never `tofu apply` production by hand, and never build an image on a laptop for it — a deploy
  is the commit's own image, pushed by digest, promoted unchanged from staging. Whether that pipeline takes
  every green commit all the way is the `AUTO_PROMOTE` variable on the forge; where it reads `false` it stops
  at staging and `.github/workflows/production.yml` is what deploys production, started by `make promote` or
  from the Actions tab. `make promote` asks the forge to run it and applies nothing itself, so it is not an
  exception to the rule above — check `make -s url ENV=production` before assuming production exists at all,
  since without auto-promotion it does not until the first promotion. `make build smoke-image
  PLATFORM=linux/arm64` proves an image locally; a bad release is undone by starting
  `.github/workflows/rollback.yml` by hand with the environment to roll back; `make deploy` and `make
  rollback` are for a person with credentials, from a checkout of `main`. `infra/` is OpenTofu; edit it as code, `tofu fmt` and `tofu
  validate` before committing, and record a changed decision in `docs/adr/0002-production-target.md`. A
  renamed or moved resource gets a `moved` block and one dropped from the code a `removed` block, so the
  apply updates or forgets it rather than destroying it (`infra/README.md`).
  Never put a credential in this repository: the pipeline authenticates with a federated identity and carries identifiers.
""",
}


# Where an agent is told how to answer a question about the code rather than about the product. Generated
# unconditionally and phrased conditionally, because an extension is chosen at `./init` — after this file is
# written — so the text has to be identical for every project and true whether or not one was adopted.
#
# It exists because the pointer an extension writes for itself could not do this job alone. `./init` can only
# *append* to `AGENTS.md`, so `codegraph`'s own block lands after the last generated section — a footnote
# below the closing line — and it was the single place in a generated project that mentioned the index at
# all. Meanwhile the two skills that ask for exactly the operation an index performs said nothing about how
# to perform it, and a specific instruction inside the skill being followed beats standing advice read once
# at the start. Naming those two here is the bridge, which is also why `tests/test_code_index.py` holds them
# to still saying what this claims they say.
CODE_INDEX = """
## Finding your way around this codebase

*Who calls this*, *where else is this symbol used*, and *what breaks if I change it* are answered by
following the call path, not by reading one file. Two skills in `skills/` ask for precisely that —
`debugging` says to search every caller before changing a shared function, and `refactoring` says to inspect
every caller and reachability path before removing a branch — and neither is satisfied by a text search,
which finds the spellings you thought to try and is silent about the rest.

If this file carries an extension block for a code index — `./init --extension codegraph` projects one,
naming `.codegraph/`, `codegraph_explore` over MCP, and the `codegraph` CLI — that index is what answers
those questions, and asking it is the first move rather than the fallback. Each session follows the
block's MCP, installed-CLI, then `npx` order for itself. A fresh delegate does not inherit the parent's MCP
connection, but where it has the CLI on `PATH` it can query the same project index.

A block is not a promise that the index is reachable or current. The database travels with the checkout
and the tooling that serves it does not, and it is only maintained while a client is attached to it — so
follow the block's own detection step first, and where no tool answers, say that and use a text search:
an index you cannot query is an index you do not have. `make check-codegraph` is what notices a database
its tooling has stopped writing to, which otherwise answers *nothing calls that* indistinguishably from
*nothing calls that yet*.

With no such block this project has no index and a text search is the tool. Either way, say which one you
used when you report what you found, so a review can tell an exhaustive answer from a lucky one.
"""


# What "code shared between services" is in each language family, and what sharing it would ask of the
# build. Keyed by family because the unit of sharing is the build tool's rather than the framework's — and
# the Java row is where the question of an aggregator pom is answered, so it is answered where a reader of
# the generated project will look for it.
SHARED_CODE = {
    "typescript": (
        "an npm workspace package under `packages/<name>`, which the root `package.json` already lists in "
        "`workspaces`; a deployable depends on it by name like any other package, and one `npm ci` installs "
        "everything. A package that compiles — one that emits the declarations its consumers import — says so "
        "with a `build` script in its own `package.json`, and `make build-packages` then builds it. Nothing "
        "else has to be done for that: `build-packages` is already a prerequisite of every target that "
        "compiles or runs this project's TypeScript code, because a package's `dist/` is not committed "
        "and a target that forgot it would pass here and fail on a fresh checkout. Only that code: a "
        "native service's own targets run in CI inside an image with no node in it"
    ),
    "python": (
        "a Python package under `packages/<name>` with its own `pyproject.toml`, named in each using service's "
        "`[project].dependencies` and pointed at by a `[tool.uv.sources]` entry (`<name> = { path = "
        "\"../../packages/<name>\" }`) so one `uv sync` covers both — then re-lock it, because `uv sync --locked` "
        "refuses a lock that disagrees with the manifest beside it"
    ),
    "go": (
        "a Go module under `packages/<name>`, added to `go.work` beside the services and imported by its module "
        "path — inside the workspace no `replace` directive is needed. `make mutation` stages the service beside "
        "the workspace modules it imports before Gremlins runs (`scripts/go-mutation.py`), because Gremlins copies "
        "only the module it mutates and would not find them; the shared module is built there, never mutated"
    ),
    "java": (
        "a Maven module under `packages/<name>` that each service's pom depends on. Every service is a Maven "
        "project of its own today, with `scripts/verify` and the Makefile as the loop that builds them; a "
        "shared module the services have to build first is what would make an aggregator pom worth having, "
        "and that is the day to add one"
    ),
}
