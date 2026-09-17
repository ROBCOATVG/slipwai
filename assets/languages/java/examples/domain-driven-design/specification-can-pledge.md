```java
/**
 * A specification: one named question with a boolean answer, so the same rule can be asked before acting
 * and again while acting without being written twice.
 */
public static boolean canPledge(
        Occasion occasion, ContributorEligibility eligibility, Money amount) {
    return eligibility.mayPledge()
            && !occasion.fundingClosed()
            && amount.isPositive()
            && amount.currency() == occasion.budget().currency()
            && amount.minorUnits()
                    <= occasion.budget().minorUnits() - occasion.totalPledged().minorUnits();
}

/** Specifications compose, which is where they earn their keep. */
public static boolean isGiftReady(Occasion occasion) {
    return occasion.totalPledged().minorUnits() >= occasion.budget().minorUnits()
            && occasion.giftIdeas().stream()
                    .anyMatch(idea -> idea.status() == GiftIdeaStatus.SELECTED);
}
```
