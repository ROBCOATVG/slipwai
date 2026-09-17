```java
static ItemBuilder anItem() {
    return new ItemBuilder().id(new ItemId("item-1")).name("Test Item").weight(Grams.of(100));
}

static OrderBuilder anOrder() {
    return new OrderBuilder()
            .id(new OrderId("order-1"))
            .items(List.of(anItem().build()))      // compose factories
            .customer(aCustomer().build())
            .payment(aPayment().build());
}

@Test
void totalsTheWeightOfEveryItem() {
    Order order = anOrder()
            .items(List.of(
                    anItem().weight(Grams.of(100)).build(),
                    anItem().weight(Grams.of(200)).build()))
            .build();

    assertThat(order.weight()).isEqualTo(Grams.of(300));
}
```
