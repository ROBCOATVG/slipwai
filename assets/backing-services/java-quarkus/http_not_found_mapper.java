package com.example.deliverystarter.adapters.driving.http;

import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;
import java.util.Map;

/**
 * One 404 body for everything no route claimed, and it says nothing the caller did not already know.
 *
 * <p>The framework's own default is a 404 with no body, which is safe as it stands — but the moment somebody
 * reaches for a friendlier message that echoes the requested path, the URL is in the response, and from
 * there in every proxy and access log along the way. For any project whose URLs carry a credential — a
 * no-login link, a password-reset path, a signed download — the 404 <em>is</em> the disclosure, and it
 * discloses to whoever probed for it.
 *
 * <p>It is also what makes the 404 in {@link SchemaFailure}'s status mapping honest. That mapping promises
 * another tenant's resource is indistinguishable from one that never existed; a handler that reflected the
 * path would undercut the promise.
 *
 * <p>So: no path, no method, no hint whether the route exists under a different verb. There is a test that
 * asserts exactly that, because it is the kind of thing a well-meaning improvement reintroduces silently.
 */
@Provider
public class NotFoundMapper implements ExceptionMapper<NotFoundException> {

    @Override
    public Response toResponse(NotFoundException exception) {
        return Response.status(Response.Status.NOT_FOUND)
                .type(MediaType.APPLICATION_JSON)
                .entity(Map.of("error", "notFound"))
                .build();
    }
}
