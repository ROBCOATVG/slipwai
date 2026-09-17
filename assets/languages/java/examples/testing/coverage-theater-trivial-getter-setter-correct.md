```java
@Test
void weighsTheWholeShipment() {
    Order order = anOrder().items(List.of(aHeavyItem(), aLightItem())).build();

    assertThat(order.weight()).isEqualTo(Grams.of(230));
}
```
