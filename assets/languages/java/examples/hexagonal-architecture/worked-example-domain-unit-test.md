```java
// domain/PledgesTest.java
@Test
void addsTheExactAmountAndRecordsWhatHappened() {
    Occasion occasion = anOccasion().totalPledged(Money.of(5_000, GBP)).build();

    PledgeDecision decision = recordPledge(
            occasion, new PledgeId("pledge-1"), new ContributorId("contributor-1"),
            Money.of(3_000, GBP));

    assertThat(decision).isInstanceOf(PledgeDecision.Recorded.class);
    PledgeDecision.Recorded recorded = (PledgeDecision.Recorded) decision;
    assertThat(recorded.occasion().totalPledged()).isEqualTo(Money.of(8_000, GBP));
    assertThat(recorded.events()).containsExactly(new PledgeRecorded(
            new PledgeId("pledge-1"), occasion.id(), new ContributorId("contributor-1"),
            Money.of(3_000, GBP)));
}
```
