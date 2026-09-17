/**
 * Write this service's published API document to a file, from the routes themselves.
 *
 * `make openapi` runs it; `make check-openapi` runs it into a scratch file and fails when the committed one
 * differs. `apps/<service>/openapi.json` is the result, and it is committed because things outside this
 * process read it: `packages/api-client` is generated from it, a consumer reads it without reading
 * TypeScript, and a reviewer sees the contract change in the diff rather than in a running service.
 *
 * ── Why a file and not a running service ──────────────────────────────────────────────────────────────
 * `app.swagger()` is the same document `GET /openapi.json` serves, and it is available the moment the app
 * is `ready()` — before anything binds. So the gate needs no port, no wait loop, and no cleanup, which is
 * what makes it a gate rather than a flaky one. `make verify` stays free of anything listening.
 *
 * ── Why it is built the way the process builds it ─────────────────────────────────────────────────────
 * The app is constructed here exactly as `src/main.ts` constructs it, flag source and all. A document
 * built from a differently-assembled app is a document that describes a service nobody runs: the route a
 * flag source adds would be missing from it, and the browser app's client would have no way to call the
 * one endpoint it actually needs.
 */
import { writeFileSync } from 'node:fs';

import { buildApp, readiness } from './adapters/driving/http/app.js';
__FLAGS_IMPORT__

// The first argument, or `openapi.json` beside this service — which is where `make openapi` wants it and
// what `check-openapi` compares against.
const destination = process.argv[2] ?? 'openapi.json';

// `readiness()` with no opener: the document needs the *route*, and `/ready`'s schema is the same
// whether or not a store was handed over. Opening one here would make writing a document a thing that
// touches a database, which is precisely what a gate must not do.
const app = buildApp([readiness()]__FLAGS_SOURCE__);
await app.ready();
// Trailing newline, two-space indent: a document a person will read in a diff, and one that does not make
// every commit look like it rewrote the whole file.
writeFileSync(destination, `${JSON.stringify(app.swagger(), null, 2)}\n`);
await app.close();
