```typescript
// ✅ Factory function enforces invariants on creation
const createOccasion = (params: CreateOccasionParams & { readonly id: OccasionId }): Occasion => {
  if (!params.name.trim()) throw new Error('Occasion name is required');
  if (!Number.isSafeInteger(params.budget.minorUnits) || params.budget.minorUnits < 0) {
    throw new Error('Budget minor units must be a non-negative safe integer');
  }
  return OccasionSchema.parse({
    ...params,
    name: params.name.trim(),
    giftIdeas: [],
  });
};

// The application or driving edge creates the ID and passes the typed value in.
// Domain creation validates business invariants without a UUID dependency.

// ✅ State transition enforces invariants — returns result type for business outcomes
type AddGiftIdeaResult =
  | { readonly success: true; readonly occasion: Occasion }
  | { readonly success: false; readonly reason: 'currency-mismatch' | 'exceeds-budget' };

const addGiftIdea = (occasion: Occasion, idea: NewGiftIdea): AddGiftIdeaResult => {
  if (
    idea.estimatedCost.currency !== occasion.budget.currency ||
    occasion.giftIdeas.some(item => item.estimatedCost.currency !== occasion.budget.currency)
  ) {
    return { success: false, reason: 'currency-mismatch' };
  }
  const totalCost = occasion.giftIdeas.reduce((sum, item) => {
    if (
      !Number.isSafeInteger(sum) ||
      !Number.isSafeInteger(item.estimatedCost.minorUnits) ||
      item.estimatedCost.minorUnits < 0
    ) {
      throw new Error('Invalid Money invariant');
    }
    const next = sum + item.estimatedCost.minorUnits;
    if (!Number.isSafeInteger(next)) throw new Error('Money addition overflowed');
    return next;
  }, 0);
  if (!Number.isSafeInteger(idea.estimatedCost.minorUnits) || idea.estimatedCost.minorUnits < 0) {
    throw new Error('Invalid Money invariant');
  }
  if (totalCost > occasion.budget.minorUnits) throw new Error('Invalid Occasion budget invariant');
  if (idea.estimatedCost.minorUnits > occasion.budget.minorUnits - totalCost) {
    return { success: false, reason: 'exceeds-budget' };
  }
  return { success: true, occasion: { ...occasion, giftIdeas: [...occasion.giftIdeas, idea] } };
};
```
