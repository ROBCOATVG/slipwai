package com.example.deliverystarter.adapters.driving.http;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * One 404 body for everything no route claimed, and it says nothing the caller did not already know.
 *
 * <p>This one is not a refinement of the framework's default — it replaces a default that discloses. Spring
 * Boot's error response carries the requested {@code path}, so out of the box a 404 puts the URL in the
 * response body, and from there in every proxy and access log along the way. For any project whose URLs
 * carry a credential — a no-login link, a password-reset path, a signed download — the 404 <em>is</em> the
 * disclosure, and it discloses to whoever probed for it.
 *
 * <p>It is also what makes the 404 in {@link SchemaFailure}'s status mapping honest. That mapping promises
 * another tenant's resource is indistinguishable from one that never existed; a handler that reflected the
 * path would undercut the promise.
 *
 * <p>Both exceptions are handled because Spring raises different ones depending on what is mapped:
 * {@code NoResourceFoundException} comes from the static-resource handler and
 * {@code NoHandlerFoundException} from the dispatcher when nothing is mapped at all — which is this
 * project's case, since {@code spring.web.resources.add-mappings} is off for a JSON API. Handling both means
 * the answer does not change if somebody later serves a file.
 *
 * <p>So: no path, no method, no hint whether the route exists under a different verb. There is a test that
 * asserts exactly that, because it is the kind of thing a well-meaning improvement reintroduces silently.
 */
@RestControllerAdvice
public class NotFoundAdvice {

    @ExceptionHandler({NoHandlerFoundException.class, NoResourceFoundException.class})
    public ResponseEntity<Map<String, String>> noRouteClaimedIt() {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("error", "notFound"));
    }
}
