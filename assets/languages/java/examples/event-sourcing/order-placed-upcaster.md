```java
/** Version 1, as it still sits on disk. Kept forever: the log cannot be edited. */
record OrderPlacedV1(String orderId, long totalMinorUnits, Currency currency) { }

/** Version 2, the shape the domain uses today — the total became one value object. */
record OrderPlacedV2(String orderId, Money totalAmount) { }

static OrderPlacedV2 upcast(OrderPlacedV1 stored) {
    return new OrderPlacedV2(
            stored.orderId(), new Money(stored.totalMinorUnits(), stored.currency()));
}

/**
 * On read: dispatch on the stored version and upcast forward to the current shape.
 *
 * <p>A sealed interface over the persisted versions is what keeps this exhaustive — add a V3 and this
 * switch stops compiling until it is handled, which is the point. The alternative, a default branch, is
 * where a forgotten version silently becomes a runtime cast failure.
 */
sealed interface StoredOrderPlaced {
    record V1(OrderPlacedV1 data) implements StoredOrderPlaced { }

    record V2(OrderPlacedV2 data) implements StoredOrderPlaced { }
}

static OrderPlacedV2 toCurrent(StoredOrderPlaced stored) {
    return switch (stored) {
        case StoredOrderPlaced.V1 v1 -> upcast(v1.data());
        case StoredOrderPlaced.V2 v2 -> v2.data();
    };
}
```
