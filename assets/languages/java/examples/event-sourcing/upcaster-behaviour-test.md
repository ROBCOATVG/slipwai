```java
@Test
void upcastsAV1OrderPlacedIntoTheShapeTheDomainCanFold() {
    OrderPlacedV1 stored = new OrderPlacedV1("o-1", 4_000, Currency.EUR);

    OrderPlacedV2 current = toCurrent(new StoredOrderPlaced.V1(stored));

    assertThat(current)
            .isEqualTo(new OrderPlacedV2("o-1", new Money(4_000, Currency.EUR)));
}
```
