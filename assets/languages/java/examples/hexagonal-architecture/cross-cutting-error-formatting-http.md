```java
// The domain returns a reason in its own vocabulary: DeductResult.Refused("funding-closed").
// The driving adapter is the only place that turns one into a status code.
private static Response toResponse(PledgeResult result) {
    return switch (result) {
        case PledgeResult.Recorded recorded ->
                Response.ok(Map.of("pledged", recorded.occasion().totalPledged())).build();
        case PledgeResult.Refused refused -> Response.status(statusFor(refused.reason()))
                .entity(Map.of("error", refused.reason()))
                .build();
    };
}

/**
 * One table, exhaustive over the reasons the application can return. A switch over an enum rather than a
 * default: add a reason and this stops compiling, which is the moment to decide its status rather than
 * discovering later that everything unknown became a 500.
 */
private static int statusFor(PledgeRefusal reason) {
    return switch (reason) {
        case NOT_FOUND -> 404;
        case CONCURRENT_CHANGE -> 409;
        case NON_POSITIVE_AMOUNT, CURRENCY_MISMATCH, EXCEEDS_BUDGET, FUNDING_CLOSED -> 422;
    };
}
```
