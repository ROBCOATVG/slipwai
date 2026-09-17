package com.example.deliverystarter.adapters.driving.http.users;

import io.quarkus.security.identity.SecurityIdentity;
import jakarta.enterprise.context.RequestScoped;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.jwt.JsonWebToken;

/**
 * Where {@link CustomerIdentity} is applied: the customer on the current request, read from the identity the
 * framework has already authenticated.
 *
 * <p>This is the seam, and it is worth being clear about which side of it does what. {@code quarkus-oidc}'s
 * {@code customers} tenant has already run the whole protocol by the time this class is asked anything — the
 * bearer token was validated against the customers realm's JWKS, and its {@code iss}, {@code aud} and
 * {@code exp} were checked. The principal it leaves on the {@link SecurityIdentity} is the token itself, so
 * this class reads four claims from it and hands them to {@link CustomerIdentity#fromClaims}, and nothing
 * else. Deciding what a customer may *do* is not here either: ownership is a use-case decision, because a
 * rule enforced in a driving adapter is a rule the next entry point will not enforce.
 *
 * <p>Inert until {@code quarkus.oidc.customers.tenant-enabled} is true, since nothing under
 * {@code /api/customers/*} authenticates before then and {@link #require} refuses an anonymous request. That
 * is deliberate — it means the customer rules are wired and tested from the first day rather than being
 * written the day they are first needed, which is the day they are least likely to be got right.
 *
 * <p>Request scoped because the identity it reads is. Inject it into a resource and call {@link #require}
 * inside the handler; a resource that does so on a path outside the tenant's routes gets a refusal, not a
 * staff member wearing a customer's hat.
 */
@RequestScoped
public class CurrentCustomer {

    private static final List<String> CLAIMS = List.of(
            CustomerIdentity.ISSUER,
            CustomerIdentity.SUBJECT,
            CustomerIdentity.EMAIL,
            CustomerIdentity.EMAIL_VERIFIED);

    private final SecurityIdentity identity;
    private final String issuer;

    CurrentCustomer(
            SecurityIdentity identity, @ConfigProperty(name = "app.users.oidc.issuer") String issuer) {
        this.identity = identity;
        this.issuer = issuer;
    }

    /**
     * The customer this request was made by.
     *
     * @throws IllegalStateException when nobody is authenticated on this request, or the principal is not a
     *     JWT — an opaque token verified by introspection carries no claims to read, and this project does
     *     not configure one
     * @throws IllegalArgumentException from {@link CustomerIdentity#fromClaims}, naming the rule the token
     *     broke; a staff token reaching this call fails the issuer rule, which is the point
     */
    public CustomerIdentity require() {
        if (identity.isAnonymous()) {
            throw new IllegalStateException(
                    "no customer is authenticated on this request; is the route under the customers "
                            + "tenant's paths, and is quarkus.oidc.customers.tenant-enabled true?");
        }
        if (!(identity.getPrincipal() instanceof JsonWebToken token)) {
            throw new IllegalStateException(
                    "the authenticated principal is not a JWT, so it carries no claims to read a customer "
                            + "from; the customers tenant expects bearer JWTs, not introspected tokens");
        }
        Map<String, Object> claims = new HashMap<>();
        for (String name : CLAIMS) {
            Object value = token.getClaim(name);
            if (value != null) {
                claims.put(name, value);
            }
        }
        return CustomerIdentity.fromClaims(claims, issuer);
    }
}
