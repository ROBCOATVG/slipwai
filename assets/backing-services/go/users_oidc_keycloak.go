// Package userskeycloak is a PLACEHOLDER — it is NOT a working token validator.
//
// Selecting Keycloak for the product's own users wires a second realm, customers, into the same
// Keycloak container as the staff realm app, plus the environment variables that name it. The
// token validation is deliberately not written here.
//
// The browser app (apps/web) performs the login — Authorization Code flow with PKCE, through
// react-oidc-context — and sends the access token as a bearer token. This service is a resource
// server for the customers realm: it validates that token on every request before trusting a
// byte of it. Before implementing, load skills/secure-oauth-oidc/SKILL.md — it covers what this
// package must get right and what silently breaks if it does not:
//
//   - Signature against the issuer's JWKS, found through the discovery document at
//     USERS_OIDC_ISSUER.
//   - exp: an expired token is one somebody may have lost.
//   - aud containing USERS_OIDC_AUDIENCE, so a token minted for another client is not accepted
//     here.
//   - iss exactly USERS_OIDC_ISSUER. See the mix-up hazard below.
//
// Use a maintained JWT/JWKS library rather than hand-rolling these checks.
//
// What this package owns: turning a validated token's claims into a Customer the domain can key
// on, in CustomerFromClaims. It is pure, so it is testable without a provider, and it is the one
// place these rules live:
//
//   - iss must be exactly the expected issuer.
//   - sub must be present. It is the only stable key a customer has; email addresses change.
//   - email_verified must be exactly true, because an unverified address is one anybody can type.
//
// What this package does not own: customers have no groups and no roles. Whether a customer may
// see an order is a question of ownership or tenancy, and it is decided in the use case that
// loads the order, against the Customer it is handed — not here, and not by anything in the
// token.
//
// The mix-up hazard worth knowing about now: both realms live in one Keycloak, so a staff token
// is a perfectly valid JWT, signed by the same server, whose issuer differs from a customer's by
// one path segment: /realms/app against /realms/customers. A resource server that checks the
// signature but not the issuer would accept a staff member as a customer. CustomerFromClaims
// refuses any issuer that is not exactly the expected one, and its test uses the staff realm's
// issuer on purpose. A staff token must never pass as a customer.
//
// The realm fixture is docker/keycloak/realms/customers.json; the staff one is
// docker/keycloak/realms/app.json. Locally the issuer is http://localhost:8081/realms/customers
// and the audience api; both are set in .env.example.
package userskeycloak

import (
	"errors"
	"fmt"
	"strings"
)

// Claims are the claims of a token that has already been validated. Untyped values, because a
// token carries what it likes.
type Claims map[string]any

// Customer is who the caller is, once a real validation has established it. Subject is the key;
// Email is for showing and for contacting.
type Customer struct {
	Subject string
	Email   string
}

// The reasons CustomerFromClaims refuses, so a transport can tell them apart with errors.Is.
var (
	ErrWrongIssuer     = errors.New("token issuer is not the customers realm")
	ErrNoSubject       = errors.New("token has no sub claim, and sub is the only stable key a customer has")
	ErrEmailUnverified = errors.New("token does not carry a verified email address; an unverified address is one anybody can type")
)

// ErrNotImplemented is returned by the unwritten validation.
//
// A placeholder that returned a Customer would be worse than one that refuses: every use case
// downstream would pass in tests against a customer nobody authenticated.
var ErrNotImplemented = errors.New(
	"customer token validation not implemented; see the guidance in this package and the secure-oauth-oidc skill")

// CustomerFromClaims turns a validated token's claims into a Customer, or refuses. Pure, so it is
// testable without a provider. The caller has already checked signature, exp and aud; this is
// what remains.
func CustomerFromClaims(claims Claims, expectedIssuer string) (Customer, error) {
	if issuer, _ := claims["iss"].(string); issuer != expectedIssuer {
		return Customer{}, fmt.Errorf("%w: %q is not %q; the staff realm lives in the same Keycloak, "+
			"and its tokens must never pass as a customer", ErrWrongIssuer, issuer, expectedIssuer)
	}
	subject, _ := claims["sub"].(string)
	if strings.TrimSpace(subject) == "" {
		return Customer{}, ErrNoSubject
	}
	verified, _ := claims["email_verified"].(bool)
	email, _ := claims["email"].(string)
	if !verified || strings.TrimSpace(email) == "" {
		return Customer{}, ErrEmailUnverified
	}
	return Customer{Subject: subject, Email: email}, nil
}

// Authenticate is the unwritten validation: check the bearer token's signature, exp and aud, then
// hand its claims to CustomerFromClaims.
func Authenticate(bearerToken string) (Customer, error) {
	return Customer{}, ErrNotImplemented
}
