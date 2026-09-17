```java
/** Driving port — exposed by the application, called by driving adapters. */
public interface ForPlacingOrders {
    OrderResult placeOrder(PlaceOrderCommand command);
}

/** Driven port — application-owned, because the use case is what consumes it. */
public interface OrderRepository {
    Optional<Order> findById(OrderId id);

    void save(Order order);
}

/** Driven port — the payment provider, in the application's own vocabulary. */
public interface PaymentGateway {

    PreparedPayment preparePayment(PaymentRequest request);

    PaymentOutcome completePayment(PaymentId paymentId, PaymentInfo info);

    record PaymentRequest(Money amount, OrderId reference, OrderId idempotencyKey) { }

    sealed interface PreparedPayment {
        record Prepared(PaymentId paymentId) implements PreparedPayment { }

        record Refused(PaymentFailure reason) implements PreparedPayment { }
    }

    /** Three outcomes, not two: "pending" is a real answer from a card network and must be modelled. */
    sealed interface PaymentOutcome {
        record Paid(ChargeId chargeId) implements PaymentOutcome { }

        record Declined(PaymentFailure reason) implements PaymentOutcome { }

        record Pending() implements PaymentOutcome { }
    }
}

/** Driven port — outbound events. */
public interface OrderEventPublisher {
    void publish(OrderEvent event);
}
```
