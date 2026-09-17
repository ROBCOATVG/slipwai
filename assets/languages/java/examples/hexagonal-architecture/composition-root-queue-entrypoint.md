```java
/**
 * A second driving adapter over the same use case. Nothing about the application changed to gain it —
 * which is the practical payoff of the port: the message consumer and the HTTP resource are peers.
 */
@ApplicationScoped
public class PledgeMessageConsumer {

    private final ForPledgingToOccasions pledging;

    PledgeMessageConsumer(ForPledgingToOccasions pledging) {
        this.pledging = pledging;
    }

    @Incoming("pledges")
    public void consume(Message<String> message) {
        PledgeBody body = parse(message.getPayload());
        // The message id as the pledge id: the broker redelivers, so the identity has to come from
        // something stable rather than from a fresh UUID on each attempt.
        pledging.pledgeToOccasion(new PledgeCommand(
                new PledgeId(messageId(message)),
                new OccasionId(body.occasionId()),
                principalFrom(message),
                body.amount()));
    }
}
```
