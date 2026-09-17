package com.example.deliverystarter.config;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import org.eclipse.microprofile.config.spi.ConfigSource;
import org.jspecify.annotations.Nullable;

/**
 * Configures Quarkus's datasource from {@code DATABASE_URL}.
 *
 * <p>Agroal owns the pool, the transactions and the datasource health check — this class only tells it where
 * to connect. A {@link ConfigSource} rather than code that builds a {@code DataSource} by hand, because that
 * keeps the framework's integration in charge of everything except the address: {@code quarkus.datasource.*}
 * is still the configuration, and every other way of setting it still works.
 *
 * <p>The ordinal is the load-bearing detail. At 275 this beats {@code application.properties} (250), whose
 * values are only the local fallback, and loses to environment variables (300) — so setting
 * {@code QUARKUS_DATASOURCE_JDBC_URL} directly still wins, which is what an operator with an unusual URL
 * needs. Registered through {@code META-INF/services}, so it is found before any bean exists.
 *
 * <p>An unparseable {@code DATABASE_URL} yields nothing here rather than throwing. A config source that
 * throws while the configuration is being assembled fails every profile at once, including the test profile
 * that never wanted a database; the datasource then reports the real problem, at the point of use, in a
 * message that names the URL.
 */
public class DatabaseUrlConfigSource implements ConfigSource {

    private static final String JDBC_URL = "quarkus.datasource.jdbc.url";
    private static final String USERNAME = "quarkus.datasource.username";
    private static final String PASSWORD = "quarkus.datasource.password";

    private final Map<String, String> properties = new HashMap<>();

    public DatabaseUrlConfigSource() {
        String url = System.getenv("DATABASE_URL");
        if (url == null || url.isBlank()) {
            return;
        }
        try {
            DatabaseUrl parsed = DatabaseUrl.parse(url);
            properties.put(JDBC_URL, parsed.jdbcUrl());
            if (!parsed.username().isEmpty()) {
                properties.put(USERNAME, parsed.username());
            }
            if (!parsed.password().isEmpty()) {
                properties.put(PASSWORD, parsed.password());
            }
        } catch (IllegalArgumentException ignored) {
            properties.clear();
        }
    }

    @Override
    public Map<String, String> getProperties() {
        return Map.copyOf(properties);
    }

    @Override
    public Set<String> getPropertyNames() {
        return getProperties().keySet();
    }

    /**
     * {@code null} for a property this source does not carry, which is the interface's own contract for
     * "ask the next source". Marked {@code @Nullable} because NullAway is on: in an annotated package
     * every reference is non-null unless it says otherwise, and a method that may genuinely return nothing
     * has to say so rather than have the check weakened for it.
     */
    @Override
    @Nullable
    public String getValue(String propertyName) {
        return properties.get(propertyName);
    }

    @Override
    public String getName() {
        return "DATABASE_URL";
    }

    @Override
    public int getOrdinal() {
        return 275;
    }
}
