```typescript
// Tests covering validation WITHOUT testing validator directly
describe('processPayment', () => {
  it('should reject negative amounts', () => {
    const payment = getMockPayment({ amountMinorUnits: -100, currency: 'GBP' });
    const result = processPayment(payment);
    expect(result.success).toBe(false);
  });

  it('should reject amounts over 10000', () => {
    const payment = getMockPayment({ amountMinorUnits: 1_500_000, currency: 'GBP' });
    const result = processPayment(payment);
    expect(result.success).toBe(false);
  });

  it('should reject invalid CVV', () => {
    const payment = getMockPayment({ cvv: '12' });
    const result = processPayment(payment);
    expect(result.success).toBe(false);
  });

  it('should process valid payments', () => {
    const payment = getMockPayment({ amountMinorUnits: 10_000, currency: 'GBP', cvv: '123' });
    const result = processPayment(payment);
    expect(result.success).toBe(true);
  });
});

// ✅ Result: validation branches are exercised through the public behavior
```
