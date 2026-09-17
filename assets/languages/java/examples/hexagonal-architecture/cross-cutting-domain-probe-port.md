```java
/**
 * A driven port for what the application wants *noticed*. Application-owned, because the use case is what
 * consumes it, and named in domain vocabulary: no levels, no metric names, no framework types.
 */
public interface PledgeInstrumentation {

    void pledgeAccepted(Money amount, OccasionId occasionId);

    void pledgeRefused(PledgeRefusal reason, OccasionId occasionId);
}

/** The use case announces facts. It does not decide that a refusal is a warning. */
final class PledgingToOccasions implements ForPledgingToOccasions {

    private final PledgePersistence persistence;
    private final PledgeInstrumentation instrumentation;

    @Override
    public PledgeResult pledgeToOccasion(PledgeCommand command) {
        PledgeResult result = apply(command);
        switch (result) {
            case PledgeResult.Recorded recorded ->
                    instrumentation.pledgeAccepted(command.amount(), command.occasionId());
            case PledgeResult.Refused refused ->
                    instrumentation.pledgeRefused(refused.reason(), command.occasionId());
        }
        return result;
    }
}

/** The adapter decides severity, metric names and span attributes — and can be swapped for any of them. */
@ApplicationScoped
final class TelemetryPledgeInstrumentation implements PledgeInstrumentation {

    private static final Logger LOG = Logger.getLogger(TelemetryPledgeInstrumentation.class);

    @Override
    public void pledgeAccepted(Money amount, OccasionId occasionId) {
        LOG.infof("Pledge accepted: %d %s to %s", amount.minorUnits(), amount.currency(), occasionId);
    }

    @Override
    public void pledgeRefused(PledgeRefusal reason, OccasionId occasionId) {
        LOG.warnf("Pledge refused: %s for %s", reason, occasionId);
    }
}
```
