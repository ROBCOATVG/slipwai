```typescript
// ❌ WRONG — cramming an external eligibility policy into one entity
const addContribution = (occasion: Occasion, contribution: Contribution): Occasion => {
  // This cannot know whether the contributor is currently eligible.
};

// ✅ CORRECT — pure domain service consumes a read-only policy fact
const pledgeContribution = (
  occasion: Occasion,
  eligibility: ContributorEligibility,
  pledge: { readonly id: PledgeId; readonly amount: Money },
): PledgeDecision => {
  if (!eligibility.mayPledge) {
    return { success: false, reason: 'contributor-ineligible' };
  }
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
  return {
    success: true,
    occasion: { ...occasion, totalPledged: createMoney(totalPledged, pledge.amount.currency) },
    events: [{
      type: 'PledgeRecorded',
      id: pledge.id,
      occasionId: occasion.id,
      contributorId: eligibility.contributorId,
      amount: pledge.amount,
    }],
  };
};
```
