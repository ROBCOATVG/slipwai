```java
// A use case takes the application-owned contracts it collaborates through. Its signature announces that
// it reaches outside itself.
PledgeResult handlePledge(PledgePersistence persistence, ContributorEligibilityGateway eligibilities,
        PledgeCommand command)

// A domain service takes only domain types. Its signature announces that it cannot reach anywhere: given
// the same arguments it returns the same answer, every time, with nothing to stub.
PledgeDecision pledgeContribution(
        Occasion occasion, ContributorEligibility eligibility, PledgeId id, Money amount)
```
