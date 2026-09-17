/**
 * The account corner of the page: who is signed in, and the button to change that.
 *
 * Everything here comes from `useAuth()`, the hook react-oidc-context provides inside `UsersProvider`.
 * The two buttons only ask the library to start a redirect — `signinRedirect()` sends the browser to
 * Keycloak's login page, `signoutRedirect()` to its logout endpoint — and the library does the rest of the
 * Authorization Code + PKCE flow (verifier, `state`, `nonce`, ID-token validation) before and after the
 * round trip. Nothing about the protocol belongs in this component; `skills/secure-oauth-oidc/SKILL.md`
 * covers what it would have to get right if it ever tried.
 *
 * The name shown is the ID token's `name`, then `preferred_username`, then `email` — whichever the realm
 * filled in first. Tokens sit in `sessionStorage`, so the name survives a reload and disappears when the
 * tab closes; see `users.tsx` for that decision.
 *
 * Real `<button>`s and landmark roles, so the controls work from a keyboard and are announced properly.
 *
 * ── Why this is two components ────────────────────────────────────────────────────────────────────────
 * `AccountView` takes the sign-in state as a prop and `Account` is the one line of wiring that reads it
 * from the hook. That seam is what lets the tests drive every state — loading, signed in, redirecting,
 * failed — with a plain object they write themselves, rather than replacing the `react-oidc-context`
 * module with a mocking framework. A seam in the code beats a mock in the test; the `finding-seams` and
 * `testing` skills say why, and nothing in this repository adds a mocking framework to make a test
 * possible.
 */
import { type AuthContextProps, useAuth } from 'react-oidc-context';

/**
 * The part of the sign-in context this corner of the page reads — narrow on purpose, because it is the
 * contract a test has to satisfy, so widening it is a deliberate act and not an accident of `useAuth()`.
 */
export type AccountAuth = Pick<
  AuthContextProps,
  | 'isLoading'
  | 'isAuthenticated'
  | 'activeNavigator'
  | 'error'
  | 'user'
  | 'signinRedirect'
  | 'signoutRedirect'
>;

export function AccountView({ auth }: { auth: AccountAuth }) {
  if (auth.activeNavigator === 'signinRedirect') {
    return <p role="status">Taking you to sign in…</p>;
  }
  if (auth.activeNavigator === 'signoutRedirect') {
    return <p role="status">Signing you out…</p>;
  }
  if (auth.isLoading) {
    return <p role="status">Checking whether you are signed in…</p>;
  }

  if (auth.error !== undefined) {
    return (
      <>
        <p role="alert">Sign-in failed: {auth.error.message}</p>
        <button type="button" onClick={() => void auth.signinRedirect()}>
          Sign in
        </button>
      </>
    );
  }

  if (auth.isAuthenticated && auth.user != null) {
    const profile = auth.user.profile;
    const shownAs = profile.name ?? profile.preferred_username ?? profile.email ?? 'Signed in';
    return (
      <nav aria-label="Account">
        <span>{shownAs}</span>{' '}
        <button type="button" onClick={() => void auth.signoutRedirect()}>
          Sign out
        </button>
      </nav>
    );
  }

  return (
    <nav aria-label="Account">
      <button type="button" onClick={() => void auth.signinRedirect()}>
        Sign in
      </button>
    </nav>
  );
}

export function Account() {
  return <AccountView auth={useAuth()} />;
}
