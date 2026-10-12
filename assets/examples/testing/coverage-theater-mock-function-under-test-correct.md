```typescript
it('should reject invalid payment', () => {
  const payment = getMockPayment({ amountMinorUnits: -100, currency: 'GBP' });
  const result = validate(payment);
  expect(result).toEqual({ success: false, error: expect.stringContaining('Amount must be positive') });
});
```
