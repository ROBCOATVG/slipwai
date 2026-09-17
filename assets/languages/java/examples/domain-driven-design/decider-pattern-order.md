```java
public sealed interface OrderDecision {
    record Accepted(List<OrderEvent> events) implements OrderDecision { }

    record Refused(String reason) implements OrderDecision { }
}

/** 1. Decide: a command plus the current state becomes an explicit acceptance or refusal. */
static OrderDecision decide(OrderCommand command, Order state, Instant now) {
    return switch (command) {
        case OrderCommand.Place place -> state instanceof Order.Draft draft
                ? new OrderDecision.Accepted(
                        List.of(new OrderEvent.OrderPlaced(draft.items(), now)))
                : new OrderDecision.Refused("order-not-draft");
        case OrderCommand.Ship ship -> state instanceof Order.Placed placed
                ? new OrderDecision.Accepted(
                        List.of(new OrderEvent.OrderShipped(ship.trackingNumber(), now)))
                : new OrderDecision.Refused("order-not-placed");
    };
}

/**
 * 2. Evolve: state plus an event becomes new state. Each case builds the whole target phase, because Order
 * is a union of lifecycle phases — there is no partial update that would type-check.
 */
static Order evolve(Order state, OrderEvent event) {
    return switch (event) {
        case OrderEvent.OrderPlaced placed -> {
            if (!(state instanceof Order.Draft draft)) {
                throw corrupt(state, event);
            }
            yield new Order.Placed(draft.id(), placed.items(), placed.placedAt());
        }
        case OrderEvent.OrderShipped shipped -> {
            if (!(state instanceof Order.Placed placed)) {
                throw corrupt(state, event);
            }
            yield new Order.Shipped(placed.id(), placed.items(), placed.placedAt(),
                    shipped.shippedAt(), shipped.trackingNumber());
        }
    };
}

/** 3. The initial state. */
static Order initialState(OrderId id) {
    return new Order.Draft(id, List.of());
}

private static IllegalStateException corrupt(Order state, OrderEvent event) {
    return new IllegalStateException("Corrupt order history: %s cannot follow %s".formatted(
            event.getClass().getSimpleName(), state.getClass().getSimpleName()));
}
```
