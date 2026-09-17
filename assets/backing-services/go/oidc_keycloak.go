// Package oidckeycloak is a PLACEHOLDER — it is NOT a working OIDC client.
//
// Selecting Keycloak wires the container, the environment variables, and the group-to-role
// mapping. The protocol flow is deliberately not written here.
//
// OIDC is one of the few places where writing it yourself from memory is a bad idea. Before
// implementing, load skills/secure-oauth-oidc/SKILL.md — it covers what this package must get
// right and what silently breaks if it does not:
//
//   - Authorization Code flow with PKCE. Never the implicit grant.
//   - `state` bound to the session (CSRF) and `nonce` bound to the ID token (replay).
//   - Full ID-token validation: signature against the issuer's JWKS, iss, aud, exp, nonce.
//   - Exact redirect-URI registration; no wildcards.
//   - Mix-up defence when more than one issuer is possible.
//
// Use a maintained OIDC client library rather than hand-rolling these checks.
//
// The parity hazard worth knowing about now: group-to-role mapping is where this breaks in the
// least helpful way. Groups that exist in staging but not production produce an authorisation
// model that passes every test and fails in production. Assert the mapping at startup, with
// AssertRoleMapping, so a misconfigured environment refuses to boot instead of misbehaving under
// load.
//
// Roles are yours to name. Nothing here prescribes a role set, because an authorisation model is
// a product decision. When the flow is written, read the groups from the claim named by
// OIDC_GROUPS_CLAIM rather than from a literal: Keycloak's group-membership mapper writes "groups",
// Cognito writes "cognito:groups", and the one mapping here serves both.
//
// The three group names in docker/keycloak/realms/app.json and in
// .env.example are the local fixture those values are checked against, not a prescription.
package oidckeycloak

import (
	"errors"
	"fmt"
	"sort"
	"strings"
)

// RoleMapping maps an application role to the provider group that grants it.
type RoleMapping map[string]string

// Principal is who the caller is, once a real flow has established it.
type Principal struct {
	Subject string
	Roles   []string
}

// ErrNotImplemented is returned by the unwritten flow.
//
// A placeholder that returned a Principal would be worse than one that refuses: every downstream
// authorisation check would pass in tests and grant nothing in production.
var ErrNotImplemented = errors.New(
	"OIDC flow not implemented; see the guidance in this package and the secure-oauth-oidc skill")

// AssertRoleMapping checks every configured role has a group, at startup. Called by the
// composition root.
//
// Fails loudly rather than granting nothing silently: a mapping assembled from environment
// variables at runtime may be missing an entry, and a missing group grants nothing while looking
// identical to a permissions bug.
func AssertRoleMapping(mapping RoleMapping) error {
	if len(mapping) == 0 {
		return errors.New("OIDC group mapping is empty, so no principal can ever hold a role; " +
			"declare the roles this product has before wiring the provider")
	}
	var missing []string
	for role, group := range mapping {
		if strings.TrimSpace(group) == "" {
			missing = append(missing, role)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return fmt.Errorf("OIDC group mapping incomplete for: %s. A missing group grants nothing "+
			"and looks identical to a permissions bug at runtime", strings.Join(missing, ", "))
	}
	return nil
}

// ResolveRoles maps provider group claims to application roles. Pure, so it is testable without a
// provider. The result is sorted, so a caller cannot come to depend on map iteration order.
func ResolveRoles(groupClaims []string, mapping RoleMapping) []string {
	// Keycloak's group-membership mapper emits "/app-admin" when full.path is true and
	// "app-admin" when it is false. Accepting both means a realm exported with the other setting
	// does not silently grant nobody anything.
	claims := make(map[string]bool, len(groupClaims))
	for _, claim := range groupClaims {
		claims[strings.TrimPrefix(claim, "/")] = true
	}

	var roles []string
	for role, group := range mapping {
		if claims[group] {
			roles = append(roles, role)
		}
	}
	sort.Strings(roles)
	return roles
}

// Authenticate is the unwritten flow.
func Authenticate() (Principal, error) {
	return Principal{}, ErrNotImplemented
}
