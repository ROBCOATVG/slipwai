```java
@Test
void refusesAContributionThatExceedsTheAvailableBalance() {
    PledgeDecision decision = pledgeContribution(occasion, poorContributor, largePledge);

    assertThat(decision).isEqualTo(new PledgeDecision.Refused(PledgeRefusal.EXCEEDS_BUDGET));
}
```
