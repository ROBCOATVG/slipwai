```typescript
it('sets retry limit', () => {
  worker.setRetryLimit(3);
  expect(worker.getRetryLimit()).toBe(3); // Trivial
});
```
