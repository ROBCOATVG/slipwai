```typescript
// Repository against real database — fresh DB per test
describe('DrizzleOrderRepository', () => {
  it('persists and retrieves an order', async () => {
    const db = await createTestDb();
    const repo = createDrizzleOrderRepository(db);
    await repo.save(testOrder);
    const found = await repo.findById(testOrder.id);
    expect(found).toEqual(testOrder);
  });
});
```
