package com.example.deliverystarter.adapters.driving.http.users;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.JwtAudienceValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Where {@link CustomerIdentity} is applied: a second filter chain for the routes customers call, and the
 * one place a handler asks who the customer is.
 *
 * <p>This is the seam, and it is worth being clear about which side of it does what. Spring Security runs
 * the whole protocol for every request this chain matches — it retrieves the customers realm's JWKS,
 * verifies the bearer token's signature and checks {@code iss}, {@code aud} and {@code exp}. The rest is
 * {@link CustomerIdentity}: four claims in, a customer out, or a refusal naming the rule. Deciding what a
 * customer may *do* is not here either: ownership is a use-case decision, because a rule enforced in a
 * driving adapter is a rule the next entry point will not enforce.
 *
 * <p>Two chains, because two realms. The staff chain in {@code SecurityConfig} (when the project has one)
 * validates against the {@code app} realm and has no matcher, so it takes whatever is left; this one is
 * {@code @Order(1)} and claims {@value #CUSTOMER_ROUTES} first. A token from the wrong realm on either set
 * of routes fails that chain's issuer check, and {@link CurrentCustomer} refuses a staff token by issuer a
 * second time in code this project tests. When the project chose staff identity {@code none}, this is the
 * only chain: Spring Boot's default chain backs off because a {@link SecurityFilterChain} bean exists, and a
 * path outside the matcher has no chain at all — open until a route needs a principal, which is the intended
 * state and the same one the staff chain starts in.
 *
 * <p>Off until {@code app.users.oidc.issuer-uri} is set, and the mechanism is worth reading once: building
 * a decoder fetches the issuer's discovery document at start-up, so a configured issuer means the service
 * refuses to boot whenever Keycloak is not up. That line is therefore commented out in
 * {@code application.properties}, and this chain permits everything under the matcher until it is set —
 * then requires a customer on all of it. The decoder is deliberately <em>not</em> a bean: the staff chain
 * asks Spring for the one {@code JwtDecoder} the {@code issuer-uri} property produces, and a second bean of
 * that type would make that request ambiguous.
 */
@Configuration
public class CustomerSecurityConfig {

    /**
     * The routes customers call. A starting convention rather than a decision: change it in the same change
     * that adds the first customer route, and keep `/health` outside it — the Compose healthcheck and
     * `make demo` both read that unauthenticated.
     */
    static final String CUSTOMER_ROUTES = "/api/customers/**";

    /**
     * The customer chain, in the one shape that is honest about what this project has decided so far.
     *
     * <p>CSRF is off and sessions are stateless because this is a token-authenticated JSON API: the browser
     * app sends a bearer token, there is no cookie for an attacker's page to ride, and a session would be
     * state this service does not want.
     */
    @Bean
    @Order(1)
    public SecurityFilterChain customerFilterChain(
            HttpSecurity http,
            @Value("${app.users.oidc.issuer-uri:}") String issuer,
            @Value("${app.users.oidc.audience}") String audience)
            throws Exception {
        http.securityMatcher(CUSTOMER_ROUTES)
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.disable());
        if (issuer.isBlank()) {
            // Open, on purpose, until the issuer is set: the matcher exists so the first customer route
            // lands somewhere already wired, not so an unconfigured realm turns every request away.
            http.authorizeHttpRequests(requests -> requests.anyRequest().permitAll());
            return http.build();
        }
        // The matcher is the definition of a customer route, so once the realm is wired every route under
        // it needs a customer. Authorisation beyond that — whose order, whose account — is the use case's.
        http.authorizeHttpRequests(requests -> requests.anyRequest().authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.decoder(customerDecoder(issuer, audience))));
        return http.build();
    }

    /** The one place a handler asks who the customer is. */
    @Bean
    public CurrentCustomer currentCustomer(@Value("${app.users.oidc.issuer-uri:}") String issuer) {
        return new CurrentCustomer(issuer);
    }

    /**
     * A decoder for the customers realm, built by hand so it is not a bean. The default validators are
     * Spring's (timestamps, and the issuer once more); the audience check is what the {@code audience}
     * property is for — a token minted for a different client in the same realm is not for this API.
     */
    private static JwtDecoder customerDecoder(String issuer, String audience) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withIssuerLocation(issuer).build();
        decoder.setJwtValidator(JwtValidators.createDefaultWithValidators(
                List.of(new JwtIssuerValidator(issuer), new JwtAudienceValidator(audience))));
        return decoder;
    }

    /**
     * The customer on the current request, read from the authentication Spring Security has already built.
     *
     * <p>A singleton rather than a request-scoped bean because it holds no request state: it reads the
     * security context at the moment a handler asks. Inject it and call {@link #require} inside the handler;
     * a handler that does so on a staff route gets a refusal, not a staff member wearing a customer's hat.
     */
    public static final class CurrentCustomer {

        private final String issuer;

        CurrentCustomer(String issuer) {
            this.issuer = issuer;
        }

        /**
         * The customer this request was made by.
         *
         * @throws IllegalStateException when customer identity is not switched on, or nobody holding a JWT is
         *     authenticated on this request
         * @throws IllegalArgumentException from {@link CustomerIdentity#fromClaims}, naming the rule the
         *     token broke; a staff token reaching this call fails the issuer rule, which is the point
         */
        public CustomerIdentity require() {
            if (issuer.isBlank()) {
                throw new IllegalStateException(
                        "customer identity is not switched on; set app.users.oidc.issuer-uri in the same "
                                + "change that adds the route asking for a customer");
            }
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (!(authentication instanceof JwtAuthenticationToken token)) {
                throw new IllegalStateException(
                        "no customer is authenticated on this request; is the route under "
                                + CUSTOMER_ROUTES + "?");
            }
            return CustomerIdentity.fromClaims(token.getToken().getClaims(), issuer);
        }
    }
}
