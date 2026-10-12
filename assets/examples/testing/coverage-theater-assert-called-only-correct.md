```typescript
it('should process payment and return transaction ID', () => {
  const payment = getMockPayment();
  const result = handlePayment(payment);
  expect(result).toEqual({ success: true, data: { transactionId: expect.any(String) } });
});
```
