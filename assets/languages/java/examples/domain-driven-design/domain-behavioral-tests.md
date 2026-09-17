```java
// Behavioural — a business rule, with time supplied as data rather than read from a clock.
@Test
void treatsAnEventWithAPastDateAsPast() {
    Instant now = Instant.parse("2026-03-20T12:00:00Z");

    assertThat(isPastEvent(Instant.parse("2026-03-19T12:00:00Z"), now)).isTrue();
    assertThat(isPastEvent(Instant.parse("2026-03-21T12:00:00Z"), now)).isFalse();
}

// Behavioural — a business calculation, asserted on the answer rather than on how it was reached.
@Test
void countsOnlyCommittedItemsInTheCommittedTotal() {
    List<GiftItem> items = List.of(
            anItem().status(COMMITTED).price(Money.of(5_000, GBP)).build(),
            anItem().status(IDEA).price(Money.of(3_000, GBP)).build());

    assertThat(committedTotal(items)).isEqualTo(Money.of(5_000, GBP));
}
```
