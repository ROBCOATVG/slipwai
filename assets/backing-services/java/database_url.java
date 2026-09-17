package com.example.deliverystarter.config;

import java.net.URI;
import java.net.URISyntaxException;
import org.jspecify.annotations.Nullable;

/**
 * The one place that translates {@code DATABASE_URL} into what JDBC needs.
 *
 * <p>Every backend this factory generates reads the same variable — {@code postgres://user:pass@host:port/db}
 * — because a project's address for its database should not depend on which language it happens to be
 * written in. JDBC wants that split three ways instead: {@code jdbc:postgresql://host:port/db}, plus the
 * username and password supplied separately.
 *
 * <p>Something therefore has to translate, and the reason this is a class rather than two lines in two
 * places is that there are two callers — {@link DatabaseUrlConfigSource}, so the application's datasource is
 * configured from it, and {@code migrations/MigrateMain}, so {@code make migrate} reaches the same database.
 * Two parsers for one URL would drift, and nothing would catch it until a deploy pointed the migration at a
 * different server than the service.
 *
 * @param jdbcUrl the JDBC form, with no credentials in it
 * @param username the user, or an empty string when the URL carried none
 * @param password the password, or an empty string when the URL carried none
 */
public record DatabaseUrl(String jdbcUrl, String username, String password) {

    /**
     * Parse a libpq-style URL.
     *
     * @param url the value of {@code DATABASE_URL}, which {@code System.getenv} may return as null — hence
     *     the annotation. Reading an unset variable is the ordinary case this has to report well, not an
     *     impossible one.
     * @throws IllegalArgumentException when the value is not a URL this can translate. Deliberately loud: a
     *     silently-ignored database URL is a service that starts up pointing at the wrong database.
     */
    public static DatabaseUrl parse(@Nullable String url) {
        if (url == null || url.isBlank()) {
            throw new IllegalArgumentException(
                    "DATABASE_URL is not set. `make migrate` and `make test-integration` export it from the "
                            + "Makefile; outside make, copy the value from .env.example");
        }
        URI parsed;
        try {
            parsed = new URI(url.trim());
        } catch (URISyntaxException failure) {
            throw new IllegalArgumentException("DATABASE_URL is not a URL: " + url, failure);
        }
        String scheme = parsed.getScheme();
        if (!"postgres".equals(scheme) && !"postgresql".equals(scheme)) {
            throw new IllegalArgumentException(
                    "DATABASE_URL must name the postgres scheme, not '" + scheme + "'");
        }
        if (parsed.getHost() == null) {
            throw new IllegalArgumentException("DATABASE_URL names no host: " + url);
        }
        StringBuilder jdbc = new StringBuilder("jdbc:postgresql://").append(parsed.getHost());
        if (parsed.getPort() != -1) {
            jdbc.append(':').append(parsed.getPort());
        }
        if (parsed.getRawPath() != null) {
            jdbc.append(parsed.getRawPath());
        }
        // The query string carries libpq options a JDBC driver mostly understands too — sslmode is the one
        // that matters in a real environment — so it is passed through rather than dropped.
        if (parsed.getRawQuery() != null) {
            jdbc.append('?').append(parsed.getRawQuery());
        }
        String userInfo = parsed.getUserInfo();
        String username = "";
        String password = "";
        if (userInfo != null && !userInfo.isEmpty()) {
            int separator = userInfo.indexOf(':');
            username = separator < 0 ? userInfo : userInfo.substring(0, separator);
            password = separator < 0 ? "" : userInfo.substring(separator + 1);
        }
        return new DatabaseUrl(jdbc.toString(), username, password);
    }
}
