```java
// application/PledgingToOccasionsTest.java
private static final Occasion OCCASION = anOccasion().totalPledged(Money.of(0, GBP)).build();
private static final PledgeId PLEDGE_ID = new PledgeId("pledge-1");
private static final AuthenticatedPledger PLEDGER =
        AuthenticatedPledger.of(new ContributorId("contributor-1"));

@Test
void updatesOneAggregateAndRecordsItsOutboxEvent() {
    InMemoryPledgePersistence persistence = new InMemoryPledgePersistence(OCCASION);
    ForPledgingToOccasions pledging = new PledgingToOccasions(persistence);

    PledgeResult result = pledging.pledgeToOccasion(
            new PledgeCommand(PLEDGE_ID, OCCASION.id(), PLEDGER, Money.of(2_500, GBP)));

    assertThat(result).isInstanceOf(PledgeResult.Recorded.class);
    assertThat(((PledgeResult.Recorded) result).occasion().totalPledged())
            .isEqualTo(Money.of(2_500, GBP));
    assertThat(persistence.saved()).hasSize(1);
    assertThat(persistence.outboxEvents()).containsExactly(new PledgeRecorded(
            PLEDGE_ID, OCCASION.id(), new ContributorId("contributor-1"), Money.of(2_500, GBP)));
}

@Test
void refusesAPledgeThatWouldExceedTheBudget() {
    Occasion nearlyFunded = anOccasion()
            .budget(Money.of(10_000, GBP))
            .totalPledged(Money.of(9_000, GBP))
            .build();
    InMemoryPledgePersistence persistence = new InMemoryPledgePersistence(nearlyFunded);
    ForPledgingToOccasions pledging = new PledgingToOccasions(persistence);

    PledgeResult result = pledging.pledgeToOccasion(
            new PledgeCommand(PLEDGE_ID, nearlyFunded.id(), PLEDGER, Money.of(2_500, GBP)));

    assertThat(result).isEqualTo(new PledgeResult.Refused("EXCEEDS_BUDGET"));
    // Nothing was written, and nothing was announced. Both matter: an outbox row for a refused pledge
    // would tell every downstream consumer that it happened.
    assertThat(persistence.saved()).isEmpty();
    assertThat(persistence.outboxEvents()).isEmpty();
}

@Test
void refusesTheSecondOfTwoWritesDecidedAgainstTheSameVersion() {
    // A persistence that always reports version 0, which is what two callers who both read before either
    // wrote actually see. Staging it this way rather than with threads keeps the test deterministic while
    // exercising the same branch a real race takes.
    InMemoryPledgePersistence persistence = new InMemoryPledgePersistence(OCCASION) {
        @Override
        public Optional<StoredOccasion> findOccasionById(OccasionId id) {
            return super.findOccasionById(id)
                    .map(stored -> new StoredOccasion(stored.value(), 0));
        }
    };
    ForPledgingToOccasions pledging = new PledgingToOccasions(persistence);

    PledgeResult first = pledging.pledgeToOccasion(
            new PledgeCommand(new PledgeId("pledge-1"), OCCASION.id(), PLEDGER, Money.of(2_500, GBP)));
    PledgeResult second = pledging.pledgeToOccasion(
            new PledgeCommand(new PledgeId("pledge-2"), OCCASION.id(), PLEDGER, Money.of(3_000, GBP)));

    assertThat(first).isInstanceOf(PledgeResult.Recorded.class);
    assertThat(second).isEqualTo(new PledgeResult.Refused("concurrent-change"));
    // Exactly one write, and exactly one outbox event. The loser announced nothing.
    assertThat(persistence.saved()).hasSize(1);
    assertThat(persistence.outboxEvents()).hasSize(1);
}
```
