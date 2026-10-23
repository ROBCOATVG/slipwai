---
name: add-module
description: Publish a slipwai language package — services, browser apps or both — walking through which it is, the layout, the answers the registry asks, the proof and the release. Use when adding a language slipwai cannot generate yet, or a frontend no installed language ships.
---

# Adding a module

A module is a **language package**: its own repository, its own release, installed from the chandlery. The
keel ships none — no language and no frontend — so nothing here touches the keel's repository. You are
writing something that stands beside it, and its CI is the contract test that keeps it standing.

Work through this in order, with the person. Each step ends on something you can run.

## 1. Decide which it is

Ask what it ships, because the answer decides everything after it:

| It ships | Shape | `--parts` | Read |
|---|---|---|---|
| Services in a language slipwai cannot generate | **backend-only** | `backend` | `docs/backend-protocol.md` |
| A browser app for a framework nobody ships | **frontend-only** | `frontend` | `docs/frontend-protocol.md` |
| Services, and the browser app that shares their npm workspace | **both** | `backend,frontend` | both |

Then rule out the two cases that are not a new module:

- **A framework for a family that exists** — `java-quarkus` beside `java-spring` — is `add-framework`.
- **A second frontend in a family that exists** — another TypeScript frontend — goes in *that* family's
  package, because its npm services and the browser app share one lock only that family can commit.

One rule settles a frontend-only package's family name: services of an npm family are refused beside another
npm family's browser app (`docs/frontend-protocol.md`, *What a frontend is*). A frontend-only package is for
projects whose services are outside the npm workspace — Go, Python, Java — and it says so in its README.

## 2. Start it

```sh
slipwai package new rust --kind language                      # backend-only
slipwai package new svelte --kind language --parts frontend   # frontend-only
slipwai package new deno --kind language --parts backend,frontend
cd rust
```

What it writes, and what state it is in:

- `language.json` — the fragment, declaring the keel schema *this* copy speaks as its `core` range, a
  backend row with `targets: ["none"]` and/or a `frontends` entry with every required field;
- `VERSION` (`1.0.0.dev0`), `CHANGELOG.md`, `changelog.d/` with the first fragment;
- `slipwai_language_<name>/__init__.py` — the `LANGUAGE` the loader imports;
- for a frontend, `assets/frontends/<name>-web/` with every tree the pipeline reads and `assets/biome/`;
- a `Makefile` with `check`, `version`, `release` and `register`;
- `.github/workflows/verify.yml`, calling the keel's reusable workflow.

**A frontend part loads and generates as written**: `slipwai list` offers `<name>-web`, and a project
generated beside any backend has it. **A backend part does not load yet, on purpose**: the loader refuses it
with one line naming every required member still unanswered. That line is the list to work through. Where
you would rather start from placeholders for all of them, copy `slipwai-language-template` (the toy)
instead, and rename it.

Rename `<name>-web` to what the frontend is (`svelte-vite`) in `language.json`, the `BROWSER_APPS` answer and
the directory, together — the loader refuses any one of the three disagreeing with the others.

## 3. The layout

One directory per kind of thing the package ships, which the loader holds:

```
assets/languages/<family>/         backend: the service skeleton, its locks, Biome for an npm family
assets/backing-services/<family>/  backend: what each axis answer adds to a service
assets/frontends/<frontend>/       frontend: app/, the variant trees, features/, api-client/, locks/
```

A backend source outside `assets/` or a browser app outside `assets/frontends/<its name>` is refused at load.
The frontend's trees are laid out like the app and copied whole, with tokens resolved in every file — the
table of trees and the token list are in `docs/frontend-protocol.md`, and are the only names the keel reads.

## 4. Fill it in, smallest first

**A backend:**

1. **One backend, no axes, target `none`.** Answer the members the loader names until `slipwai package
   check .` loads it, then until a generated project builds and its tests run.
2. **`slipwai generate demo --backend <key> --frontend none` into a scratch directory, and run its
   `make verify`.** The only thing that says your answers make a project rather than a plausible tree.
3. **One axis at a time.** An answer is a row in the backend's `options` (`persistence`, `http`, `auth`,
   `users`, `write-model`) plus its files under `assets/`; a `defaults` entry must be one of the `options`.
   An option named after a library — `fastify`, `gin` — is yours to declare, in the fragment's `axes` block;
   one the keel already declares, or another package does, is refused by name.
4. **`write-model`.** Offer `events` and `state`; each rung is a `state` block beside the feature rows in
   `write_side_files`, and `event_model_paths` answers `repository` as well as `events`, `domain`,
   `usecase` and `test`.
5. **Then a target.** A backend that lists `aws` in `targets` is promising its skeleton deploys there.

**A frontend:**

1. **Replace the placeholders with the framework's own**, tree by tree, keeping the tokens.
2. **Declare its features** — what each adds (`files`), owns (`owned`) and depends on (`dependencies`) —
   and `marked` for every file in `app/` carrying a marked region, and `design` if it ships a styled
   baseline.
3. **Commit a lock per dependency set**: `locks/frontend-only<suffix>.json` for each lock suffix the
   features imply, resolved by `npm install` over exactly the manifests the keel writes; in a family with
   npm services, a `workspace_lock` per service selection beside it as well.
4. **Generate it beside each backend you mean to support** and run that project's `make verify`.

## 5. Prove it

```sh
make check          # slipwai package check . — every required member, each profile and target, every frontend
```

It generates projects and holds each to its own gate. **It is slow and it is the point.** A frontend-only
package is generated beside a backend loaded with it: put a language in the same directory locally, and
name it in the workflow's `beside` in CI.

The generated-variant matrix builds images and starts containers. It runs on `main` and on tags, and on a
branch when asked: `gh workflow run verify.yml -R <you>/<repo> -f matrix=true`.

## 6. Keep it proved

`verify.yml` is the package's **contract test**, and the package owns it. It runs the keel's conformance
suite against the newest published keel the `core` range takes **and against the keel's `main`**, on every
push and every night. A red nightly against `main` with no change here means the keel moved: read what it
says, and either answer the new thing or tell the keel — from 2.0.0 the keel promises a 9.x never asks a
package for something it did not opt into (`docs/backend-protocol.md`, *Compatibility*).

## 7. Release it

```sh
make version                              # assemble changelog.d/ into CHANGELOG.md and set VERSION
make release                              # the file, its digest, its index entry under dist/
make register CHANNEL=../slipwai-index    # both, into a channel checkout, and its index rebuilt
```

Then a pull request to that channel, which CI holds to `slipwai channel check`. A release that ships a
browser app records `"answers": ["npm_workspace", "browser_apps"]` in its entry, which is how `slipwai list`
tells somebody without it what to install. A name belongs to its first publisher, and a release is
immutable once anybody has installed it.

## The mistakes worth naming

**Answering a member with what a framework's tutorial does.** The generated project is somebody's
production repository on day two. If the tutorial puts the database URL in the source, your package should
not.

**Pinning nothing.** A package that resolves "latest" at generation makes two projects generated a week
apart different projects. Every lock is committed, per dependency set, for this reason.

**Testing against a keel nobody else runs.** A CI pinned to one old keel commit is green for ever and tells
you nothing; the package found out it was broken when somebody generated with it.
