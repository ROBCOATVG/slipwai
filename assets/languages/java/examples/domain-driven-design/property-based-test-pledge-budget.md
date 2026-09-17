```java
/**
 * A property, not an example: for every already-pledged total and every pledge amount, an accepted pledge
 * never puts the occasion over its budget.
 *
 * <p>Worth reaching for exactly here — the rule is arithmetic over a range, so hand-picked cases will
 * always leave the boundary somebody eventually hits untested. jqwik generates them, and shrinks a failure
 * to the smallest pair that breaks it.
 */
@Property
void anAcceptedPledgeNeverExceedsTheBudget(
        @ForAll @LongRange(min = 0, max = 10_000) long alreadyPledged,
        @ForAll @LongRange(min = 1, max = 10_000) long pledged) {

    Occasion occasion = anOccasion()
            .budget(Money.of(10_000, GBP))
            .totalPledged(Money.of(alreadyPledged, GBP))
            .build();

    PledgeDecision decision = pledgeContribution(
            occasion, eligible(), new PledgeId("pledge-1"), Money.of(pledged, GBP));

    // A refusal is always valid; only an acceptance has something to prove.
    if (decision instanceof PledgeDecision.Recorded recorded) {
        assertThat(recorded.occasion().totalPledged().minorUnits())
                .isLessThanOrEqualTo(recorded.occasion().budget().minorUnits());
    }
}
```
