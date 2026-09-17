```java
// adapters/driving/http/PledgeResource.java — the driving adapter, and nothing else.
@Path("/occasions/{id}/pledges")
public class PledgeResource {

    private final ForPledgingToOccasions pledging;

    PledgeResource(ForPledgingToOccasions pledging) {
        this.pledging = pledging;
    }

    @POST
    @Authenticated
    @Consumes(MediaType.APPLICATION_JSON)
    public Response pledge(
            @PathParam("id") @NotBlank String occasionId,
            @Context SecurityContext security,
            @Valid PledgeBody body) {

        // The authentication adapter is the only production source of this principal, so the body
        // cannot choose the actor. Bean Validation has already rejected a malformed body with a 400.
        AuthenticatedPledger pledger = AuthenticatedPledger.of(security);

        PledgeResult result = pledging.pledgeToOccasion(new PledgeCommand(
                PledgeId.random(), new OccasionId(occasionId), pledger, body.toMoney()));

        return switch (result) {
            case PledgeResult.Recorded recorded ->
                    Response.ok(Map.of("pledged", recorded.occasion().totalPledged().minorUnits()))
                            .build();
            case PledgeResult.Refused refused -> Response.status(statusFor(refused.reason()))
                    .entity(Map.of("error", refused.reason()))
                    .build();
        };
    }

    /** The request body: only what a caller may decide. No contributor, no tenant, no version. */
    public record PledgeBody(@Positive long amountMinorUnits, @NotNull Currency currency) {
        Money toMoney() {
            return Money.of(amountMinorUnits, currency);
        }
    }
}
```
