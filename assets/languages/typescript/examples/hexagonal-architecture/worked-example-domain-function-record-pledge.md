```typescript
// packages/gifting/hexagon/domain/src/pledge.ts — aggregate operation, pure function
const recordPledge = (
  occasion: Occasion,
  pledge: {
    readonly id: PledgeId;
    readonly contributorId: ContributorId;
    readonly amount: Money;
  },
): PledgeDecision => {
  if (occasion.isFundingClosed) {
    return { success: false, reason: 'funding-closed' };
  }
  if (
    pledge.amount.currency !== occasion.totalPledged.currency ||
    occasion.totalPledged.currency !== occasion.budget.currency
  ) {
    return { success: false, reason: 'currency-mismatch' };
  }
  const values = [
    occasion.totalPledged.minorUnits,
    occasion.budget.minorUnits,
    pledge.amount.minorUnits,
  ];
  if (!values.every(Number.isSafeInteger)) throw new Error('Invalid Money invariant');
  if (pledge.amount.minorUnits <= 0) {
    return { success: false, reason: 'non-positive-amount' };
  }
  if (occasion.totalPledged.minorUnits > occasion.budget.minorUnits) {
    throw new Error('Invalid Occasion funding invariant');
  }
  if (pledge.amount.minorUnits > occasion.budget.minorUnits - occasion.totalPledged.minorUnits) {
    return { success: false, reason: 'exceeds-budget' };
  }

  const totalPledged = occasion.totalPledged.minorUnits + pledge.amount.minorUnits;
  if (!Number.isSafeInteger(totalPledged)) throw new Error('Money addition overflowed');

  const updatedOccasion = {
    ...occasion,
    totalPledged: createMoney(
      totalPledged,
      occasion.totalPledged.currency,
    ),
  };

  return {
    success: true,
    occasion: updatedOccasion,
    events: [{
      type: 'PledgeRecorded',
      id: pledge.id,
      occasionId: occasion.id,
      contributorId: pledge.contributorId,
      amount: pledge.amount,
    }],
  };
};
```
