/**
 * Where the browser app starts: mount the shell, and nothing else.
 *
 * Nothing is awaited before `createRoot`. A top-level `await` in this module is an `await` before the
 * first paint — the browser has the bundle, React is loaded, and the tab is still blank while one request
 * finishes — so a slow service or a cold network is a blank page rather than a page saying what it is
 * waiting for. Anything that has to be fetched is fetched inside a component, where there is somewhere to
 * render "loading" and somewhere to render a failure. `App` does that for the feature flags.
 *
 * The stylesheets are imported here, once, for the same reason: they are the app's, not any screen's.
 * `styles/tokens.css` holds every value this project's look is made of and `styles/base.css` builds the
 * page out of them — see `docs/design.md` before changing either.
 */
import { type ReactNode, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './App';
// backing-service:users-keycloak:begin
import { UsersProvider } from './auth/users';
// backing-service:users-keycloak:end
import './styles/tokens.css';
import './styles/base.css';

const root = document.getElementById('root');
if (root === null) {
  throw new Error('Missing #root element');
}

// Everything the app is wrapped in, outermost first — one entry each rather than one more level of JSX
// nesting. The nest reads better right up until a wrapper is removed: everything that was inside it is
// then indented a level too deep, and the formatter and the pruner disagree about a file neither of them
// is wrong about. A wrapper this project was not given leaves with its own line and its own import, and
// what is left renders exactly the tree it rendered before — which is why `StrictMode` and the router,
// which every project has, are entries here too rather than a nest around the fold below.
const wrappers: Record<string, (tree: ReactNode) => ReactNode> = {
  strictMode: (tree) => <StrictMode>{tree}</StrictMode>,
  // backing-service:users-keycloak:begin
  // The customer login, so every screen below it can ask who is signed in.
  customerLogin: (tree) => <UsersProvider>{tree}</UsersProvider>,
  // backing-service:users-keycloak:end
  router: (tree) => <BrowserRouter>{tree}</BrowserRouter>,
};

const app = Object.values(wrappers).reduceRight<ReactNode>((tree, wrap) => wrap(tree), <App />);

createRoot(root).render(app);
