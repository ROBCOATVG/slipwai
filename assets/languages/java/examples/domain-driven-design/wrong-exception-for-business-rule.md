```java
// WRONG — an unchecked exception for an expected outcome. The signature says it returns an Occasion, so
// nothing tells the caller that "funding closed" is a thing that happens, and nothing makes it handle it.
public static Occasion pledgeContribution(Occasion occasion, Money amount) {
    if (occasion.fundingClosed()) {
        throw new FundingClosedException();
    }
    return occasion.withPledge(amount);
}
```
