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

import { flagEnabled, loadFlags, setFlagSource } from './flags';
import { AddBook } from './routes/AddBook';
import { Ask } from './routes/Ask';
import { BookVoice } from './routes/BookVoice';
import { CatchUp } from './routes/CatchUp';
import { ConnectServer } from './routes/ConnectServer';
// backing-service:fastify:begin
import { Home } from './routes/Home';
// backing-service:fastify:end
import { Player } from './routes/Player';
import { RemoveBook } from './routes/RemoveBook';
import { ServerBooks } from './routes/ServerBooks';
import { Settings } from './routes/Settings';

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
        <h1>recap</h1>
        <nav className="app-nav" aria-label="Sections">
          <Link to="/">Overview</Link>
          {/* Behind `import-audio`: with the flag off the link is not rendered and the route not mounted. */}
          {flagsLoaded && flagEnabled('import-audio') && <Link to="/add-book">Add a book</Link>}
          {/* Behind `audiobookshelf-companion`: with the flag off neither the link nor the route exists. */}
          {flagsLoaded && flagEnabled('audiobookshelf-companion') && (
            <Link to="/connect-server">Connect a server</Link>
          )}
          {flagsLoaded && flagEnabled('audiobookshelf-companion') && (
            <Link to="/server-books">Pick from your server</Link>
          )}
          {/* Behind `voice-and-settings`: with the flag off the link is not rendered and the route not mounted. */}
          {flagsLoaded && flagEnabled('voice-and-settings') && <Link to="/settings">Settings</Link>}
        </nav>
      </header>
      <main className="app-main">
        {flagsLoaded ? (
          <Routes>
            {/* backing-service:fastify:begin */}
            {/* One route, and the first slice adds the second beside it. The route is marked because
                what it shows is this project's own API answering, and a project with no transport has
                no API to show. */}
            <Route path="/" element={<Home />} />
            {/* backing-service:fastify:end */}
            {flagEnabled('import-audio') && <Route path="/add-book" element={<AddBook />} />}
            {/* LB15: removal is reached by URL and from the imported card until LB12's library row links it (D90). */}
            {flagEnabled('import-audio') && (
              <Route path="/books/:bookId/remove" element={<RemoveBook />} />
            )}
            {flagEnabled('audiobookshelf-companion') && (
              <Route path="/connect-server" element={<ConnectServer />} />
            )}
            {flagEnabled('audiobookshelf-companion') && (
              <Route path="/server-books" element={<ServerBooks />} />
            )}
            {flagEnabled('voice-and-settings') && (
              <Route path="/books/:bookId/voice" element={<BookVoice />} />
            )}
            {flagEnabled('voice-and-settings') && <Route path="/settings" element={<Settings />} />}
            {flagEnabled('catch-me-up') && (
              <Route path="/books/:bookId/catch-up" element={<CatchUp />} />
            )}
            {/* Behind `ask-about-the-book`: with the flag off the route is not mounted. */}
            {flagEnabled('ask-about-the-book') && (
              <Route path="/books/:bookId/ask" element={<Ask />} />
            )}
            {/* Behind `track-position`: with the flag off the route is not mounted. */}
            {flagEnabled('track-position') && (
              <Route path="/books/:bookId/player" element={<Player />} />
            )}
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
