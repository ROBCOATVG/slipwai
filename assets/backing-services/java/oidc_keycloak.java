package com.example.deliverystarter.adapters.driving.http.auth;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;

/**
 * Group-to-role mapping for the Keycloak realm — the part of staff identity this project actually owns.
 *
 * <p><strong>The protocol flow is not here, and must never be.</strong> {@code quarkus-oidc} performs the
 * Authorization Code flow with PKCE, binds {@code state} to the session and {@code nonce} to the ID token,
 * retrieves the issuer's JWKS and validates the token's signature, {@code iss}, {@code aud}, {@code exp} and
 * {@code nonce}. Hand-rolling any of that is a security defect rather than a style choice, which is why the
 * extension is a dependency and the flow is nobody's code in this repository. It is configured in
 * {@code application.properties} and disabled until a route needs a principal; read
 * {@code skills/secure-oauth-oidc/SKILL.md} before enabling it.
 *
 * <p>What is left over is this: which realm group grants which application role. That is a product decision
 * and nothing outside this project can make it, which is also why it is the part that breaks in the least
 * helpful way. Groups that exist in staging but not production produce an authorisation model that passes
 * every test and grants nothing in production — identical, from the outside, to a permissions bug. So
 * {@link #assertComplete} exists to be called from a startup observer, and to refuse to boot rather than
 * misbehave under load.
 *
 * <p>Roles are yours to name. Nothing here prescribes a role set: the three group names in
 * {@code docker/keycloak/realms/app.json} and in {@code .env.example} are the local fixture these values are
 * checked against, not a prescription.
 *
 * <p>Where the mapping gets applied is {@link KeycloakGroupRoleAugmentor}. Keeping the decision pure and the
 * wiring separate is what lets every rule below be tested with no provider running.
 */
public final class KeycloakRoles {

    private final Map<String, String> groupByRole;

    /**
     * @param groupByRole application role to the realm group that grants it
     */
    public KeycloakRoles(Map<String, String> groupByRole) {
        this.groupByRole = Collections.unmodifiableMap(new LinkedHashMap<>(groupByRole));
    }

    /**
     * The application roles a token's group claims grant, sorted.
     *
     * <p>Sorted so no caller can come to depend on map iteration order, and pure so it is testable without a
     * provider.
     */
    public List<String> resolve(List<String> groupClaims) {
        // Keycloak's group-membership mapper emits "/app-admin" when full.path is true and "app-admin" when
        // it is false. Accepting both means a realm exported with the other setting does not silently grant
        // nobody anything.
        List<String> claimed = new ArrayList<>();
        for (String claim : groupClaims) {
            claimed.add(claim.startsWith("/") ? claim.substring(1) : claim);
        }
        SortedSet<String> roles = new TreeSet<>();
        groupByRole.forEach((role, group) -> {
            if (claimed.contains(group)) {
                roles.add(role);
            }
        });
        return List.copyOf(roles);
    }

    /**
     * Check every configured role has a group, at startup.
     *
     * @throws IllegalStateException naming the roles with no group. Loud rather than silent: a mapping
     *     assembled from environment variables at runtime may be missing an entry, and a missing group
     *     grants nothing while looking identical to a permissions bug.
     */
    public void assertComplete() {
        if (groupByRole.isEmpty()) {
            throw new IllegalStateException(
                    "OIDC group mapping is empty, so no principal can ever hold a role; declare the roles "
                            + "this product has before wiring the provider");
        }
        Set<String> missing = new TreeSet<>();
        groupByRole.forEach((role, group) -> {
            if (group == null || group.isBlank()) {
                missing.add(role);
            }
        });
        if (!missing.isEmpty()) {
            throw new IllegalStateException("OIDC group mapping incomplete for: "
                    + String.join(", ", missing)
                    + ". A missing group grants nothing and looks identical to a permissions bug at runtime");
        }
    }

    /** The roles this mapping knows about, for a startup log line or a diagnostic endpoint. */
    public List<String> roles() {
        return List.copyOf(groupByRole.keySet());
    }
}
