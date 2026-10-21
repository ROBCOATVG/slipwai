import { describe, expect, it } from 'vitest';

import { backToWhereSignInStarted, hereNow, returnPath, usersConfig } from '../../src/auth/users';

const env = {
  VITE_USERS_ISSUER: 'http://localhost:8081/realms/customers',
  VITE_USERS_CLIENT_ID: 'web',
};

describe('usersConfig', () => {
  it('points the client at the realm named in the environment', () => {
    const config = usersConfig(env);
    if (!('authority' in config)) throw new Error('expected settings, not a UserManager');

    expect(config.authority).toBe('http://localhost:8081/realms/customers');
    expect(config.client_id).toBe('web');
    expect(config.response_type).toBe('code');
    expect(config.scope).toBe('openid profile email');
  });

  it('sends the browser back to this origin after sign-in and sign-out', () => {
    const config = usersConfig(env);
    if (!('redirect_uri' in config)) throw new Error('expected settings, not a UserManager');

    expect(config.redirect_uri).toBe(`${window.location.origin}/`);
    expect(config.post_logout_redirect_uri).toBe(`${window.location.origin}/`);
  });

  it('keeps tokens in sessionStorage and renews them silently', async () => {
    const config = usersConfig(env);
    if (!('userStore' in config) || config.userStore === undefined) {
      throw new Error('expected an explicit userStore');
    }

    await config.userStore.set('probe', 'value');

    expect(window.sessionStorage.getItem('oidc.probe')).toBe('value');
    expect(window.localStorage.getItem('oidc.probe')).toBeNull();
    expect(config.automaticSilentRenew).toBe(true);
    window.sessionStorage.removeItem('oidc.probe');
  });

  it('strips the spent code and state from the address bar after sign-in', () => {
    const config = usersConfig(env);
    window.history.pushState({}, '', '/?code=spent&state=used');

    config.onSigninCallback?.(undefined);

    expect(window.location.search).toBe('');
    expect(window.location.pathname).toBe('/');
  });

  it('puts the person back on the page they signed in from', () => {
    window.history.pushState({}, '', '/?code=spent&state=used');

    backToWhereSignInStarted({ state: '/leaver-records/r-1?tab=facts' } as never);

    expect(`${window.location.pathname}${window.location.search}`).toBe(
      '/leaver-records/r-1?tab=facts',
    );
  });

  it('carries where this page is, and returns only to a path on this origin', () => {
    window.history.pushState({}, '', '/leaver-records/r-1?x=1#notes');
    expect(hereNow()).toBe('/leaver-records/r-1?x=1#notes');

    expect(returnPath('/leaver-records/r-1')).toBe('/leaver-records/r-1');
    for (const elsewhere of [
      '//evil.example/',
      'https://evil.example/',
      '/\\evil.example',
      '',
      42,
      undefined,
    ]) {
      expect(returnPath(elsewhere)).toBeNull();
    }
  });

  it.each(['VITE_USERS_ISSUER', 'VITE_USERS_CLIENT_ID'])(
    'fails at startup naming %s when it is missing',
    (name) => {
      const missing = { ...env, [name]: undefined };
      const empty = { ...env, [name]: '' };

      expect(() => usersConfig(missing)).toThrow(name);
      expect(() => usersConfig(missing)).toThrow('.env.example');
      expect(() => usersConfig(empty)).toThrow(name);
    },
  );
});
