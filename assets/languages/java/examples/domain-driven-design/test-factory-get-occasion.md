```java
/**
 * A builder for the aggregate under test: complete, valid defaults, with one call per thing a test cares
 * about. `build()` goes through the real constructor, so a factory that produced an impossible Occasion
 * would fail in the factory rather than misleading the test.
 */
static OccasionBuilder anOccasion() {
    return new OccasionBuilder()
            .id(new OccasionId("occasion-1"))
            .name("Mum's Birthday")
            .budget(Money.of(10_000, Currency.GBP))
            .totalPledged(Money.of(0, Currency.GBP))
            .giftIdeas(List.of())
            .fundingClosed(false);
}
```
