```typescript
// ❌ Names the pattern or type mechanism
interface IPaymentPort {
  readonly charge: (amount: Money, paymentInfo: PaymentInfo) => Promise<ChargeResult>;
}
const createPaymentGatewayImpl = (): IPaymentPort => ...
const placeOrderUseCase = async (...) => ...

// ✅ Names the role and the concrete adapter
interface PaymentGateway {
  readonly charge: (amount: Money, paymentInfo: PaymentInfo) => Promise<ChargeResult>;
}
const createStripePaymentGateway = (): PaymentGateway => ...
const placeOrder = async (...) => ...
```
