package com.example.deliverystarter.adapters.driving.http;

import com.example.deliverystarter.health.HealthStatus;
import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Readiness;

/**
 * What this application contributes to the readiness probe.
 *
 * <p>SmallRye Health owns the endpoint — its path, its aggregation of every check, and the status code it
 * answers with. This class is a check registered into it, which is the whole extent of what a project should
 * write: a hand-written {@code /health} route beside a maintained one is a route this repository would then
 * own forever, and it would have to be kept in step with every probe added later.
 *
 * <p>Two consequences worth knowing. The body is MicroProfile Health's shape,
 * {@code {"status":"UP","checks":[…]}}, rather than the {@code {"status":"ok"}} the other backends in this
 * factory answer with — that is fixed by the specification and is the price of not maintaining a probe. And
 * extensions register their own checks here too: with Postgres selected, Agroal adds a datasource check on
 * its own, so an unreachable event store makes this service correctly report itself not ready.
 *
 * <p>Readiness rather than liveness, deliberately. Liveness means "restarting me might help"; readiness means
 * "send me traffic". A dependency this service cannot reach is the second, and answering the first would get
 * the process killed instead of taken out of the pool.
 */
@Readiness
public class ServiceHealthCheck implements HealthCheck {

    @Override
    public HealthCheckResponse call() {
        // The value comes from the application rather than being built here, so what "ready" means stays
        // testable with nothing running. See HealthStatusTest.
        return HealthCheckResponse.named("service")
                .status("ok".equals(HealthStatus.check().status()))
                .build();
    }
}
