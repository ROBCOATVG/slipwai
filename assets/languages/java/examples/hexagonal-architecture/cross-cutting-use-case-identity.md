```java
/**
 * The use case receives an identity and coordinates. It does not validate a token, read a cookie, or know
 * what an issuer is: by the time a principal reaches here it is a provider-free value, and the only way to
 * make one in production is through the authentication adapter.
 */
final class PledgingToOccasions implements ForPledgingToOccasions {

    private final PledgePersistence persistence;

    @Override
    public PledgeResult pledgeToOccasion(PledgeCommand command) {
        // command.pledger() is an AuthenticatedPledger — a type only the auth adapter can produce, so a
        // caller cannot fabricate one by passing a string.
        return apply(command.occasionId(), occasion ->
                recordPledge(occasion, command.pledgeId(), command.pledger().contributorId(),
                        command.amount()));
    }
}
```
