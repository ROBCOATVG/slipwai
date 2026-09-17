```typescript
// Specification: "can this eligible contributor pledge to this occasion?"
const canPledge = (occasion: Occasion, eligibility: ContributorEligibility, amount: Money): boolean => {
  const values = [amount.minorUnits, occasion.totalPledged.minorUnits, occasion.budget.minorUnits];
  if (!values.every(Number.isSafeInteger)) return false;
  if (occasion.totalPledged.minorUnits > occasion.budget.minorUnits) return false;
  return eligibility.mayPledge &&
    !occasion.isFundingClosed &&
    amount.minorUnits > 0 &&
    amount.currency === occasion.totalPledged.currency &&
    occasion.totalPledged.currency === occasion.budget.currency &&
    amount.minorUnits <= occasion.budget.minorUnits - occasion.totalPledged.minorUnits;
};

// Compose specifications for complex eligibility
const isGiftReady = (occasion: Occasion): boolean =>
  occasion.totalPledged.minorUnits >= occasion.budget.minorUnits &&
  occasion.giftIdeas.some(idea => idea.status === 'selected');
```
