```java
/**
 * The use case is the primary boundary to test: it is where the interesting coordination lives, and fakes
 * for its ports make it fast enough to test exhaustively.
 */
@Test
void savesTheOrderAndChargesThePaymentOnSuccess() {
    InMemoryOrderRepository orders = new InMemoryOrderRepository();
    ForPlacingOrders placement = new OrderPlacement(orders, new AlwaysSucceedingGateway());

    OrderResult result = placement.placeOrder(anOrder().build());

    assertThat(result).isInstanceOf(OrderResult.Placed.class);
    assertThat(orders.saved()).hasSize(1);
}

@Test
void doesNotSaveTheOrderWhenPaymentFails() {
    InMemoryOrderRepository orders = new InMemoryOrderRepository();
    ForPlacingOrders placement = new OrderPlacement(orders, new AlwaysDecliningGateway());

    OrderResult result = placement.placeOrder(anOrder().build());

    assertThat(result).isInstanceOf(OrderResult.Refused.class);
    assertThat(orders.saved()).isEmpty();
}
```
