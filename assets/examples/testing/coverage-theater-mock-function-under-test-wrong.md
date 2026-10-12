```typescript
it('calls validator', () => {
  const spy = vi.spyOn(validator, 'validate');
  validator.validate(payment);
  expect(spy).toHaveBeenCalled(); // Meaningless assertion
});
```
