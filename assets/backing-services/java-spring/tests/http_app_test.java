package com.example.deliverystarter.adapters.driving.http;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Edge tests: the outermost surface, exercised through the real application rather than around it.
 *
 * <p>{@code @SpringBootTest} builds the real application context and {@code MockMvc} dispatches real requests
 * through the real handler chain — the same filters, the same advice, the same message converters — with no
 * socket bound. That is deliberately not a listening server: a fixed test port is machine-global, so the
 * moment this project's own Keycloak container publishes one locally, `make verify` and `make demo` stop
 * being runnable at the same time and the failure reads as a broken test. No port, no collision.
 *
 * <p>Two Spring Boot 4 details, both of which fail loudly rather than subtly, and both of which every guide
 * written before it gets wrong. {@code @SpringBootTest} no longer configures MockMvc on its own, so
 * {@code @AutoConfigureMockMvc} is required rather than decorative; and the annotation lives in
 * {@code org.springframework.boot.webmvc.test.autoconfigure}, in a `spring-boot-starter-webmvc-test`
 * dependency that has to be declared beside `spring-boot-starter-web` — Boot 4 ships a test starter per
 * regular starter, and `spring-boot-starter-test` alone does not carry this one.
 *
 * <p>It also keeps these tests inside `make verify`: no database, no Keycloak, no Docker. The datasource bean
 * may exist when Postgres is selected, but Hikari opens nothing until something asks for a connection, and
 * nothing here does. An entry-point test that needs a *backing service* is an integration test wearing the
 * wrong name and belongs in an {@code *IT} class.
 */
@SpringBootTest
@AutoConfigureMockMvc
class HttpAppTest {

    @Autowired
    private MockMvc mockMvc;

    /**
     * The probe every part of this project agrees on: the Compose healthcheck waits for it, {@code make demo}
     * prints it, and {@code skills/run-the-app} tells the reader to curl it.
     *
     * <p>The body is Actuator's rather than {@code {"status":"ok"}}, because Actuator owns this endpoint.
     * Asserting the shape here is what makes that a stated contract instead of a surprise — including what
     * it does *not* contain: details are hidden, so the per-contributor breakdown never reaches an
     * unauthenticated caller.
     */
    @Test
    void reportsReadinessOnThePathEveryBackendAgreesOn() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.components").doesNotExist());
    }

    /**
     * The contributor this application registers, asserted directly rather than through the endpoint. With
     * details hidden the aggregate body cannot show it, so the only honest way to prove it is wired is to ask
     * it — and this way the assertion does not depend on the disclosure setting staying as it is.
     */
    @Test
    void contributesItsOwnReadinessToThatProbe() {
        assertThat(new ServiceHealthIndicator().health().getStatus().getCode()).isEqualTo("UP");
    }

    /**
     * A 404 body that repeats the URL puts whatever the URL carried into every access log downstream.
     * Asserted rather than assumed, because Spring Boot's default error body *does* carry the path — this is
     * a default being replaced, not decorated.
     */
    @Test
    void doesNotEchoTheRequestedPathBackOnA404() throws Exception {
        mockMvc.perform(get("/orders/tok-live-abc123"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("notFound"))
                .andExpect(content().string(not(containsString("tok-live-abc123"))))
                .andExpect(content().string(not(containsString("/orders"))));
    }

    /**
     * A different verb on an unclaimed path gets the same 404 as a GET, with the same body — so a probe
     * cannot learn from the response that a route exists under some other method.
     *
     * <p>This is what `spring.web.resources.add-mappings=false` buys. With the static-resource handler on, it
     * claims every path and accepts GET and HEAD only, so this request would come back 405 and the
     * difference would be the disclosure.
     */
    @Test
    void doesNotRevealThatAPathExistsUnderADifferentMethod() throws Exception {
        mockMvc.perform(post("/orders/tok-live-abc123"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("notFound"))
                .andExpect(content().string(not(containsString("tok-live-abc123"))));
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
