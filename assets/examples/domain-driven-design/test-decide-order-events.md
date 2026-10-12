```typescript
it('produces OrderPlaced event when placing a draft order', () => {
  const now = new Date('2026-03-20');
  const state: OrderState = { status: 'draft', items: [testItem] };
  const decision = decide({ type: 'place' }, state, now);
  expect(decision).toEqual({
    accepted: true,
    events: [{ type: 'OrderPlaced', items: [testItem], placedAt: now }],
  });
});

it('rejects placing an already-placed order with a reason', () => {
  const now = new Date('2026-03-20');
  const state: OrderState = { status: 'placed', items: [testItem], placedAt: someDate };
  const decision = decide({ type: 'place' }, state, now);
  expect(decision).toEqual({ accepted: false, reason: 'order-not-draft' });
});
```
