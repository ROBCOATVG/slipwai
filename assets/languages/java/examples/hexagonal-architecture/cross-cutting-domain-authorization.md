```java
/**
 * "Only the organiser may close funding" is a business rule, not a transport concern — so it lives in the
 * domain, where a queue consumer and a scheduled job get it too.
 *
 * <p>The distinction worth holding on to: *who you are* is the adapter's question, and *what you may do*
 * is the domain's.
 */
public static CloseResult closeFunding(Occasion occasion, ContributorId requester) {
    if (!occasion.organiserId().equals(requester)) {
        return new CloseResult.Refused("not-organiser");
    }
    return new CloseResult.Closed(occasion.withFundingClosed());
}
```
