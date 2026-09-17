package userskeycloak_test

import (
	"errors"
	"testing"

	"example.com/delivery-starter/adapters/driving/http/users/userskeycloak"
)

const (
	customersIssuer = "http://localhost:8081/realms/customers"
	staffIssuer     = "http://localhost:8081/realms/app"
)

func verifiedCustomer() userskeycloak.Claims {
	return userskeycloak.Claims{
		"iss":            customersIssuer,
		"sub":            "a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34",
		"email":          "ada@example.com",
		"email_verified": true,
	}
}

func TestAcceptsAVerifiedCustomerOfTheExpectedRealm(t *testing.T) {
	customer, err := userskeycloak.CustomerFromClaims(verifiedCustomer(), customersIssuer)
	if err != nil {
		t.Fatalf("a verified customer was refused: %v", err)
	}
	want := userskeycloak.Customer{Subject: "a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34", Email: "ada@example.com"}
	if customer != want {
		t.Fatalf("customer is %+v", customer)
	}
}

// Both realms live in one Keycloak, so a staff token is a valid JWT whose issuer differs from a
// customer's by one path segment. It must never pass as a customer.
func TestRefusesTheStaffRealm(t *testing.T) {
	claims := verifiedCustomer()
	claims["iss"] = staffIssuer
	if _, err := userskeycloak.CustomerFromClaims(claims, customersIssuer); !errors.Is(err, userskeycloak.ErrWrongIssuer) {
		t.Fatalf("error is %v", err)
	}
}

func TestRefusesATokenWithNoSubjectBecauseNothingElseIsAStableKey(t *testing.T) {
	claims := verifiedCustomer()
	claims["sub"] = ""
	if _, err := userskeycloak.CustomerFromClaims(claims, customersIssuer); !errors.Is(err, userskeycloak.ErrNoSubject) {
		t.Fatalf("error is %v", err)
	}
}

func TestRefusesAnUnverifiedEmailBecauseItIsOneAnybodyCanType(t *testing.T) {
	claims := verifiedCustomer()
	claims["email_verified"] = false
	if _, err := userskeycloak.CustomerFromClaims(claims, customersIssuer); !errors.Is(err, userskeycloak.ErrEmailUnverified) {
		t.Fatalf("error is %v", err)
	}
}

func TestTheTokenValidationItselfRefusesRatherThanPretending(t *testing.T) {
	if _, err := userskeycloak.Authenticate("any.bearer.token"); !errors.Is(err, userskeycloak.ErrNotImplemented) {
		t.Fatalf("error is %v", err)
	}
}
