```typescript
it('should upcast a V1 OrderPlaced into the current shape the domain can fold', () => {
  const v1 = {
    type: 'OrderPlaced', version: 1, orderId: 'o-1', totalMinorUnits: 4_000, currency: 'EUR',
  } as const;

  const current = upcastOrderPlaced(v1);

  expect(current).toEqual({
    type: 'OrderPlaced', version: 2, orderId: 'o-1',
    totalAmount: { minorUnits: 4_000, currency: 'EUR' },
  });
});
```
