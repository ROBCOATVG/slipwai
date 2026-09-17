```typescript
it('should reject negative amounts', () => {
  const payment = getMockPayment({ amountMinorUnits: -100, currency: 'GBP' });
  const result = processPayment(payment);
  expect(result).toEqual({ success: false, error: expect.stringContaining('Amount must be positive') });
});

it('should reject invalid CVV', () => {
  const payment = getMockPayment({ cvv: '12' }); // Only 2 digits
  const result = processPayment(payment);
  expect(result).toEqual({ success: false, error: expect.stringContaining('Invalid CVV') });
});

it('should process valid payments', () => {
  const payment = getMockPayment({ amountMinorUnits: 10_000, currency: 'GBP', cvv: '123' });
  const result = processPayment(payment);
  expect(result).toEqual({ success: true, data: { transactionId: expect.any(String) } });
});
```
