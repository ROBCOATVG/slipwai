package oidckeycloak_test

import (
	"errors"
	"strings"
	"testing"

	"example.com/delivery-starter/adapters/driving/http/auth/oidckeycloak"
)

var mapping = oidckeycloak.RoleMapping{
	"admin":    "app-admin",
	"operator": "app-operator",
	"viewer":   "app-viewer",
}

func TestGrantsOnlyTheRolesWhoseGroupsTheTokenCarries(t *testing.T) {
	roles := oidckeycloak.ResolveRoles([]string{"app-admin", "app-viewer"}, mapping)
	if strings.Join(roles, ",") != "admin,viewer" {
		t.Fatalf("roles are %v", roles)
	}
}

// A realm may be exported with full.path either way, and a project should not silently grant
// nobody anything because of it.
func TestAcceptsAFullPathGroupClaim(t *testing.T) {
	roles := oidckeycloak.ResolveRoles([]string{"/app-operator"}, mapping)
	if strings.Join(roles, ",") != "operator" {
		t.Fatalf("roles are %v", roles)
	}
}

func TestGrantsNothingForAGroupThatMapsToNoRole(t *testing.T) {
	if roles := oidckeycloak.ResolveRoles([]string{"some-other-group"}, mapping); len(roles) != 0 {
		t.Fatalf("roles are %v", roles)
	}
}

func TestRefusesAnIncompleteMappingRatherThanGrantingNothingSilently(t *testing.T) {
	broken := oidckeycloak.RoleMapping{"admin": "app-admin", "operator": "   "}
	err := oidckeycloak.AssertRoleMapping(broken)
	if err == nil || !strings.Contains(err.Error(), "incomplete for: operator") {
		t.Fatalf("error is %v", err)
	}
}

func TestRefusesAnEmptyMappingBecauseNoPrincipalCouldEverHoldARole(t *testing.T) {
	if err := oidckeycloak.AssertRoleMapping(oidckeycloak.RoleMapping{}); err == nil {
		t.Fatal("an empty mapping was accepted")
	}
}

func TestAcceptsACompleteMapping(t *testing.T) {
	if err := oidckeycloak.AssertRoleMapping(mapping); err != nil {
		t.Fatalf("a complete mapping was refused: %v", err)
	}
}

func TestTheFlowItselfRefusesRatherThanPretending(t *testing.T) {
	if _, err := oidckeycloak.Authenticate(); !errors.Is(err, oidckeycloak.ErrNotImplemented) {
		t.Fatalf("error is %v", err)
	}
}
