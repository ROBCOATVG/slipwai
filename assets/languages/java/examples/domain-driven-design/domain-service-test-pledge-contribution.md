```java
@Test
void refusesAPledgeWhenTheContributorIsIneligible() {
    Occasion occasion = anOccasion().build();
    ContributorEligibility eligibility = anEligibility().mayPledge(false).build();

    PledgeDecision decision = pledgeContribution(
            occasion, eligibility, new PledgeId("pledge-1"), Money.of(5_000, GBP));

    assertThat(decision)
            .isEqualTo(new PledgeDecision.Refused(PledgeRefusal.CONTRIBUTOR_INELIGIBLE));
}
```
