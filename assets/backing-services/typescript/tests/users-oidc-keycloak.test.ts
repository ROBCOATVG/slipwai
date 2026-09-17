import { describe, expect, it } from 'vitest';

import {
  type Claims,
  customerFromClaims,
  notImplemented,
} from '../../src/adapters/driving/http/users/oidc-keycloak.js';

const customersIssuer = 'http://localhost:8081/realms/customers';
const staffIssuer = 'http://localhost:8081/realms/app';

const verifiedCustomer: Claims = {
  iss: customersIssuer,
  sub: 'a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34',
  email: 'ada@example.com',
  email_verified: true,
};

describe('a customer from validated claims', () => {
  it('accepts a verified customer of the expected realm', () => {
    expect(customerFromClaims(verifiedCustomer, customersIssuer)).toEqual({
      subject: 'a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34',
      email: 'ada@example.com',
    });
  });

  it('refuses the staff realm, whose issuer differs by one path segment', () => {
    expect(() =>
      customerFromClaims({ ...verifiedCustomer, iss: staffIssuer }, customersIssuer),
    ).toThrow(/is not http:\/\/localhost:8081\/realms\/customers/);
  });

  it('refuses a token with no subject, because nothing else is a stable key', () => {
    expect(() => customerFromClaims({ ...verifiedCustomer, sub: '' }, customersIssuer)).toThrow(
      /no sub claim/,
    );
  });

  it('refuses an unverified email, because it is one anybody can type', () => {
    expect(() =>
      customerFromClaims({ ...verifiedCustomer, email_verified: false }, customersIssuer),
    ).toThrow(/verified email/);
  });
});

describe('the token validation itself', () => {
  it('is a placeholder that refuses to pretend otherwise', () => {
    expect(() => notImplemented()).toThrow(/not implemented/);
  });
});
