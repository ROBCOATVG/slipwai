/**
 * The shell every screen is inside, and the routing table.
 *
 * ── Why there is a shell at all ───────────────────────────────────────────────────────────────────────
 * A first slice demonstrated on a browser-default page gets feedback about the page. Header, main and
 * footer, styled from `src/styles/`, mean the first thing anybody sees is a page — and the slice is what
 * is being looked at. It is deliberately generic: a baseline to react to, not a design. `docs/design.md`
 * is where this project writes down what it decided instead.
 *
 * ── Why the flags are awaited here and not before `createRoot` ────────────────────────────────────────
 * `flagEnabled` answers off until it has been told otherwise, so rendering a gated screen before the flags
 * arrive shows every gated feature in its off state and then changes its mind — a flash of the wrong
 * screen on every load, for the one flag that is on.
 *
 * The fix used to be a top-level `await` in `main.tsx`, which bought that at the cost of the whole page:
 * nothing at all painted until the request came back, so a slow or dead service was a blank tab. Waiting
 * *here* is the same guarantee where it is actually needed — the shell paints immediately, and only the
 * routed content waits. `loadFlags` never rejects, so the wait is bounded by one request either way.
 */
import { useEffect, useState } from 'react';
import { Link, Route, Routes } from 'react-router';

import { loadFlags, setFlagSource } from './flags';
// backing-service:__TRANSPORT__:begin
import { Home } from './routes/Home';
// backing-service:__TRANSPORT__:end

/**
 * Hand this bundle its flags, once, and say when that has happened.
 *
 * `setFlagSource` is module state rather than a context on purpose (`src/flags.ts` says why), so this
 * returns a boolean rather than the flags themselves: a slice asks `flagEnabled('checkout-v2')` wherever
 * it needs to, and nothing has to be threaded through the tree.
 */
export function useFlagsLoaded(): boolean {
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let live = true;
    void loadFlags().then((source) => {
      setFlagSource(source);
      if (live) {
        setLoaded(true);
      }
    });
    // React runs an effect twice in development under StrictMode. Setting state on an unmounted
    // component is the warning that follows, and this is the two lines that avoid it.
    return () => {
      live = false;
    };
  }, []);
  return loaded;
}

export function App() {
  const flagsLoaded = useFlagsLoaded();
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>__PROJECT_NAME__</h1>
        <nav className="app-nav" aria-label="Sections">
          <Link to="/">Overview</Link>
        </nav>
      </header>
      <main className="app-main">
        {flagsLoaded ? (
          <Routes>
            {/* backing-service:__TRANSPORT__:begin */}
            {/* One route, and the first slice adds the second beside it. The route is marked because
                what it shows is this project's own API answering, and a project with no transport has
                no API to show. */}
            <Route path="/" element={<Home />} />
            {/* backing-service:__TRANSPORT__:end */}
          </Routes>
        ) : (
          <p role="status" className="muted">
            Loading…
          </p>
        )}
      </main>
      <footer className="app-footer">
        <span>Replace this walking skeleton with the first actor-visible slice.</span>
        <span className="muted">docs/design.md — what this project looks like, and why</span>
      </footer>
    </div>
  );
}
