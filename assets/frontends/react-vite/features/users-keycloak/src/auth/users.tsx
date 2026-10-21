/**
 * How an external user signs in to this browser app.
 *
 * Keycloak's `customers` realm is the identity provider. The app sends the browser there to log in and
 * gets tokens back — the Authorization Code flow with PKCE, which is the one the OAuth security BCP
 * (RFC 9700) leaves standing for an app that runs in a browser. Everything the protocol needs to be safe
 * is done by a maintained client, react-oidc-context over oidc-client-ts, and none of it is written here:
 *
 *   - PKCE: a fresh code verifier per attempt, so a stolen authorization code is worthless on its own.
 *   - `state`: ties the response to the request this tab made, so a response injected from elsewhere is
 *     refused.
 *   - `nonce`: ties the ID token to this login, so a replayed token is refused.
 *   - ID-token validation: signature against the issuer's keys, `iss`, `aud`, `exp`.
 *   - Renewal: `automaticSilentRenew` swaps the refresh token for new tokens before the old ones expire.
 *
 * Hand-rolling any of those is how apps end up with a login that looks fine and is not. If this file
 * starts growing protocol code, stop and load `skills/secure-oauth-oidc/SKILL.md` first.
 *
 * ── Where the tokens live ─────────────────────────────────────────────────────────────────────────────
 * `sessionStorage`, stated explicitly below even though it is the library's default, because it is a
 * decision: tokens survive a reload and are gone when the tab closes, and no other tab or a later visit
 * sees them. `localStorage` would keep an external user signed in across visits at the cost of tokens that
 * outlive the tab. Either way the browser holds the tokens, and any script running on this origin can read
 * them. The alternative that keeps tokens out of the browser altogether is a backend-for-frontend that
 * holds them server-side and gives the browser only a session cookie — `skills/bff-entry-points/SKILL.md`
 * is the guide when that is what the product needs.
 *
 * ── Configuration ─────────────────────────────────────────────────────────────────────────────────────
 * Two values, from the repository's `.env` (documented in `.env.example` at the root; `vite.config.ts`
 * points Vite at that directory):
 *
 *   VITE_USERS_ISSUER     the realm's issuer URL — locally `http://localhost:8081/realms/customers`
 *   VITE_USERS_CLIENT_ID  the public client registered for this app — locally `web`
 *
 * Vite only copies `VITE_`-prefixed keys into the bundle, which is why these two carry the prefix, and
 * why nothing without it — a client secret, say — can leak in by accident. There is no secret here anyway:
 * a browser cannot keep one, which is exactly what PKCE is for.
 *
 * `usersConfig` is a pure function of its input so the tests can drive it with plain objects;
 * `UsersProvider` is the only place that hands it the real `import.meta.env`.
 *
 * ── Back to where sign-in started ─────────────────────────────────────────────────────────────────────
 * Keycloak sends the browser back to one address, this origin's root, so a person who opened a link to a
 * record, was asked to sign in and did, landed on the home page with the record gone. Every sign-in now
 * carries the page it started on in OAuth's own `state` — which the library already round-trips and checks —
 * and the callback puts the person back there. It is done once, in the manager the provider is given, so a
 * screen that starts a sign-in of its own (`auth.signinRedirect()`) gets it without asking. Only a path on
 * this origin is ever returned to: `state` comes back through the browser, and an address it named
 * anywhere else would make this app an open redirect.
 */
import {
  type SigninRedirectArgs,
  type User,
  UserManager,
  type UserManagerSettings,
  WebStorageStateStore,
} from 'oidc-client-ts';
import { type ReactNode, useState } from 'react';
import { AuthProvider, type AuthProviderProps } from 'react-oidc-context';

import { Account } from './Account';

function required(env: Record<string, string | undefined>, name: string): string {
  const value = env[name];
  if (value === undefined || value === '') {
    throw new Error(
      `${name} is not set. The browser app reads it from the repository's .env file — ` +
        `copy .env.example to .env at the repository root and fill in ${name}.`,
    );
  }
  return value;
}

/**
 * Builds the provider's settings from an environment. Throws, naming the variable, when one is missing:
 * an app that starts without knowing its issuer would fail on the first click with a far less useful
 * message.
 */
export function usersConfig(env: Record<string, string | undefined>): AuthProviderProps {
  const home = `${window.location.origin}/`;
  return {
    authority: required(env, 'VITE_USERS_ISSUER'),
    client_id: required(env, 'VITE_USERS_CLIENT_ID'),
    // Authorization Code flow. oidc-client-ts adds PKCE to it on its own; there is no switch to turn off.
    response_type: 'code',
    scope: 'openid profile email',
    // Keycloak sends the browser back here after both sign-in and sign-out. Both must be registered on the
    // client — locally the realm allows `http://localhost:5173/*`.
    redirect_uri: home,
    post_logout_redirect_uri: home,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: true,
    // After the redirect back, the address bar holds `?code=...&state=...`. Both have been used up by the
    // time this runs; leaving them there means a reload replays a spent code and shows an error.
    onSigninCallback: backToWhereSignInStarted,
  };
}

/** Where this page is, as somewhere a sign-in can bring a person back to. */
export function hereNow(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

/** A sign-in's `state` as a path on this origin, or null: one leading slash, never two, never a backslash. */
export function returnPath(state: unknown): string | null {
  if (typeof state !== 'string' || !state.startsWith('/')) return null;
  return state.startsWith('//') || state.includes('\\') ? null : state;
}

/**
 * After the redirect back: the spent code and state out of the address bar, and the person on the page
 * they signed in from. The router is told by the same event the browser's own back button sends.
 */
// biome-ignore lint/suspicious/noConfusingVoidType: react-oidc-context's `onSigninCallback` is typed `User | void`.
export function backToWhereSignInStarted(user?: User | void): void {
  const back = returnPath(user?.state) ?? window.location.pathname;
  window.history.replaceState({}, document.title, back);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

/** A manager whose every sign-in carries the page it started on, unless its caller says otherwise. */
export class ReturningUserManager extends UserManager {
  override signinRedirect(args: SigninRedirectArgs = {}): Promise<void> {
    return super.signinRedirect({ state: hereNow(), ...args });
  }
}

/**
 * Wraps the app in the sign-in context and puts the account controls in a header above it.
 *
 * The header lives here rather than in `App.tsx` on purpose: `useAuth()` throws when rendered outside an
 * `AuthProvider`, so keeping every consumer inside this component means `App` and its test never need to
 * know that sign-in exists.
 */
export function UsersProvider({ children }: { children: ReactNode }) {
  return (
    <AuthProvider userManager={useManager()} onSigninCallback={backToWhereSignInStarted}>
      <header>
        <Account />
      </header>
      {children}
    </AuthProvider>
  );
}

/** One manager for the life of the provider: a new one per render would lose the sign-in in flight. */
function useManager(): UserManager {
  const [manager] = useState(
    () => new ReturningUserManager(usersConfig(import.meta.env) as UserManagerSettings),
  );
  return manager;
}
