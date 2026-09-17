/**
 * ⚠️  PLACEHOLDER — this is NOT a working token validator.
 *
 * Selecting Keycloak for the product's own users wires a second realm, `customers`, into the same
 * Keycloak container as the staff realm `app`, plus the environment variables that name it. The token
 * validation is deliberately not written here.
 *
 * The browser app (`apps/web`) performs the login — Authorization Code flow with PKCE, through
 * react-oidc-context — and sends the access token as a bearer token. This service is a resource server
 * for the `customers` realm: it validates that token on every request before trusting a byte of it.
 * Before implementing, load `skills/secure-oauth-oidc/SKILL.md` — it covers what this file must get
 * right and what silently breaks if it does not:
 *
 *   - Signature against the issuer's JWKS, found through the discovery document at `USERS_OIDC_ISSUER`.
 *   - `exp`: an expired token is one somebody may have lost.
 *   - `aud` containing `USERS_OIDC_AUDIENCE`, so a token minted for another client is not accepted here.
 *   - `iss` exactly `USERS_OIDC_ISSUER`. See the mix-up hazard below.
 *
 * Use a maintained JWT/JWKS library rather than hand-rolling these checks.
 *
 * ── What this file owns ───────────────────────────────────────────────────────────────────────────────
 * Turning a validated token's claims into a `Customer` the domain can key on: `customerFromClaims`
 * below. It is pure, so it is testable without a provider, and it is the one place these rules live:
 *
 *   - `iss` must be exactly the expected issuer.
 *   - `sub` must be present. It is the only stable key a customer has; email addresses change.
 *   - `email_verified` must be exactly `true`, because an unverified address is one anybody can type.
 *
 * ── What this file does not own ───────────────────────────────────────────────────────────────────────
 * Customers have no groups and no roles. Whether a customer may see an order is a question of ownership
 * or tenancy, and it is decided in the use case that loads the order, against the `Customer` it is
 * handed — not here, and not by anything in the token.
 *
 * ── The mix-up hazard worth knowing about now ─────────────────────────────────────────────────────────
 * Both realms live in one Keycloak, so a staff token is a perfectly valid JWT, signed by the same server,
 * whose issuer differs from a customer's by one path segment: `/realms/app` against `/realms/customers`.
 * A resource server that checks the signature but not the issuer would accept a staff member as a
 * customer. `customerFromClaims` refuses any issuer that is not exactly the expected one, and its test
 * uses the staff realm's issuer on purpose. A staff token must never pass as a customer.
 *
 * The realm fixture is `docker/keycloak/realms/customers.json`; the staff one is
 * `docker/keycloak/realms/app.json`. Locally the issuer is `http://localhost:8081/realms/customers` and
 * the audience `api`; both are set in `.env.example`.
 */

/** The claims of a token that has already been validated. Unknown, because a token carries what it likes. */
export type Claims = Readonly<Record<string, unknown>>;

/** A customer the domain can key on. `subject` is the key; `email` is for showing and for contacting. */
export type Customer = {
  readonly subject: string;
  readonly email: string;
};

/**
 * Turn a validated token's claims into a `Customer`, or throw. Pure, so it is testable without a
 * provider. The caller has already checked signature, `exp` and `aud`; this is what remains.
 */
export function customerFromClaims(claims: Claims, expectedIssuer: string): Customer {
  if (claims.iss !== expectedIssuer) {
    throw new Error(
      `Token issuer ${String(claims.iss)} is not ${expectedIssuer}. ` +
        'The staff realm lives in the same Keycloak, and its tokens must never pass as a customer.',
    );
  }
  const subject = claims.sub;
  if (typeof subject !== 'string' || subject.trim().length === 0) {
    throw new Error('Token has no sub claim, and sub is the only stable key a customer has.');
  }
  const email = claims.email;
  if (claims.email_verified !== true || typeof email !== 'string' || email.trim().length === 0) {
    throw new Error(
      'Token does not carry a verified email address. An unverified address is one anybody can type.',
    );
  }
  return { subject, email };
}

export function notImplemented(): never {
  throw new Error(
    'Customer token validation not implemented. See the guidance at the top of this file and the ' +
      'secure-oauth-oidc skill.',
  );
}
