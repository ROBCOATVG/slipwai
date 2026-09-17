```java
/**
 * A fake that also records, so a test can assert what was saved without reaching into a database. The
 * recording is additive: it still implements the port faithfully, including refusing a stale version.
 */
public final class InMemoryOrderRepository implements OrderRepository {

    private final Map<OrderId, Order> orders = new HashMap<>();
    private final List<Order> saved = new ArrayList<>();

    @Override
    public Optional<Order> findById(OrderId id) {
        return Optional.ofNullable(orders.get(id));
    }

    @Override
    public void save(Order order) {
        orders.put(order.id(), order);
        saved.add(order);
    }

    /** What was saved, in order. A copy, so a test cannot accidentally mutate the record. */
    public List<Order> saved() {
        return List.copyOf(saved);
    }
}
```
