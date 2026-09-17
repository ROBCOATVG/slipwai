package com.example.deliverystarter.health;

/**
 * Whether this service considers itself ready, as a value the application owns.
 *
 * <p>The walking skeleton: the smallest thing that is genuinely end to end — a value, a test that asserts
 * its behaviour, and a gate that runs the test. There is deliberately no framework type here and no
 * annotation. Quarkus serves the readiness probe through SmallRye Health, and the check that reports this
 * value lives in the transport adapter; this record is what the check reports *about*, and it stays
 * testable with nothing running.
 */
public record HealthStatus(String status) {

    /** What this service reports before any slice has been built. */
    public static HealthStatus check() {
        return new HealthStatus("ok");
    }
}
