package com.example.deliverystarter.adapters.driving.http.users;

import java.util.Map;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

/**
 * Who a customer is, read from the claims of a token the framework has already validated — the part of
 * customer identity this project actually owns.
 *
 * <p><strong>The protocol flow is not here, and must never be.</strong> The browser app performs the
 * Authorization Code flow with PKCE against the {@code customers} realm and sends the access token as a
 * bearer token; the framework ({@code quarkus-oidc}, or Spring Security's resource server) retrieves the
 * realm's JWKS and validates the token's signature, {@code iss}, {@code aud} and {@code exp}. Hand-rolling
 * any of that is a security defect rather than a style choice, which is why it is nobody's code in this
 * repository. It is configured in {@code application.properties} and off until a route needs a customer;
 * read {@code skills/secure-oauth-oidc/SKILL.md} before turning it on.
 *
 * <p>What is left over is turning a validated token into something the domain can key on, and three rules
 * the framework's validation does not make for you:
 *
 * <ul>
 *   <li><strong>The issuer is the customers realm, exactly.</strong> Staff and customers are two realms in
 *       one Keycloak, so a staff token is a perfectly valid JWT from the same host whose issuer differs from
 *       a customer's by one path segment. The framework checks the issuer too; this check is here so the
 *       guarantee lives in code this project owns and tests, and survives the day someone points both
 *       realms at one tenant or one shared JWKS in configuration.
 *   <li><strong>There is a subject.</strong> {@code sub} is the identifier Keycloak keeps stable for the
 *       life of the account. An email address is something a customer can change; the domain keys on the
 *       subject, never the address.
 *   <li><strong>The email is verified, and the flag is the boolean {@code true}.</strong> An unverified
 *       address is whatever the customer typed at sign-up, and a claim that is the string {@code "true"} is
 *       a realm exporting something other than what this project expects — both are refused rather than
 *       coerced.
 * </ul>
 *
 * <p>No groups and no roles: customers are all one kind of principal. Whether <em>this</em> customer may see
 * <em>that</em> order is ownership, and ownership is decided inside use cases — a rule enforced in a
 * driving adapter is a rule the next entry point will not enforce.
 *
 * <p>Where this gets applied is the framework's own hook ({@code CurrentCustomer} on Quarkus,
 * {@code CustomerSecurityConfig} on Spring). Keeping the rules pure and the wiring separate is what lets
 * every one of them be tested with no provider running.
 *
 * @param subject the realm's stable identifier for the account, from {@code sub}
 * @param email the verified address, from {@code email}
 */
public record CustomerIdentity(String subject, String email) {

    /** The claim names read by {@link #fromClaims}, as one place to look when a realm renames one. */
    static final String ISSUER = "iss";
    static final String SUBJECT = "sub";
    static final String EMAIL = "email";
    static final String EMAIL_VERIFIED = "email_verified";

    /**
     * @throws IllegalArgumentException when either value is blank; the factory below is where a token gets
     *     to this constructor, and it has already said which rule failed
     */
    public CustomerIdentity {
        if (subject.isBlank()) {
            throw new IllegalArgumentException("a customer needs a non-blank subject");
        }
        if (email.isBlank()) {
            throw new IllegalArgumentException("a customer needs a non-blank email");
        }
    }

    /**
     * The customer a validated token's claims describe, or a refusal saying which rule failed.
     *
     * <p>Pure, so it is testable without a provider: the claims arrive as the plain map every framework can
     * produce from its own token type, and the expected issuer arrives as the configured string rather than
     * being looked up here.
     *
     * @param claims the validated token's claims, as the framework exposes them
     * @param expectedIssuer the customers realm's issuer, exactly as configured
     * @throws IllegalArgumentException naming the rule a claim broke — the issuer is another realm's, the
     *     subject is missing, the email is unverified, or the verified flag has no address to verify
     */
    public static CustomerIdentity fromClaims(Map<String, Object> claims, String expectedIssuer) {
        String issuer = Objects.toString(claims.get(ISSUER), "");
        if (!expectedIssuer.equals(issuer)) {
            throw new IllegalArgumentException(
                    "token issuer is '" + issuer + "', not the customers realm '" + expectedIssuer
                            + "'; a token from another realm in the same Keycloak is not a customer");
        }
        String subject = Objects.toString(claims.get(SUBJECT), "");
        if (subject.isBlank()) {
            throw new IllegalArgumentException(
                    "token has no subject (sub), so there is no stable identity to key on");
        }
        Object verified = claims.get(EMAIL_VERIFIED);
        if (!Boolean.TRUE.equals(verified)) {
            throw new IllegalArgumentException(
                    "email_verified is " + describe(verified) + ", not the boolean true; an unverified "
                            + "address is whatever the customer typed at sign-up");
        }
        String email = Objects.toString(claims.get(EMAIL), "");
        if (email.isBlank()) {
            throw new IllegalArgumentException(
                    "email_verified is true but the token carries no email; the realm's client scopes are "
                            + "not releasing the address");
        }
        return new CustomerIdentity(subject, email);
    }

    private static String describe(@Nullable Object value) {
        if (value == null) {
            return "absent";
        }
        return value instanceof String ? "the string \"" + value + "\"" : String.valueOf(value);
    }
}
