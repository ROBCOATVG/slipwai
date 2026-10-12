<!-- section: browser-app -->
- `{{path}}/**` is a TypeScript/React browser frontend{{api}}. Use browser-facing component tests and do not
  import backend implementation or persistence types.
<!-- end section -->
<!-- section: browser-contract -->
- The frontend consumes published API/query contracts{{api-contracts}}.{{api-client}}
  Frontend state is ordinary UI, server, and URL state; it is not reconstructed from backend
  persistence history.
- Read `docs/design.md` before writing anything with a browser surface. It says what this project's
  screens are made of — the design tokens in `{{web}}/src/styles/`, the layout shell, the element styles
  the slice inherits for free — and it is where a decision about how this project looks is recorded.
<!-- end section -->
<!-- section: demo -->
- A green gate is not a demonstration. `make demo` starts the whole app in containers and prints its
  addresses, `make dev` runs it in the foreground, and `skills/run-the-app/SKILL.md` says what this project
  serves, what to seed first, and how far to go before opening a browser. Show a slice by running it.
<!-- end section -->
<!-- section: containers -->
- `docker-compose.yml` holds the app's own services behind an `app` profile as well as the backing
  services, so `make services-up` still starts only the latter. `make verify` must stay runnable without any
  of it: a test that needs a real backing service goes under the service's integration suite, which only
  `make test-integration` runs.
<!-- end section -->
<!-- section: sqlite-event-store -->
<!-- backing-service:sqlite:begin -->
- The SQLite adapter carries its own schema, so there is nothing to migrate and nothing to start. It cannot
  prove concurrent behaviour — SQLite serialises writers — so do not write a test that claims to race on
  it. Durability and the append-only rule are provable there, and are proved.
<!-- backing-service:sqlite:end -->
<!-- end section -->
<!-- section: postgres-event-store -->
<!-- backing-service:postgres:begin -->
- The Postgres adapter is where the never-write-the-same-version-twice guarantee is proved: its
  `(stream_id, version)` unique constraint is the concurrency control, and the integration suite races two
  appends at one version. A concurrency claim asserted anywhere else is not evidence.
<!-- backing-service:postgres:end -->
<!-- end section -->
<!-- section: sqlite-state-store -->
<!-- backing-service:sqlite:begin -->
- The SQLite repository adapter carries its own schema, so there is nothing to migrate and nothing to start.
  It cannot prove concurrent behaviour — SQLite serialises writers — so do not write a test there claiming
  two writers raced for one row's version. Durability is provable on it, and is proved.
<!-- backing-service:sqlite:end -->
<!-- end section -->
<!-- section: postgres-state-store -->
<!-- backing-service:postgres:begin -->
- The Postgres repository adapter is where the no-lost-update guarantee is proved: a save carries the
  version the state was read at, the UPDATE matches on it and bumps it, and the integration suite races two
  writers at one version so that exactly one wins and the other is told. A concurrency claim asserted
  anywhere else is not evidence.
<!-- backing-service:postgres:end -->
<!-- end section -->
<!-- section: http-transport -->
<!-- backing-service:{{transport}}:begin -->
- The HTTP adapter parses untrusted input into typed commands, calls a use case, and maps the outcome to a
  status. It holds no business rules and makes no authorisation decision — a rule enforced in a route
  handler is a rule the next entry point will not enforce.
- One file binds a port, and it is the only untested file in the service: everything worth asserting about
  a route is asserted against the app object with no socket at all. Keep composition there and behaviour
  out of it. Product routes live under `/api`, which is what the dev server proxies and what an ingress can
  route unchanged; `/health` sits outside it, being a probe rather than API surface.
<!-- backing-service:{{transport}}:end -->
<!-- end section -->
<!-- section: keycloak-auth -->
<!-- backing-service:keycloak:begin -->
- The OIDC flow in the auth adapter is a placeholder. Load `skills/secure-oauth-oidc/SKILL.md` before
  implementing it and use a maintained client library; never hand-roll token validation. Authorisation
  decisions belong in use cases, not in the adapter.
<!-- backing-service:keycloak:end -->
<!-- end section -->
<!-- section: users-keycloak -->
<!-- backing-service:users-keycloak:begin -->
- External users sign in from the browser app, which owns the login: `apps/web/src/auth/` uses react-oidc-context
  over oidc-client-ts for the authorization-code flow with PKCE, the session and silent renewal. Do not add a
  second login path in a service, and never hand-roll any of that — load `skills/secure-oauth-oidc/SKILL.md`
  before touching it.
- A service accepts an external user only from the external realm. The users adapter refuses any other issuer,
  because the internal realm lives in the same Keycloak and an internal token is a valid JWT that differs by one path
  segment; keep that check exact. An external user is `sub` plus a verified email — what an account may do is a
  use-case decision about ownership, not a role in an adapter.
<!-- backing-service:users-keycloak:end -->
<!-- end section -->
<!-- section: skiff -->
- This skiff deploys one production environment after verify passes; there is no staging promotion. Use immutable images, make smoke and the recorded rollback.
- Compute: {{compute}}. Database: {{database}}.
- Read infra/SHAPE.md and infra/README.md before changing infrastructure. Shape convergence prepares only: retain the current database/state until verified cutover.
<!-- end section -->
<!-- section: flags -->
- **A feature flag is what makes merging and releasing two decisions**, and here it is the only thing
  that does: every commit that passes `verify` on `main` is applied to staging and then to production, with
  nobody in between. Unfinished work therefore ships **dark**. A flag is declared in
  `infra/service/flags.auto.tfvars` under the service that reads it, seeded `off`, in the same change as
  the code that reads it; it reaches that service as `FLAG_<KEY>` — `checkout-v2` is `FLAG_CHECKOUT_V2` —
  and it is read through {{readers}}, asked by key ({{calls}}) and nowhere else. Never derive the variable
  name at the point of use and never read the environment for a flag anywhere else: a typo reads as
  absent, absent reads as off, and the feature simply never turns on. Read it where the behaviour branches
  — a use case or an adapter — never in the domain, which takes decided values as inputs the way it takes
  the clock. No service calls {{cloud}} for a flag.
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
<!-- end section -->
<!-- section: browser-flags -->
- The same flag reaches `{{web}}` as `VITE_FLAG_<KEY>`, and `{{web}}/src/flags.ts` is the only place that
  transform is written on this side: ask with `flagEnabled('checkout-v2')`, never by reading
  `import.meta.env` at the point of use. Vite inlines the value while the bundle is *built*, so a browser
  flag is a property of the bundle: `scripts/deploy.py` builds it with what this environment's parameters
  are set to at deploy time, and a flag flipped afterwards reaches the browser only on the next `make
  deploy ENV=…` of that environment. `make flag` says so when it flips one this app reads. A flag declared
  under a service other than the one `{{web}}`'s `/api` goes to does not reach the bundle at all.
- That asymmetry has a window in it, and a direction. On in the service, off in the bundle: the feature is
  invisible and nothing is at risk. Off in the service, on in the bundle: an inviting UI whose every call
  is refused. So turn a feature **on** in the service first and reveal it with the next deploy, and turn it
  **off** in the bundle first — by deploying — before the service stops honouring it. Either way the
  service is the authority: gate the surface on the flag *and* handle the endpoint refusing, because for
  the couple of minutes a restart takes it will. Locally both halves come from `.env`, `FLAG_<KEY>` and
  `VITE_FLAG_<KEY>` set to the same value unless you are deliberately reproducing that window.
<!-- end section -->
