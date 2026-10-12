```typescript
// External API returns their model
type StripeCharge = {
  readonly id: string;
  readonly amount: number;        // integer minor units in Stripe's contract
  readonly currency: string;      // lowercase
  readonly status: string;
};

// Your domain model
type PaymentResult =
  | { readonly success: true; readonly chargeId: ChargeId; readonly amount: Money }
  | { readonly success: false; readonly reason: string };

// ACL: translate at the boundary — adapter implements this
const toPaymentResult = (charge: StripeCharge): PaymentResult => {
  if (charge.status === 'succeeded') {
    return {
      success: true,
      chargeId: createChargeId(charge.id),
      amount: createMoney(charge.amount, parseCurrency(charge.currency)),
    };
  }
  return { success: false, reason: `Payment failed: ${charge.status}` };
};
```
