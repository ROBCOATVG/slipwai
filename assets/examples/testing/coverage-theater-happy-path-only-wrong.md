```typescript
it('validates payment', () => {
  const result = validate(getMockPayment());
  expect(result.success).toBe(true); // Only happy path!
});
// Missing: negative amounts, invalid CVV, missing fields, etc.
```
