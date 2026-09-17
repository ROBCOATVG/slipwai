```java
// Names the pattern and the type mechanism, which tells a reader nothing they could not already see.
interface IPaymentPort {
    ChargeResult charge(Money amount, PaymentInfo info);
}

final class PaymentGatewayImpl implements IPaymentPort { }

final class PlaceOrderUseCase { }

// Names the role, and the concrete thing behind it.
interface PaymentGateway {
    ChargeResult charge(Money amount, PaymentInfo info);
}

final class StripePaymentGateway implements PaymentGateway { }

final class OrderPlacement implements ForPlacingOrders { }
```
