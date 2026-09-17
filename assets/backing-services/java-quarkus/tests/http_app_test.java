package com.example.deliverystarter.adapters.driving.http;

import static io.restassured.RestAssured.given;
import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasItem;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

/**
 * Edge tests: the outermost surface, exercised through the real application rather than around it.
 *
 * <p>{@code @QuarkusTest} boots the application on a port the framework picks — {@code test-port=0} in
 * {@code application.properties}, so a container publishing a fixed port cannot collide with the gate — and
 * RestAssured drives real requests through the real router. That keeps these tests inside
 * {@code make verify}: no database, no Keycloak, no Docker. An entry-point test that needs a *backing
 * service* is an integration test wearing the wrong name and belongs in an {@code *IT} class.
 */
@QuarkusTest
class HttpAppTest {

    /**
     * The probe every part of this project agrees on: the Compose healthcheck waits for it, {@code make demo}
     * prints it, and {@code skills/run-the-app} tells the reader to curl it.
     *
     * <p>The body is MicroProfile Health's rather than {@code {"status":"ok"}}, because SmallRye Health owns
     * this endpoint. Asserting the shape here is what makes that a stated contract instead of a surprise.
     */
    @Test
    void reportsReadinessOnThePathEveryBackendAgreesOn() {
        given().when()
                .get("/health")
                .then()
                .statusCode(200)
                .body("status", equalTo("UP"))
                .body("checks.name", hasItem("service"));
    }

    /**
     * A 404 body that repeats the URL puts whatever the URL carried into every access log downstream.
     * Asserted rather than assumed, because it is the kind of regression a well-meaning custom error page
     * reintroduces silently.
     */
    @Test
    void doesNotEchoTheRequestedPathBackOnA404() {
        given().when()
                .get("/orders/tok-live-abc123")
                .then()
                .statusCode(404)
                .body("error", equalTo("notFound"))
                .body(not(containsString("tok-live-abc123")))
                .body(not(containsString("/orders")));
    }

    /**
     * A different verb on an unclaimed path gets the same 404 as a GET, with the same body — so a probe
     * cannot learn from the response that a route exists under some other method.
     *
     * <p>The path probed here is deliberately not {@code /health}. That one is SmallRye Health's route
     * rather than a JAX-RS resource, and it answers every method with the report — a divergence from the
     * other backends in this factory, whose hand-written probe is GET-only. It is the correct trade: the
     * alternative is wrapping a maintained endpoint to narrow its methods, which is most of the cost of
     * having written it. Worth knowing if something downstream reads a 404 as "no such route".
     */
    @Test
    void doesNotRevealThatAPathExistsUnderADifferentMethod() {
        given().when()
                .post("/orders/tok-live-abc123")
                .then()
                .statusCode(404)
                .body("error", equalTo("notFound"))
                .body(not(containsString("tok-live-abc123")));
    }

    /** The 400 body, in one shape, with the offending value deliberately not in it. */
    @Test
    void reportsASchemaFailureInOneShape() {
        assertThat(new SchemaFailure("customer.email", "must be an email").asBody())
                .containsEntry("error", "schemaValidationFailed")
                .containsEntry("field", "customer.email")
                .containsEntry("message", "must be an email");

        assertThat(new SchemaFailure("", "").asBody())
                .containsEntry("field", "(root)")
                .containsEntry("message", "invalid request body");
    }
}
