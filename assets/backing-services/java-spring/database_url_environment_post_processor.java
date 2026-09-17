package com.example.deliverystarter.config;

import java.util.HashMap;
import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.MutablePropertySources;
import org.springframework.core.env.StandardEnvironment;

/**
 * Configures Spring Boot's datasource from {@code DATABASE_URL}.
 *
 * <p>Spring Boot owns the pool (HikariCP), the transactions and the datasource health contributor — this
 * class only tells it where to connect. A property source rather than code that builds a {@code DataSource}
 * by hand, because that keeps the framework's auto-configuration in charge of everything except the address:
 * {@code spring.datasource.*} is still the configuration, and every other way of setting it still works.
 *
 * <p>Where it is inserted is the load-bearing detail. Immediately after the OS environment, so
 * {@code SPRING_DATASOURCE_URL} set directly still wins — which is what an operator with an unusual URL
 * needs — and above {@code application.properties}, whose values are only the local fallback. Registered
 * through {@code META-INF/spring/org.springframework.boot.env.EnvironmentPostProcessor.imports}, so it runs
 * while the environment is being assembled and before any bean exists.
 *
 * <p>An unparseable {@code DATABASE_URL} contributes nothing here rather than throwing. A post-processor
 * that throws while the environment is being assembled fails every profile at once, including the test
 * profile that never wanted a database; the datasource then reports the real problem, at the point of use,
 * in a message that names the URL.
 *
 * <p>Instantiated reflectively by Spring Boot, so the public no-argument constructor is the interface even
 * though nothing in this project calls it.
 */
public class DatabaseUrlEnvironmentPostProcessor implements EnvironmentPostProcessor {

    /** Named so `/actuator/env` and a startup log line say where the values came from. */
    private static final String SOURCE_NAME = "DATABASE_URL";

    private static final String URL = "spring.datasource.url";
    private static final String USERNAME = "spring.datasource.username";
    private static final String PASSWORD = "spring.datasource.password";

    @Override
    public void postProcessEnvironment(
            ConfigurableEnvironment environment, SpringApplication application) {
        Map<String, Object> resolved = resolve(System.getenv("DATABASE_URL"));
        if (resolved.isEmpty()) {
            return;
        }
        MutablePropertySources sources = environment.getPropertySources();
        MapPropertySource source = new MapPropertySource(SOURCE_NAME, resolved);
        // After the OS environment so a directly-set SPRING_DATASOURCE_URL still wins, and before
        // everything below it — which is where `application.properties` lands — so the fallback loses.
        // The environment source is absent in a few embedded cases; last place is then the only honest
        // answer, since there is nothing to be relative to.
        if (sources.contains(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME)) {
            sources.addAfter(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, source);
        } else {
            sources.addLast(source);
        }
    }

    private static Map<String, Object> resolve(String url) {
        Map<String, Object> properties = new HashMap<>();
        if (url == null || url.isBlank()) {
            return properties;
        }
        try {
            DatabaseUrl parsed = DatabaseUrl.parse(url);
            properties.put(URL, parsed.jdbcUrl());
            if (!parsed.username().isEmpty()) {
                properties.put(USERNAME, parsed.username());
            }
            if (!parsed.password().isEmpty()) {
                properties.put(PASSWORD, parsed.password());
            }
        } catch (IllegalArgumentException ignored) {
            properties.clear();
        }
        return properties;
    }
}
