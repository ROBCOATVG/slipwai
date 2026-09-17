```java
/** A recording fake for the probe port, so a test can assert what the application announced. */
public final class RecordingPledgeInstrumentation implements PledgeInstrumentation {

    /** One record type for every observation, so a test asserts on values rather than on call order. */
    public sealed interface Observed {
        record Accepted(Money amount, OccasionId occasionId) implements Observed { }

        record Refused(PledgeRefusal reason, OccasionId occasionId) implements Observed { }
    }

    private final List<Observed> observed = new ArrayList<>();

    @Override
    public void pledgeAccepted(Money amount, OccasionId occasionId) {
        observed.add(new Observed.Accepted(amount, occasionId));
    }

    @Override
    public void pledgeRefused(PledgeRefusal reason, OccasionId occasionId) {
        observed.add(new Observed.Refused(reason, occasionId));
    }

    public List<Observed> observed() {
        return List.copyOf(observed);
    }
}

@Test
void announcesTheRefusalWhenFundingIsClosed() {
    RecordingPledgeInstrumentation instrumentation = new RecordingPledgeInstrumentation();
    ForPledgingToOccasions pledging = new PledgingToOccasions(
            new InMemoryPledgePersistence(closedOccasion), instrumentation);

    pledging.pledgeToOccasion(aPledge().occasionId(closedOccasion.id()).build());

    assertThat(instrumentation.observed()).containsExactly(
            new RecordingPledgeInstrumentation.Observed.Refused(
                    PledgeRefusal.FUNDING_CLOSED, closedOccasion.id()));
}
```
