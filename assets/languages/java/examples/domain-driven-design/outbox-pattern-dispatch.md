```java
/**
 * An application-owned persistence contract requiring one atomic aggregate-plus-outbox operation. One
 * method rather than two, because "save the order" and "record the event" must not be interruptible
 * between them.
 */
public interface PlaceOrderPersistence {

    Optional<StoredOrder> findOrderById(OrderId id);

    Saved saveWithOutbox(Order state, List<OrderEvent> events, int expectedVersion);

    record StoredOrder(Order state, int version) { }

    enum Saved { SAVED, CONFLICT }
}

PlaceOrderResult handlePlaceOrder(PlaceOrderCommand command, Instant now) {
    Optional<PlaceOrderPersistence.StoredOrder> stored =
            persistence.findOrderById(command.orderId());
    if (stored.isEmpty()) {
        return new PlaceOrderResult.Refused("not-found");
    }

    OrderDecision decision = decide(command, stored.get().state(), now);
    if (!(decision instanceof OrderDecision.Accepted accepted)) {
        return new PlaceOrderResult.Refused(((OrderDecision.Refused) decision).reason());
    }

    Order updated = stored.get().state();
    for (OrderEvent event : accepted.events()) {
        updated = evolve(updated, event);
    }

    // One compare-and-save: the aggregate and the outbox rows commit together, or neither does. A separate
    // relay publishes from the outbox afterwards and may retry as often as it likes.
    return persistence.saveWithOutbox(updated, accepted.events(), stored.get().version())
                    == PlaceOrderPersistence.Saved.SAVED
            ? new PlaceOrderResult.Placed(updated)
            : new PlaceOrderResult.Refused("concurrent-change");
}
```
