# The frontend protocol

How a language package ships a browser app, what slipwai reads from it, and how to add a new one.
`docs/backend-protocol.md` is the same contract for services; this page is its browser-app half, and the
two are read together by anybody publishing a package that has both.

## What a frontend is, and whose

A **frontend** is a kind of browser app — `react-vite` is one — that `slipwai generate --frontend <name>`
and `slipwai add-frontend` can write into a project's `apps/<name>`. **The keel ships none.** Every frontend
is declared and supplied by a language package's **family**, because a browser app is an npm package in the
project's one npm workspace, and the family that owns that workspace already commits the lock that resolves
the app's dependencies and pins the Biome that lints it. A frontend is not a fifth kind of package: it is a
member of a language family, declared in `language.json` beside its backends.

So a language package has one of three shapes:

| Shape | `backends` | `frontends` | Example |
|---|---|---|---|
| **Backend-only** | one or more | absent | `go`, `python`, `java` |
| **Frontend-only** | `{}` | one or more | `tests/fixtures/frontend-family/toy-web` |
| **Both** | one or more | one or more | `typescript` (services and `react-vite`) |

A backend-only package is unchanged by any of this and is never asked a frontend question. A project may
combine a backend from one package with a frontend from another — a Go service beside `react-vite` — with
one exception: **services of an npm family beside another npm family's browser app** are refused at
generation, naming both, because they would share one workspace lock and neither package has committed one
resolving the two together. Choose a frontend that family ships, or a service in a language outside the npm
workspace.

## Where everything lives in a package

One directory per kind of thing a package ships, so a reviewer can see which is which:

```
slipwai-language-<name>/
  language.json                 # "backends": {...} and/or "frontends": {...}
  VERSION  CHANGELOG.md  changelog.d/
  slipwai_language_<name>/      # the Python the loader imports: LANGUAGE, and the answers below
  assets/
    languages/<family>/         # backend: a service's skeleton, its locks, Biome (an npm family)
    backing-services/<family>/  # backend: what each axis answer adds to a service
    frontends/<frontend>/       # frontend: one directory per browser app, laid out as below
  tests/
```

The loader holds the frontend half of this: a `BrowserApp` whose root is anything but
`<package>/assets/frontends/<its name>` is refused when the package loads.

### Inside `assets/frontends/<frontend>/`

Every tree here except `locks/` is **laid out like the app** — paths relative to `apps/<name>/` — and is
copied into the project whole. slipwai names the trees, never a file inside them, so a frontend in another
framework is a different tree and the same code.

| Tree | Copied when | What it is |
|---|---|---|
| `app/` | always | The skeleton: manifest, entry point, shell, styles, config, tests. `app/package.json` is the one file read as data — its `name` is replaced and the features' `dependencies` merged in — and it pins `@biomejs/biome`, which must agree with the family's pin. |
| `app-flags-local/` | the project has no deploy target | The feature-flag reader that reads `.env` through the bundle. |
| `app-flags-target/` | the project deploys somewhere | The flag reader that asks `GET /api/flags`. Both export the same names. |
| `app-route-client/` | the app's service publishes an API document | The one route, calling through the typed client. |
| `app-route-plain/` | the service publishes no document | The one route, fetching by hand. |
| `features/<feature>/` | any service in the project has `<feature>` | What the feature adds to the app — the external login, for `users-keycloak`. Named by the feature's `files` in `language.json`. |
| `api-client/` | the service publishes an API document | `packages/api-client`: its `package.json` (whose `scripts.build` names `__DOCUMENT__`) and source. |
| `locks/frontend-only<suffix>.json` | the project has no npm service | The workspace lock for the browser apps alone. One per dependency set: `''` and one per combination of dependency-adding features, named by the lock suffix below. |

**Tokens.** Every file in every copied tree has these replaced:

| Token | Becomes |
|---|---|
| `__PROJECT_NAME__` | the project's name |
| `__WEB_PORT__` | this browser app's dev-server port (`5173` for the first) |
| `__WEB_PORT_VARIABLE__` | the variable that moves it (`WEB_PORT`, `WEB_PORT_ADMIN`, …) |
| `__TRANSPORT__` | the transport feature of the service it proxies to, or `none` — so a marked region of that name is kept or cut |
| `__API_PORT__` | the port of the service it proxies to |
| `__STATUS_PATH__` | the one path the route calls: `/api/flags` with a deploy target, the health probe without |
| `__API_CLIENT__` | the typed client's package name |

**Marked regions.** A file may carry `backing-service:<feature>:begin` / `:end` regions; slipwai keeps a
region where the project has the feature and cuts it otherwise, at generation and again whenever the project
is pruned. Every file in `app/` that carries a region is listed in the entry's `marked`, so the pruner a
generated project carries knows where to look.

**The workspace lock's shape.** A committed lock — the family's `workspace_lock`, or `locks/frontend-only*` —
is resolved for one browser app at `apps/web` named `delivery-starter-web`, linked at
`node_modules/delivery-starter-web`, and the typed client at `packages/api-client` linked at
`node_modules/@packages/api-client`; a lock beside a service also has the service at `apps/service` linked
at `node_modules/delivery-starter`. slipwai renames those records for the project and repeats them for each
further app, so a lock has to use exactly those names.

## What `language.json` declares

```json
{
  "name": "typescript",
  "family": "typescript",
  "backends": { "typescript": { "...": "..." } },
  "frontends": {
    "react-vite": {
      "label": "React and Vite — a TypeScript browser app, Biome, Vitest and Testing Library",
      "stack": "TypeScript/React/Vite",
      "gate": "Biome, TypeScript and React component tests",
      "capabilities": ["frontend", "typescript", "react", "vite"],
      "marked": ["vite.config.ts", "src/main.tsx", "src/App.tsx", "tests/App.test.tsx"],
      "features": {
        "users-keycloak": {
          "files": "features/users-keycloak",
          "owned": ["src/auth", "tests/auth"],
          "dependencies": { "oidc-client-ts": "3.5.0", "react-oidc-context": "3.3.1" },
          "where": "`src/auth/users.tsx`, react-oidc-context over oidc-client-ts"
        }
      },
      "design": {
        "tokens": "src/styles/tokens.css",
        "base": "src/styles/base.css",
        "shell": "src/App.tsx",
        "entry": "src/main.tsx",
        "imports": ["import './styles/tokens.css';\n", "import './styles/base.css';\n"],
        "route": "src/routes/Home.tsx"
      }
    }
  }
}
```

| Field | Required | Read by |
|---|---|---|
| `label` | yes | `slipwai list`, the interview's frontend question |
| `stack` | yes | `docs/whats-included.md`'s line about the browser app ("A separate TypeScript/React/Vite browser application…") |
| `gate` | yes | `docs/gates.md`'s line about what `make verify` runs for the app |
| `capabilities` | yes | `project.json`'s capabilities, and which skills a project ships (`capabilities.py`) |
| `marked` | no | the pruner: the files in `app/` carrying a marked region |
| `features.<f>.files` | per feature | the directory under the frontend copied in when the project has `<f>` |
| `features.<f>.owned` | no | the pruner: the app's paths the feature owns, removed with it |
| `features.<f>.dependencies` | no | merged into `app/package.json`, removed again by the pruner, and part of the lock suffix |
| `features.<f>.where` | no | the README's sentence on where in the app the feature lives |
| `lock-name` | no | a family shipping more than one frontend names each one's locks apart with it |
| `design` | no | `docs/design.md` and `migrate`'s handling of a replaced baseline. All six keys or none: without it the project gets no design page |

**The lock suffix** is `-<lock-name>` (if any) followed by `-<feature>` for each feature with
`dependencies` that the project has, in the order `features` lists them: `''` and `-users-keycloak` for
`react-vite`. It is the second argument to the family's `workspace_lock`, and the `<suffix>` of
`locks/frontend-only<suffix>.json`.

The rules the catalogue holds: a frontend name is a lower-case slug; it is declared by one package only, and
never as `none`, which is the keel's; a framework package (one with `requires`) declares none, because a
browser app is a family's answer; and the first frontend in package `order` is the default `--frontend`
where any is installed, `none` where none is.

## What the Python answers

On the family (`protocol.Family(...)`), and nowhere else:

| Member | What it is |
|---|---|
| `browser_apps` | `{name: BrowserApp(name, <package>/assets/frontends/<name>)}` — one per frontend in `language.json`, exactly: a name in one and not the other is refused at load |
| `npm_workspace` | an `NpmWorkspace`: `image` (the dev server's image under Compose), `biome` (the directory with `biome.jsonc` and `domain-purity.grit`), `biome_pins` (its manifests pinning `@biomejs/biome`), `member_lock` and `workspace_lock` (its services' locks — asked only of a family with npm services) |
| `shared_code` | the architecture page's paragraph on where shared code lives. Required of a family shipping a browser app even with no backend |
| `formatter` | the `make format` line for the app, or `None` for none |

Nothing else is asked of a browser app's family: pins, Renovate rules, CI toolchain setup and prune rows are
asked of the families of a project's services. The smallest frontend-only family that loads and generates is
`tests/fixtures/frontend-family/toy-web/slipwai_language_toy_web/__init__.py`: those four answers and a tree.

## Adding a frontend

The maintainer skill `add-module` walks this with you; the steps are:

1. **Decide the shape.** A frontend in a family that already has services (TypeScript, a second
   TypeScript frontend) goes in that family's package. A frontend for a family nobody publishes goes in a
   frontend-only package of its own, with `"backends": {}`.
2. **Lay out `assets/frontends/<name>/`** as above. Start from a copy of a working one — `react-vite` in
   `slipwai-language-typescript`, or the `toy-web` fixture for the minimum — and change the framework, not
   the layout.
3. **Declare it** in `language.json`'s `frontends` block, with every required field.
4. **Answer it**: add it to the family's `browser_apps`; a frontend-only family also answers
   `npm_workspace`, `shared_code` and `formatter`.
5. **Commit the locks.** For each dependency set (each lock suffix), the frontend-only lock, and — in a
   family with npm services — a `workspace_lock` for each service selection beside it. Resolve them with
   `npm install` over exactly the manifests slipwai would write; a lock that disagrees with its manifest is
   refused by `npm ci`.
6. **Prove it.** `slipwai package check .` loads the package, refuses every fault above by name, and
   generates; then `slipwai generate demo --frontend <name>` beside each backend you mean to support, and run
   that project's `make verify`. Nothing short of a generated project's own gate says a frontend works.
7. **Release** as any language: `make release`, then `make register`. The release's index entry records
   `"answers": ["npm_workspace", "browser_apps"]`, which is what lets `slipwai list` and a refusal tell
   somebody without the package which one to install.

## What a second frontend in another bundler still has to move

`react-vite` is the only frontend there has been, and three couplings are still the keel's rather than the
frontend's. None of them stops a package shipping a second frontend; each is something it would get wrong:

- **The bundler's environment prefix.** The keel writes `VITE_USERS_*` for the login into `.env.example` and
  `docker-compose.yml`, and `scripts/agents/try_it.py` passes a flag to the app as `VITE_FLAG_<KEY>`.
- **`try_it.py` reads routes and flags by framework.** Its two patterns are keyed by `react-vite`; another
  frontend's app gets no route or flag discovery in Try it until its own are added there.
- **Node.** CI sets up Node for any browser app (`ci_workflows.NODE_SETUP`): a frontend is an npm package.

These are plan 17.5's to move into the `frontends` entry.

## Compatibility

The frontend protocol is versioned with the backend protocol, by the keel's `schemaVersion` and a
package's `core` range. **From the 2.0.0 release on**, a MINOR may only add what an existing package can
ignore — an optional field, an optional member — and a new obligation applies only to a package that opts
into the feature it comes with. Anything else is a new schema major, which every existing `core: "<10"`
refuses by name rather than failing in a generated project. A package proves it still conforms in its own CI,
against the keel's `main` (`docs/backend-protocol.md`, *Compatibility*).
