package com.example.deliverystarter.adapters.driving.http;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The 400 body, so every route reports a bad shape the same way.
 *
 * <p>Status mapping belongs in this layer precisely because the domain speaks business vocabulary:
 *
 * <ul>
 *   <li>400 — schema failure: the shape is wrong
 *   <li>422 — business rejection: the shape is fine, the rule says no
 *   <li>404 — not found, INCLUDING another tenant's resource, so existence is not leaked
 *   <li>409 — a conflict the caller may retry differently, which is where an
 *       {@code AppendResult.VersionConflict} from the event store surfaces: the store returns it as a value,
 *       and this is the layer that gives it a status
 * </ul>
 *
 * <p>The offending value is deliberately absent from the body. A validation error on a field holding a token
 * or a password must not quote it back — into the response, and from there into every log along the way.
 */
public record SchemaFailure(String field, String message) {

    /**
     * Blank becomes a usable default. There is deliberately no null check: NullAway holds this package to
     * non-null by default, so a null here does not compile, and a branch the compiler has already made
     * unreachable is a branch no test can cover.
     */
    public SchemaFailure {
        field = field.isBlank() ? "(root)" : field;
        message = message.isBlank() ? "invalid request body" : message;
    }

    /** The JSON body, with the error code every schema failure shares. */
    public Map<String, String> asBody() {
        Map<String, String> body = new LinkedHashMap<>();
        body.put("error", "schemaValidationFailed");
        body.put("field", field);
        body.put("message", message);
        return body;
    }
}
