/**
 * The browser app's client for this project's own API — typed from the service's published contract.
 *
 * ── Where the types come from ─────────────────────────────────────────────────────────────────────────
 * `src/schema.ts` is generated from `__DOCUMENT__`, which the service writes out of its own routes
 * (`make openapi`) and `make check-openapi` keeps in step with them. So the shape this app expects and the
 * shape the service serialises are one declaration: a route that changes its response breaks the build
 * here, at the line that reads the field, rather than at run time in front of somebody.
 *
 * The generated file is not committed. It is a build output like any other — `make build-packages` writes
 * it, and every target that compiles this project's npm code has that as a prerequisite — so a fresh
 * checkout has none and nobody can edit it and be right.
 *
 * ── Why this wrapper is hand-written ──────────────────────────────────────────────────────────────────
 * The generator emits types and no code, which is the honest split: types are derived from a document and
 * cannot drift, while *how* this app talks to its service is a decision — the base path, what counts as a
 * failure, whether a body is JSON — and a generated client answers those questions with whatever its
 * author preferred. Twenty lines here, readable in full, beats a generated module nobody opens.
 *
 * ── Relative paths, on purpose ────────────────────────────────────────────────────────────────────────
 * `baseUrl` is empty by default, so every call is same-origin: the dev server forwards `/api` to the
 * service and a deployment serves both from one origin. An absolute backend URL in a bundle is a URL
 * somebody forgets to change, and it is what turns every request into a CORS preflight.
 */
import type { paths } from './schema';

/** Every path in the published contract that answers a GET — the only ones this client can be asked for. */
export type GetPath = { [P in keyof paths]: paths[P] extends { get: unknown } ? P : never }[keyof paths];

/** What a GET on that path answers with, as the contract declares it. */
export type Answer<P extends GetPath> = paths[P] extends {
  get: { responses: { 200: { content: { 'application/json': infer Body } } } };
}
  ? Body
  : never;

/**
 * A request the service refused, or one nothing answered.
 *
 * An error class rather than a result type, deliberately: a screen that forgets to check a result renders
 * `undefined`, while a screen that forgets to catch shows an error boundary. Of the two ways to be wrong,
 * the loud one is the one worth having.
 */
export class ApiError extends Error {
  constructor(
    readonly path: string,
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export type ApiClient = {
  /** GET one path from the published contract, typed by what that path says it answers. */
  get<P extends GetPath>(path: P): Promise<Answer<P>>;
};

/**
 * Build a client.
 *
 * `fetcher` is a parameter so a test can hand over its own — a plain function, written by hand, that
 * answers what the case is about. That is the whole of what this needs to be testable, and it is why
 * nothing here reaches for a mocking framework.
 *
 * @param options `fetcher` to drive it with something other than the browser's `fetch`; `baseUrl` to
 *   address a service that is not on this origin, which a deployed bundle should never need to
 */
export function createApiClient(options: { fetcher?: typeof fetch; baseUrl?: string } = {}): ApiClient {
  const fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
  const baseUrl = options.baseUrl ?? '';
  return {
    async get<P extends GetPath>(path: P): Promise<Answer<P>> {
      const url = `${baseUrl}${String(path)}`;
      let response: Response;
      try {
        response = await fetcher(url, { headers: { accept: 'application/json' } });
      } catch {
        // A network failure has no status, and pretending it is a 500 would hide the difference between
        // "the service said no" and "nothing was reached".
        throw new ApiError(url, 0, `${url} could not be reached`);
      }
      if (!response.ok) {
        throw new ApiError(url, response.status, `${url} answered ${response.status}`);
      }
      return (await response.json()) as Answer<P>;
    },
  };
}
