```typescript
describe('validate payment', () => {
  it('should reject negative amounts', () => {
    const payment = getMockPayment({ amountMinorUnits: -100, currency: 'GBP' });
    expect(validate(payment).success).toBe(false);
  });

  it('should reject amounts over limit', () => {
    const payment = getMockPayment({ amountMinorUnits: 1_500_000, currency: 'GBP' });
    expect(validate(payment).success).toBe(false);
  });

  it('should reject invalid CVV', () => {
    const payment = getMockPayment({ cvv: '12' });
    expect(validate(payment).success).toBe(false);
  });

  it('should accept valid payments', () => {
    const payment = getMockPayment();
    expect(validate(payment).success).toBe(true);
  });
});
```
