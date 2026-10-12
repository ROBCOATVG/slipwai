```typescript
// Driving port — exposed by the application, called by driving adapters
interface ForPlacingOrders {
  readonly placeOrder: (command: PlaceOrderCommand) => Promise<PlaceOrderResult>;
}

// Driven port — application-owned because the use case consumes it
interface UserRepository {
  readonly findById: (id: UserId) => Promise<User | undefined>;
  readonly save: (user: User) => Promise<void>;
}

type PreparePaymentResult =
  | { readonly success: true; readonly paymentId: PaymentId }
  | { readonly success: false; readonly reason: PaymentFailure };

type PaymentOutcome =
  | { readonly outcome: 'paid'; readonly chargeId: ChargeId }
  | { readonly outcome: 'declined'; readonly reason: PaymentFailure }
  | { readonly outcome: 'pending' };

// Driven port — application-owned because the use case consumes it
interface PaymentGateway {
  readonly preparePayment: (request: {
    readonly amount: Money;
    readonly reference: OrderId;
    readonly idempotencyKey: OrderId;
  }) => Promise<PreparePaymentResult>;
  readonly completePayment: (request: {
    readonly paymentId: PaymentId;
    readonly paymentInfo: PaymentInfo;
  }) => Promise<PaymentOutcome>;
}

// Driven port — event publishing (outbound to message brokers)
interface OrderEventPublisher {
  readonly publish: (event: OrderEvent) => Promise<void>;
}
```
