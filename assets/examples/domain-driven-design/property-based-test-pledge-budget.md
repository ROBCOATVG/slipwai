```typescript
import fc from 'fast-check';

it('a successful pledge never exceeds the occasion budget', () => {
  fc.assert(fc.property(
    fc.integer({ min: 0, max: 10000 }),
    fc.integer({ min: 1, max: 10000 }),
    (alreadyPledged, pledge) => {
      const occasion = getTestOccasion({
        budget: createMoney(10000, 'GBP'),
        totalPledged: createMoney(alreadyPledged, 'GBP'),
      });
      const eligibility = getTestContributorEligibility({ mayPledge: true });
      const result = pledgeContribution(occasion, eligibility, {
        id: createPledgeId('pledge-1'),
        amount: createMoney(pledge, 'GBP'),
      });
      if (result.success) {
        return result.occasion.totalPledged.minorUnits <= result.occasion.budget.minorUnits;
      }
      return true; // rejected pledges are always valid
    },
  ));
});
```
