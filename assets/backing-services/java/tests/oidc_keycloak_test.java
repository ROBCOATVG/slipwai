package com.example.deliverystarter.adapters.driving.http.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The mapping, tested with no provider running and no framework booted.
 *
 * <p>That is the point of keeping the decision pure and the wiring in a separate class: every rule below is
 * about which group grants which role, and none of it needs a token, an issuer, or a container.
 */
class KeycloakRolesTest {

    private static final Map<String, String> MAPPING =
            Map.of("admin", "app-admin", "operator", "app-operator", "viewer", "app-viewer");

    @Test
    void grantsOnlyTheRolesWhoseGroupsTheTokenCarries() {
        assertThat(new KeycloakRoles(MAPPING).resolve(List.of("app-admin", "app-viewer")))
                .containsExactly("admin", "viewer");
    }

    /**
     * A realm may be exported with full.path either way, and a project should not silently grant nobody
     * anything because of it.
     */
    @Test
    void acceptsAFullPathGroupClaim() {
        assertThat(new KeycloakRoles(MAPPING).resolve(List.of("/app-operator")))
                .containsExactly("operator");
    }

    @Test
    void grantsNothingForAGroupThatMapsToNoRole() {
        assertThat(new KeycloakRoles(MAPPING).resolve(List.of("some-other-group"))).isEmpty();
    }

    @Test
    void grantsNothingForATokenWithNoGroupsAtAll() {
        assertThat(new KeycloakRoles(MAPPING).resolve(List.of())).isEmpty();
    }

    @Test
    void refusesAnIncompleteMappingRatherThanGrantingNothingSilently() {
        Map<String, String> broken = new HashMap<>();
        broken.put("admin", "app-admin");
        broken.put("operator", "   ");

        assertThatThrownBy(() -> new KeycloakRoles(broken).assertComplete())
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("incomplete for: operator");
    }

    @Test
    void refusesAnEmptyMappingBecauseNoPrincipalCouldEverHoldARole() {
        assertThatThrownBy(() -> new KeycloakRoles(Map.of()).assertComplete())
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void acceptsACompleteMapping() {
        KeycloakRoles complete = new KeycloakRoles(MAPPING);

        complete.assertComplete();

        assertThat(complete.roles()).containsExactlyInAnyOrder("admin", "operator", "viewer");
    }
}
