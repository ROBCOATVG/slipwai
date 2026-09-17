```typescript
describe('pledgeContribution', () => {
  it('rejects pledge when the contributor is ineligible', () => {
    const occasion = getTestOccasion();
    const eligibility = getTestContributorEligibility({ mayPledge: false });
    const result = pledgeContribution(occasion, eligibility, {
      id: createPledgeId('pledge-1'),
      amount: createMoney(5_000, 'GBP'),
    });
    expect(result.success).toBe(false);
  });
});
```
