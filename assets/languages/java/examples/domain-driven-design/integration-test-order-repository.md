```java
/**
 * The repository against a real database, and nothing above it. Named `*IT`, so Surefire never picks it up
 * and `make verify` stays runnable with nothing installed.
 */
@QuarkusTest
class JdbcOrderRepositoryIT {

    @Inject
    DataSource dataSource;

    @Test
    void persistsAndRetrievesAnOrder() {
        OrderRepository orders = new JdbcOrderRepository(dataSource);
        Order order = anOrder().build();

        orders.save(order);

        // Round-tripped, not just written: an adapter that saves correctly and reads back wrongly passes
        // a save-only test.
        assertThat(orders.findById(order.id())).contains(order);
    }
}
```
