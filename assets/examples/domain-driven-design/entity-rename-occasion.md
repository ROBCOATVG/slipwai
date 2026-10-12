```typescript
type Occasion = {
  readonly id: OccasionId;
  readonly name: string;
  readonly giftIdeas: ReadonlyArray<GiftIdea>;
  readonly budget: Money;
  readonly totalPledged: Money;
  readonly isFundingClosed: boolean;
};

// Immutable update — returns new valid state
const renameOccasion = (occasion: Occasion, newName: string): Occasion => ({
  ...occasion,
  name: newName,
});
```
