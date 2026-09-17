package com.example.deliverystarter.health;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Plain JUnit 5, with no {@code @SpringBootTest} anywhere near it.
 *
 * <p>That is the point rather than an economy: the framework owns startup for this backend, and a test that
 * boots an application context to assert a value would be slower and would prove less. Reach for
 * {@code @SpringBootTest} where the thing under test genuinely needs the application — a route, an injected
 * datasource — and nowhere else.
 */
class HealthStatusTest {

    @Test
    void reportsReady() {
        assertThat(HealthStatus.check().status()).isEqualTo("ok");
    }
}
