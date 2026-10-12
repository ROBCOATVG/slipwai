```typescript
const getTestOccasion = (overrides?: Partial<Occasion>): Occasion =>
  OccasionSchema.parse({
    id: createOccasionId('occasion-1'),
    name: "Mum's Birthday",
    giftIdeas: [],
    budget: createMoney(10_000, 'GBP'),
    totalPledged: createMoney(0, 'GBP'),
    isFundingClosed: false,
    ...overrides,
  });
```
