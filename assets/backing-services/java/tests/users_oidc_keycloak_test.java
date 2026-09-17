package com.example.deliverystarter.adapters.driving.http.users;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The rules, tested with no provider running and no framework booted.
 *
 * <p>That is the point of keeping them pure and the wiring in a separate class: every rule below is about
 * which claims make a customer, and none of it needs a signed token, an issuer, or a container.
 */
class CustomerIdentityTest {

    private static final String CUSTOMERS = "http://localhost:8081/realms/customers";
    private static final String STAFF = "http://localhost:8081/realms/app";

    @Test
    void acceptsAVerifiedCustomerFromTheCustomersRealm() {
        CustomerIdentity customer = CustomerIdentity.fromClaims(verified(), CUSTOMERS);

        assertThat(customer.subject()).isEqualTo("3f1c9c2e-0d7e-4c1a-9a1e-2b6e2f0c7d11");
        assertThat(customer.email()).isEqualTo("ada@example.com");
    }

    /**
     * The mix-up defence. Both realms live in one Keycloak, so a staff token is a valid JWT from the same
     * host whose issuer differs by one path segment — and it is not a customer.
     */
    @Test
    void refusesATokenFromTheStaffRealm() {
        Map<String, Object> claims = verified();
        claims.put("iss", STAFF);

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("not the customers realm");
    }

    /** Exactly, not by prefix: an issuer with a trailing slash is a different issuer. */
    @Test
    void refusesAnIssuerThatMerelyStartsWithTheExpectedOne() {
        Map<String, Object> claims = verified();
        claims.put("iss", CUSTOMERS + "/");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("not the customers realm");
    }

    @Test
    void refusesATokenWithNoIssuer() {
        Map<String, Object> claims = verified();
        claims.remove("iss");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("not the customers realm");
    }

    @Test
    void refusesATokenWithNoSubject() {
        Map<String, Object> claims = verified();
        claims.remove("sub");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("no subject");
    }

    @Test
    void refusesABlankSubject() {
        Map<String, Object> claims = verified();
        claims.put("sub", "   ");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("no subject");
    }

    @Test
    void refusesAnUnverifiedEmail() {
        Map<String, Object> claims = verified();
        claims.put("email_verified", false);

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("email_verified is false");
    }

    @Test
    void refusesAMissingVerifiedFlag() {
        Map<String, Object> claims = verified();
        claims.remove("email_verified");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("email_verified is absent");
    }

    /** The boolean, not a string that spells it: a realm exporting "true" is not what this project expects. */
    @Test
    void refusesAVerifiedFlagThatIsTheStringTrue() {
        Map<String, Object> claims = verified();
        claims.put("email_verified", "true");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("the string \"true\"");
    }

    @Test
    void refusesAVerifiedFlagWithNoEmailToVerify() {
        Map<String, Object> claims = verified();
        claims.remove("email");

        assertThatThrownBy(() -> CustomerIdentity.fromClaims(claims, CUSTOMERS))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("carries no email");
    }

    /** The claims a token from the local `customers` realm fixture carries, as a mutable map to break. */
    private static Map<String, Object> verified() {
        Map<String, Object> claims = new HashMap<>();
        claims.put("iss", CUSTOMERS);
        claims.put("sub", "3f1c9c2e-0d7e-4c1a-9a1e-2b6e2f0c7d11");
        claims.put("email", "ada@example.com");
        claims.put("email_verified", true);
        claims.put("aud", "api");
        return claims;
    }
}
