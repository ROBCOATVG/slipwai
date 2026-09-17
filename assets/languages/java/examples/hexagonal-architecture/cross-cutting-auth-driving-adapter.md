```java
/**
 * Authentication is the driving adapter's, because it is about the transport: a bearer token, a cookie, a
 * mutual-TLS certificate. `@Authenticated` is the framework's, and the identity it establishes arrives
 * through the security context.
 *
 * <p>The body deliberately has no actor field. A request that could name the user it acts as is a request
 * that could act as anyone, and no amount of checking downstream fixes that.
 */
@Path("/occasions/{id}/pledges")
public class PledgeResource {

    private final ForPledgingToOccasions pledging;

    @POST
    @Authenticated
    public Response pledge(
            @PathParam("id") String occasionId,
            @Context SecurityContext security,
            @Valid PledgeBody body) {

        AuthenticatedPledger pledger = AuthenticatedPledger.of(security);

        PledgeResult result = pledging.pledgeToOccasion(new PledgeCommand(
                PledgeId.random(), new OccasionId(occasionId), pledger, body.amount()));

        return toResponse(result);
    }
}
```
