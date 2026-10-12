```typescript
// WRONG — creates dependencies internally (untestable, tightly coupled)
const createOrder = async (order: NewOrder) => {
  const repo = new DrizzleOrderRepo(getDb());          // hardcoded
  const gateway = new StripeGateway(process.env.KEY);   // hardcoded
  // ...
};

// RIGHT — dependencies injected into a use case implementation
type RecordPaymentResult =
  | { readonly outcome: 'recorded'; readonly order: Order }
  | { readonly outcome: 'conflict' };

type RecordChargeResult =
  | { readonly outcome: 'recorded'; readonly order: Order }
  | { readonly outcome: 'conflict' };

interface OrderRepository {
  readonly findById: (id: OrderId) => Promise<Order | undefined>;
  readonly findOrCreatePending: (
    order: NewOrder & { readonly id: OrderId },
  ) => Promise<Order>;
  readonly recordPayment: (
    id: OrderId,
    paymentId: PaymentId,
    options: { readonly expectedVersion: number },
  ) => Promise<RecordPaymentResult>;
  readonly recordCharge: (
    id: OrderId,
    chargeId: ChargeId,
    options: { readonly expectedVersion: number },
  ) => Promise<RecordChargeResult>;
}

interface ForPlacingOrders {
  readonly placeOrder: (order: NewOrder & { readonly id: OrderId }) => Promise<OrderResult>;
}

const createOrderPlacement = (
  repo: OrderRepository,
  gateway: PaymentGateway,
): ForPlacingOrders => ({
  placeOrder: async (order) => {
    const pending = await repo.findOrCreatePending(order);
    if (pending.status === 'paid') return { success: true, order: pending };

    let payable = pending;
    if (payable.paymentId === undefined) {
      const prepared = await gateway.preparePayment({
        amount: payable.total,
        reference: payable.id,
        idempotencyKey: payable.id,
      });
      if (!prepared.success) return { success: false, reason: prepared.reason };

      const paymentRecorded = await repo.recordPayment(payable.id, prepared.paymentId, {
        expectedVersion: payable.version,
      });
      if (paymentRecorded.outcome === 'recorded') {
        payable = paymentRecorded.order;
      } else {
        const current = await repo.findById(payable.id);
        if (current?.status === 'paid') return { success: true, order: current };
        if (current?.status !== 'pending' || current.paymentId === undefined) {
          return { success: false, reason: 'concurrent-change' };
        }
        payable = current;
      }
    }

    if (payable.paymentId === undefined) return { success: false, reason: 'concurrent-change' };
    const payment = await gateway.completePayment({
      paymentId: payable.paymentId,
      paymentInfo: payable.payment,
    });
    if (payment.outcome === 'pending') return { success: false, reason: 'payment-pending' };
    if (payment.outcome === 'declined') return { success: false, reason: payment.reason };

    const recorded = await repo.recordCharge(payable.id, payment.chargeId, {
      expectedVersion: payable.version,
    });
    if (recorded.outcome === 'recorded') return { success: true, order: recorded.order };

    const current = await repo.findById(payable.id);
    if (current?.status === 'paid' && current.chargeId === payment.chargeId) {
      return { success: true, order: current };
    }
    return { success: false, reason: 'concurrent-change' };
  },
});
```
