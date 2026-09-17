package com.example.deliverystarter.adapters.driving.http.auth;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Where {@link KeycloakRoles} is applied: the framework's own hook for turning a validated token into
 * authorities.
 *
 * <p>This is the seam, and it is worth being clear about which side of it does what. Spring Security has
 * already run the whole protocol by the time the converter below is called — it retrieved the issuer's JWKS,
 * verified the token's signature and checked {@code iss}, {@code aud} and {@code exp}. This adds the
 * application's roles to the resulting authentication, and nothing else. Deciding what a role may *do* is not
 * here either: authorisation belongs inside use cases, because a rule enforced in a driving adapter is a rule
 * the next entry point will not enforce.
 *
 * <p>Every route is open until one needs a principal. That is deliberate, and the mechanism is worth reading
 * once: a {@code JwtDecoder} exists only when
 * {@code spring.security.oauth2.resourceserver.jwt.issuer-uri} is set, and that line is commented out in
 * {@code application.properties} because building a decoder fetches the issuer's discovery document at
 * start-up. So the filter chain asks for the decoder rather than requiring it, and turns bearer-token
 * validation on when — and only when — one is configured. The group mapping itself is wired and tested from
 * the first day either way, which is the point: it is written the day the realm is understood rather than the
 * day it is first needed, which is the day it is least likely to be got right.
 */
@Configuration
public class SecurityConfig {

    /**
     * The claim the groups arrive in: {@code groups} from Keycloak's group-membership mapper, {@code
     * cognito:groups} from Cognito. Configuration ({@code OIDC_GROUPS_CLAIM}) rather than a constant, so the
     * same mapping serves the local stand-in and the production issuer.
     */
    private final String groupsClaim;

    public SecurityConfig(@Value("${app.oidc.groups-claim}") String groupsClaim) {
        this.groupsClaim = groupsClaim;
    }

    /**
     * The chain, in the one shape that is honest about what this project has decided so far.
     *
     * <p>CSRF is off and sessions are stateless because this is a token-authenticated JSON API: there is no
     * cookie for an attacker's page to ride, and a session would be state this service does not want. Both
     * change if a browser login is ever added, which is a different decision from this one.
     */
    @Bean
    public SecurityFilterChain filterChain(
            HttpSecurity http,
            ObjectProvider<JwtDecoder> decoder,
            JwtAuthenticationConverter converter)
            throws Exception {
        http.csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.disable())
                // Open, on purpose. Replace this with the routes that need a principal in the same change
                // that uncomments the issuer, and leave `/health` out of whatever you require: the Compose
                // healthcheck and `make demo` both read it unauthenticated.
                .authorizeHttpRequests(requests -> requests.anyRequest().permitAll());
        if (decoder.getIfAvailable() != null) {
            http.oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.jwtAuthenticationConverter(converter)));
        }
        return http.build();
    }

    /**
     * The token-to-authorities mapping, built from the realm's groups.
     *
     * <p>{@code ROLE_} is Spring Security's own prefix for an authority reached through {@code hasRole} —
     * added here rather than at every call site, because forgetting it once produces a rule that silently
     * never matches.
     */
    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter(KeycloakRoles roles) {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> authorities(roles, jwt, groupsClaim));
        return converter;
    }

    /**
     * The mapping itself, as a bean so it is one object the whole application agrees with.
     *
     * <p>{@code assertComplete} runs at construction rather than on the first request: a misconfigured
     * environment should refuse to start, not serve traffic that silently grants nobody anything.
     */
    @Bean
    public KeycloakRoles keycloakRoles(
            @Value("${app.oidc.group.admin}") String admin,
            @Value("${app.oidc.group.operator}") String operator,
            @Value("${app.oidc.group.viewer}") String viewer) {
        KeycloakRoles roles = new KeycloakRoles(Map.of("admin", admin, "operator", operator, "viewer", viewer));
        roles.assertComplete();
        return roles;
    }

    private static Collection<GrantedAuthority> authorities(KeycloakRoles roles, Jwt jwt, String groupsClaim) {
        Collection<GrantedAuthority> granted = new ArrayList<>();
        for (String role : roles.resolve(groupsOf(jwt, groupsClaim))) {
            granted.add(new SimpleGrantedAuthority("ROLE_" + role));
        }
        return granted;
    }

    private static List<String> groupsOf(Jwt jwt, String groupsClaim) {
        Object claim = jwt.getClaim(groupsClaim);
        List<String> groups = new ArrayList<>();
        if (claim instanceof Iterable<?> values) {
            values.forEach(value -> groups.add(String.valueOf(value)));
        } else if (claim != null) {
            groups.add(String.valueOf(claim));
        }
        return groups;
    }
}
