```java
// WRONG — the use case builds its own dependencies, so it can only ever run against the real ones.
final class OrderPlacement {

    OrderResult placeOrder(PlaceOrderCommand command) {
        OrderRepository orders = new JdbcOrderRepository(Databases.production());   // hard-coded
        PaymentGateway payments = new StripePaymentGateway(System.getenv("STRIPE_KEY"));
    }
}

// RIGHT — the dependencies arrive through the constructor, so a test supplies fakes and production
// supplies adapters. Note what the use case orchestrates and what it refuses to decide: the rules are
// the domain's, the retries and the conflict handling are the coordination this class owns.
final class OrderPlacement implements ForPlacingOrders {

    private final OrderRepository orders;
    private final PaymentGateway payments;

    OrderPlacement(OrderRepository orders, PaymentGateway payments) {
        this.orders = orders;
        this.payments = payments;
    }

    @Override
    public OrderResult placeOrder(PlaceOrderCommand command) {
        Order pending = orders.findOrCreatePending(command);
        if (pending.status() == OrderStatus.PAID) {
            return OrderResult.placed(pending);   // already done: a retry must not charge twice
        }

        Order payable = pending.paymentId().isPresent() ? pending : prepare(pending);
        PaymentId paymentId = payable.paymentId()
                .orElseThrow(() -> new IllegalStateException("no payment to complete"));

        return switch (payments.completePayment(paymentId, payable.paymentInfo())) {
            case PaymentGateway.PaymentOutcome.Pending pendingPayment ->
                    OrderResult.refused("payment-pending");
            case PaymentGateway.PaymentOutcome.Declined declined ->
                    OrderResult.refused(declined.reason().name());
            case PaymentGateway.PaymentOutcome.Paid paid -> record(payable, paid.chargeId());
        };
    }

    /** A conflict means somebody else moved the order: re-read before deciding it failed. */
    private OrderResult record(Order payable, ChargeId chargeId) {
        if (orders.recordCharge(payable.id(), chargeId, payable.version())
                == OrderRepository.Recorded.YES) {
            return OrderResult.placed(orders.findById(payable.id()).orElseThrow());
        }
        Optional<Order> current = orders.findById(payable.id());
        boolean alreadyOurs = current
                .filter(order -> order.status() == OrderStatus.PAID)
                .flatMap(Order::chargeId)
                .filter(chargeId::equals)
                .isPresent();
        return alreadyOurs
                ? OrderResult.placed(current.orElseThrow())
                : OrderResult.refused("concurrent-change");
    }
}
```
