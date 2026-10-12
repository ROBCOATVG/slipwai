```typescript
// ❌ Testing HOW (implementation detail)
it('should call validateAmount', () => {
  const spy = vi.spyOn(validator, 'validateAmount');
  processPayment(payment);
  expect(spy).toHaveBeenCalled(); // Tests HOW, not WHAT
});

// ❌ Testing private methods
it('should validate CVV format', () => {
  const result = validator._validateCVV('123'); // Private method!
  expect(result).toBe(true);
});

// ❌ Testing internal state
it('should set isValidated flag', () => {
  processPayment(payment);
  expect(processor.isValidated).toBe(true); // Internal state
});
```
