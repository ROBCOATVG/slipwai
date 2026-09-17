package com.example.deliverystarter.adapters.driving.http.auth;

import io.quarkus.security.identity.AuthenticationRequestContext;
import io.quarkus.security.identity.SecurityIdentity;
import io.quarkus.security.identity.SecurityIdentityAugmentor;
import io.quarkus.security.runtime.QuarkusSecurityIdentity;
import io.smallrye.mutiny.Uni;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.eclipse.microprofile.config.inject.ConfigProperty;

/**
 * Where {@link KeycloakRoles} is applied: the framework's own hook for adding roles to an identity it has
 * already authenticated.
 *
 * <p>This is the seam, and it is worth being clear about which side of it does what. {@code quarkus-oidc} has
 * already run the whole protocol by the time this class is called — the identity it hands over is one whose
 * token was validated against the issuer's JWKS. This adds the application's roles to it, and nothing else.
 * Deciding what a role may *do* is not here either: authorisation belongs inside use cases, because a rule
 * enforced in a driving adapter is a rule the next entry point will not enforce.
 *
 * <p>Inert until {@code quarkus.oidc.tenant-enabled} is true, since nothing authenticates before then. That
 * is deliberate — it means the mapping is wired and tested from the first day rather than being written the
 * day it is first needed, which is the day it is least likely to be got right.
 */
@ApplicationScoped
public class KeycloakGroupRoleAugmentor implements SecurityIdentityAugmentor {

    /**
     * The claim the groups arrive in: {@code groups} from Keycloak's group-membership mapper, {@code
     * cognito:groups} from Cognito. Configuration ({@code OIDC_GROUPS_CLAIM}) rather than a constant, so the
     * same mapping serves the local stand-in and the production issuer.
     */
    private final String groupsClaim;

    private final KeycloakRoles roles;

    KeycloakGroupRoleAugmentor(
            @ConfigProperty(name = "app.oidc.groups-claim") String groupsClaim,
            @ConfigProperty(name = "app.oidc.group.admin") String admin,
            @ConfigProperty(name = "app.oidc.group.operator") String operator,
            @ConfigProperty(name = "app.oidc.group.viewer") String viewer) {
        this.groupsClaim = groupsClaim;
        this.roles = new KeycloakRoles(Map.of("admin", admin, "operator", operator, "viewer", viewer));
        // At construction rather than on the first request: a misconfigured environment should refuse to
        // start, not serve traffic that silently grants nobody anything.
        this.roles.assertComplete();
    }

    @Override
    public Uni<SecurityIdentity> augment(
            SecurityIdentity identity, AuthenticationRequestContext context) {
        if (identity.isAnonymous()) {
            return Uni.createFrom().item(identity);
        }
        List<String> granted = roles.resolve(groupsOf(identity, groupsClaim));
        if (granted.isEmpty()) {
            return Uni.createFrom().item(identity);
        }
        QuarkusSecurityIdentity.Builder builder = QuarkusSecurityIdentity.builder(identity);
        granted.forEach(builder::addRole);
        return Uni.createFrom().item(builder.build());
    }

    private static List<String> groupsOf(SecurityIdentity identity, String groupsClaim) {
        Object claim = identity.getAttribute(groupsClaim);
        List<String> groups = new ArrayList<>();
        if (claim instanceof Iterable<?> values) {
            values.forEach(value -> groups.add(String.valueOf(value)));
        } else if (claim != null) {
            groups.add(String.valueOf(claim));
        }
        return groups;
    }
}
