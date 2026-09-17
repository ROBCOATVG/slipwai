import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { User } from 'oidc-client-ts';
import { describe, expect, it } from 'vitest';

import { type AccountAuth, AccountView } from '../../src/auth/Account';

/**
 * A hand-written stand-in for the sign-in state react-oidc-context hands the component, with the two
 * redirects recording where they were asked to send the browser. No mocking framework: `AccountView`
 * takes `AccountAuth` as a prop precisely so a test can describe one state as a plain object, and a
 * fake that implements the contract survives a refactoring that a recorded call sequence would not.
 */
function signedInAs(state: Partial<AccountAuth> = {}) {
  const redirects: string[] = [];
  const auth: AccountAuth = {
    isLoading: false,
    isAuthenticated: false,
    signinRedirect: async () => {
      redirects.push('sign in');
    },
    signoutRedirect: async () => {
      redirects.push('sign out');
    },
    ...state,
  };
  return { auth, redirects };
}

// The claims every ID token from the realm carries; the tests add the ones about the person.
const claims = {
  iss: 'http://localhost:8081/realms/customers',
  sub: 'f1c4e2',
  aud: 'web',
  exp: 2_000_000_000,
  iat: 1_000_000_000,
};

function customer(profile: { name?: string; email?: string }) {
  return new User({
    access_token: 'opaque',
    token_type: 'Bearer',
    profile: { ...claims, ...profile },
  });
}

const ada = customer({ name: 'Ada Lovelace', email: 'ada@example.com' });

describe('Account', () => {
  it('offers to sign in when nobody is signed in', async () => {
    const { auth, redirects } = signedInAs();
    render(<AccountView auth={auth} />);

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(redirects).toEqual(['sign in']);
    expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument();
  });

  it('shows who is signed in and offers to sign out', async () => {
    const { auth, redirects } = signedInAs({ isAuthenticated: true, user: ada });
    render(<AccountView auth={auth} />);

    expect(screen.getByRole('navigation', { name: 'Account' })).toHaveTextContent('Ada Lovelace');
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(redirects).toEqual(['sign out']);
    expect(screen.queryByRole('button', { name: 'Sign in' })).not.toBeInTheDocument();
  });

  it('falls back to the email when the realm sent no name', () => {
    const { auth } = signedInAs({
      isAuthenticated: true,
      user: customer({ email: 'ada@example.com' }),
    });
    render(<AccountView auth={auth} />);

    expect(screen.getByRole('navigation', { name: 'Account' })).toHaveTextContent(
      'ada@example.com',
    );
  });

  it('reports that it is still checking while the library loads', () => {
    const { auth } = signedInAs({ isLoading: true });
    render(<AccountView auth={auth} />);

    expect(screen.getByRole('status')).toHaveTextContent('Checking');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('says where the browser is going while a redirect is in flight', () => {
    const { auth } = signedInAs({ activeNavigator: 'signinRedirect' });
    render(<AccountView auth={auth} />);

    expect(screen.getByRole('status')).toHaveTextContent('sign in');
  });

  it('shows the error and a way to try again when sign-in failed', async () => {
    const error = Object.assign(new Error('invalid_grant: Code not valid'), {
      source: 'signinCallback' as const,
    });
    const { auth, redirects } = signedInAs({ error });
    render(<AccountView auth={auth} />);

    expect(screen.getByRole('alert')).toHaveTextContent('invalid_grant: Code not valid');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(redirects).toEqual(['sign in']);
  });
});
