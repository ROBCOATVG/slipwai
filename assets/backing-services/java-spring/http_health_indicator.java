package com.example.deliverystarter.adapters.driving.http;

import com.example.deliverystarter.health.HealthStatus;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * What this application contributes to the readiness probe.
 *
 * <p>Actuator owns the endpoint — its path, its aggregation of every contributor, and the status code it
 * answers with. This class is one contributor registered into it, which is the whole extent of what a project
 * should write: a hand-written {@code /health} route beside a maintained one is a route this repository would
 * then own forever, and it would have to be kept in step with every probe added later.
 *
 * <p>Two consequences worth knowing. The body is Actuator's shape, {@code {"status":"UP"}}, rather than the
 * {@code {"status":"ok"}} the plain backends in this factory answer with — that is the price of not
 * maintaining a probe. And starters register their own contributors here too: with Postgres selected, Boot
 * adds a datasource contributor on its own, which is why `management.health.db.enabled` is switched off in
 * `application.properties` until this service actually depends on the store.
 *
 * <p>Readiness rather than liveness, deliberately. Liveness means "restarting me might help"; readiness means
 * "send me traffic". A dependency this service cannot reach is the second, and answering the first would get
 * the process killed instead of taken out of the pool.
 *
 * <p>The contributor's name is derived from the bean name with {@code HealthIndicator} removed, so this one
 * reports as {@code service}. Renaming the class renames it in the report.
 *
 * <p>{@code org.springframework.boot.health.contributor}, not the {@code boot.actuate.health} every guide
 * written before Spring Boot 4 will show you: Boot 4 split auto-configuration into per-technology modules
 * and the health contract moved with it. The old package does not exist, so the failure is a clean
 * compile error rather than anything subtle.
 */
@Component
public class ServiceHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        // The value comes from the application rather than being built here, so what "ready" means stays
        // testable with nothing running. See HealthStatusTest.
        return "ok".equals(HealthStatus.check().status()) ? Health.up().build() : Health.down().build();
    }
}
