```typescript
it('should calculate shipment weight', () => {
  const order = createOrder({ items: [item1, item2] });
  expect(order.calculateWeightGrams()).toBe(230);
});
```
