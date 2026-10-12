```typescript
// packages/gifting/hexagon/domain/src/pledge-rules.test.ts
describe('recordPledge', () => {
  it('adds the exact amount and records what happened', () => {
    const occasion = getTestOccasion({ totalPledged: createMoney(5_000, 'GBP') });

    const result = recordPledge(occasion, {
      id: createPledgeId('pledge-1'),
      contributorId: createContributorId('contributor-1'),
      amount: createMoney(3_000, 'GBP'),
    });

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.occasion.totalPledged).toEqual(createMoney(8_000, 'GBP'));
      expect(result.events).toEqual([expect.objectContaining({
        type: 'PledgeRecorded',
        amount: createMoney(3_000, 'GBP'),
      })]);
    }
  });
});
```
