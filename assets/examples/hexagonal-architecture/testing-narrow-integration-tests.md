```typescript
// Real database — fresh DB per test, no shared state
describe('DrizzleOrderRepository', () => {
  it('round-trips an order through persistence', async () => {
    const db = await createTestDb();
    const repo = createDrizzleOrderRepository(db);
    await repo.save(testOrder);
    expect(await repo.findById(testOrder.id)).toEqual(testOrder);
  });
});

// Real HTTP via MSW
describe('StripePaymentGateway', () => {
  it('returns success on valid charge', async () => {
    worker.use(http.post('https://api.stripe.com/v1/charges', () =>
      HttpResponse.json({ id: 'ch_123', status: 'succeeded' })
    ));
    const gateway = createStripeGateway('sk_test');
    const result = await gateway.charge(testAmount, testPayment);
    expect(result.success).toBe(true);
  });
});
```
