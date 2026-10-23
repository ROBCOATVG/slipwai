MINOR

**The keel ships no browser app: a language package ships each frontend, and may ship frontends alone.**
`react-vite` moved into the TypeScript language package, and a language's `language.json` now declares the
frontends it ships in a `frontends` block — label, capabilities, what each feature adds, owns and depends on,
the files carrying a marked region, the styled baseline — which the keel and a project's pruner both read, so the
keel names no frontend and no file inside one. A package may ship services, browser apps or both: a
frontend-only family has `"backends": {}` and answers `browser_apps`, `npm_workspace`, `shared_code` and
`formatter`, and its browser app can be generated beside any backend outside the npm workspace. `--frontend`
offers what the installed languages ship, the first of them by default, and `none` where nothing does; a
frontend nobody ships is refused naming the language that would. `add-frontend` takes `--frontend` for a
project's first browser app. The contract is `docs/frontend-protocol.md`; conformance checks every frontend a
package ships, and `slipwai package new --kind language --parts frontend` scaffolds one that loads and generates.

**Catch-up:** `slipwai language upgrade typescript` before generating with `--frontend react-vite`; an existing
project's browser app is unchanged, and `slipwai migrate` gives its `scripts/backing-services.py` the frontend's
rows in place of the keel's.
