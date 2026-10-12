```typescript
describe('place order', () => {
  it('saves order and charges payment on success', async () => {
    const orderRepo = createFakeOrderRepo();
    const paymentGateway = createFakePaymentGateway({ alwaysSucceeds: true });
    const orderPlacement = createOrderPlacement(orderRepo, paymentGateway);

    const result = await orderPlacement.placeOrder(testOrder);

    expect(result.success).toBe(true);
    expect(orderRepo.savedEntities).toHaveLength(1);
  });

  it('does not save order when payment fails', async () => {
    const orderRepo = createFakeOrderRepo();
    const paymentGateway = createFakePaymentGateway({ alwaysFails: true });
    const orderPlacement = createOrderPlacement(orderRepo, paymentGateway);

    const result = await orderPlacement.placeOrder(testOrder);

    expect(result.success).toBe(false);
    expect(orderRepo.savedEntities).toHaveLength(0);
  });
});
```
