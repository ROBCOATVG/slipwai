```java
@Test
void refusesAPledgeWhenFundingIsClosed() {
    Occasion closed = anOccasion().fundingClosed(true).build();
    InMemoryPledgePersistence persistence = new InMemoryPledgePersistence(closed);
    PledgeHandler handler = new PledgeHandler(persistence, eligibleFor(CONTRIBUTOR_ID));

    PledgeResult result = handler.handle(new PledgeCommand(
            new PledgeId("pledge-1"), closed.id(), CONTRIBUTOR_ID, Money.of(2_500, GBP)));

    assertThat(result).isEqualTo(new PledgeResult.Decided(
            new PledgeDecision.Refused(PledgeRefusal.FUNDING_CLOSED)));
    assertThat(persistence.saved()).isEmpty();
}
```
