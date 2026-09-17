/**
 * The one route this skeleton ships, and the one call it makes.
 *
 * It exists to prove the whole path end to end — browser, dev-server proxy or ingress, service — so that a
 * first slice starts from a screen that is already talking to its own API rather than from an unproven one.
 * Delete it the moment the first actor-visible slice replaces it.
 *
 * ── Why this fetches by hand ──────────────────────────────────────────────────────────────────────────
 * This project's transport publishes no API document, so there is nothing to generate a typed client from
 * and there is no `packages/api-client`. What that costs is visible right here: `Answer` is
 * `Record<string, unknown>`, because the honest thing to say about a response shape nobody declared is
 * that it is JSON — and a field read off it is a field the compiler cannot check. A project whose service
 * published a contract would have those fields typed from it, and a route renamed in the service would
 * stop this file compiling instead of failing in front of somebody.
 *
 * The way out is to publish one: the framework has an OpenAPI extension, and `docs/design.md` says what
 * changes here when it is added. Until then, hand-written is better than guessed — a type asserting fields
 * nothing promised is worse than no type at all.
 *
 * ── Why the fetch is a prop ───────────────────────────────────────────────────────────────────────────
 * `HomeView` takes the `fetch` it should use, and `Home` is the one line of wiring that passes the
 * browser's. That seam is what lets the test drive every state — checking, answered, unreachable — with a
 * plain function it writes itself, rather than replacing a module with a mocking framework. A seam in the
 * code beats a mock in the test; the `finding-seams` and `testing` skills say why, and nothing in this
 * repository adds a mocking framework to make a test possible.
 */
import { useEffect, useState } from 'react';

// The path the panel reports on — a constant, so the prose below reads the same at any length of it.
const statusPath = '__STATUS_PATH__';

/**
 * What `__STATUS_PATH__` answers, as much as this project can say about it without inventing anything.
 * Narrow it to the fields the service actually returns once you have read them off the service — and
 * prefer publishing a document and generating this instead.
 */
export type Answer = Record<string, unknown>;

/** What the panel is showing: the call has not finished, it answered, or nothing was reachable. */
export type Reachability =
  | { state: 'checking' }
  | { state: 'answered'; body: string }
  | { state: 'failed'; reason: string };

export function HomeView({ fetcher }: { fetcher: typeof fetch }) {
  const [reachability, setReachability] = useState<Reachability>({ state: 'checking' });

  useEffect(() => {
    let live = true;
    const answer = async (): Promise<string> => {
      const response = await fetcher(statusPath, {
        headers: { accept: 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`${statusPath} answered ${response.status}`);
      }
      return JSON.stringify((await response.json()) as Answer);
    };
    void answer()
      .then((body) => {
        if (live) {
          setReachability({ state: 'answered', body });
        }
      })
      .catch((error: unknown) => {
        if (live) {
          setReachability({
            state: 'failed',
            reason: error instanceof Error ? error.message : 'unknown',
          });
        }
      });
    return () => {
      live = false;
    };
  }, [fetcher]);

  return (
    <section className="panel">
      <h2>Ready</h2>
      <p>
        This page, the stylesheet it uses and the call below are the walking skeleton. Replace them
        with the first actor-visible slice; keep the shape.
      </p>
      <h3>This project&apos;s API</h3>
      <p>
        <code>{statusPath}</code>, fetched by hand: this project&apos;s transport publishes no API
        document, so there is no typed client to call it through. See <code>docs/design.md</code>.
      </p>
      {reachability.state === 'checking' && (
        <p role="status" className="status status-checking">
          Asking the service…
        </p>
      )}
      {reachability.state === 'answered' && (
        <p role="status" className="status status-ok">
          The service answered <code>{reachability.body}</code>
        </p>
      )}
      {reachability.state === 'failed' && (
        <p role="status" className="status status-failed">
          The service could not be reached: {reachability.reason}
        </p>
      )}
    </section>
  );
}

export function Home() {
  return <HomeView fetcher={globalThis.fetch.bind(globalThis)} />;
}
