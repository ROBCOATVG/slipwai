```java
@Test
void refusesAPledgeFromAnIneligibleContributor() {
    InMemoryPledgePersistence persistence = new InMemoryPledgePersistence(OCCASION);
    InMemoryEligibilityGateway eligibilities = new InMemoryEligibilityGateway(
            anEligibility().contributorId(CONTRIBUTOR_ID).mayPledge(false).build());
    PledgeHandler handler = new PledgeHandler(persistence, eligibilities);

    PledgeResult result = handler.handle(new PledgeCommand(
            new PledgeId("pledge-1"), OCCASION.id(), CONTRIBUTOR_ID, Money.of(5_000, GBP)));

    assertThat(result).isEqualTo(new PledgeResult.Decided(
            new PledgeDecision.Refused(PledgeRefusal.CONTRIBUTOR_INELIGIBLE)));
    // Both, because either alone would be a bug: a saved aggregate, or an announcement of something that
    // did not happen.
    assertThat(persistence.saved()).isEmpty();
    assertThat(persistence.outboxEvents()).isEmpty();
}
```
