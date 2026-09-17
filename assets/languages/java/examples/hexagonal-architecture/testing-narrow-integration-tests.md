```java
/**
 * A narrow integration test: one adapter, against the real thing it adapts, and nothing above it.
 *
 * <p>Named `*IT`, so `make verify` never compiles a database into the gate — Failsafe runs these and
 * Surefire does not.
 */
@QuarkusTest
class JdbcOrderRepositoryIT {

    @Inject
    DataSource dataSource;

    @Test
    void roundTripsAnOrderThroughPersistence() {
        OrderRepository orders = new JdbcOrderRepository(dataSource);
        Order order = anOrder().build();

        orders.save(order);

        assertThat(orders.findById(order.id())).contains(order);
    }
}

/**
 * The same shape for an HTTP provider: a real client against a stub server, so the adapter's parsing and
 * error translation are exercised without depending on somebody else's uptime.
 */
@QuarkusTest
class StripePaymentGatewayIT {

    @Test
    void reportsASuccessfulCharge() {
        stubFor(post("/v1/charges").willReturn(okJson("{\"id\":\"ch_123\",\"status\":\"succeeded\"}")));
        PaymentGateway gateway = new StripePaymentGateway(stubUrl(), "sk_test");

        PaymentGateway.PaymentOutcome outcome = gateway.completePayment(paymentId, paymentInfo);

        assertThat(outcome).isEqualTo(new PaymentGateway.PaymentOutcome.Paid(new ChargeId("ch_123")));
    }
}
```
