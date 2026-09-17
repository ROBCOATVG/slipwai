```java
/**
 * A sealed interface over the lifecycle, so each phase carries exactly the fields that phase has.
 *
 * <p>A single record with nullable `placedAt` and `trackingNumber` would let a draft order carry a tracking
 * number, and every reader would then have to check. Here it cannot be written down.
 */
public sealed interface Order {

    OrderId id();

    List<OrderItem> items();

    record Draft(OrderId id, List<OrderItem> items) implements Order { }

    record Placed(OrderId id, List<OrderItem> items, Instant placedAt) implements Order { }

    record Shipped(
            OrderId id,
            List<OrderItem> items,
            Instant placedAt,
            Instant shippedAt,
            String trackingNumber) implements Order { }
}
```
