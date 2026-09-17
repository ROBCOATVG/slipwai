```java
// AFTER — the resource parses, calls, and maps a status. Every rule moved inward, and the two things
// left are the two things a transport is actually for.
@Path("/balance")
public class BalanceResource {

    private final ForDeductingUserBalances balances;

    BalanceResource(ForDeductingUserBalances balances) {
        this.balances = balances;
    }

    @POST
    @Path("/deduct")
    @Authenticated
    public Response deduct(@Context SecurityContext security, @Valid DeductBody body) {
        // The authenticated identity comes from the framework's own security context, never from the
        // body: a request must not be able to name the user it acts as.
        AuthenticatedPrincipal principal = AuthenticatedPrincipal.of(security);

        return switch (balances.deductUserBalance(principal, body.toMoney())) {
            case DeductResult.Deducted deducted ->
                    Response.ok(Map.of("balance", deducted.user().balance().minorUnits())).build();
            case DeductResult.Refused refused -> Response.status(statusFor(refused.reason()))
                    .entity(Map.of("error", refused.reason()))
                    .build();
        };
    }

    /** The one place the domain's vocabulary becomes HTTP. */
    private static int statusFor(String reason) {
        return switch (reason) {
            case "not-found" -> 404;
            case "concurrent-change" -> 409;
            default -> 422;
        };
    }
}
```
