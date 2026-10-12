```typescript
// ✅ Behavioral — tests a business rule
it('event with a past date is considered past', () => {
  const now = new Date('2026-03-20T12:00:00.000Z');
  expect(isPastEvent(new Date('2026-03-19T12:00:00.000Z'), now)).toBe(true);
  expect(isPastEvent(new Date('2026-03-21T12:00:00.000Z'), now)).toBe(false);
});

// ✅ Behavioral — tests a business calculation
it('committed total includes only non-idea items', () => {
  const items = [
    getTestItem({ status: 'committed', pricePence: 5000 }),
    getTestItem({ status: 'idea', pricePence: 3000 }),
  ];
  expect(calculateCommittedTotal(items)).toBe(5000);
});
```
