```java
public interface OrderRepository {

    Optional<StoredOrder> findById(OrderId id);

    Saved save(Order state, int expectedVersion);

    record StoredOrder(Order state, int version) { }

    enum Saved { SAVED, CONFLICT }
}

PlaceOrderResult handlePlaceOrder(PlaceOrderCommand command, Instant now) {
    Optional<OrderRepository.StoredOrder> stored = orders.findById(command.orderId());
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
    if (orders.save(updated, stored.get().version()) == OrderRepository.Saved.CONFLICT) {
        return new PlaceOrderResult.Refused("concurrent-change");
    }

    // Dispatched in-process: simple, and NOT durable. The save has committed, so a crash on the next line
    // loses the notification with no record that it was owed — which is exactly what the outbox pattern
    // exists to fix. Acceptable while a missed notification is a nuisance; not once it is money.
    for (OrderEvent event : accepted.events()) {
        notifier.notify(event);
    }
    return new PlaceOrderResult.Placed(updated);
}
```
