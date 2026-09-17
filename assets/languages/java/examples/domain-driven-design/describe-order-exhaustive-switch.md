```java
/**
 * A switch expression over a sealed type needs no default, and that is the point: add a fourth phase and
 * this stops compiling until it is handled.
 *
 * <p>A `default` branch here would turn that compile error into a silent wrong answer — which is why one
 * should never be added to a switch over a sealed hierarchy just to satisfy a linter.
 */
static String describe(Order order) {
    return switch (order) {
        case Order.Draft draft -> "Draft with %d items".formatted(draft.items().size());
        case Order.Placed placed -> "Placed at " + placed.placedAt();
        case Order.Shipped shipped -> "Shipped: " + shipped.trackingNumber();
    };
}
```
