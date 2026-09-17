```java
@Test
void producesOrderPlacedWhenPlacingADraftOrder() {
    Instant now = Instant.parse("2026-03-20T00:00:00Z");
    Order state = new Order.Draft(ORDER_ID, List.of(anItem()));

    OrderDecision decision = decide(new OrderCommand.Place(), state, now);

    assertThat(decision).isEqualTo(new OrderDecision.Accepted(
            List.of(new OrderEvent.OrderPlaced(List.of(anItem()), now))));
}

@Test
void refusesPlacingAnAlreadyPlacedOrderWithAReason() {
    Instant now = Instant.parse("2026-03-20T00:00:00Z");
    Order state = new Order.Placed(ORDER_ID, List.of(anItem()), Instant.parse("2026-03-01T00:00:00Z"));

    OrderDecision decision = decide(new OrderCommand.Place(), state, now);

    assertThat(decision).isEqualTo(new OrderDecision.Refused("order-not-draft"));
}
```
