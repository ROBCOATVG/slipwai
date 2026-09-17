/**
 * The one route this skeleton ships, and the one call it makes.
 *
 * It exists to prove the whole path end to end — browser, dev-server proxy or ingress, service, published
 * contract, typed client — so that a first slice starts from a screen that is already talking to its own
 * API rather than from an unproven one. Delete it the moment the first actor-visible slice replaces it.
 *
 * ── Why the client is a prop ──────────────────────────────────────────────────────────────────────────
 * `HomeView` takes the client it should use, and `Home` is the one line of wiring that builds the real
 * one. That seam is what lets the test drive every state — checking, answered, unreachable — with a plain
 * object it writes itself, rather than replacing a module with a mocking framework. A seam in the code
 * beats a mock in the test; the `finding-seams` and `testing` skills say why, and nothing in this
 * repository adds a mocking framework to make a test possible.
 *
 * ── Why this path ────────────────────────────────────────────────────────────────────────────────────
 * `__STATUS_PATH__` is what this project's service publishes and this origin can actually reach: the dev
 * server forwards `/api` to the service, and a deployment routes the same prefix there. The path is typed
 * — it has to be one the published contract names — so a route that is renamed in the service stops this
 * file from compiling instead of failing in a browser.
 */

import type { ApiClient } from '__API_CLIENT__';
import { createApiClient } from '__API_CLIENT__';
import { useEffect, useState } from 'react';

// The path the panel reports on — a constant, so the prose below reads the same at any length of it.
const statusPath = '__STATUS_PATH__';

/** What the panel is showing: the call has not finished, it answered, or nothing was reachable. */
export type Reachability =
  | { state: 'checking' }
  | { state: 'answered'; body: string }
  | { state: 'failed'; reason: string };

export function HomeView({ client }: { client: ApiClient }) {
  const [reachability, setReachability] = useState<Reachability>({ state: 'checking' });

  useEffect(() => {
    let live = true;
    void client
      .get(statusPath)
      .then((body) => {
        if (live) {
          setReachability({ state: 'answered', body: JSON.stringify(body) });
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
  }, [client]);

  return (
    <section className="panel">
      <h2>Ready</h2>
      <p>
        This page, the stylesheet it uses and the call below are the walking skeleton. Replace them
        with the first actor-visible slice; keep the shape.
      </p>
      <h3>This project&apos;s API</h3>
      <p>
        <code>{statusPath}</code>, through the typed client generated from the service&apos;s
        published contract.
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

// One client for the life of the bundle. Built here rather than inside the component, because a new
// client on every render is a new `useEffect` dependency on every render, and that is a request loop.
const client = createApiClient();

export function Home() {
  return <HomeView client={client} />;
}
