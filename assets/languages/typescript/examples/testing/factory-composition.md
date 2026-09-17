```typescript
const getMockItem = (overrides?: Partial<Item>): Item => {
  return ItemSchema.parse({
    id: 'item-1',
    name: 'Test Item',
    weightGrams: 100,
    ...overrides,
  });
};

const getMockOrder = (overrides?: Partial<Order>): Order => {
  return OrderSchema.parse({
    id: 'order-1',
    items: [getMockItem()],      // ✅ Compose factories
    customer: getMockCustomer(),  // ✅ Compose factories
    payment: getMockPayment(),    // ✅ Compose factories
    ...overrides,
  });
};

// Usage - override nested objects
it('calculates total with multiple items', () => {
  const order = getMockOrder({
    items: [
      getMockItem({ weightGrams: 100 }),
      getMockItem({ weightGrams: 200 }),
    ],
  });
  expect(calculateTotalWeightGrams(order)).toBe(300);
});
```
