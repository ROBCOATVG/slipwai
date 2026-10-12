```typescript
it('processes payment', () => {
  const spy = vi.spyOn(processor, 'process');
  handlePayment(payment);
  expect(spy).toHaveBeenCalledWith(payment); // So what?
});
```
